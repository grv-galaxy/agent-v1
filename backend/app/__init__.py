# Package root — exposes the FastAPI app instance for uvicorn and run_all.py
from app.main import app

__all__ = ["app"]
