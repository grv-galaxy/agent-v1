# backend/app/services/ltm_client.py
import os
from mcp import ClientSession
from mcp.client.sse import sse_client

MCP_SERVER_URL = os.environ.get("LTM_MCP_URL", "http://127.0.0.1:8765/sse")

async def call_ltm_tool(tool_name: str, arguments: dict | None = None):
    async with sse_client(MCP_SERVER_URL) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            return await session.call_tool(tool_name, arguments=arguments or {})