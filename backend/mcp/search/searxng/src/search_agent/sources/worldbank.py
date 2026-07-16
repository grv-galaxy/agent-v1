import httpx
import urllib.parse
from src.search_agent.http_client import http_client

async def search_worldbank(query: str, entities: list[str] = None) -> list[dict]:
    """
    Searches World Bank data/projects.
    """
    results = []
    quoted_query = urllib.parse.quote(query)
    # Using the World Bank Projects API as a text-searchable endpoint
    url = f"https://search.worldbank.org/api/v2/projects?format=json&qterm={quoted_query}&rows=5"
    
    try:
        resp = await http_client.get(url)
        if resp.status_code == 200:
            data = resp.json().get("projects", {})
            
            # The API returns a dictionary of projects keyed by ID
            for proj_id, proj in data.items():
                # The first item might be a string indicating total rows if it's not a dict
                if not isinstance(proj, dict):
                    continue
                    
                title = proj.get("project_name", "Unknown Project")
                url = proj.get("url", f"https://projects.worldbank.org/en/projects-operations/project-detail/{proj_id}")
                abstract = proj.get("project_abstract", {}).get("cdata", "No abstract available.")
                
                results.append({
                    "title": f"World Bank: {title}",
                    "url": url,
                    "content": abstract
                })
    except Exception as e:
            print(f"[worldbank] Error searching: {e}")
            
    return results
