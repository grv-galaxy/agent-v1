import asyncio
import json
import re
from app.utils.token import count_tokens, cap_summary_by_tokens
from app.utils.storage import trigger_on_demand_save
from app.core.prompts import FIRST_EPOCH_PROMPT, ANCHORED_COMPRESSION_PROMPT, GROUNDING_PROMPT

def extract_json_from_output(output: str, marker: str = None) -> dict:
    """
    Robustly extracts a JSON object from the LLM output string.
    If a marker is provided, it attempts to find JSON within or after that marker block.
    Handles strict structural raw JSON objects as well as markdown code wrapping.
    """
    if not output or not isinstance(output, str):
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

    # Remove markdown code fences if present
    json_str = re.sub(r'^```(?:json)?\s*', '', json_str)
    json_str = re.sub(r'\s*```$', '', json_str)

    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"[Warning] JSON parsing failed: {e}. Raw content: {json_str[:200]}...")
        return None


async def compress_chunk(
    chunk_messages: list[dict],
    existing_summary: str,
    provider_instance,
    model_name: str,
    session_id: str,
    compression_epoch: int,
    max_summary_tokens: int = None,
) -> str:
    try:
        # --- Step 1: Prepare chunk_text ---
        chunk_text = "\n".join(
            f"[{m.get('role', 'unknown').upper()}]: {m.get('content', '')}"
            for m in chunk_messages
        )

        # --- Step 2: Select prompt ---
        if compression_epoch == 1:
            prompt = FIRST_EPOCH_PROMPT.format(chunk_text=chunk_text)
        else:
            prompt = ANCHORED_COMPRESSION_PROMPT.format(
                existing_summary=existing_summary or "",
                chunk_text=chunk_text
            )

        # --- Step 3: Stream LLM response ---
        result_tokens = []
        async for chunk in provider_instance.generate_stream(model_name, [{"role": "user", "content": prompt}]):
            if isinstance(chunk, dict):
                result_tokens.append(chunk.get("text", ""))
        raw_response = "".join(result_tokens).strip()

        # --- Step 4: Parse JSON ---
        parsed_payload = extract_json_from_output(raw_response)
        if parsed_payload and isinstance(parsed_payload, dict):
            new_summary = parsed_payload.get("summary", "").strip()
            facts = parsed_payload.get("facts_json", {})
        else:
            # Emergency fallback
            new_summary = raw_response
            facts = None
            if "SUMMARY:" in new_summary:
                new_summary = new_summary.split("SUMMARY:")[-1]
            if "FACTS_JSON:" in new_summary:
                parts = new_summary.split("FACTS_JSON:")
                new_summary = parts[0].strip()
                facts = extract_json_from_output(parts[1])

        # --- Step 5: Save and return ---
        trigger_on_demand_save(
            session_id=session_id,
            epoch=compression_epoch,
            event_type="compression_pass",
            rolling_summary=new_summary,
            facts=facts,
        )
        return cap_summary_by_tokens(new_summary, max_summary_tokens)

    except Exception as e:
        print(f"[ERROR] Compression failed at step: {e}")
        import traceback
        traceback.print_exc()
        return cap_summary_by_tokens(existing_summary or "", max_summary_tokens)


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
    try:
        all_versions = [s for s in summary_history if s] + [current_summary]
        if len(all_versions) < 2:
            return cap_summary_by_tokens(current_summary, max_summary_tokens)

        versions_text = "\n\n---\n\n".join(
            f"Epoch {i+1}:\n{s}" for i, s in enumerate(all_versions)
        )

        prompt = GROUNDING_PROMPT.format(existing_summary=versions_text)
        messages = [{"role": "user", "content": prompt}]

        # --- Stream LLM response ---
        result_tokens = []
        try:
            async for chunk in provider_instance.generate_stream(model_name, messages):
                if isinstance(chunk, dict):
                    result_tokens.append(chunk.get("text", ""))
        except Exception as e:
            print(f"[Error] Streaming failed: {e}")
            return cap_summary_by_tokens(current_summary, max_summary_tokens)

        raw_response = "".join(result_tokens).strip()

        # --- Parse Master grounding payload ---
        parsed_payload = extract_json_from_output(raw_response)

        if parsed_payload and isinstance(parsed_payload, dict):
            grounded_summary = parsed_payload.get("summary", "").strip()
            facts = parsed_payload.get("facts_json", {})
        else:
            # Flat text partition emergency fallback
            print("[grounding_service] Grounding fallback processing triggered.")
            grounded_summary = raw_response
            facts = None

            if "SUPER_COMPRESSION:" in grounded_summary:
                grounded_summary = grounded_summary.split("SUPER_COMPRESSION:")[-1].strip()
            if "RECONCILED_FACTS_JSON:" in grounded_summary:
                parts = grounded_summary.split("RECONCILED_FACTS_JSON:")
                grounded_summary = parts[0].strip()
                facts = extract_json_from_output(parts[1])

        # --- Save grounding pass ---
        try:
            trigger_on_demand_save(
                session_id=session_id,
                epoch=compression_epoch,
                event_type="grounding_pass",
                rolling_summary=grounded_summary,
                facts=facts,
            )
        except Exception as e:
            print(f"[Error] Failed to save grounding pass: {e}")

        return cap_summary_by_tokens(grounded_summary, max_summary_tokens)

    except Exception as e:
        print(f"[Error] Grounding failed: {e}")
        return cap_summary_by_tokens(current_summary, max_summary_tokens)
