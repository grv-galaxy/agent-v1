# backend/services/compression_service.py
import asyncio
import json
import re
from utils.memory_utils import count_tokens
from utils.memory_utils import cap_summary_by_tokens
from utils.fact_storage import trigger_on_demand_save

def extract_json_from_output(output: str, marker: str = None) -> dict:
    """
    Robustly extracts a JSON object from the LLM output string.
    If a marker is provided, it attempts to find JSON within or after that marker block.
    Handles strict structural raw JSON objects as well as markdown code wrapping.
    """
    if not output:
        return None

    content = output
    if marker and marker in output:
        marker_pos = output.find(marker)
        content = output[marker_pos + len(marker):]

    # Find the outer bounds of the JSON object
    first_brace = content.find("{")
    last_brace = content.rfind("}")
    
    if first_brace == -1 or last_brace == -1 or last_brace <= first_brace:
        print(f"[Warning] Failed to find valid JSON brace limits. Marker used: {marker}")
        return None

    json_str = content[first_brace:last_brace + 1].strip()
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"[Warning] JSON parsing failed: {e}. Raw content length: {len(json_str)}")
        return None

FIRST_EPOCH_PROMPT = """
You are a Conversation Analyzer and State Reduction Engine. 
Given the **first raw conversation chunk**, analyze it and return a single, unified, structurally valid JSON object matching the exact template format below.

### Rules:
- The `summary` key must contain a detailed, coherent narrative summary matching the complexity of the conversation without artificially cutting details.
- Do not add any conversational markdown headers (like SUMMARY: or FACTS_JSON:) or markdown text outside the valid JSON boundaries.

### Expected JSON Output Template:
{{
  "summary": "[Your detailed narrative summary tracking critical context and user intent here]",
  "facts_json": {{
    "facts": [
      {{"fact": "User asked about project specifications", "source": "user", "type": "question"}},
      {{"fact": "Assistant provided architecture guidelines", "source": "assistant", "type": "explicit"}}
    ],
    "decisions": [],
    "preferences": [],
    "entities": {{
      "Files/Paths": ["NONE"],
      "Variables/Functions": ["NONE"],
      "Errors/Bugs": ["NONE"]
    }}
  }}
}}

---
CONVERSATION CHUNK:
{chunk_text}
"""

ANCHORED_COMPRESSION_PROMPT = """
You are a Memory Consolidation Engine.
Your primary objective is to PRESERVE memory, not compress it.
The EXISTING SUMMARY is the authoritative memory state accumulated from previous epochs.
The NEW CONVERSATION CHUNK contains newly observed information.
Your task is to UPDATE the existing memory state while minimizing information loss.

──────────────────────────────────────
CORE PRINCIPLES & RULES
──────────────────────────────────────
- Treat the EXISTING SUMMARY as a persistent memory document. DO NOT rewrite it from scratch.
- Merged details should make the narrative text richer, more complete, and more detailed over time.
- Never remove an existing fact unless the new chunk explicitly contradicts or provides a newer version of that exact fact.
- Only additions and structural modifications belong in the `facts_json` registry block. Do not repeat old facts.

──────────────────────────────────────
FINAL MANDATORY FORMATTING RULE
──────────────────────────────────────
- Your entire response must be a single, structurally valid JSON object matching the exact template below. 
- Do not print "SUMMARY:" or "FACTS_JSON:" as plain text headers outside of the object. 
- Do not wrap the JSON object inside markdown backticks (like ```json).

### Expected JSON Output Template:
{{
  "summary": "[Updated narrative summary document with preserved history and merged new information goes here]",
  "facts_json": {{
    "new_facts": [
      {{
        "fact": "new fact text",
        "source": "user",
        "type": "explicit"
      }}
    ],
    "new_decisions": [],
    "new_preferences": [],
    "new_entities": {{
      "Files/Paths": [],
      "Variables/Functions": [],
      "Errors/Bugs": []
    }}
  }}
}}

---
EXISTING SUMMARY:
{existing_summary}

NEW CONVERSATION CHUNK:
{chunk_text}
"""

