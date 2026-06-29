import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from dotenv import dotenv_values
from providers.provider_factory import ProviderFactory

router = APIRouter()

def get_env_path():
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")

# Keep these helper functions to read your state
def get_saved_config():
    env_path = get_env_path()
    file_values = dotenv_values(env_path) if os.path.exists(env_path) else {}
    
    # Check if all required fields are present and not empty
    provider = file_values.get("LLM_PROVIDER", "").strip()
    api_key = file_values.get("LLM_API_KEY", "").strip()
    model_name = file_values.get("LLM_MODEL_NAME", "").strip()
    
    return {
        "isConfigured": bool(provider and api_key and model_name),
        "provider": provider,
        "model_name": model_name,
        "api_key": api_key,
        # 🧠 Forward memory keys from .env so auth.py can read them
        "MEMORY_ENABLED": file_values.get("MEMORY_ENABLED", "false").strip(),
        "USE_SEPARATE_MEMORY_PROVIDER": file_values.get("USE_SEPARATE_MEMORY_PROVIDER", "false").strip(),
        "MEMORY_PROVIDER": file_values.get("MEMORY_PROVIDER", "").strip(),
        "MEMORY_MODEL": file_values.get("MEMORY_MODEL", "").strip(),
        "MEMORY_API_KEY": file_values.get("MEMORY_API_KEY", "").strip(),
        "LONG_TERM_MEMORY_ENABLED": file_values.get("LONG_TERM_MEMORY_ENABLED", "true").strip()
    }

def set_saved_config(provider: str, model_name: str, api_key: str = None):
    env_path = get_env_path()
    lines = []
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    
    config_keys = {
        "LLM_PROVIDER": provider,
        "LLM_MODEL_NAME": model_name
    }
    if api_key is not None:
        config_keys["LLM_API_KEY"] = api_key
        
    updated = set()
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            new_lines.append(line)
            continue
        if "=" in stripped:
            parts = stripped.split("=", 1)
            key = parts[0].strip()
            if key in config_keys:
                new_lines.append(f"{key}={config_keys[key]}\n")
                updated.add(key)
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)
            
    for key, val in config_keys.items():
        if key not in updated:
            new_lines.append(f"{key}={val}\n")
            
    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

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