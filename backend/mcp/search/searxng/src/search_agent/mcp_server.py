import httpx
import json
from fastmcp import FastMCP

# Initialize the FastMCP server
mcp = FastMCP("SearXNG Search Agent")

# SearXNG local endpoint
SEARXNG_URL = "http://localhost:8080/search"

@mcp.tool()
async def search_web(
    query: str, 
    categories: str = "", 
    time_range: str = "", 
    language: str = "en-US", 
    engines: str = ""
) -> str:
    """
    Executes a web search against the local SearXNG instance.
    Returns the JSON payload of the search results.
    """
    params = {
        "q": query,
        "format": "json",
    }
    
    # Add optional parameters only if provided
    if categories:
        params["categories"] = categories
    if time_range:
        params["time_range"] = time_range
    if language:
        params["language"] = language
    if engines:
        params["engines"] = engines

    # We use a strict timeout to fail fast so the orchestrator's circuit breaker can react.
    # The timeout should be slightly higher than SearXNG's internal timeout (which we set to 2.5s)
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(SEARXNG_URL, params=params)
            response.raise_for_status()
            
            # We return it as a formatted string rather than raw JSON because 
            # MCP tools typically return strings, but since we will parse it 
            # in the orchestrator, we just return the text payload directly.
            return response.text
            
        except httpx.TimeoutException:
            # MCP tools can return error strings or raise exceptions
            # The orchestrator will catch this to trip the circuit breaker
            raise RuntimeError(f"Timeout connecting to SearXNG")
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"HTTP Error from SearXNG: {e.response.status_code}")
        except httpx.RequestError as e:
            raise RuntimeError(f"Request Error connecting to SearXNG: {str(e)}")

# This allows running via `fastmcp dev src/search_agent/mcp_server.py`
if __name__ == "__main__":
    mcp.run(transport="stdio")
