import httpx
import urllib.parse

async def search_npm(query: str, entities: list[str] = None) -> list[dict]:
    """
    Searches NPM registry for packages matching the query.
    """
    results = []
    quoted_query = urllib.parse.quote(query)
    # Use the NPM search endpoint which accepts text queries
    url = f"https://registry.npmjs.org/-/v1/search?text={quoted_query}&size=5"
    
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            resp = await client.get(url)
            if resp.status_code == 200:
                data = resp.json().get("objects", [])
                for obj in data:
                    pkg = obj.get("package", {})
                    content = f"Version: {pkg.get('version')}\nSummary: {pkg.get('description')}\nPublisher: {pkg.get('publisher', {}).get('username')}"
                    
                    results.append({
                        "title": f"npm: {pkg.get('name')}",
                        "url": pkg.get("links", {}).get("npm", f"https://www.npmjs.com/package/{pkg.get('name')}"),
                        "content": content
                    })
        except Exception as e:
            print(f"[npm] Error searching: {e}")
            
    return results
