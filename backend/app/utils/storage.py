# import os
# import json
# import asyncio
# import re
# import uuid
# from datetime import datetime, timezone

# # 1. Define and Ensure Directory (Module Level - Runs Once at Import)
# DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "facts"))
# os.makedirs(DATA_DIR, exist_ok=True)

# def _sanitize_filename(session_id: str) -> str:
#     """Sanitize session_id to ensure it's a valid filename."""
#     sanitized = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", session_id)
#     return sanitized[:100]

# def _sync_append_worker(filepath: str, payload_line: str):
#     """
#     LAYER 2 ISOLATION: Pure Disk Writer
#     Only handles the physical I/O. No directory checks, no string manipulation.
#     """
#     try:
#         with open(filepath, "a", encoding="utf-8") as f:
#             f.write(payload_line)
#     except Exception as e:
#         print(f"[Error] Failed to write to {filepath}: {e}")

# async def _process_isolated_ledger_write(
#     session_id: str,
#     epoch: int,
#     event_type: str,
#     rolling_summary: str,
#     facts: dict = None
# ):
#     """
#     BACKGROUND ASYNC CORE: Data Preparation
#     Uses Python 3.12+ compliant timezone-aware datetime for both filename and JSON.
#     Accepts an optional `facts` dict to store alongside the summary.
#     """
#     try:
#         if not session_id or not isinstance(session_id, str):
#             print("[Error] Invalid session_id. Skipping save.")
#             return

#         if not rolling_summary or not isinstance(rolling_summary, str):
#             print("[Error] Invalid rolling_summary. Skipping save.")
#             return

#         # Sanitize session_id for filename
#         sanitized_session_id = _sanitize_filename(session_id)

#         # 2. Unified Timezone Logic (UTC Everywhere)
#         now = datetime.now(timezone.utc)
        
#         # --- FIX: Changed format to YYYYMMDD_HHMM for perfect alphabetical sorting ---
#         # --- FIX: Renamed 'min' to 'minute' to avoid overwriting Python's built-in min() ---
#         yyyy = now.strftime("%Y")
#         mm = now.strftime("%m")
#         dd = now.strftime("%d")
#         hh = now.strftime("%H")
#         minute = now.strftime("%M")

#         # New chronological filename format: YYYYMMDD_HHMM_session.jsonl
#         filename = f"{yyyy}{mm}{dd}_{hh}{minute}_{sanitized_session_id}.jsonl"
#         filepath = os.path.join(DATA_DIR, filename)

#         # --- UNIQUE MESSAGE ID GENERATION ---
#         # Choice A: Generate a perfectly unique UUID (Safe, standard, eliminates collision risk)
#         unique_msg_id = f"msg_{uuid.uuid4().hex[:12]}"

#         # 3. Consolidated Formatting
#         log_entry = {
#             "timestamp": now.isoformat(),
#             "epoch": epoch,
#             "event_type": event_type,
#             "rolling_summary": rolling_summary,
#             "conversation_id": session_id,
#             "message_ids": [unique_msg_id]
#         }
        
#         # Add facts if provided and valid
#         if facts is not None and isinstance(facts, dict):
#             try:
#                 # Ensure facts are JSON-serializable
#                 json.dumps(facts)
#                 log_entry["facts"] = facts
#             except (TypeError, ValueError) as e:
#                 print(f"[Error] Facts are not JSON-serializable: {e}. Omitting facts.")

#         # Append the newline here so the worker has a single, complete unit of work
#         payload_packet = json.dumps(log_entry, ensure_ascii=False) + "\n"

#         # LAYER 2 PROTECTION: Dispatch to thread pool
#         await asyncio.to_thread(_sync_append_worker, filepath, payload_packet)

#     except Exception as io_error:
#         # Fail-silent protection for the main chat stream
#         print(f"[Error] Background Ledger Error: {io_error}")

# def trigger_on_demand_save(
#     session_id: str,
#     epoch: int,
#     event_type: str,
#     rolling_summary: str,
#     facts: dict = None
# ):
#     """
#     LAYER 1 ISOLATION: Event Loop Detachment
#     Accepts an optional `facts` dict to store alongside the summary.
#     """
#     if not session_id:
#         return

