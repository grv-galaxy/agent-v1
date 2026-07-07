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


import asyncio
from app.core.config import get_saved_config
from app.providers.factory import ProviderFactory
from app.utils.raw_ledger import get_all_ledger_session_ids, count_session_tokens, read_and_clear_ledger
from app.services.compression import process_batch_compression

async def startup_ledger_cleanup_task():
    try:
        session_ids = await get_all_ledger_session_ids()
        if not session_ids:
            return
            
        total_tokens = 0
        for sid in session_ids:
            total_tokens += await count_session_tokens(sid)
            
        if total_tokens >= 5000:
            print(f"[Startup] Total raw ledger tokens ({total_tokens}) >= 5000. Triggering per-session batch compression.")
            
            config = get_saved_config()
            provider_name = config.get("MEMORY_PROVIDER") or config.get("provider") or ""
            api_key = config.get("MEMORY_API_KEY") or config.get("api_key") or ""
            model_name = config.get("MEMORY_MODEL") or config.get("model_name") or ""
            
            if not provider_name or not api_key or not model_name:
                print("[Startup] Missing LLM config. Cannot run batch compression.")
                return
                
            provider_factory_key = "gemini" if provider_name.lower() == "google-gemini" else provider_name
            provider_instance = ProviderFactory.create(provider_factory_key, api_key)
            
            for sid in session_ids:
                chunk = await read_and_clear_ledger(sid)
                if chunk:
                    # process_batch_compression internally calls trigger_sync_background
                    await process_batch_compression(
                        chunk_messages=chunk,
                        provider_instance=provider_instance,
                        model_name=model_name,
                        session_id=sid
                    )
    except Exception as e:
        print(f"[Startup] Failed to run ledger cleanup: {e}")

@app.on_event("startup")
async def on_startup():
    # Fire-and-forget — does not block FastAPI's startup sequence.
    trigger_sync_background()
    asyncio.create_task(startup_ledger_cleanup_task())


@app.on_event("shutdown")
async def on_shutdown():
    # Best-effort final flush, bounded so shutdown can't hang.
    await trigger_sync_and_wait(timeout=5.0)