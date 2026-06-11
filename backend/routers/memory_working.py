from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional, Dict, Literal, Any
import os
from pathlib import Path
import asyncio

# Import existing utilities (adjust paths as needed)
from providers.provider_factory import ProviderFactory
from services.compression_service import compress_chunk, grounding_pass
from utils.memory_utils import should_compress, get_chunk_for_compression
from .auth import get_saved_config
# from backend.memory.working_memory import get_memory_stats
# from backend.monitor.backend.monitored_backend_runner import (
#     start_monitor_services,
#     stop_monitor_services,
#     set_forwarding_enabled,
#     is_monitor_running
# )

router = APIRouter()


# --- Pydantic Models ---

class ConfigResponse(BaseModel):
    isConfigured: bool
    provider: Optional[str] = None
    model: Optional[str] = None
    hasApiKey: bool
    memory_enabled: bool
    use_separate_memory_provider: bool
    memory_provider: Optional[str] = None
    memory_model: Optional[str] = None
    has_memory_api_key: bool


class MemoryConfigRequest(BaseModel):
    memory_enabled: bool
    use_separate_provider: bool
    provider: Optional[str] = None
    model_name: Optional[str] = None
    api_key: Optional[str] = None


class VerifyRequest(BaseModel):
    provider: str
    api_key: str
    model_name: str


class CompressRequest(BaseModel):
    messages: List[dict]
    rolling_summary: str = ""
    summary_history: List[str] = []
    compression_epoch: int = 0


class CompressResponse(BaseModel):
    new_summary: str
    truncated_count: int
    grounding_applied: bool


# class MemoryStatsResponse(BaseModel):
#     active_sessions: int
#     total_compressions: int
#     total_messages_compressed: int
#     estimated_tokens_saved: int
#     total_facts_stored: int = 0
#     facts_by_category: Dict[str, int] = {}
#     last_compression_quality: Dict[str, Any] = {}


# class MonitorStatusResponse(BaseModel):
#     is_running: bool


# --- Helper Functions ---

async def get_env_path() -> Path:
    """Return the path to the .env file."""
    return Path(__file__).parent.parent / ".env"


async def read_memory_config() -> Dict[str, Any]:
    """Read memory-related config from .env."""
    env_path = await get_env_path()
    config = {}
    if env_path.exists():
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    config[key.strip()] = value.strip()
    return config


async def write_memory_config(config: Dict[str, Any]) -> None:
    """Write memory-related config to .env."""
    env_path = await get_env_path()
    existing_config = {}
    if env_path.exists():
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    existing_config[key.strip()] = value.strip()

    # Update with new config
    existing_config.update(config)

    # Write back
    with open(env_path, "w") as f:
        for key, value in existing_config.items():
            f.write(f"{key}={value}\n")


async def resolve_provider_config(payload: VerifyRequest) -> Dict[str, Any]:
    """Resolve provider config from payload or .env."""
    config = await read_memory_config()
    provider = payload.provider or config.get("MEMORY_PROVIDER", config.get("LLM_PROVIDER", ""))
    api_key = payload.api_key or config.get("MEMORY_API_KEY", config.get("LLM_API_KEY", ""))
    model_name = payload.model_name or config.get("MEMORY_MODEL", config.get("LLM_MODEL_NAME", ""))
    return {"provider": provider, "api_key": api_key, "model_name": model_name}


# --- Endpoints ---

# @router.get("/config", response_model=ConfigResponse)
# async def get_config():
#     """Return current memory and LLM config from .env."""
#     config = await read_memory_config()
    
#     # Defaults
#     is_configured = bool(config.get("LLM_PROVIDER"))
#     provider = config.get("LLM_PROVIDER")
#     model = config.get("LLM_MODEL_NAME")
#     has_api_key = bool(config.get("LLM_API_KEY"))
    
