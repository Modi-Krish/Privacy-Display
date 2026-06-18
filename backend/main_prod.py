import sys
import os
import uvicorn

# Ensure the backend directory is in sys.path
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

from app.main import app

if __name__ == "__main__":
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    print(f"Starting REAI Backend sidecar on {host}:{port}...")
    uvicorn.run(app, host=host, port=port, log_level="info")
