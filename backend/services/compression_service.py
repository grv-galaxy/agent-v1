# backend/services/compression_service.py
import asyncio
import json
import re
from utils.memory_utils import count_tokens
from utils.memory_utils import cap_summary_by_tokens
from utils.fact_storage import trigger_on_demand_save

def extract_json_from_output(output: str, marker: str = "FACTS_JSON:") -> dict:
    """
    Extracts JSON from LLM output after a marker (e.g., "FACTS_JSON:").
    Returns `None` if no valid JSON is found.
    Handles edge cases: empty JSON, trailing text, malformed JSON.
    """
    if not output or marker not in output:
        return None

    # Extract everything after the marker
    json_start = output.find(marker) + len(marker)
    json_str = output[json_start:].strip()

    # Remove trailing non-JSON text (e.g., "---", "SUMMARY:", etc.)
    for trailing in ["---", "SUMMARY:", "HOLISTIC_SUMMARY:", "CANONICAL_FACTS_JSON:"]:
        if trailing in json_str:
            json_str = json_str.split(trailing)[0].strip()

    # Clean up common JSON issues
    json_str = json_str.rstrip(",")
    json_str = re.sub(r'\s+', ' ', json_str).strip()  # Normalize whitespace

    # Try to parse JSON
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        return None

FIRST_EPOCH_PROMPT = """
    You are a conversation analyzer. Given the **first raw conversation chunk**, produce:

    1. A **detailed, coherent summary** of what happened (length should match the complexity of the conversation).
    2. A **JSON object** extracting ALL facts, decisions, preferences, and entities.

    ### Rules:
    - The summary must **capture all critical information** from the chunk. Do NOT artificially limit its length.
    - The JSON must include:
    - `facts`: Array of objects with `fact` (string), `source` ("user" or "assistant"), `type` ("explicit", "question", or "request").
    - `decisions`: Array of strings (e.g., ["User decided to explore London"]).
    - `preferences`: Array of strings (e.g., ["User prefers concise answers"]).
    - `entities`: Object with `Files/Paths`, `Variables/Functions`, `Errors/Bugs` (all arrays or ["NONE"]).

    ### Output Format:
    SUMMARY:
    [Your detailed summary here]

    ---
    FACTS_JSON:
    {{
    "facts": [
        {{"fact": "User asked about London", "source": "user", "type": "question"}},
        {{"fact": "Assistant listed capabilities", "source": "assistant", "type": "explicit"}}
    ],
    "decisions": ["User decided to explore London"],
    "preferences": ["User prefers concise answers"],
    "entities": {{
        "Files/Paths": ["NONE"],
        "Variables/Functions": ["NONE"],
        "Errors/Bugs": ["NONE"]
    }}
    }}
    ---
    CONVERSATION CHUNK:
    {chunk_text}
"""

GROUNDING_PROMPT = """
    You are a grounding expert. Given **ALL previous compression summaries**, produce:

    1. A **holistic, narrative summary** of the entire conversation so far (describe the flow, key events, and current state).
    2. A **canonical JSON** that:
    - Merges ALL facts from all epochs.
    - **Resolves ALL contradictions** (keep the most recent version of any fact).
    - Tracks **repetitions** (count + epochs where each fact appears).
    - Includes **source** and **resolution** for contradictions.

    ### Rules:
    - The holistic summary should **tell the story** of the conversation (e.g., "The user started by asking about X, then explored Y, and finally decided Z").
    - The canonical JSON should be the **single source of truth** for all facts.

    ### Output Format:
    HOLISTIC_SUMMARY:
    [Your narrative summary of the entire conversation here]

    ---
    CANONICAL_FACTS_JSON:
    {{
    "facts": [
        {{
        "fact": "Fact text",
        "source": "user" | "assistant",
        "type": "explicit" | "contradiction_resolved" | "updated",
        "count": 2,
        "epochs": [1, 3],
        "resolution": "Final resolved value" | null
        }}
    ],
    "decisions": ["Decision 1", "Decision 2"],
    "preferences": ["Preference 1"],
    "entities": {{
        "Files/Paths": ["path1", "path2"],
        "Variables/Functions": ["var1"],
        "Errors/Bugs": ["error1"]
    }},
    "metadata": {{
        "total_facts": 10,
        "contradictions_resolved": 2,
        "epochs_merged": [1, 2, 3]
    }}
    }}
    ---
    ALL PREVIOUS SUMMARIES (oldest to newest):
    {all_summaries}
"""

