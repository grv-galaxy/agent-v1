import time


def process_memory(session_id: str):

    print("\n==============================")
    print("✅ Started MCP Check Pass")
    print(f"Session : {session_id}")

    time.sleep(3)

    print("🧠 Running dummy memory manager...")

    time.sleep(2)

    print("✅ Ending MCP Check Pass")
    print("==============================\n")

    return {
        "status": "success",
        "session": session_id,
    }