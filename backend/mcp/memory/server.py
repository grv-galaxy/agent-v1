from fastmcp import FastMCP

from handlers import process_memory

mcp = FastMCP("Memory MCP")

mcp.tool(process_memory)

if __name__ == "__main__":
    print("=" * 50)
    print("🚀 Memory MCP Started")
    print("📡 Waiting for memory jobs...")
    print("=" * 50)

    mcp.run()