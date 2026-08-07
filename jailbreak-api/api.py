#!/usr/bin/env python3
"""
Jailbreak Detection API
Model: Sentence Embeddings (all-MiniLM-L6-v2) + XGBoost
Optimized for CPU inference, sub-10ms latency per request.
"""

import os
import re
import gc
import time
from typing import List, Optional
from contextlib import asynccontextmanager

import numpy as np
import joblib
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from sentence_transformers import SentenceTransformer

# =============================================================================
# CONFIG
# =============================================================================
MODEL_DIR = os.environ.get("MODEL_DIR", "models")
EMBEDDER_PATH = os.path.join(MODEL_DIR, "sentence_embedder")
XGB_PATH = os.path.join(MODEL_DIR, "embedding_xgboost.joblib")
DEFAULT_THRESHOLD = float(os.environ.get("THRESHOLD", "0.5"))
BATCH_SIZE = int(os.environ.get("BATCH_SIZE", "64"))

# =============================================================================
# PREPROCESSING (must match training exactly)
# =============================================================================
def clean_text(text: str) -> str:
    """Identical to training preprocessing."""
    text = str(text).lower()
    text = re.sub(r'http\S+|www\S+|https\S+', '', text, flags=re.MULTILINE)
    text = re.sub(r'\S+@\S+', '', text)
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)
    text = re.sub(r'[^\w\s\.\,\!\?\-]', ' ', text)
    text = ' '.join(text.split())
    return text

# =============================================================================
# HEURISTIC LAYER (0.01ms — catches obvious attacks instantly)
# =============================================================================
JAILBREAK_PATTERNS = [
    r"ignore (all )?previous instructions",
    r"ignore (all )?above",
    r"do not (follow|obey|comply)",
    r"you are now (?:a|an) ",
    r"pretend to be",
    r"new instruction[s]?",
    r"system prompt",
    r"developer mode",
    r"DAN",
    r"jailbreak",
    r"sudo",
    r"root access",
    r"ignore safety",
    r"ignore your (instructions|rules)",
    r"disregard",
    r"you are (?:in|now in) .{0,20} mode",
    r"simulate",
    r"hypothetically",
    r"for educational purposes",
]

def heuristic_scan(text: str) -> tuple[bool, float, str]:
    """Fast regex layer. Returns (is_jailbreak, confidence, matched_pattern)."""
    t = text.lower()
    for pattern in JAILBREAK_PATTERNS:
        if re.search(pattern, t):
            return True, 0.95, pattern
    return False, 0.0, ""

# =============================================================================
# MODEL LOADER (lifespan context)
# =============================================================================
class ModelContainer:
    def __init__(self):
        self.embedder: Optional[SentenceTransformer] = None
        self.classifier: Optional[object] = None
        self.ready = False

    def load(self):
        print(f"[Loader] Loading embedder from: {EMBEDDER_PATH}")
        if not os.path.exists(EMBEDDER_PATH):
            raise FileNotFoundError(f"Embedder not found at {EMBEDDER_PATH}")
        
        self.embedder = SentenceTransformer(EMBEDDER_PATH, device="cpu")
        print(f"[Loader] Embedder ready. Dim: {self.embedder.get_sentence_embedding_dimension()}")

        print(f"[Loader] Loading classifier from: {XGB_PATH}")
        if not os.path.exists(XGB_PATH):
            raise FileNotFoundError(f"Classifier not found at {XGB_PATH}")
        
        self.classifier = joblib.load(XGB_PATH)
        print(f"[Loader] Classifier ready. Type: {type(self.classifier).__name__}")
        self.ready = True

    def predict(self, texts: List[str]) -> np.ndarray:
        """Batch prediction: clean → embed → classify."""
        cleaned = [clean_text(t) for t in texts]
        embeddings = self.embedder.encode(
            cleaned,
            batch_size=BATCH_SIZE,
            convert_to_numpy=True,
            show_progress_bar=False,
            normalize_embeddings=True,  # cosine similarity normalized
        )
        probs = self.classifier.predict_proba(embeddings)[:, 1]
        return probs

