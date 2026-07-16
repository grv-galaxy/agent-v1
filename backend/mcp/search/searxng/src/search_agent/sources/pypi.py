import httpx
from src.search_agent.http_client import http_client

async def search_pypi(query: str, entities: list[str] = None) -> list[dict]:
    """
    Fetches package metadata from PyPI for each extracted entity.
    """
    if not entities:
        # Fallback: try using the raw query as the package name if it's a single word
        if len(query.split()) == 1:
            entities = [query]
        else:
            return []
            
    results = []
    for pkg in entities:
        # PyPI package names usually don't have spaces, but entities might
        pkg_name = pkg.replace(" ", "-").lower()
        try:
            resp = await http_client.get(f"https://pypi.org/pypi/{pkg_name}/json", follow_redirects=True)
            if resp.status_code == 200:
                data = resp.json().get("info", {})
                content = f"Version: {data.get('version')}\nSummary: {data.get('summary')}\nAuthor: {data.get('author')}"
                
                results.append({
                    "title": f"PyPI: {data.get('name')}",
                    "url": data.get("package_url", f"https://pypi.org/project/{pkg_name}/"),
                    "content": content
                })
        except Exception as e:
                print(f"[pypi] Error fetching {pkg_name}: {e}")
                continue
                
    return results
