import asyncio
import sys

# Ensure the external wikipedia tool is in the path
tool_dir = r"C:\Users\kumar\Documents\agent-v1\backend\mcp\search\wikipedia"
if tool_dir not in sys.path:
    sys.path.append(tool_dir)

from search_tool import wikipedia_search

async def search_wikipedia(query: str, entities: list[str] = None) -> list[dict]:
    """
    Uses the external Wikipedia search tool (search_tool.py) and wraps it asynchronously.
    """
    # Run the synchronous requests-based tool in a thread pool to avoid blocking the orchestrator
    res = await asyncio.to_thread(wikipedia_search, query, 6)
    
    if "error" in res:
        print(f"[wikipedia] Error: {res['error']}")
        return []
        
    # Map the custom tool's output to our standard format
    title = res.get("title", "Unknown")
    url = res.get("url", "")
    
    content_lines = []
    
    facts = res.get("facts", {})
    if facts:
        content_lines.append("Facts:")
        for k, v in facts.items():
            content_lines.append(f"  {k}: {v}")
    else:
        points = res.get("points", [])
        if points:
            content_lines.append("Summary:")
            for p in points:
                content_lines.append(f"  - {p}")
            
    content = "\n".join(content_lines)
    
    return [{
        "title": f"Wikipedia: {title}",
        "url": url,
        "content": content
    }]
