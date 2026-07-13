import json
import asyncio
from src.search_agent.utils.extractor import extract_text_from_url
from src.search_agent.mcp_server import search_web

async def _do_searxng_search(query: str):
    raw = await search_web(query)
    return json.loads(raw).get("results", [])

async def search_indian_kanoon(query: str, entities: list[str] = None) -> list[dict]:
    """
    Searches Indian Kanoon for legal cases.
    We leverage SearXNG to find the exact case URL, then deep-read it using Playwright+Trafilatura.
    """
    print(f"[extraction] Searching Indian Kanoon for: {query}")
    # 1. Use SearXNG to find the top Indian Kanoon link
    searxng_results = await _do_searxng_search(f"site:indiankanoon.org {query}")
    
    if not searxng_results:
        return []
        
    # Take the top result URL
    top_url = searxng_results[0].get("url")
    if not top_url:
        return []
        
    print(f"[extraction] Deep reading Indian Kanoon URL: {top_url}")
    
    # 2. Extract the full case text
    full_text = await extract_text_from_url(top_url)
    
    # Trim to 2000 chars to avoid blowing up LLM context window
    if len(full_text) > 2000:
        full_text = full_text[:2000] + "\n...[TRUNCATED]"
        
    return [{
        "title": searxng_results[0].get("title", "Indian Kanoon Case"),
        "url": top_url,
        "content": full_text
    }]

async def search_wipo(query: str, entities: list[str] = None) -> list[dict]:
    """
    Searches WIPO Patentscope for global patents using deep-read extraction.
    """
    print(f"[extraction] Searching WIPO for: {query}")
    searxng_results = await _do_searxng_search(f"site:patentscope.wipo.int {query}")
    
    if not searxng_results:
        return []
        
    top_url = searxng_results[0].get("url")
    if not top_url:
        return []
        
    print(f"[extraction] Deep reading WIPO URL: {top_url}")
    full_text = await extract_text_from_url(top_url)
    
    if len(full_text) > 2000:
        full_text = full_text[:2000] + "\n...[TRUNCATED]"
        
    return [{
        "title": searxng_results[0].get("title", "WIPO Patent"),
        "url": top_url,
        "content": full_text
    }]

async def fallback_docs_search(query: str, entities: list[str] = None) -> list[dict]:
    """
    Generic pipeline to deep-read the top results for IT/Package queries.
    """
    print(f"[extraction] Fallback docs searching for: {query}")
    searxng_results = await _do_searxng_search(query)
    
    if not searxng_results:
        return []
        
    urls = [res.get("url") for res in searxng_results[:2] if res.get("url")]
    
    results = []
    
    tasks = [extract_text_from_url(url) for url in urls]
    extracted_texts = await asyncio.gather(*tasks, return_exceptions=True)
    
    for i, text in enumerate(extracted_texts):
        url = urls[i]
        if isinstance(text, str) and "Error extracting content" not in text:
            if len(text) > 1500:
                text = text[:1500] + "..."
            results.append({
                "title": searxng_results[i].get("title", f"Extracted Doc {i+1}"),
                "url": url,
                "content": text
            })
            
    return results
