# ----------------------------------------------------------------------
# 1. ALWAYS FIRST: Future Flags & Docstring
# ----------------------------------------------------------------------
from __future__ import annotations

"""
handlers.py
-----------
FastMCP Request Handlers and File Triggers for the Long-Term Memory (LTM) system.

Responsibilities:
  - Coordinate non-blocking background orchestration loops (ltm_doc.md §4, §5).
  - Implement the Cursor + Lock checkpoint guardrail safety net (ltm_doc.md §6).
  - Handle safe, read-only semantic retrieval hooks for runtime agents (ltm_doc.md §12).
"""

import logging
import os
import sys
import json
from pathlib import Path
from typing import Callable, Any

import numpy as np

# ----------------------------------------------------------------------
# 2. RUNTIME PATH RESOLUTION (Fixes Sibling Import Paths Dynamically)
# ----------------------------------------------------------------------
current_dir = Path(__file__).parent.resolve()      # memory folder
parent_dir = current_dir.parent.resolve()          # mcp folder
core_dir = current_dir / "core"

# Push paths into search hierarchy safely
for path in (parent_dir, current_dir, core_dir):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

# Make sure logger is declared cleanly right here
logger = logging.getLogger("ltm.handlers")

# Dynamic Module Alias Registration to bridge Test context and Server context
try:
    import config as direct_config
    sys.modules['memory.config'] = direct_config
except ImportError:
    pass

import config
from core import storage
from core import vector_store
from core import engine
from core import retrieval
from core import markdown
from core import maintenance
from core import fetcher

config.setup_logging()

# ----------------------------------------------------------------------
# 3. CROSS-PLATFORM SYSTEM LOCKING ABSTRACTION (Windows & Unix support)
# ----------------------------------------------------------------------
if os.name == 'nt':
    # Windows Platform Mechanics
    import msvcrt
    
    def _acquire_lock(file_desc) -> bool:
        try:
            # LK_NBLCK: Windows constant for a non-blocking lock
            msvcrt.locking(file_desc.fileno(), msvcrt.LK_NBLCK, 1)
            return True
        except (IOError, OSError):
            return False

    def _release_lock(file_desc):
        try:
            msvcrt.locking(file_desc.fileno(), msvcrt.LK_UNLCK, 1)
        except (IOError, OSError):
            pass
