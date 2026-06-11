import json
import asyncio
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Literal, Optional, List
from providers.provider_factory import ProviderFactory
from .auth import get_saved_config
from utils.memory_utils import build_payload_within_budget, should_compress, get_chunk_for_compression, cap_summary_by_tokens, count_tokens, is_oversized_message
from services.compression_service import compress_chunk, grounding_pass

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
    rolling_summary: Optional[str] = ""   #<-- NEW FIELD FOR ROLLING SUMMARY
    compression_epoch: Optional[int] = 0    # <-- ADDED
    summary_history: Optional[List[str]] = [] # <-- ADDED
    should_compress: Optional[bool] = False   # <-- ADDED FLAG TO EXPLICITLY TRIGGER COMPRESSION
    compression_chunk: Optional[List[Message]] = []  # <-- ADDED FIELD TO PASS PRE-EXTRACTED CHUNK FOR COMPRESSION (AVOIDS DUPLICATE EXTRACTION IN SERVICE LAYER)

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
        raw_messages = [{"role": msg.role, "content": msg.content} for msg in req.messages]

        # 🧠 Defensive recovery: clean/cap incoming summary before injection
        safe_rolling_summary = cap_summary_by_tokens(req.rolling_summary or "")

        # Inject rolling summary if present
        if safe_rolling_summary:
            summary_message = {
                "role": "user",
                "content": f"[CONVERSATION CONTEXT - earlier messages summarized]\n{safe_rolling_summary}"
            } 
            insert_at = 1 if raw_messages and raw_messages[0]["role"] == "system" else 0
            raw_messages.insert(insert_at, summary_message)
            
        # Extract the system prompt to anchor it as a non-negotiable token cost
        system_prompt = next((m["content"] for m in raw_messages if m["role"] == "system"), "")
        
        # Pre-flight token budget check (Offloaded asynchronously to a background thread pool)
        budget_result = await build_payload_within_budget(
            system_prompt=system_prompt,
            rolling_summary=safe_rolling_summary, # 🧠 Using capped summary variation
            messages=[m for m in raw_messages if m["role"] != "system"],
        )
        
        # Extract the safely truncated message history
        messages_list = budget_result["messages"]
        
        # Re-insert system prompt back at index 0 if it was stripped for budget calculations
        if system_prompt:
            messages_list.insert(0, {"role": "system", "content": system_prompt})

        # Log if messages were dropped (useful for production debugging)
        if budget_result["messages_dropped"] > 0:
            print(f"[budget] Trimmed {budget_result['messages_dropped']} messages to comply with token budget limits.")
        
        provider_instance = ProviderFactory.create(provider_factory_key, api_key)     
        #------------------------------------------------------------------------- 

        
        # Load backend configuration for memory env/fallback variables
        config = get_saved_config()
        
        # Resolve separate memory provider details from request incoming payloads
        memory_provider_name = (req.memory_provider or "").strip()
        memory_api_key_value = (req.memory_api_key or "").strip()
        memory_model_name = (req.memory_model or "").strip()
        
        # Check if separate memory fallback configuration exists in the environment settings (.env config fields)
        if not memory_provider_name or not memory_api_key_value or not memory_model_name:
            if str(config.get("use_separate_memory_provider", "")).lower() == "true" or config.get("memory_provider"):
                if not memory_provider_name:
                    memory_provider_name = config.get("memory_provider", "")
                if not memory_api_key_value:
                    memory_api_key_value = config.get("memory_api_key", "")
                if not memory_model_name:
                    memory_model_name = config.get("memory_model", "")

        # Fallback to the main chatting provider and model if separate memory credentials are missing or disabled
        if not memory_provider_name or not memory_api_key_value or not memory_model_name:
            memory_provider_name = provider_name
            memory_api_key_value = api_key
            memory_model_name = model_name

        memory_provider_factory_key = "gemini" if memory_provider_name.lower() == "google-gemini" else memory_provider_name
        memory_provider_instance = ProviderFactory.create(memory_provider_factory_key, memory_api_key_value)

        # --- Frontend-driven compression trigger ---
        visible_messages = [{"role": m.role, "content": m.content} for m in req.messages]
        compression_chunk = [
            {"role": m.role, "content": m.content}
            for m in (req.compression_chunk or [])
        ]

        compression_task = None

        if req.use_memory and req.should_compress and compression_chunk:
            compression_task = asyncio.create_task(
                compress_chunk(
                    chunk_messages=compression_chunk,
                    existing_summary=req.rolling_summary or "",
                    provider_instance=memory_provider_instance,
                    model_name=memory_model_name,
                )
            )

        # --- Task A: Stream main response to user ---
        async for chunk in provider_instance.generate_stream(model_name, messages_list):
            text = chunk.get("text", "")
            if text:
                yield f"data: {json.dumps({'chunk': text})}\n\n"
                
        # --- After streaming: check if compression finished ---
        if compression_task is not None:
            try:
                new_summary = await asyncio.wait_for(compression_task, timeout=30.0)
                
                # Every 5th compression: run grounding pass to fix drift
                next_epoch = (req.compression_epoch or 0) + 1
                if next_epoch > 0 and next_epoch % 5 == 0:
                    summary_history = getattr(req, 'summary_history', []) or []
                    new_summary = await grounding_pass(
                        summary_history=summary_history,
                        current_summary=new_summary,
                        provider_instance=memory_provider_instance,
                        model_name=memory_model_name,
                    )
                
                control_frame = {
                    "control": "memory_compact",
                    "rolling_summary": new_summary,
                    "truncated_count": len(compression_chunk),
                    "compression_epoch": next_epoch,
                }
                yield f"data: {json.dumps(control_frame)}\n\n"
            
            except asyncio.TimeoutError:
                print("[compression] Timeout reached; skipping sync frame injection.")
            except Exception as e:
                print(f"[compression] Failed safely: {e}")
                
            yield "data: [DONE]\n\n"
    except Exception as e:
        error_msg = str(e)
        # Log the real error for debugging
        print(f"[chat] Stream error: {type(e).__name__}: {error_msg}")
        # Send error to frontend as SSE event
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