ANCHORED_COMPRESSION_PROMPT = """
    You are a memory manager. Your job is to **rewrite and improve** the existing summary by merging it with new information from the conversation chunk.
    **Do NOT simply append the new chunk to the old summary.** Instead, create a **new, coherent summary** that:
    - Retains ALL critical information from the old summary.
    - Incorporates ALL new information from the chunk.
    - **Resolves any contradictions** between the old summary and new chunk (prioritize the new chunk if there is a conflict).
    - **Removes redundancies** (do not repeat the same fact twice).

    ### Rules:
    - If a fact in the new chunk **contradicts** the old summary, **resolve it in the new summary** and mark it in the JSON as `"type": "contradiction_resolved"`.
    - If a fact is **updated**, mark it in the JSON as `"type": "updated"`.
    - The JSON must only include **new or updated facts** from this chunk.

    ### Output Format:
    SUMMARY:
    [Your new, rewritten, and improved summary here]

    ---
    FACTS_JSON:
    {{
    "new_facts": [
        {{"fact": "New or updated fact text", "source": "user" | "assistant", "type": "explicit" | "contradiction_resolved" | "updated"}}
    ],
    "new_decisions": ["New decision"],
    "new_preferences": ["New preference"],
    "new_entities": {{
        "Files/Paths": ["new_path"],
        "Variables/Functions": ["new_var"],
        "Errors/Bugs": ["new_error"]
    }}
    }}
    ---
    EXISTING SUMMARY:
    {existing_summary}

    NEW CONVERSATION CHUNK:
    {chunk_text}
"""

async def compress_chunk(
    chunk_messages: list[dict],
    existing_summary: str,
    provider_instance,
    model_name: str,
    session_id: str,
    compression_epoch: int,
    max_summary_tokens: int = None,
) -> str:
    """
    - Epoch 1: Uses FIRST_EPOCH_PROMPT (raw chunks → new summary + JSON).
    - Epoch 2+: Uses ANCHORED_COMPRESSION_PROMPT (rewrite old summary + new chunks → improved summary + JSON).
    - Parses and stores JSON facts separately.
    """
    chunk_text = "\n".join(
        f"[{m['role'].upper()}]: {m['content']}" for m in chunk_messages
    )

    # --- Select prompt based on epoch ---
    if compression_epoch == 1:
        prompt = FIRST_EPOCH_PROMPT.format(chunk_text=chunk_text)
    else:
        prompt = ANCHORED_COMPRESSION_PROMPT.format(
            existing_summary=existing_summary,
            chunk_text=chunk_text
        )

    messages = [{"role": "user", "content": prompt}]

    # --- Stream LLM response ---
    result_tokens = []
    async for chunk in provider_instance.generate_stream(model_name, messages):
        if isinstance(chunk, dict):
            result_tokens.append(chunk.get("text", ""))

    new_summary = "".join(result_tokens).strip()

    # --- Parse JSON facts (robustly) ---
    facts = extract_json_from_output(new_summary, "FACTS_JSON:")

    # --- Remove JSON from the summary text (keep it clean) ---
    if facts is not None:
        new_summary = new_summary.split("FACTS_JSON:")[0].strip()

    # --- Save compression pass with separate facts ---
    trigger_on_demand_save(
        session_id=session_id,
        epoch=compression_epoch,
        event_type="compression_pass",
        rolling_summary=new_summary,  # Text summary only
        facts=facts,                   # Structured JSON facts
    )

    return cap_summary_by_tokens(new_summary, max_summary_tokens)

async def grounding_pass(
    summary_history: list[str],
    current_summary: str,
    provider_instance,
    model_name: str,
    session_id: str,
    compression_epoch: int,
    max_summary_tokens: int = None,
) -> str:
    """
    - Takes ALL prior compression summaries.
    - Outputs holistic summary + canonical JSON (resolves all contradictions).
    - Parses and stores JSON facts separately.
    """
    all_versions = [s for s in summary_history if s] + [current_summary]
    if len(all_versions) < 2:
        return current_summary  # Nothing to reconcile

    versions_text = "\n\n---\n\n".join(
        f"Epoch {i+1}:\n{s}" for i, s in enumerate(all_versions)
    )

    prompt = GROUNDING_PROMPT.format(all_summaries=versions_text)
    messages = [{"role": "user", "content": prompt}]

    # --- Stream LLM response ---
    result_tokens = []
    async for chunk in provider_instance.generate_stream(model_name, messages):
        if isinstance(chunk, dict):
            result_tokens.append(chunk.get("text", ""))

    grounded_summary = "".join(result_tokens).strip()

    # --- Parse JSON facts (robustly) ---
    facts = extract_json_from_output(grounded_summary, "CANONICAL_FACTS_JSON:")

    # --- Remove JSON from the summary text (keep it clean) ---
    if facts is not None:
        grounded_summary = grounded_summary.split("CANONICAL_FACTS_JSON:")[0].strip()

    # --- Save grounding pass with separate facts ---
    trigger_on_demand_save(
        session_id=session_id,
        epoch=compression_epoch,
        event_type="grounding_pass",
        rolling_summary=grounded_summary,  # Text summary only
        facts=facts,                        # Structured JSON facts
    )

    return cap_summary_by_tokens(grounded_summary, max_summary_tokens)