#     memory_enabled = config.get("MEMORY_ENABLED", "false").lower() == "true"
#     use_separate = config.get("USE_SEPARATE_MEMORY_PROVIDER", "false").lower() == "true"
#     memory_provider = config.get("MEMORY_PROVIDER")
#     memory_model = config.get("MEMORY_MODEL")
#     has_memory_api_key = bool(config.get("MEMORY_API_KEY"))
    
#     return ConfigResponse(
#         isConfigured=is_configured,
#         provider=provider,
#         model=model,
#         hasApiKey=has_api_key,
#         memory_enabled=memory_enabled,
#         use_separate_memory_provider=use_separate,
#         memory_provider=memory_provider,
#         memory_model=memory_model,
#         has_memory_api_key=has_memory_api_key
#     )


@router.post("/memory-config")
async def save_memory_config(payload: MemoryConfigRequest):
    """Save memory settings to .env."""
    if payload.use_separate_provider:
        if not all([payload.provider, payload.model_name]):
            raise HTTPException(
                status_code=400,
                detail="Memory provider, API key, and model name are required when using a separate provider."
            )
    
    # Prepare config to write
    new_config = {
        "MEMORY_ENABLED": str(payload.memory_enabled).lower(),
        "USE_SEPARATE_MEMORY_PROVIDER": str(payload.use_separate_provider).lower(),
    }
    
    if payload.use_separate_provider:
        new_config["MEMORY_PROVIDER"] = payload.provider
        new_config["MEMORY_MODEL"] = payload.model_name
        if payload.api_key:
            new_config["MEMORY_API_KEY"] = payload.api_key
    else:
        new_config["MEMORY_PROVIDER"] = ""
        new_config["MEMORY_MODEL"] = ""
        new_config["MEMORY_API_KEY"] = ""
    
    await write_memory_config(new_config)
    return {"success": True, "message": "Memory config saved successfully."}


# @router.get("/memory-stats", response_model=MemoryStatsResponse)
# async def memory_stats():
#     """Return in-RAM memory stats."""
#     stats = get_memory_stats()
#     return MemoryStatsResponse(**stats)


# @router.post("/verify-provider")
# async def verify_provider(payload: VerifyRequest):
#     """Verify a memory provider's API key/model."""
#     try:
#         resolved_config = await resolve_provider_config(payload)
#         provider_name = resolved_config["provider"]
#         api_key = resolved_config["api_key"]
#         model_name = resolved_config["model_name"]
        
#         if provider_name not in PROVIDER_MODULES:
#             raise ValueError(f"Unsupported provider: {provider_name}")
        
#         provider_module = get_provider_module(provider_name)
#         success, message = provider_module.verify(api_key, model_name)
        
#         return {"success": success, "message": message}
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=str(e))


@router.post("/api/compress", response_model=CompressResponse)
async def compress_endpoint(req: CompressRequest):
    chunk, raw_buffer = get_chunk_for_compression(req.messages, R=10)
    if not chunk:
        return CompressResponse(
            new_summary=req.rolling_summary,
            truncated_count=0,
            grounding_applied=False
        )
    return CompressResponse(
        new_summary=req.rolling_summary,
        truncated_count=len(chunk),
        grounding_applied=False
    )


# @router.get("/monitor-control/status", response_model=MonitorStatusResponse)
# async def monitor_status():
#     """Return monitor service status."""
#     return MonitorStatusResponse(is_running=is_monitor_running())


# @router.post("/monitor-control/start")
# async def monitor_start():
#     """Start monitor services."""
#     await asyncio.to_thread(start_monitor_services)
#     await asyncio.to_thread(set_forwarding_enabled, True)
#     return {"success": True, "message": "Monitor services started."}


# @router.post("/monitor-control/stop")
# async def monitor_stop():
#     """Stop monitor services."""
#     await asyncio.to_thread(set_forwarding_enabled, False)
#     await asyncio.to_thread(stop_monitor_services)
#     return {"success": True, "message": "Monitor services stopped."}