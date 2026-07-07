import os
import json
import asyncio
import re

# Directory for raw ledger files
LEDGER_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "raw_ledger"))
os.makedirs(LEDGER_DIR, exist_ok=True)

def _sanitize_filename(session_id: str) -> str:
    """Sanitize session_id to ensure it's a valid filename."""
    sanitized = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", session_id)
    return sanitized[:100]

async def append_ledger(session_id: str, user_msg: str, assistant_msg: str):
    """
    Appends a user-assistant exchange to the raw ledger without checking limits.
    """
    if not session_id:
        return

    sanitized_session_id = _sanitize_filename(session_id)
    filepath = os.path.join(LEDGER_DIR, f"raw_{sanitized_session_id}.jsonl")
    
    entry = {
        "user": user_msg,
        "assistant": assistant_msg
    }
    
    try:
        def _write():
            with open(filepath, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        await asyncio.to_thread(_write)
    except Exception as e:
        print(f"[Error] Failed to write to raw ledger {filepath}: {e}")


async def read_and_clear_ledger(session_id: str) -> list:
    """
    Reads all messages from the raw ledger file, formats them into a chunk 
    for the LLM, deletes the file, and returns the chunk.
    """
    if not session_id:
        return []

    sanitized_session_id = _sanitize_filename(session_id)
    filepath = os.path.join(LEDGER_DIR, f"raw_{sanitized_session_id}.jsonl")

    if not os.path.exists(filepath):
        return []

    lines = []
    try:
        def _read():
            with open(filepath, "r", encoding="utf-8") as f:
                return f.readlines()
        lines = await asyncio.to_thread(_read)
    except Exception as e:
        print(f"[Error] Failed to read raw ledger {filepath}: {e}")
        return []

    chunk = []
    for line in lines:
        try:
            data = json.loads(line)
            if "user" in data:
                chunk.append({"role": "user", "content": data["user"]})
            if "assistant" in data:
                chunk.append({"role": "assistant", "content": data["assistant"]})
        except json.JSONDecodeError:
            continue
            
    # Delete file
    try:
        os.remove(filepath)
    except Exception as e:
        print(f"[Error] Failed to delete raw ledger {filepath}: {e}")
        
    return chunk


async def count_ledger_files() -> int:
    """
    Returns the number of raw ledger files currently in the directory.
    """
    try:
        def _count():
            if not os.path.exists(LEDGER_DIR):
                return 0
            return len([f for f in os.listdir(LEDGER_DIR) if f.endswith(".jsonl")])
        return await asyncio.to_thread(_count)
    except Exception as e:
        print(f"[Error] Failed to count ledger files: {e}")
        return 0

from app.utils.token import count_tokens

async def count_session_tokens(session_id: str) -> int:
    """
    Reads the specific raw ledger file for a session and calculates the total token count.
    """
    if not session_id:
        return 0

    sanitized_session_id = _sanitize_filename(session_id)
    filepath = os.path.join(LEDGER_DIR, f"raw_{sanitized_session_id}.jsonl")

    if not os.path.exists(filepath):
        return 0

    try:
        def _read_file():
            with open(filepath, "r", encoding="utf-8") as f:
                return f.readlines()
        
        lines = await asyncio.to_thread(_read_file)
        total_text = ""
        
        for line in lines:
            try:
                data = json.loads(line)
                if "user" in data:
                    total_text += data["user"] + "\n"
                if "assistant" in data:
                    total_text += data["assistant"] + "\n"
            except json.JSONDecodeError:
                continue
                
        return count_tokens(total_text)
    except Exception as e:
        print(f"[Error] Failed to count session tokens: {e}")
        return 0

async def get_all_ledger_session_ids() -> list:
    """
    Returns a list of session IDs based on the files in the ledger directory.
    """
    if not os.path.exists(LEDGER_DIR):
        return []
    
    def _get_sessions():
        sessions = []
        for f in os.listdir(LEDGER_DIR):
            if f.startswith("raw_") and f.endswith(".jsonl"):
                # Extract session id: remove 'raw_' prefix (4 chars) and '.jsonl' suffix (6 chars)
                session_id = f[4:-6]
                sessions.append(session_id)
        return sessions
    
    return await asyncio.to_thread(_get_sessions)
