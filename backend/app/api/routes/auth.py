import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.providers.factory import ProviderFactory
from app.core.config import get_saved_config, set_saved_config

router = APIRouter()

@router.get("/config")
async def get_config():
    """
    Returns the configuration status. 
    Frontend will check 'isConfigured' to decide whether to show 
    the Setup page or the Chat page.
    """
    config = get_saved_config()
    return {
        "success": True,
        "isConfigured": config["isConfigured"],
        "provider": config["provider"],
        "model": config["model_name"],
        "hasApiKey": bool(config["api_key"]),
        # 🧠 Added memory payload configurations so the frontend hydrates perfectly on restart
        # 🧠 Defensive lookups checking both case variants so hydration never misses a beat
        "memory_enabled": str(config.get("MEMORY_ENABLED") or config.get("memory_enabled", "false")).lower() == "true",
        "use_separate_memory_provider": str(config.get("USE_SEPARATE_MEMORY_PROVIDER") or config.get("use_separate_memory_provider", "false")).lower() == "true",
        "memory_provider": config.get("MEMORY_PROVIDER") or config.get("memory_provider", ""),
        "memory_model": config.get("MEMORY_MODEL") or config.get("memory_model", ""),
        "has_memory_api_key": bool(config.get("MEMORY_API_KEY") or config.get("memory_api_key")),
        "long_term_memory_enabled": str(config.get("LONG_TERM_MEMORY_ENABLED") or config.get("long_term_memory_enabled", "true")).lower() == "true"
    }

@router.post("/verify-provider")
async def verify_provider(req: dict):
    """
    Logic to test the credentials. 
    If this returns success, your frontend should save them and redirect.
    """
    provider_name = req.get("provider", "").strip()
    api_key = req.get("api_key", "").strip()
    model_name = req.get("model_name", "").strip()
    
    if not api_key:
        config = get_saved_config()
        if config["api_key"]:
            api_key = config["api_key"]
        else:
            return {"success": False, "message": "API Key is required."}
            
    if not provider_name:
        return {"success": False, "message": "Provider is required."}
        
    if not model_name:
        return {"success": False, "message": "Model name is required."}
        
    # Map google-gemini to gemini for compatibility with ProviderFactory registry
    provider_factory_key = "gemini" if provider_name.lower() == "google-gemini" else provider_name
    
    try:
        provider_instance = ProviderFactory.create(provider_factory_key, api_key)
        # Verify by sending a small ping message (max_tokens=5 to save resources/tokens)
        ping_messages = [{"role": "user", "content": "Ping"}]
        await provider_instance.generate_response(model_name, ping_messages, max_tokens=5)
        return {"success": True, "message": "Connection verified."}
    except Exception as e:
        message = str(e)
        if isinstance(e, HTTPException):
            message = e.detail
        return {"success": False, "message": message}

@router.post("/config")
async def save_config(req: dict):
    """
    Saves credentials to .env. 
    Once saved, isConfigured will become True on the next /config call.
    """
    provider = req.get("provider", "").strip()
    model_name = req.get("model_name", "").strip()
    api_key = req.get("api_key")
    if api_key is not None:
        api_key = api_key.strip()
        
    if not provider or not model_name:
        return {"success": False, "message": "Provider and Model name are required."}
        
    try:
        set_saved_config(provider, model_name, api_key)
        return {"success": True, "message": "Credentials saved."}
    except Exception as e:
        return {"success": False, "message": f"Failed to save credentials: {str(e)}"}
