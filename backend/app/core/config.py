import os
from pathlib import Path
from typing import Dict, Any
from dotenv import dotenv_values

def get_env_path() -> str:
    """Return the absolute path to the .env file in the backend root directory."""
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

def get_saved_config() -> Dict[str, Any]:
    """Read full configuration status from the .env file."""
    env_path = get_env_path()
    file_values = dotenv_values(env_path) if os.path.exists(env_path) else {}
    
    provider = file_values.get("LLM_PROVIDER", "").strip()
    api_key = file_values.get("LLM_API_KEY", "").strip()
    model_name = file_values.get("LLM_MODEL_NAME", "").strip()
    
    return {
        "isConfigured": bool(provider and api_key and model_name),
        "provider": provider,
        "model_name": model_name,
        "api_key": api_key,
        "MEMORY_ENABLED": file_values.get("MEMORY_ENABLED", "false").strip(),
        "USE_SEPARATE_MEMORY_PROVIDER": file_values.get("USE_SEPARATE_MEMORY_PROVIDER", "false").strip(),
        "MEMORY_PROVIDER": file_values.get("MEMORY_PROVIDER", "").strip(),
        "MEMORY_MODEL": file_values.get("MEMORY_MODEL", "").strip(),
        "MEMORY_API_KEY": file_values.get("MEMORY_API_KEY", "").strip(),
        "LONG_TERM_MEMORY_ENABLED": file_values.get("LONG_TERM_MEMORY_ENABLED", "true").strip()
    }

def set_saved_config(provider: str, model_name: str, api_key: str = None) -> None:
    """Write primary provider details back to the .env file."""
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

async def read_memory_config() -> Dict[str, Any]:
    """Read memory-related config from the .env file asynchronously."""
    env_path = Path(get_env_path())
    config = {}
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    config[key.strip()] = value.strip()
    return config

async def write_memory_config(config: Dict[str, Any]) -> None:
    """Write memory-related config to the .env file asynchronously."""
    env_path = Path(get_env_path())
    existing_config = {}
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    existing_config[key.strip()] = value.strip()

    # Update with new config
    existing_config.update(config)

    # Write back
    with open(env_path, "w", encoding="utf-8") as f:
        for key, value in existing_config.items():
            f.write(f"{key}={value}\n")

async def resolve_provider_config(payload: Any) -> Dict[str, Any]:
    """Resolve provider config from a request payload or .env fallbacks."""
    config = await read_memory_config()
    provider = payload.provider or config.get("MEMORY_PROVIDER", config.get("LLM_PROVIDER", ""))
    api_key = payload.api_key or config.get("MEMORY_API_KEY", config.get("LLM_API_KEY", ""))
    model_name = payload.model_name or config.get("MEMORY_MODEL", config.get("LLM_MODEL_NAME", ""))
    return {"provider": provider, "api_key": api_key, "model_name": model_name}
