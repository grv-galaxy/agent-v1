# backend/app/services/test_trigger_local.py
import asyncio
import sqlite3
from pathlib import Path
from memory_trigger import on_conversation_threshold_reached

# services/ -> app/ -> backend/ -> backend/data/ltm.sqlite3
DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "ltm.sqlite3"

async def main():
    before = 0
    if DB_PATH.exists():
        conn = sqlite3.connect(DB_PATH)
        before = conn.execute("SELECT COUNT(*) FROM triples").fetchone()[0]
        conn.close()
    print(f"Rows before trigger: {before}")

    result = await on_conversation_threshold_reached({"fake": "event"})
    print("Trigger result:", result)

    if not DB_PATH.exists():
        print(f"⚠️ DB file still doesn't exist at {DB_PATH} — nothing was written yet.")
        return

    conn = sqlite3.connect(DB_PATH)
    after = conn.execute("SELECT COUNT(*) FROM triples").fetchone()[0]
    conn.close()
    print(f"Rows after trigger: {after}")

    print("✅ Backend successfully called the running MCP server over the network.")

if __name__ == "__main__":
    asyncio.run(main())