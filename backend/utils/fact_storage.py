# backend/utils/fact_storage.py
import os
import json
import asyncio
from datetime import datetime, timezone

# 1. Define and Ensure Directory (Module Level - Runs Once at Import)
DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "facts"))
os.makedirs(DATA_DIR, exist_ok=True)

def _sync_append_worker(filepath: str, payload_line: str):
    """
    LAYER 2 ISOLATION: Pure Disk Writer
    Only handles the physical I/O. No directory checks, no string manipulation.
    """
    with open(filepath, "a", encoding="utf-8") as f:
        f.write(payload_line)

async def _process_isolated_ledger_write(session_id: str, epoch: int, event_type: str, rolling_summary: str, facts: dict = None):
    """
    BACKGROUND ASYNC CORE: Data Preparation
    Uses Python 3.12+ compliant timezone-aware datetime for both filename and JSON.
    Now accepts an optional `facts` dict to store alongside the summary.
    """
    try:
        # 2. Unified Timezone Logic (UTC Everywhere)
        now = datetime.now(timezone.utc)
        dd = now.strftime("%d")
        mm = now.strftime("%m")

        filename = f"{dd}_{mm}_{session_id}.jsonl"
        filepath = os.path.join(DATA_DIR, filename)

        # 3. Consolidated Formatting
        # We prepare the final packet (JSON + Newline) here in the async loop
        log_entry = {
            "timestamp": now.isoformat(),
            "epoch": epoch,
            "event_type": event_type,
            "rolling_summary": rolling_summary
        }

        # Add facts if provided
        if facts is not None:
            log_entry["facts"] = facts

        # Append the newline here so the worker has a single, complete unit of work
        payload_packet = json.dumps(log_entry, ensure_ascii=False) + "\n"

        # LAYER 2 PROTECTION: Dispatch to thread pool
        await asyncio.to_thread(_sync_append_worker, filepath, payload_packet)

    except Exception as io_error:
        # Fail-silent protection for the main chat stream
        print(f"Background Ledger Error: {io_error}")

def trigger_on_demand_save(session_id: str, epoch: int, event_type: str, rolling_summary: str, facts: dict = None):
    """
    LAYER 1 ISOLATION: Event Loop Detachment
    Now accepts an optional `facts` dict to store alongside the summary.
    """
    if not session_id:
        return

    asyncio.create_task(
        _process_isolated_ledger_write(session_id, epoch, event_type, rolling_summary, facts)
    )