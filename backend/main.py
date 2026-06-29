import uvicorn
from app.main import app  # noqa: F401 — re-exported for uvicorn discovery

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)