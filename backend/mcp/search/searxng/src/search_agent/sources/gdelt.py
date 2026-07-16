import httpx
import urllib.parse
from src.search_agent.http_client import http_client

async def search_gdelt(query: str) -> list[dict]:
    """
    Fetches global news from GDELT API using the artlist format.
    """
    # GDELT requires query to be url encoded
    encoded_query = urllib.parse.quote(query)
    url = f"https://api.gdeltproject.org/api/v2/search/search?query={encoded_query}&format=json&mode=artlist"
    
    try:
        # Some servers block the default httpx User-Agent
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = await http_client.get(url, headers=headers, timeout=5.0)
        
        if resp.status_code == 200:
            data = resp.json()
            results = []
            for art in data.get("articles", [])[:10]:
                title = art.get("title", "")
                domain = art.get("domain", "")
                results.append({
                    "title": f"[GDELT - {domain}] {title}",
                    "url": art.get("url", ""),
                    "content": title 
                })
            return results
    except Exception as e:
        # Don't print the error if it's just a 404 or DecodeError from GDELT finding 0 articles
        if "JSONDecodeError" not in str(type(e)):
            print(f"[gdelt] Error fetching {url}: {e}")
            
    return []

