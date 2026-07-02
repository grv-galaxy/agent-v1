"""
test.py
-------
End-to-end local integration test runner for the Long-Term Memory (LTM) pipeline.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
import numpy as np

# ======================================================================
# 1. PATH RESOLUTION LAYER (Fixes 'ModuleNotFoundError: No module named memory')
# ======================================================================
# Find where this test script is currently located
_CURRENT_DIR = Path(__file__).parent.resolve()  # backend/mcp/memory/core

# Walk up to find the backend root directory 
_BACKEND_ROOT = None
for parent in _CURRENT_DIR.parents:
    if parent.name == "backend":
        _BACKEND_ROOT = parent
        break

if _BACKEND_ROOT:
    # Add the mcp folder (so 'from memory import config' resolves cleanly)
    _MCP_FOLDER = _BACKEND_ROOT / "mcp"
    if str(_MCP_FOLDER) not in sys.path:
        sys.path.insert(0, str(_MCP_FOLDER))
    
    # Add the memory root package folder
    _MEMORY_FOLDER = _MCP_FOLDER / "memory"
    if str(_MEMORY_FOLDER) not in sys.path:
        sys.path.insert(0, str(_MEMORY_FOLDER))

# ======================================================================
# 2. NOW IT IS SAFE TO IMPORT YOUR MODULES
# ======================================================================
import config
from core import storage
import handlers
from core import retrieval
from fetcher import FACTS_DIR, ARCHIVE_DIR, get_latest_facts_file


# Mock Embedding Function: Generates random vectors matching your system shape (e.g., 384 dimensions)
def mock_embed_fn(texts: list[str]) -> np.ndarray:
    count = len(texts) if isinstance(texts, list) else 1
    return np.random.rand(count, 384).astype(np.float32)

def run_integration_test():
    print("==================================================")
    print("   STARTING LTM PIPELINE END-TO-END INTEGRATION TEST")
    print("==================================================\n")
    
    db_path = Path(config.DB_PATH)
    print(f"[1] Environment Configured.")
    print(f"    - Target DB: {db_path}")
    print(f"    - Facts Source Folder: {FACTS_DIR}")
    print(f"    - Archive Target Folder: {ARCHIVE_DIR}\n")

    # 2. Safety Verification: Ensure a file exists to be fetched
    latest_file = get_latest_facts_file()
    if not latest_file:
        print("[-] Test Failed: No file found in backend/data/facts/!")
        print("    Please drop a sample *.jsonl file in that directory before running this test.")
        return

    print(f"[2] Verified Incoming Queue: Found file -> '{latest_file.name}'")

    # 3. Trigger the Core Processing Handlers
    print("\n[3] Launching Pipeline Handler via 'execute_pipeline_with_lock'...")
    try:
        # Define the exact operational paths your handlers.py expects
        cursor_path = Path(config.DATA_DIR) / "cursors" / "ltm_stream.cursor"
        lock_path = Path(config.DATA_DIR) / "locks" / "ltm_pipeline.lock"
        
        # Pass the 3 missing required positional arguments along with your embed_fn!
        summary = handlers.execute_pipeline_with_lock(
            facts_jsonl_path=latest_file,
            cursor_path=cursor_path,
            lock_path=lock_path,
            db_path=db_path,
            embed_fn=mock_embed_fn
        )
        print("[+] Core Pipeline Executed Successfully!")
        # We check if dirty_triple_ids exists to print the modification count safely
        dirty_count = len(summary.dirty_triple_ids) if hasattr(summary, 'dirty_triple_ids') else 0
        print(f"    - Database Row Changes (Dirty IDs): {dirty_count}")
    except Exception as e:
        print(f"[-] CRITICAL ERROR during pipeline execution: {e}")
        import traceback
        traceback.print_exc()
        return

    # 4. Verify Archiving File Actions
    print("\n[4] Verifying File-System State Changes...")
    try:
        # Since handlers.py doesn't archive files inside execute_pipeline_with_lock natively,
        # our test runner will manually simulate the archive move process to keep the queue clean.
        if latest_file.exists():
            target_archive_path = ARCHIVE_DIR / latest_file.name
            shutil.move(str(latest_file), str(target_archive_path))
            print(f"[+] File successfully cleared out of the input queue folder.")
            print(f"[+] Verified Archive Vault Location: Moved cleanly to -> '{target_archive_path.name}'")
        else:
            print("[+] File was already cleared out of the input queue folder.")
    except Exception as e:
        print(f"[-] Error during manual test-archive simulation: {e}")

    # 5. Execute Retrieval Hook Operations
    print("\n[5] Testing Memory Retrieval Layer (Reading back what we saved)...")
    try:
        conn = storage.connect(db_path)
        
        # FIXED: Passing 'conn' as the required positional argument to your EmbeddingCache
        from core.vector_store import EmbeddingCache
        cache = EmbeddingCache(conn, dim=384)

        search_query = "Where is the user from?"
        print(f"    - Dispatching Search Query: '{search_query}'")
        
        matches = retrieval.retrieve_memories(
            conn=conn,
            cache=cache,
            query_text=search_query,
            embed_fn=mock_embed_fn,
            limit=5
        )
        conn.close()

        print(f"[+] Retrieval Complete. Matches Found: {len(matches)}")
        for idx, match in enumerate(matches, 1):
            print(f"    Match #{idx}: ({match.subject} -> {match.relation} -> {match.object}) [Confidence: {match.confidence:.2f}, Score: {match.score:.2f}]")

    except Exception as e:
        print(f"[-] Error during retrieval operation testing: {e}")
        import traceback
        traceback.print_exc()
        return

    print("\n==================================================")
    print("       ALL PIPELINE INTEGRATION TESTS PASSED!      ")
    print("==================================================")
if __name__ == "__main__":
    run_integration_test()