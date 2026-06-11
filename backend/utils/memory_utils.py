import asyncio
import tiktoken
from typing import List, Dict, Any, Tuple

def get_encoder():
    """
    Retrieves the tiktoken tokenizer. Uses gpt-4o token tracking schemas,
    falling back to standard cl100k_base if offline.
    """
    try:
        return tiktoken.encoding_for_model("gpt-4o")
    except Exception:
        return tiktoken.get_encoding("cl100k_base")

# Initialize the global encoder instance
enc = get_encoder()

def count_tokens(text: str) -> int:
    """
    Encodes the given string and returns its exact token footprint length.
    This is a synchronous CPU-heavy function.
    """
    if not text:
        return 0
    return len(enc.encode(text))


def is_oversized_message(content: str, budget: int, ratio: float = 0.30) -> bool:
    """
    Checks if a single message string consumes an excessive threshold percentage 
    of the absolute total token allowance.
    """
    return count_tokens(content) > (budget * ratio)


def _sync_build_payload_within_budget(
    system_prompt: str,
    rolling_summary: str,
    messages: List[Dict[str, str]],
    model_limit: int,
    output_reserve: int,
) -> Dict[str, Any]:
    """
    Internal synchronous worker function that performs the CPU-heavy token loop.
    Executed in a background thread to prevent blocking the event loop.
    """
    budget = model_limit - output_reserve
    
    # Core system prompts and historical summaries are non-negotiable anchors
    used = count_tokens(system_prompt) + count_tokens(rolling_summary)
    
    if used > budget:
        raise ValueError(f"Summary exceeds budget ({used} tokens). Trigger grounding pass.")
        
    messages_to_send = []
    
    # Iterate through history backwards: freshest messages take precedence
    for msg in reversed(messages):
        content = msg.get("content", "")
        
        # 🧠 Intercept single oversized items before evaluating context limits
        if is_oversized_message(content, budget, ratio=0.30):
            condensed = content[:4000]
            msg = {
                **msg,
                "content": condensed + "\n\n[truncated - oversized message condensed before model call]",
            }
            
        cost = count_tokens(msg.get("content", "")) + 4
        
        if used + cost > budget:
            break
            
        messages_to_send.insert(0, msg)
        used += cost
        
    # Hard Floor Constraint: Always retain the last 5 messages for fundamental alignment
    if len(messages_to_send) < 5 and len(messages) >= 5:
        messages_to_send = messages[-5:]
        
    return {
        "messages": messages_to_send,
        "tokens_used": used,
        "tokens_remaining": max(0, budget - used),
        "messages_dropped": len(messages) - len(messages_to_send),
    }


async def build_payload_within_budget(
    system_prompt: str,
    rolling_summary: str,
    messages: List[Dict[str, str]],
    model_limit: int = 128000,
    output_reserve: int = 2000,
) -> Dict[str, Any]:
    """
    Asynchronously assembles a safe conversation message payload.
    Offloads CPU tokenization to a separate thread pool so FastAPI can handle 
    hundreds of other requests concurrently.
    """
    return await asyncio.to_thread(
        _sync_build_payload_within_budget,
        system_prompt,
        rolling_summary,
        messages,
        model_limit,
        output_reserve
    )


def should_compress(messages: List[Any], trigger_threshold: int = 30) -> bool:
    """
    Checks if the conversation list has hit the trigger point (T) to execute compression.
    O(1) list length operation - safe to remain synchronous.
    """
    return len(messages) >= trigger_threshold


def get_chunk_for_compression(messages: List[Any], R: int = 10) -> Tuple[List[Any], List[Any]]:
    """
    Splits the conversation list into two parts: (chunk_to_compress, raw_buffer_to_keep).
    O(1) slicing pointer operation - safe to remain synchronous.
    """
    if len(messages) <= R:
        return [], messages
    return messages[:-R], messages[-R:]


def cap_summary_by_tokens(summary: str, max_summary_tokens: int = 800) -> str:
    """
    Defensively prunes a summary line-by-line if it expands past a safe token allocation threshold.
    """
    if not summary or count_tokens(summary) <= max_summary_tokens:
        return summary

    lines = summary.splitlines()
    kept = []
    used = 0

    for line in lines:
        cost = count_tokens(line) + 1  # +1 accounts for the newline character
        if used + cost > max_summary_tokens:
            kept.append("[summary capped at token limit]")
            break
        kept.append(line)
        used += cost

    return "\n".join(kept)