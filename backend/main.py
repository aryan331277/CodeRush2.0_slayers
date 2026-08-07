from fastapi import FastAPI, WebSocket
import uvicorn
import asyncio
from pydantic import BaseModel

from database import init_db, get_connection
from supervisor import SupervisorAgent

app = FastAPI(title="Intelibot Scribe Backend")

# Initialize database on startup
@app.on_event("startup")
def startup_event():
    init_db()

class ExecuteRequest(BaseModel):
    project_id: str
    user_id: str
    code: str
    config: dict
    label: str = "baseline"
    architecture_change: bool = False

@app.post("/api/execute")
async def execute_code(req: ExecuteRequest):
    agent = SupervisorAgent(req.project_id, req.user_id)
    result = agent.execute_and_evaluate(
        code=req.code,
        config=req.config,
        label=req.label,
        architecture_change=req.architecture_change
    )
    return {"status": "success", "data": result}

@app.websocket("/api/ws/trace/{project_id}")
async def trace_websocket(websocket: WebSocket, project_id: str):
    await websocket.accept()
    conn = get_connection()
    c = conn.cursor()
    last_id = 0
    
    try:
        while True:
            # Poll for new audit logs
            c.execute("SELECT id, stage, event, actor, severity, detail FROM audit_logs WHERE project_id = ? AND id > ? ORDER BY id ASC", (project_id, last_id))
            rows = c.fetchall()
            
            for row in rows:
                last_id = row['id']
                await websocket.send_json({
                    "id": row['id'],
                    "stage": row['stage'],
                    "event": row['event'],
                    "actor": row['actor'],
                    "severity": row['severity'],
                    "detail": row['detail']
                })
                
            await asyncio.sleep(1) # Simple polling loop for demonstration
    except Exception as e:
        print(f"WebSocket closed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
