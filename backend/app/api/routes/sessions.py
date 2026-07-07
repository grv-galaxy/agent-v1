import os
import json
import asyncio
from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List

router = APIRouter()

SESSIONS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "sessions"))
os.makedirs(SESSIONS_DIR, exist_ok=True)

def _get_session_filepath(session_id: str) -> str:
    # Sanitize session_id to prevent path traversal
    safe_id = "".join(c for c in session_id if c.isalnum() or c in ('-', '_'))
    return os.path.join(SESSIONS_DIR, f"{safe_id}.json")

@router.get("/sessions", response_model=List[Dict[str, Any]])
async def get_all_sessions():
    """Reads all saved session files and returns them."""
    try:
        def _read_all():
            sessions = []
            if not os.path.exists(SESSIONS_DIR):
                return sessions
                
            for filename in os.listdir(SESSIONS_DIR):
                if filename.endswith(".json"):
                    filepath = os.path.join(SESSIONS_DIR, filename)
                    try:
                        with open(filepath, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            sessions.append(data)
                    except Exception as e:
                        print(f"[Sessions] Error reading {filename}: {e}")
            
            # Sort by startedAt descending (newest first) if available
            sessions.sort(key=lambda s: s.get("startedAt", ""), reverse=True)
            return sessions
            
        return await asyncio.to_thread(_read_all)
    except Exception as e:
        print(f"[Sessions] Failed to load sessions: {e}")
        raise HTTPException(status_code=500, detail="Failed to load sessions")

@router.post("/sessions")
async def save_session(session_data: Dict[str, Any]):
    """Saves or updates a single session object asynchronously to prevent CPU blocking."""
    session_id = session_data.get("id") or session_data.get("session_id")
    if not session_id:
        raise HTTPException(status_code=400, detail="Session ID is required")
        
    filepath = _get_session_filepath(session_id)
    
    try:
        def _write():
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(session_data, f, ensure_ascii=False, indent=2)
                
        await asyncio.to_thread(_write)
        return {"status": "success", "session_id": session_id}
    except Exception as e:
        print(f"[Sessions] Failed to save session {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to save session")

@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Deletes a saved session file."""
    filepath = _get_session_filepath(session_id)
    
    try:
        def _delete():
            if os.path.exists(filepath):
                os.remove(filepath)
                
        await asyncio.to_thread(_delete)
        return {"status": "success", "deleted": session_id}
    except Exception as e:
        print(f"[Sessions] Failed to delete session {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete session")
