import os
import logging
from e2b_code_interpreter import Sandbox
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

E2B_API_KEY = os.getenv("E2B_API_KEY")

def run_code_in_sandbox(python_code: str, timeout_seconds: int = 900) -> dict:
    """
    Executes Python code in a secure E2B sandbox.
    Network is restricted by default.
    Returns the stdout, stderr, and any error message.
    """
    logger.info("Provisioning E2B Sandbox...")
    try:
        # Create a new disposable sandbox
        # We enforce a timeout for safety and cost control
        sbx = Sandbox.create(
            timeout=timeout_seconds, 
            envs={"KAGGLE_API_TOKEN": os.getenv("KAGGLE_API_TOKEN", "")}
        )
        
        logger.info("Executing code in sandbox...")
        execution = sbx.run_code(python_code)
        
        stdout = "\n".join(execution.logs.stdout)
        stderr = "\n".join(execution.logs.stderr)
        
        # Shut down immediately to save compute
        sbx.kill()
        
        return {
            "success": execution.error is None,
            "stdout": stdout,
            "stderr": stderr,
            "error": getattr(execution.error, 'value', str(execution.error)) if execution.error else None,
            "results": [result.text for result in execution.results]
        }
    except Exception as e:
        logger.error(f"Sandbox execution failed: {e}")
        return {
            "success": False,
            "stdout": "",
            "stderr": "",
            "error": str(e),
            "results": []
        }