else:
    # Unix / Linux / macOS Mechanics
    import fcntl
    
    def _acquire_lock(file_desc) -> bool:
        try:
            fcntl.flock(file_desc, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except BlockingIOError:
            return False

    def _release_lock(file_desc):
        try:
            fcntl.flock(file_desc, fcntl.LOCK_UN)
        except (IOError, OSError):
            pass

# ----------------------------------------------------------------------
# Guardrail Infrastructure: Lock + Cursor Management
# ----------------------------------------------------------------------

class FileLockError(Exception):
    """Raised when an active background pipeline run is already holding the lock."""
    pass


def execute_pipeline_with_lock(
    db_path: Path,
    facts_jsonl_path: Path | None,
    cursor_path: Path | None,
    lock_path: Path,
    embed_fn: Callable[[list[str]], np.ndarray]
) -> engine.PipelineSummary | None:
    """
    Acquires an exclusive file lock before stepping into the engine pipeline.
    Ensures zero race conditions across both Windows and POSIX targets.
    """
    # Open or create the lock file descriptor
    lock_file = open(lock_path, "w")
    
    # Attempt to acquire the lock using our cross-platform abstractions
    if not _acquire_lock(lock_file):
        logger.info("Pipeline execution bypassed: Lock file is already held by an active process.")
        lock_file.close()
        raise FileLockError("Another instance of the memory engine is currently processing a batch.")

    try:
        raw_facts_batch = None
        final_offset = None

        if facts_jsonl_path is not None:
            # Step 1: Read the verified cursor pointer offset
            current_offset = 0
            if cursor_path and cursor_path.exists():
                try:
                    current_offset = int(cursor_path.read_text(encoding="utf-8").strip())
                except (ValueError, TypeError) as e:
                    logger.warning(f"Malformed cursor file found, resetting tracking pointer to 0: {e}")

            # Step 2: Read only the freshly appended segments from facts.jsonl
            if not facts_jsonl_path.exists():
                logger.info(f"No facts file discovered at {facts_jsonl_path}. Pipeline run completed with empty summary.")
                return None

            file_size = facts_jsonl_path.stat().st_size
            if current_offset >= file_size:
                logger.info(f"No new entries detected since last checkpoint pointer (Offset: {current_offset}B).")
                return None

            raw_facts_batch = []
            with open(facts_jsonl_path, "r", encoding="utf-8") as f:
                f.seek(current_offset)
                for line in f:
                    if line.strip():
                        try:
                            raw_facts_batch.append(json.loads(line.strip()))
                        except json.JSONDecodeError:
                            pass
                final_offset = f.tell()

            if not raw_facts_batch:
                return None

            logger.info(f"Ingesting batch window: {len(raw_facts_batch)} structured log entries found ({current_offset} -> {final_offset} bytes).")
        else:
            # Fallback queue-based fetcher logic: read all unprocessed session files chronologically
            raw_lines, latest_file = fetcher.read_latest_facts()
            if not latest_file:
                logger.info("No queue session files found in facts directory.")
                return None
            
            raw_facts_batch = []
            for line in raw_lines:
                if line.strip():
                    try:
                        raw_facts_batch.append(json.loads(line.strip()))
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse json line: {e}")
            
            if not raw_facts_batch:
                # If files are empty or invalid, let's archive them so they don't block the queue
                logger.warning("Queue files contain no valid JSON facts. Archiving to clear queue.")
                fetcher.archive_processed_file(latest_file)
                return None

            # Temporarily set this so we know which files to archive on success
            facts_jsonl_path = latest_file
            file_names = ", ".join(f.name for f in latest_file) if isinstance(latest_file, list) else latest_file.name
            logger.info(f"Queue Fetcher found file(s) {file_names} with {len(raw_facts_batch)} facts.")

        # Step 3: Establish connection context handles via storage API
        conn = storage.connect(db_path)
        
        try:
            vector_store.init_vector_table(conn, dim=384)
            cache = vector_store.EmbeddingCache(conn, dim=384)

            # Step 4: Execute pipeline utilizing batch processing with retry mechanics
            summary = engine.run_batch_pipeline_with_retry(
                conn=conn,
                cache=cache,
                embed_fn=embed_fn,
                raw_facts=raw_facts_batch
            )

            # Step 5: Render markdown projection using dynamic incremental checks
            if summary and summary.dirty_triple_ids:
                logger.info(f"Projecting dynamic changes into markdown files: {summary.dirty_triple_ids}")
                dirty_set = markdown.classify_dirty_sections(conn, summary.dirty_triple_ids)
                markdown.project_markdown_incremental(conn, dirty_set)

            # Step 6: Atomic Cursor Advance Protection OR Queue Archive
            if facts_jsonl_path is not None and cursor_path is not None and final_offset is not None:
                cursor_path.write_text(str(final_offset), encoding="utf-8")
                logger.info(f"Cursor advanced successfully to absolute checkpoint tracking offset: {final_offset}B.")
            elif facts_jsonl_path is not None and cursor_path is None:
                # Archive the processed session file to keep the input queue directory clean
                archive_success = fetcher.archive_processed_file(facts_jsonl_path)
                file_names = ", ".join(f.name for f in facts_jsonl_path) if isinstance(facts_jsonl_path, list) else facts_jsonl_path.name
                if archive_success:
                    logger.info(f"Successfully archived processed queue file(s): {file_names}")
                else:
                    logger.error(f"Failed to archive processed queue file(s): {file_names}")
            
            return summary

        finally:
            conn.close()

    finally:
        # Always release the lock cleanly using our platform handler
        _release_lock(lock_file)
        lock_file.close()


# ----------------------------------------------------------------------
# Read-Only Unified Context Access Layer (Step 20)
# ----------------------------------------------------------------------
def query_memory_handler(
    db_path: Path, 
    query_text: str, 
    embed_fn: Callable[[list[str]], np.ndarray], 
    limit: int = 5
) -> list[dict]:
    """
    Connects to the context store to retrieve and score active memories.
    Bumps tracking usage metrics for any hits found before returning.
    """
    conn = storage.connect(db_path)
    try:
        cache = vector_store.EmbeddingCache(conn, dim=384)
        matches = retrieval.retrieve_memories(
            conn=conn,
            cache=cache,
            query_text=query_text,
            embed_fn=embed_fn,
            limit=limit
        )
        
        if matches:
            retrieved_ids = [m.id for m in matches]
            retrieval.increment_retrieval_metrics(conn, retrieved_ids=retrieved_ids)
            
        return [
            {
                "subject": m.subject,
                "relation": m.relation,
                "object": m.object,
                "layer": m.layer,
                "score": float(m.score)
            }
            for m in matches
        ]
    finally:
        conn.close()


# ----------------------------------------------------------------------
# Offline Periodic Maintenance Access Layer (Step 21)
# ----------------------------------------------------------------------
def run_relation_maintenance_handler(
    db_path: Path, 
    embed_fn: Callable[[list[str]], np.ndarray], 
    similarity_threshold: float = 0.85
) -> int:
    """
    Triggers the offline similarity-clustering maintenance routine to 
    collapse near-duplicate relation items into canonical structures.
    """
    conn = storage.connect(db_path)
    try:
        return maintenance.maintain_relation_aliases(
            conn=conn,
            embed_fn=embed_fn,
            similarity_threshold=similarity_threshold
        )
    finally:
        conn.close()