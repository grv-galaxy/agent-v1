import httpx
import urllib.parse

async def search_github(query: str, entities: list[str] = None) -> list[dict]:
    """
    Searches GitHub for repositories matching the query.
    """
    results = []
    quoted_query = urllib.parse.quote(query)
    # Use GitHub search API
    url = f"https://api.github.com/search/repositories?q={quoted_query}&per_page=5"
    
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Search-Agent-v1"
    }
    
    async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
        try:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                data = resp.json().get("items", [])
                for repo in data:
                    content = f"Stars: {repo.get('stargazers_count')}\nLanguage: {repo.get('language')}\nDescription: {repo.get('description')}"
                    
                    results.append({
                        "title": f"GitHub: {repo.get('full_name')}",
                        "url": repo.get("html_url"),
                        "content": content
                    })
        except Exception as e:
            print(f"[github] Error searching: {e}")
            
    return results