#     asyncio.create_task(
#         _process_isolated_ledger_write(
#             session_id,
#             epoch,
#             event_type,
#             rolling_summary,
#             facts
#         )
#     )













































































import os
import json
import asyncio
import re
import uuid
from datetime import datetime, timezone

# 1. Define and Ensure Directory (Module Level - Runs Once at Import)
DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "facts"))
os.makedirs(DATA_DIR, exist_ok=True)

# Store session start times in memory (cleared on server restart)
_session_start_times = {}

def _sanitize_filename(session_id: str) -> str:
    """Sanitize session_id to ensure it's a valid filename."""
    sanitized = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", session_id)
    return sanitized[:100]

def _sync_append_worker(filepath: str, payload_line: str):
    """
    LAYER 2 ISOLATION: Pure Disk Writer
    Only handles the physical I/O. No directory checks, no string manipulation.
    """
    try:
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(payload_line)
    except Exception as e:
        print(f"[Error] Failed to write to {filepath}: {e}")

async def _process_isolated_ledger_write(
    session_id: str,
    epoch: int,
    event_type: str,
    rolling_summary: str,
    facts: dict = None
):
    """
    BACKGROUND ASYNC CORE: Data Preparation
    Uses Python 3.12+ compliant timezone-aware datetime for JSON.
    Accepts an optional `facts` dict to store alongside the summary.
    """
    try:
        if not session_id or not isinstance(session_id, str):
            print("[Error] Invalid session_id. Skipping save.")
            return

        if not rolling_summary or not isinstance(rolling_summary, str):
            print("[Error] Invalid rolling_summary. Skipping save.")
            return

        # Sanitize session_id for filename
        sanitized_session_id = _sanitize_filename(session_id)

        # Get or set the session start time (first call for this session_id)
        if session_id not in _session_start_times:
            _session_start_times[session_id] = datetime.now(timezone.utc)

        session_start = _session_start_times[session_id]

        # Use the session start time for the filename
        yyyy = session_start.strftime("%Y")
        mm = session_start.strftime("%m")
        dd = session_start.strftime("%d")
        hh = session_start.strftime("%H")
        minute = session_start.strftime("%M")

        # Filename: YYYYMMDD_HHMM_session_id.jsonl (based on session start time)
        filename = f"{yyyy}{mm}{dd}_{hh}{minute}_{sanitized_session_id}.jsonl"
        filepath = os.path.join(DATA_DIR, filename)

        # Current time for the log entry
        now = datetime.now(timezone.utc)

        # --- UNIQUE MESSAGE ID GENERATION ---
        unique_msg_id = f"msg_{uuid.uuid4().hex[:12]}"

        # 3. Consolidated Formatting
        log_entry = {
            "timestamp": now.isoformat(),
            "epoch": epoch,
            "event_type": event_type,
            "rolling_summary": rolling_summary,
            "conversation_id": session_id,
            "message_ids": [unique_msg_id]
        }

        # Add facts if provided and valid
        if facts is not None and isinstance(facts, dict):
            try:
                # Ensure facts are JSON-serializable
                json.dumps(facts)
                log_entry["facts"] = facts
            except (TypeError, ValueError) as e:
                print(f"[Error] Facts are not JSON-serializable: {e}. Omitting facts.")

        # Append the newline here so the worker has a single, complete unit of work
        payload_packet = json.dumps(log_entry, ensure_ascii=False) + "\n"

        # LAYER 2 PROTECTION: Dispatch to thread pool
        await asyncio.to_thread(_sync_append_worker, filepath, payload_packet)

    except Exception as io_error:
        # Fail-silent protection for the main chat stream
        print(f"[Error] Background Ledger Error: {io_error}")

def trigger_on_demand_save(
    session_id: str,
    epoch: int,
    event_type: str,
    rolling_summary: str,
    facts: dict = None
):
    """
    LAYER 1 ISOLATION: Event Loop Detachment
    Accepts an optional `facts` dict to store alongside the summary.
    """
    if not session_id:
        return

    asyncio.create_task(
        _process_isolated_ledger_write(
            session_id,
            epoch,
            event_type,
            rolling_summary,
            facts
        )
    )