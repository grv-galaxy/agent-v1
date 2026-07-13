import sqlite3
import json
import pytest
import os
from src.search_agent.telemetry import init_db, log_query

@pytest.fixture
def memory_db():
    """Provides an in-memory SQLite database path for testing."""
    # Using a file-based temporary DB because Python sqlite3 
    # connection to ':memory:' creates a new DB per connection,
    # which breaks across init_db() and log_query() calls.
    db_path = "test_telemetry.db"
    
    # Setup
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except OSError:
            pass # Ignore if locked by something else
            
    init_db(db_path)
    yield db_path
    
    # Teardown
    if os.path.exists(db_path):
        os.remove(db_path)

def test_telemetry_insert_and_read(memory_db):
    # Log a mock query
    log_query(
        query="What is the speed of light?",
        latency_classify_ms=500,
        latency_route_ms=1,
        latency_searxng_ms=1200,
        latency_rank_ms=45,
        latency_extract_ms=0,
        latency_synthesize_ms=2100,
        engines_used=["duckduckgo", "brave"],
        engines_skipped=["startpage"],
        top_urls=["https://en.wikipedia.org/wiki/Speed_of_light"],
        final_answer="The speed of light is exactly 299,792,458 metres per second [1].",
        citation_pass_rate=1.0,
        db_path=memory_db
    )
    
    # Connect and verify
    conn = sqlite3.connect(memory_db)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM queries")
        rows = cursor.fetchall()
        
        # 1 row inserted
        assert len(rows) == 1
        
        row = rows[0]
        # Check query string
        assert row[2] == "What is the speed of light?"
        
        # Check latencies
        assert row[3] == 500  # classify
        assert row[4] == 1    # route
        assert row[5] == 1200 # searxng
        
        # Check JSON parsing of engines
        engines_used = json.loads(row[9])
        assert "duckduckgo" in engines_used
        assert "brave" in engines_used
        
        engines_skipped = json.loads(row[10])
        assert "startpage" in engines_skipped
        
        # Check citation rate
        assert row[13] == 1.0
    finally:
        conn.close()
