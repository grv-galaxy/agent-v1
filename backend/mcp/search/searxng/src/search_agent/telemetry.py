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
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tool_contribution (
                query_id TEXT,
                sub_query_id TEXT,
                source_id TEXT,
                category TEXT,
                elapsed_ms INTEGER,
                called BOOLEAN,
                returned_results BOOLEAN,
                result_count INTEGER,
                survived_biencoder BOOLEAN,
                survived_crossencoder BOOLEAN,
                cited_in_answer BOOLEAN,
                citation_check_passed BOOLEAN,
                circuit_breaker_state TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS llm_calls (
                query_id TEXT,
                sub_query_id TEXT,
                step TEXT,
                model TEXT,
                provider TEXT,
                prompt_text TEXT,
                system_prompt_text TEXT,
                response_text TEXT,
                input_tokens INTEGER,
                output_tokens INTEGER,
                total_tokens INTEGER,
                elapsed_ms INTEGER,
                cost_usd REAL,
                temperature REAL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        
        # Retrofit existing tables if they don't have the column
        try:
            cursor.execute("ALTER TABLE tool_contribution ADD COLUMN sub_query_id TEXT")
        except sqlite3.OperationalError:
            pass
            
        try:
            cursor.execute("ALTER TABLE llm_calls ADD COLUMN sub_query_id TEXT")
        except sqlite3.OperationalError:
            pass
            
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

def log_tool_contributions(contributions: List[Dict[str, Any]], db_path: str = DEFAULT_DB_PATH) -> None:
    """Batch inserts tool contributions for a query."""
    if not contributions:
        return
        
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.executemany("""
            INSERT INTO tool_contribution (
                query_id, sub_query_id, source_id, category, elapsed_ms, called, returned_results,
                result_count, survived_biencoder, survived_crossencoder, cited_in_answer,
                citation_check_passed, circuit_breaker_state
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            (
                c.get("query_id"),
                c.get("sub_query_id"),
                c.get("source_id"),
                c.get("category"),
                c.get("elapsed_ms"),
                c.get("called", False),
                c.get("returned_results", False),
                c.get("result_count", 0),
                c.get("survived_biencoder", False),
                c.get("survived_crossencoder", False),
                c.get("cited_in_answer", False),
                c.get("citation_check_passed", False),
                c.get("circuit_breaker_state")
            ) for c in contributions
        ])
        conn.commit()
    finally:
        conn.close()

def log_llm_call(
    query_id: str,
    step: str,
    model: str,
    provider: str,
    prompt_text: str,
    system_prompt_text: Optional[str],
    response_text: str,
    input_tokens: Optional[int],
    output_tokens: Optional[int],
    total_tokens: Optional[int],
    elapsed_ms: int,
    cost_usd: float = 0.0,
    temperature: Optional[float] = None,
    sub_query_id: Optional[str] = None,
    db_path: str = DEFAULT_DB_PATH
) -> None:
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO llm_calls (
                query_id, sub_query_id, step, model, provider, prompt_text, system_prompt_text,
                response_text, input_tokens, output_tokens, total_tokens, elapsed_ms, cost_usd, temperature
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            query_id, sub_query_id, step, model, provider, prompt_text, system_prompt_text,
            response_text, input_tokens, output_tokens, total_tokens, elapsed_ms, cost_usd, temperature
        ))
        conn.commit()
    finally:
        conn.close()
