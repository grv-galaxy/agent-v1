# """
# handlers.py
# -----------
# FastMCP Request Handlers and File Triggers for the Long-Term Memory (LTM) system.

# Responsibilities:
#   - Coordinate non-blocking background orchestration loops (ltm_doc.md §4, §5).
#   - Implement the Cursor + Lock checkpoint guardrail safety net (ltm_doc.md §6).
#   - Handle safe, read-only semantic retrieval hooks for runtime agents (ltm_doc.md §12).
# """

# from __future__ import annotations

# import logging
# import os
# import sys
# import fcntl
# from pathlib import Path
# from typing import Callable, Any

# import numpy as np

# current_dir = Path(__file__).parent.resolve()
# core_dir = current_dir / "core"
# for path in (current_dir, core_dir):
#     if str(path) not in sys.path:
#         sys.path.insert(0, str(path))

# import config
# import storage
# import vector_store
# import engine
# import extractor
# import retrieval
# import markdown

# logger = logging.getLogger("ltm.handlers")

# # ----------------------------------------------------------------------
# # Guardrail Infrastructure: Lock + Cursor Management (ltm_doc.md §6)
# # ----------------------------------------------------------------------

# class FileLockError(Exception):
#     """Raised when an active background pipeline run is already holding the lock."""
#     pass


# def execute_pipeline_with_lock(
#     db_path: Path,
#     facts_jsonl_path: Path,
#     cursor_path: Path,
#     lock_path: Path,
#     embed_fn: Callable[[list[str]], list[np.ndarray]]
# ) -> engine.PipelineSummary | None:
#     """
#     Acquires an exclusive advisory flock file lock before stepping into the engine pipeline.
#     Ensures zero race conditions when spawned concurrently via background triggers (ltm_doc.md §5, §6).
#     """
#     # Open or create the lock file descriptor
#     lock_file = open(lock_path, "w")
    
#     try:
#         # Attempt to acquire exclusive advisory lock non-blockingly
#         fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
#     except BlockingIOError:
#         logger.info("Pipeline execution bypassed: Lock file is already held by an active process.")
#         lock_file.close()
#         raise FileLockError("Another instance of the memory engine is currently processing a batch.")

#     try:
#         # Step 1: Read the verified cursor pointer offset (bytes processed previously)
#         current_offset = 0
#         if cursor_path.exists():
#             try:
#                 current_offset = int(cursor_path.read_text(encoding="utf-8").strip())
#             except (ValueError, TypeError) as e:
#                 logger.warning(f"Malformed cursor file found, resetting tracking pointer to 0: {e}")

#         # Step 2: Read only the freshly appended segments from facts.jsonl (ltm_doc.md §8)
#         if not facts_jsonl_path.exists():
#             logger.info("No facts.jsonl file discovered. Pipeline run completed with empty summary.")
#             return None

#         file_size = facts_jsonl_path.stat().st_size
#         if current_offset >= file_size:
#             logger.info(f"No new entries detected since last checkpoint pointer (Offset: {current_offset}B).")
#             return None

#         # Gather target chunk lines safely without pulling the entire historical file into memory
#         new_lines = []
#         with open(facts_jsonl_path, "r", encoding="utf-8") as f:
#             f.seek(current_offset)
#             # Read line-by-line until EOF to handle large deltas reliably
#             for line in f:
#                 new_lines.append(line)
#             # Record the actual precise end pointer boundary reached
#             final_offset = f.tell()

#         if not new_lines:
#             return None

#         logger.info(f"Ingesting batch window: {len(new_lines)} log strings found ({current_offset} -> {final_offset} bytes).")

#         # Step 3: Establish connection context handles
#         conn = storage.get_connection(db_path)
        
#         try:
#             # Initialize tables dynamically if needed
#             storage.init_db(conn)
#             vector_store.init_vector_table(conn)

#             # Pre-load or initialize the memory dot-product accelerator matrix
#             cache = vector_store.load_embedding_cache(conn)

#             # Step 4: Execute the complete 13-step batch logic pipeline (ltm_doc.md §8)
#             summary = engine.run_pipeline(
#                 conn=conn,
#                 cache=cache,
#                 raw_lines=new_lines,
#                 embed_fn=embed_fn,
#                 lifecycle_policy=config.DEFAULT_LIFECYCLE_POLICY
#             )

#             # Step 5: Render dirty changes into the human-readable Markdown OKF layer (ltm_doc.md §11)
#             if not summary.dirty_triple_ids.is_empty():
#                 logger.info(f"Projecting dynamic changes into markdown files: {summary.dirty_triple_ids}")
#                 markdown.project_markdown_incremental(conn, summary.dirty_triple_ids)

