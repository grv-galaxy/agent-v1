import sqlite3
import json
import os
from datetime import datetime
from typing import Optional, List, Dict, Any

# Default path relative to project root
DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "telemetry.db")

def init_db(db_path: str = DEFAULT_DB_PATH) -> None:
    """Initializes the SQLite schema for telemetry if it doesn't exist."""
    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS queries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                query TEXT NOT NULL,
                latency_classify_ms INTEGER,
                latency_route_ms INTEGER,
                latency_searxng_ms INTEGER,
                latency_rank_ms INTEGER,
                latency_extract_ms INTEGER,
                latency_synthesize_ms INTEGER,
                engines_used TEXT,
                engines_skipped TEXT,
                top_urls TEXT,
                final_answer TEXT,
                citation_pass_rate REAL
            )
        """)
        conn.commit()
    finally:
        conn.close()

def log_query(
    query: str,
    latency_classify_ms: Optional[int] = None,
    latency_route_ms: Optional[int] = None,
    latency_searxng_ms: Optional[int] = None,
    latency_rank_ms: Optional[int] = None,
    latency_extract_ms: Optional[int] = None,
    latency_synthesize_ms: Optional[int] = None,
    engines_used: Optional[List[str]] = None,
    engines_skipped: Optional[List[str]] = None,
    top_urls: Optional[List[str]] = None,
    final_answer: Optional[str] = None,
    citation_pass_rate: Optional[float] = None,
    db_path: str = DEFAULT_DB_PATH
) -> None:
    """Logs a completed query and its latency waterfall to SQLite."""
    # Ensure JSON structures for arrays
    engines_used_str = json.dumps(engines_used or [])
    engines_skipped_str = json.dumps(engines_skipped or [])
    top_urls_str = json.dumps(top_urls or [])
    
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO queries (
                query, latency_classify_ms, latency_route_ms, latency_searxng_ms,
                latency_rank_ms, latency_extract_ms, latency_synthesize_ms,
                engines_used, engines_skipped, top_urls, final_answer, citation_pass_rate
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            query,
            latency_classify_ms,
            latency_route_ms,
            latency_searxng_ms,
            latency_rank_ms,
            latency_extract_ms,
            latency_synthesize_ms,
            engines_used_str,
            engines_skipped_str,
            top_urls_str,
            final_answer,
            citation_pass_rate
        ))
        conn.commit()
    finally:
        conn.close()