model_container = ModelContainer()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load models on startup, cleanup on shutdown."""
    print("=" * 60)
    print("  Jailbreak Detection API — Embeddings + XGBoost")
    print("=" * 60)
    model_container.load()
    yield
    print("[Shutdown] Cleaning up...")
    model_container.ready = False
    del model_container.embedder
    del model_container.classifier
    gc.collect()

# =============================================================================
# FASTAPI APP
# =============================================================================
app = FastAPI(
    title="Jailbreak Shield API",
    description="Sentence Embeddings + XGBoost for LLM prompt safety",
    version="1.0.0",
    lifespan=lifespan,
)

# =============================================================================
# REQUEST / RESPONSE SCHEMAS
# =============================================================================
class PredictRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=10000, description="User prompt to scan")
    threshold: float = Field(DEFAULT_THRESHOLD, ge=0.0, le=1.0, description="Jailbreak probability threshold")
    use_heuristic: bool = Field(True, description="Enable fast regex pre-filter")

class BatchPredictRequest(BaseModel):
    prompts: List[str] = Field(..., min_length=1, max_length=100, description="List of prompts to scan")
    threshold: float = Field(DEFAULT_THRESHOLD, ge=0.0, le=1.0)
    use_heuristic: bool = Field(True)

class PredictResponse(BaseModel):
    prompt: str
    is_jailbreak: bool
    confidence: float
    layer: str  # 'heuristic' or 'embedding_xgboost'
    matched_pattern: Optional[str] = None
    inference_ms: float

class BatchPredictResponse(BaseModel):
    results: List[PredictResponse]
    total_ms: float

class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    model_type: str
    threshold: float

# =============================================================================
# ENDPOINTS
# =============================================================================
@app.post("/predict", response_model=PredictResponse)
async def predict(req: PredictRequest):
    """
    Scan a single prompt.
    Layer 1: Regex heuristic (instant).
    Layer 2: Embedding + XGBoost (if heuristic misses).
    """
    start = time.perf_counter()

    # Layer 1: Heuristic
    if req.use_heuristic:
        is_jb, conf, pattern = heuristic_scan(req.prompt)
        if is_jb:
            elapsed = (time.perf_counter() - start) * 1000
            return PredictResponse(
                prompt=req.prompt,
                is_jailbreak=True,
                confidence=conf,
                layer="heuristic",
                matched_pattern=pattern,
                inference_ms=round(elapsed, 3),
            )

    # Layer 2: ML
    if not model_container.ready:
        raise HTTPException(status_code=503, detail="Model not loaded yet")

    prob = model_container.predict([req.prompt])[0]
    is_jb = prob >= req.threshold
    elapsed = (time.perf_counter() - start) * 1000

    return PredictResponse(
        prompt=req.prompt,
        is_jailbreak=bool(is_jb),
        confidence=float(prob),
        layer="embedding_xgboost",
        matched_pattern=None,
        inference_ms=round(elapsed, 3),
    )

@app.post("/predict/batch", response_model=BatchPredictResponse)
async def predict_batch(req: BatchPredictRequest):
    """
    Scan multiple prompts in one call (much more efficient).
    """
    start = time.perf_counter()

    if not model_container.ready:
        raise HTTPException(status_code=503, detail="Model not loaded yet")

    results = []
    ml_indices = []
    ml_prompts = []

    # Layer 1: Heuristic pass
    for i, prompt in enumerate(req.prompts):
        if req.use_heuristic:
            is_jb, conf, pattern = heuristic_scan(prompt)
            if is_jb:
                results.append(PredictResponse(
                    prompt=prompt,
                    is_jailbreak=True,
                    confidence=conf,
                    layer="heuristic",
                    matched_pattern=pattern,
                    inference_ms=0.0,
                ))
                continue
        
        # Defer to ML layer
        results.append(None)  # placeholder
        ml_indices.append(i)
        ml_prompts.append(prompt)

    # Layer 2: Batch ML inference
    if ml_prompts:
        probs = model_container.predict(ml_prompts)
        for idx, prob in zip(ml_indices, probs):
            is_jb = prob >= req.threshold
            results[idx] = PredictResponse(
                prompt=req.prompts[idx],
                is_jailbreak=bool(is_jb),
                confidence=float(prob),
                layer="embedding_xgboost",
                matched_pattern=None,
                inference_ms=0.0,  # averaged below
            )

    total_elapsed = (time.perf_counter() - start) * 1000
    per_item_ms = total_elapsed / len(req.prompts) if req.prompts else 0.0

    # Fill averaged latency
    for r in results:
        r.inference_ms = round(per_item_ms, 3)

    return BatchPredictResponse(results=results, total_ms=round(total_elapsed, 3))

@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(
        status="healthy",
        model_loaded=model_container.ready,
        model_type="sentence-transformers + xgboost",
        threshold=DEFAULT_THRESHOLD,
    )

@app.get("/")
async def root():
    return {
        "service": "Jailbreak Shield API",
        "endpoints": ["/predict", "/predict/batch", "/health"],
        "model": "all-MiniLM-L6-v2 + XGBoost",
        "layers": ["heuristic_regex", "embedding_xgboost"],
    }

# =============================================================================
# LOCAL DEV ENTRYPOINT
# =============================================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=False)
