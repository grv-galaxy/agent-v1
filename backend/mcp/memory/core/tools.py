"""
tools.py
--------
Defines and registers core Long-Term Memory capabilities as FastMCP tools.
"""

from __future__ import annotations

import os
import sys
import numpy as np
from pathlib import Path
from mcp.server.fastmcp import FastMCP

# Fix sibling paths dynamically so config/handlers/core can be discovered cleanly
current_dir = Path(__file__).parent.resolve()
parent_dir = current_dir.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

import config
import handlers
from core.embedder import encode_batch

# Toggle between production files and isolated test artifacts dynamically.
# Both branches now route through config.py's DATA_DIR so nothing is
# hardcoded to a specific machine or Windows path anymore.
if os.environ.get("LTM_ENV") == "test":
    DB_PATH = config.DATA_DIR / "test_mcp_server.db"
    FACTS_JSONL = config.DATA_DIR / "test_mcp_facts.jsonl"
    CURSOR_PATH = config.DATA_DIR / "test_mcp_cursor.txt"
    LOCK_PATH = config.DATA_DIR / "test_mcp_memory.lock"
else:
    DB_PATH = config.DB_PATH
    FACTS_JSONL = config.FACTS_JSONL_PATH
    CURSOR_PATH = config.CURSOR_PATH
    LOCK_PATH = config.LOCK_PATH


def runtime_embed_fn(texts: list[str]) -> np.ndarray:
    """
    Delegates to the real quantized ONNX BGE embedding model
    (core.embedder.encode_batch), matching the LTM production vector schema.
    """
    if not texts:
        return np.empty((0, 384), dtype=np.float32)

    return encode_batch(texts)


def register_ltm_tools(mcp: FastMCP):
    """
    Registers the core operational memory tools onto a running FastMCP instance.
    """
    
    @mcp.tool(
        name="sync_memory_now", 
        description="Ingest all newly appended lines from facts.jsonl through the locked LTM batch pipeline."
    )
    def sync_memory_now() -> str:
        try:
            summary = handlers.execute_pipeline_with_lock(
                db_path=DB_PATH,
                facts_jsonl_path=FACTS_JSONL,
                cursor_path=CURSOR_PATH,
                lock_path=LOCK_PATH,
                embed_fn=runtime_embed_fn
            )
            if summary is None:
                return "Sync execution completed: No new fact entries found to ingest or file is missing."
            return f"Sync successful! Inserted: {summary.inserted}, Reinforced: {summary.reinforced}, Contradicted: {summary.contradicted}."
        except handlers.FileLockError as e:
            return f"Sync bypassed: {str(e)}"
        except Exception as e:
            return f"Sync failed with error: {str(e)}"

    @mcp.tool(
        name="query_memory", 
        description="Query semantic information matching a human natural language query string."
    )
    def query_memory(query: str, limit: int = 5) -> list[dict]:
        try:
            return handlers.query_memory_handler(
                db_path=DB_PATH,
                query_text=query,
                embed_fn=runtime_embed_fn,
                limit=limit
            )
        except Exception as e:
            return [{"error": f"Query failed: {str(e)}"}]

    @mcp.tool(
        name="run_relation_maintenance", 
        description="Execute offline relational alias-clustering to collapse near-duplicate relation descriptors."
    )
    def run_relation_maintenance(similarity_threshold: float = 0.85) -> str:
        try:
            rows_changed = handlers.run_relation_maintenance_handler(
                db_path=DB_PATH,
                embed_fn=runtime_embed_fn,
                similarity_threshold=similarity_threshold
            )
            return f"Maintenance complete. Standardized {rows_changed} relation rows in database."
        except Exception as e:
            return f"Maintenance failed: {str(e)}"