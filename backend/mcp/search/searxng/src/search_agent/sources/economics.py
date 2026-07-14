import json
from src.search_agent.mcp_server import search_web

async def search_economic_databases(query: str) -> list[dict]:
    """
    Searches World Bank, IMF, and RBI DBIE by leveraging SearXNG with site filters.
    """
    advanced_query = f"{query} (site:worldbank.org OR site:imf.org OR site:dbie.rbi.org.in OR site:rbi.org.in)"
    
    try:
        raw_json_str = await search_web(
            query=advanced_query,
            categories="general"
        )
        data = json.loads(raw_json_str)
        results = data.get("results", [])
        
        formatted_results = []
        for r in results[:5]:
            title = r.get("title", "")
            url = r.get("url", "")
            
            # Identify source visually
            prefix = "Economic DB"
            if "worldbank.org" in url:
                prefix = "World Bank"
            elif "imf.org" in url:
                prefix = "IMF"
            elif "rbi.org.in" in url:
                prefix = "RBI"
                
            formatted_results.append({
                "title": f"[{prefix}] {title}",
                "url": url,
                "content": r.get("content", "")
            })
            
        return formatted_results
    except Exception as e:
        print(f"[economic_databases] Error: {e}")
        return []