#             # Step 6: Atomic Cursor Advance Protection (ltm_doc.md §6, §7)
#             # The tracking checkpoint pointer ONLY advances to 'final_offset' if everything succeeded.
#             # If a crash happened mid-run, the cursor stays back, forcing a safe re-run on next trigger.
#             cursor_path.write_text(str(final_offset), encoding="utf-8")
#             logger.info(f"Cursor advanced successfully to absolute checkpoint tracking offset: {final_offset}B.")
            
#             return summary

#         finally:
#             conn.close()

#     finally:
#         # Always release file advisory locks cleanly and close descriptors
#         fcntl.flock(lock_file, fcntl.LOCK_UN)
#         lock_file.close()

# # ----------------------------------------------------------------------
# # FastMCP Core Application Tool Intermediaries (ltm_doc.md §12, §16)
# # ----------------------------------------------------------------------

# def handle_query_memories(
#     db_path: Path,
#     query: str,
#     embed_fn: Callable[[list[str]], list[np.ndarray]],
#     subject_filter: str | None = None,
#     limit: int = 10,
#     similarity_threshold: float = 0.40
# ) -> list[dict[str, Any]]:
#     """
#     Handles read-only agent lookups via high-speed unified vector + namespace retrieval (ltm_doc.md §12).
#     """
#     conn = storage.get_connection(db_path)
#     try:
#         # Load the in-memory cache dynamically to resolve queries via optimized BLAS matmul
#         cache = vector_store.load_embedding_cache(conn)
        
#         matches = retrieval.retrieve_memories(
#             conn=conn,
#             cache=cache,
#             query_text=query,
#             embed_fn=embed_fn,
#             subject_filter=subject_filter,
#             limit=limit,
#             similarity_threshold=similarity_threshold
#         )
        
#         # Format structures cleanly into native serializable dictionaries for standard FastMCP tool delivery
#         return [
#             {
#                 "id": m.id,
#                 "subject": m.subject,
#                 "relation": m.relation,
#                 "object": m.object,
#                 "layer": m.layer,
#                 "confidence": round(m.confidence, 3),
#                 "importance": m.importance,
#                 "decay_score": round(m.decay_score, 4),
#                 "composite_score": round(m.score, 4)
#             }
#             for m in matches
#         ]
#     finally:
#         conn.close()


# def handle_record_retrieval_feedback(
#     db_path: Path,
#     retrieved_ids: list[str],
#     successful_ids: list[str] | None = None
# ) -> str:
#     """
#     Increments fact usefulness records to tighten reinforcement optimization feedback loops (ltm_doc.md §12).
#     """
#     conn = storage.get_connection(db_path)
#     try:
#         retrieval.increment_retrieval_metrics(
#             conn=conn,
#             retrieved_ids=retrieved_ids,
#             successful_ids=successful_ids
#         )
#         return f"Successfully updated hit counters for {len(retrieved_ids)} identifiers."
#     finally:
#         conn.close()
























































































"""
server.py
---------
Entrypoint to run the FastMCP Long-Term Memory (LTM) server over standard I/O pipes.
"""

import sys
import sqlite3
import sqlite_vec
from pathlib import Path
from mcp.server.fastmcp import FastMCP

# Resolve paths safely
current_dir = Path(__file__).parent.resolve()      # C:\...\mcp\memory
parent_dir = current_dir.parent.resolve()          # C:\...\mcp

# 1. Inject parent directory so 'from memory import ...' works smoothly
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

# 2. Safety fallback alias if executed inside the directory directly
import handlers
import sqlite_vec
sys.modules['memory'] = handlers.sys.modules[handlers.__package__ or 'handlers']

# 💡 EXPLICIT EXTENSION AUTHORIZATION: Force the built-in sqlite3 factory 
# to ALWAYS authorize and load the vec0 extension for every connection created by this process.
def _connection_factory(*args, **kwargs):
    # This matches your existing line 327
    conn = sqlite3.Connection(*args, **kwargs)
    
    # CRUCIAL FIX: Force the factory interceptor to load the vec extension! ⚡
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    
    return conn

# Your existing line 336 remains right below it:
sqlite3.connect = _connection_factory

# Import tools module safely matching layout
from core import tools

# Initialize the official FastMCP server instance
# Initialize the official FastMCP server instance
mcp = FastMCP(
    "Long-Term-Memory-Server",
    host="0.0.0.0",       # must bind to all interfaces inside a container
    port=8765,             # pick any free port, make it configurable via env if you like
)

# Bind and register tools
tools.register_ltm_tools(mcp)

if __name__ == "__main__":
    mcp.run(transport="sse")   # <-- was "stdio"