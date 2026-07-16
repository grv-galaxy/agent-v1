import httpx
import xml.etree.ElementTree as ET
import urllib.parse
from src.search_agent.http_client import http_client

async def search_arxiv(query: str, entities: list[str] = None) -> list[dict]:
    """
    Searches arXiv for academic papers matching the query.
    """
    results = []
    quoted_query = urllib.parse.quote(query)
    # arXiv uses a simple REST API returning Atom XML
    url = f"http://export.arxiv.org/api/query?search_query=all:{quoted_query}&max_results=5"
    
    try:
        resp = await http_client.get(url, follow_redirects=True)
        if resp.status_code == 200:
            root = ET.fromstring(resp.text)
            # arXiv uses atom namespace
            ns = {'atom': 'http://www.w3.org/2005/Atom'}
            
            for entry in root.findall('atom:entry', ns):
                title = entry.find('atom:title', ns).text.replace('\n', ' ').strip()
                summary = entry.find('atom:summary', ns).text.replace('\n', ' ').strip()
                link = entry.find('atom:id', ns).text
                authors = [a.find('atom:name', ns).text for a in entry.findall('atom:author', ns)]
                published = entry.find('atom:published', ns).text
                
                content = f"Authors: {', '.join(authors)}\nPublished: {published}\nAbstract: {summary}"
                
                results.append({
                    "title": f"arXiv: {title}",
                    "url": link,
                    "content": content
                })
    except Exception as e:
        print(f"[arxiv] Error searching: {e}")
            
    return results
