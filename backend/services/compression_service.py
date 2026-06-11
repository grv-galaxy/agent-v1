import asyncio
import json
from utils.memory_utils import count_tokens
from utils.memory_utils import cap_summary_by_tokens

GROUNDING_PROMPT = """
You are given 2-3 versions of a conversation summary (oldest to newest). Produce ONE canonical summary that:
- Keeps the most recent version of any fact that changed
- Removes contradictions between versions
- Preserves ALL unique identifiers, file paths, decisions, and constraints
- Does NOT add any new information
- Output only the final canonical summary, no explanations

Summary versions (oldest first):
{versions}
"""

ANCHORED_COMPRESSION_PROMPT = """
You are a memory manager. Your job is NOT to rewrite the existing summary.
Your job is to EXTEND it with new information from the conversation chunk.

Rules:
1. Preserve every fact, name, path, variable, and decision from the existing summary EXACTLY as written.
2. Only add new information from the conversation chunk below.
3. If new info contradicts an existing fact, update only that line: [UPDATED: old value -> new value]
4. Do NOT paraphrase existing content. Do NOT restructure.

Output format:
--- PRESERVED SUMMARY ---
{existing_summary}

--- NEW ADDITIONS ---
[only new facts, decisions, preferences, constraints from chunk]

--- ENTITIES (new in this chunk) ---
Files/Paths: [list or NONE]
Variables/Functions: [list or NONE]
Decisions made: [list or NONE]
User preferences: [list or NONE]
Errors/Bugs: [list or NONE]
"""

async def compress_chunk(
    chunk_messages: list[dict],
    existing_summary: str,
    provider_instance,
    model_name: str,
    max_summary_tokens: int = 800,
) -> str:
    """
    Takes an isolated chunk of conversation history and blends it into the 
    historical rolling summary ledger without rewriting or degrading prior facts.
    """
    # Initialize prompt state
    prompt = ANCHORED_COMPRESSION_PROMPT.format(
        existing_summary=existing_summary.strip() if existing_summary else "(no prior summary)"
    )
    
    # Format incoming message history chunk into an easily parsed transcript block
    chunk_text = "\n".join(
        f"[{m['role'].upper()}]: {m['content']}" for m in chunk_messages
    )
    
    messages = [
        {"role": "user", "content": f"{prompt}\n\nCONVERSATION CHUNK:\n{chunk_text}"}
    ]
    
    result_tokens = []
    
    # Stream the compression response from the provider
    async for chunk in provider_instance.generate_stream(model_name, messages):
        # FIX: Safely parse chunk dictionary to get the text fragment string
        if isinstance(chunk, dict):
            text_fragment = chunk.get("text", "")
        else:
            text_fragment = ""
            
        if text_fragment:
            result_tokens.append(text_fragment)
            
    new_summary = "".join(result_tokens).strip()
    
    # Cap memory summary length to maintain compact context token footprints
    if count_tokens(new_summary) > max_summary_tokens:
        lines = new_summary.split("\n")
        trimmed = []
        token_count = 0
        
        for line in lines:
            line_cost = count_tokens(line) + 1  # +1 accounts for newline separator character
            if token_count + line_cost > max_summary_tokens:
                trimmed.append("[summary capped at token limit]")
                break
            trimmed.append(line)
            token_count += line_cost
            
        new_summary = "\n".join(trimmed)
    return cap_summary_by_tokens(new_summary, max_summary_tokens)

        
   
async def grounding_pass(
    summary_history: list[str],
    current_summary: str,
    provider_instance,
    model_name: str,
) -> str:
    all_versions = [s for s in summary_history if s] + [current_summary]
    if len(all_versions) < 2:
        return current_summary  # nothing to reconcile

    versions_text = "\n\n---\n\n".join(
        f"Version {i+1}:\n{s}" for i, s in enumerate(all_versions)
    )
    prompt = GROUNDING_PROMPT.format(versions=versions_text)
    messages = [{"role": "user", "content": prompt}]
    
    result_tokens = []
    async for chunk in provider_instance.generate_stream(model_name, messages):
        if isinstance(chunk, dict):
            text_fragment = chunk.get("text", "")
        else:
            text_fragment = ""
            
        if text_fragment:
            result_tokens.append(text_fragment)
            
    return cap_summary_by_tokens("".join(result_tokens).strip())