GROUNDING_PROMPT = """
You are a Master Memory Reconciliation Anchor and Grounding Expert.
Given **ALL previous compression summaries**, analyze the entire chronological ledger to perform an analytical cleanup pass.

### Objectives:
1. Build a holistic, narrative summary telling the master story timeline of how the conversation progressed.
2. Formulate a single canonical fact registry. Remove contradictions, deduplicate values, and keep the latest verified state.

### Final Output Requirements:
- The entire response must be a single, raw, structurally valid JSON object matching the exact format template below.
- Do not include conversational prefaces or text fields outside the JSON braces.

### Expected JSON Output Template:
{{
  "holistic_summary": "[Your master timeline abstract. Where it started -> how it evolved -> current core state objective]",
  "canonical_facts_json": {{
    "facts": [
      {{
        "fact": "Fact value text description",
        "source": "user",
        "type": "explicit",
        "count": 1,
        "epochs": [1],
        "resolution": null
      }}
    ],
    "decisions": [],
    "preferences": [],
    "entities": {{
      "Files/Paths": [],
      "Variables/Functions": [],
      "Errors/Bugs": []
    }},
    "metadata": {{
      "total_facts": 0,
      "contradictions_resolved": 0,
      "epochs_merged": []
    }}
  }}
}}

---
ALL PREVIOUS SUMMARIES (oldest to newest):
{all_summaries}
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
    - Epoch 1: Uses FIRST_EPOCH_PROMPT (raw chunks -> new summary + JSON).
    - Epoch 2+: Uses ANCHORED_COMPRESSION_PROMPT (rewrite old summary + new chunks -> improved summary + JSON).
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

    raw_response = "".join(result_tokens).strip()

    # --- Parse JSON payloads robustly out of the unified root schema ---
    parsed_payload = extract_json_from_output(raw_response)

    if parsed_payload and isinstance(parsed_payload, dict):
        new_summary = parsed_payload.get("summary", "").strip()
        facts = parsed_payload.get("facts_json", {})
    else:
        # Emergency healing fallback if structure failed
        print("[compression_service] Prompt broken schema layout. Initiating emergency flat text partition fallback.")
        new_summary = raw_response
        facts = None
        if "SUMMARY:" in new_summary:
            new_summary = new_summary.split("SUMMARY:")[-1]
        if "FACTS_JSON:" in new_summary:
            parts = new_summary.split("FACTS_JSON:")
            new_summary = parts[0].strip()
            facts = extract_json_from_output(parts[1])

    # --- Save compression pass with separate facts ---
    trigger_on_demand_save(
        session_id=session_id,
        epoch=compression_epoch,
        event_type="compression_pass",
        rolling_summary=new_summary,  # Text summary only
        facts=facts,                    # Structured JSON facts
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

    raw_response = "".join(result_tokens).strip()

    # --- Parse Master grounding payload object structures ---
    parsed_payload = extract_json_from_output(raw_response)

    if parsed_payload and isinstance(parsed_payload, dict):
        grounded_summary = parsed_payload.get("holistic_summary", "").strip()
        facts = parsed_payload.get("canonical_facts_json", {})
    else:
        # Flat text partition emergency fallback
        print("[grounding_service] Grounding fallback processing triggered.")
        grounded_summary = raw_response
        facts = None
        if "HOLISTIC_SUMMARY:" in grounded_summary:
            grounded_summary = grounded_summary.split("HOLISTIC_SUMMARY:")[-1]
        if "CANONICAL_FACTS_JSON:" in grounded_summary:
            parts = grounded_summary.split("CANONICAL_FACTS_JSON:")
            grounded_summary = parts[0].strip()
            facts = extract_json_from_output(parts[1])

    # --- Save grounding pass with separate facts ---
    trigger_on_demand_save(
        session_id=session_id,
        epoch=compression_epoch,
        event_type="grounding_pass",
        rolling_summary=grounded_summary,  # Text summary only
        facts=facts,                        # Structured JSON facts
    )

    return cap_summary_by_tokens(grounded_summary, max_summary_tokens)