import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Literal, Optional, List
from providers.provider_factory import ProviderFactory
from .auth import get_saved_config

router = APIRouter()

class Message(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str

class ChatRequest(BaseModel):
    provider: Optional[str] = ""
    api_key: Optional[str] = ""
    model_name: Optional[str] = ""
    messages: List[Message]
    session_id: Optional[str] = "default"
    use_memory: Optional[bool] = True
    memory_provider: Optional[str] = ""
    memory_model: Optional[str] = ""
    memory_api_key: Optional[str] = ""

async def stream_chat_response(req: ChatRequest):
    provider_name = (req.provider or "").strip()
    api_key = (req.api_key or "").strip()
    model_name = (req.model_name or "").strip()
    
    # Load fallback config from .env if needed
    if not provider_name or not api_key or not model_name:
        config = get_saved_config()
        if not provider_name:
            provider_name = config.get("provider", "")
        if not api_key:
            api_key = config.get("api_key", "")
        if not model_name:
            model_name = config.get("model_name", "")
            
    if not provider_name or not api_key or not model_name:
        error_msg = "LLM settings are not configured. Please complete setup in LLM Config Card."
        yield f"data: {json.dumps({'error': error_msg})}\n\n"
        yield "data: [DONE]\n\n"
        return

    # Map google-gemini to gemini for registry compatibility
    provider_factory_key = "gemini" if provider_name.lower() == "google-gemini" else provider_name

    try:
        # Convert Pydantic message structures into standard List[Dict[str, str]]
        messages_list = [{"role": msg.role, "content": msg.content} for msg in req.messages]
        
        provider_instance = ProviderFactory.create(provider_factory_key, api_key)
        
        async for chunk in provider_instance.generate_stream(model_name, messages_list):
            # The chunk yielded is standard Dict: {"text": "chunk_text", "usage": ...}
            text = chunk.get("text", "")
            if text:
                yield f"data: {json.dumps({'chunk': text})}\n\n"
                
        yield "data: [DONE]\n\n"
    except Exception as e:
        error_msg = str(e)
        # Handle FastAPI's HTTPException details
        if hasattr(e, "detail"):
            error_msg = e.detail
        yield f"data: {json.dumps({'error': error_msg})}\n\n"
        yield "data: [DONE]\n\n"

@router.post("/chat")
async def chat(req: ChatRequest):
    """
    Streams LLM chat response back to the client using Server-Sent Events (SSE).
    """
    return StreamingResponse(
        stream_chat_response(req),
        media_type="text/event-stream"
    )