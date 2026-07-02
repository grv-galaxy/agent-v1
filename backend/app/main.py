from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import api_router
from app.services.memory_trigger import trigger_sync_background, trigger_sync_and_wait

app = FastAPI(title="Agent Backend Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.on_event("startup")
async def on_startup():
    # Fire-and-forget — does not block FastAPI's startup sequence.
    trigger_sync_background()


@app.on_event("shutdown")
async def on_shutdown():
    # Best-effort final flush, bounded so shutdown can't hang.
    await trigger_sync_and_wait(timeout=5.0)