import json
import asyncio
import time  # 🧠 Added for microsecond latency tracking
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Literal, Optional, List
from app.providers.factory import ProviderFactory
from app.core.config import get_saved_config
from app.utils.token import build_payload_within_budget, should_compress, get_chunk_for_compression, cap_summary_by_tokens, count_tokens, is_oversized_message
from app.services.compression import compress_chunk, grounding_pass, process_batch_compression
from app.services.telemetry import dispatch_stats_event  # 🧠 Import our zero-friction dispatcher
from app.utils.raw_ledger import append_ledger, read_and_clear_ledger, count_ledger_files, count_session_tokens
from app.core.chat_prompts import FIRST_TURN_SYSTEM_PROMPT, ONGOING_CONVERSATION_SYSTEM_PROMPT
from app.services import skill_reader
from app.core import skill_prompts

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
    memory_trigger_threshold: Optional[int] = 30
    memory_raw_buffer: Optional[int] = 10
    memory_summary_cap_tokens: Optional[int] = 800
    memory_preset: Optional[str] = "balanced"    #<-- Dynamic Preset UI Settings Fields
    memory_grounding_interval: Optional[int] = 5  #<-- Dynamic Preset UI Settings Fields

async def stream_chat_response(req: ChatRequest):
    # 🧠 Telemetry Hook: Increment active session counter instantly (O(1))
    dispatch_stats_event("session_increment", {})
    
    try:
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

        # Convert Pydantic message structures into standard List[Dict[str, str]]
        raw_messages = [{"role": msg.role, "content": msg.content} for msg in req.messages]

        # 🧠 Defensive recovery: clean/cap incoming summary before injection
        safe_rolling_summary = cap_summary_by_tokens(
            req.rolling_summary or "", 
            max_summary_tokens=req.memory_summary_cap_tokens
        )

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

        base_system_prompt = system_prompt + "\n\n" if system_prompt else ""
        
        # Inject the new formal system prompts
        if safe_rolling_summary:
            raw_buffer_size = req.memory_raw_buffer or 10
            final_system_prompt = base_system_prompt + ONGOING_CONVERSATION_SYSTEM_PROMPT.replace(
                "{rolling_summary}", safe_rolling_summary
            ).replace(
                "{raw_buffer_size}", str(raw_buffer_size)
            )
        else:
            final_system_prompt = base_system_prompt + FIRST_TURN_SYSTEM_PROMPT

        messages_list.insert(0, {"role": "system", "content": final_system_prompt})

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
            env_use_separate = config.get("USE_SEPARATE_MEMORY_PROVIDER") or config.get("use_separate_memory_provider", "")
            env_provider = config.get("MEMORY_PROVIDER") or config.get("memory_provider", "")
            env_api_key = config.get("MEMORY_API_KEY") or config.get("memory_api_key", "")
            env_model = config.get("MEMORY_MODEL") or config.get("memory_model", "")

            if str(env_use_separate).lower() == "true" or env_provider:
                if not memory_provider_name:
                    memory_provider_name = env_provider
                if not memory_api_key_value:
                    memory_api_key_value = env_api_key
                if not memory_model_name:
                    memory_model_name = env_model

        # Fallback to the main chatting provider and model if separate memory credentials are missing or disabled
        if not memory_provider_name or not memory_api_key_value or not memory_model_name:
            memory_provider_name = provider_name
            memory_api_key_value = api_key
            memory_model_name = model_name

        memory_provider_factory_key = "gemini" if memory_provider_name.lower() == "google-gemini" else memory_provider_name
        memory_provider_instance = ProviderFactory.create(memory_provider_factory_key, memory_api_key_value)

        # --- Frontend-driven compression trigger (Reads from Ledger) ---
        next_epoch = (req.compression_epoch or 0) + 1
        compression_task = None
        compression_chunk = None

        if req.use_memory and req.should_compress:
            compression_chunk = await read_and_clear_ledger(req.session_id or "default")
            
            if compression_chunk:
                compression_task = asyncio.create_task(
                    compress_chunk(
                        chunk_messages=compression_chunk,
                        existing_summary=req.rolling_summary or "",
                        provider_instance=memory_provider_instance,
                        model_name=memory_model_name,
                        session_id=req.session_id or "default",
                        compression_epoch=next_epoch,
                        max_summary_tokens=req.memory_summary_cap_tokens or 800,
                    )
                )

        # --- Task A: Stream main response to user ---
        start_time = time.time()  # 🧠 Benchmark metric point start
        completion_text_accum = ""
        
        # -----------------------------------------------------------------------
        # Sliding-window @jsonstart / @jsonstop interceptor
        # Text before a tag streams normally.
        # Text inside a @jsonstart...@jsonstop block is buffered silently;
        # when the closing tag arrives we parse it and emit a tool_status event.
        # -----------------------------------------------------------------------
        OPEN_TAG  = "@jsonstart"
        CLOSE_TAG = "@jsonstop"

        intercept_buffer = ""   # accumulates chars while in interception mode
        pre_tag_buffer   = ""   # accumulates chars when we might be mid-open-tag
        intercepting     = False

        # Extract user query once — used by both tool handlers below
        _user_query = next(
            (m.content for m in reversed(req.messages) if m.role == "user"), ""
        )

        async for chunk in provider_instance.generate_stream(model_name, messages_list):
            text = chunk.get("text", "")
            if not text:
                continue

            completion_text_accum += text

            if intercepting:
                # --- We are inside a @jsonstart block ---
                intercept_buffer += text
                close_idx = intercept_buffer.find(CLOSE_TAG)
                if close_idx != -1:
                    # Everything before @jsonstop is the JSON payload
                    raw_json = intercept_buffer[:close_idx].strip()
                    # Everything after @jsonstop continues as normal text
                    leftover = intercept_buffer[close_idx + len(CLOSE_TAG):]

                    # Parse and emit the tool_status event, then execute the tool
                    try:
                        parsed_tool = json.loads(raw_json)
                        logo        = parsed_tool.get("logo", "Reading")
                        reason      = parsed_tool.get("reason", "")
                        tool_name   = parsed_tool.get("tool", "")
                        skill_name  = parsed_tool.get("skill_name", "")

                        # 1️⃣  Emit tool_status banner to the frontend
                        yield f"data: {json.dumps({'tool_status': {'logo': logo, 'reason': reason, 'tool': tool_name, 'skill_name': skill_name}})}\n\n"

                        # 2️⃣  Execute: read_skill → load file → second grounded LLM call
                        if tool_name == "read_skill" and skill_name:
                            skill_content = await skill_reader.read_skill(skill_name)

                            if skill_content:
                                grounded_msgs = skill_prompts.build_grounded_messages(
                                    skill_name=skill_name,
                                    skill_content=skill_content,
                                    user_query=_user_query,
                                )
                                # Stream the skill-grounded answer as normal chunks
                                async for sk_chunk in provider_instance.generate_stream(
                                    model_name, grounded_msgs
                                ):
                                    sk_text = sk_chunk.get("text", "")
                                    if sk_text:
                                        completion_text_accum += sk_text
                                        yield f"data: {json.dumps({'chunk': sk_text})}\n\n"
                            else:
                                # Skill file missing — tell the user gracefully
                                fallback = (
                                    f"\n> ⚠️ Skill `{skill_name}` not found — "
                                    "proceeding from general knowledge.\n\n"
                                )
                                completion_text_accum += fallback
                                yield f"data: {json.dumps({'chunk': fallback})}\n\n"

                        # 2️⃣  Execute: search_skills → keyword match → inject results
                        elif tool_name == "search_skills":
                            keywords = parsed_tool.get("keywords", [])
                            matches  = skill_reader.search_skills(keywords)
                            if matches:
                                result_text = (
                                    f"\n*Relevant skills found: **{', '.join(matches)}**. "
                                    "Loading the best match now.*\n\n"
                                )
                            else:
                                result_text = (
                                    "\n*No specific skill found for this task — "
                                    "proceeding from general knowledge.*\n\n"
                                )
                            completion_text_accum += result_text
                            yield f"data: {json.dumps({'chunk': result_text})}\n\n"

                    except json.JSONDecodeError:
                        # Malformed JSON — drop it silently (never leak to user)
                        pass

                    intercept_buffer = ""
                    intercepting = False

                    # Stream any text that came after the closing tag
                    if leftover.strip():
                        yield f"data: {json.dumps({'chunk': leftover})}\n\n"
            else:
                # --- Normal streaming mode ---
                # Combine with any partial open-tag we were watching
                candidate = pre_tag_buffer + text
                pre_tag_buffer = ""

                open_idx = candidate.find(OPEN_TAG)
                if open_idx != -1:
                    # Flush text before the tag
                    before = candidate[:open_idx]
                    if before:
                        yield f"data: {json.dumps({'chunk': before})}\n\n"
                    # Switch to interception mode
                    intercept_buffer = candidate[open_idx + len(OPEN_TAG):]
                    intercepting = True
                else:
                    # No open tag found, but the tail might be a partial match
                    # (e.g. text ends with "@json" — hold it back one cycle)
                    safe_len = max(0, len(candidate) - len(OPEN_TAG))
                    safe_text   = candidate[:safe_len]
                    held_back   = candidate[safe_len:]

                    if safe_text:
                        yield f"data: {json.dumps({'chunk': safe_text})}\n\n"
                    pre_tag_buffer = held_back

        # Flush any held-back text that never matched a tag
        if pre_tag_buffer:
            yield f"data: {json.dumps({'chunk': pre_tag_buffer})}\n\n"
                
        # 🧠 Telemetry Hook: Calculate latency & total token footprints post-stream
        latency_ms = (time.time() - start_time) * 1000.0
        prompt_tokens = sum(count_tokens(m["content"]) for m in messages_list)
        completion_tokens = count_tokens(completion_text_accum)
        
        dispatch_stats_event("chat_message", {
            "latency_ms": latency_ms,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens
        })

        # --- Append to Raw Ledger ---
        if req.use_memory:
            user_msg_content = next((m.content for m in reversed(req.messages) if m.role == "user"), "")
            
            await append_ledger(
                session_id=req.session_id or "default",
                user_msg=user_msg_content,
                assistant_msg=completion_text_accum
            )

            # --- Check for Batch Compression ---
            session_tokens = await count_session_tokens(req.session_id or "default")
            if session_tokens >= 5000:
                session_chunk = await read_and_clear_ledger(req.session_id or "default")
                if session_chunk:
                    asyncio.create_task(
                        process_batch_compression(
                            chunk_messages=session_chunk,
                            provider_instance=memory_provider_instance,
                            model_name=memory_model_name,
                            session_id=req.session_id or "default"
                        )
                    )

        # --- After streaming: check if compression finished ---
        if compression_task is not None:
            try:
                # Calculate current base window token size before modification updates
                tokens_before = sum(count_tokens(m["content"]) for m in compression_chunk)
                
                compression_summary = await asyncio.wait_for(compression_task, timeout=30.0)
                new_summary = compression_summary  # Store compression summary to pass to chat
                
                # Every 5th compression: run grounding pass to fix drift
                next_epoch = (req.compression_epoch or 0) + 1
                grounding_applied = False

                # Safe-guarding extraction to prevent division by zero or negative integers
                interval = req.memory_grounding_interval if (req.memory_grounding_interval and req.memory_grounding_interval > 0) else 5

                if next_epoch > 0 and next_epoch % interval == 0:
                    grounding_applied = True
                    summary_history = getattr(req, 'summary_history', []) or []
                    grounded_summary = await grounding_pass(
                        summary_history=summary_history,
                        current_summary=compression_summary,
                        provider_instance=memory_provider_instance,
                        model_name=memory_model_name,
                        session_id=req.session_id or "default",
                        compression_epoch=next_epoch,
                        max_summary_tokens=req.memory_summary_cap_tokens or 800,
                    )
                    new_summary = grounded_summary or compression_summary

                # Calculate metrics for compression efficiencies
                tokens_after = count_tokens(new_summary)
                tokens_saved = max(0, tokens_before - tokens_after)
                
                # 🧠 Telemetry Hook: Dispatch structural metrics data frame to event processing queue
                dispatch_stats_event("compression", {
                    "tokens_before": tokens_before,
                    "tokens_after": tokens_after,
                    "tokens_saved": tokens_saved,
                    "epoch": next_epoch,
                    "grounding_applied": grounding_applied
                })
                
                control_frame = {
                    "control": "memory_compact",
                    "rolling_summary": new_summary,
                    "compression_summary": compression_summary,
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
        print(f"[chat] Stream error: {type(e).__name__}: {error_msg}")
        yield f"data: {json.dumps({'error': error_msg})}\n\n"
        yield "data: [DONE]\n\n"
        
    finally:
        # 🧠 Telemetry Hook: Safely decrement the active connection array counters
        dispatch_stats_event("session_decrement", {})


@router.post("/chat")
async def chat(req: ChatRequest):
    """
    Streams LLM chat response back to the client using Server-Sent Events (SSE).
    """
    return StreamingResponse(
        stream_chat_response(req),
        media_type="text/event-stream"
    )
