import httpx
import urllib.parse

async def search_gdelt(query: str) -> list[dict]:
    """
    Fetches global news from GDELT API using the artlist format.
    """
    # GDELT requires query to be url encoded
    encoded_query = urllib.parse.quote(query)
    url = f"https://api.gdeltproject.org/api/v2/search/search?query={encoded_query}&format=json&mode=artlist"
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                results = []
                for art in data.get("articles", [])[:10]:
                    title = art.get("title", "")
                    domain = art.get("domain", "")
                    results.append({
                        "title": f"[GDELT - {domain}] {title}",
                        "url": art.get("url", ""),
                        # GDELT artlist doesn't provide a full summary, so we use title as a fallback snippet.
                        "content": title 
                    })
                return results
        except Exception as e:
            print(f"[gdelt] Error fetching {url}: {e}")
            
    return []
