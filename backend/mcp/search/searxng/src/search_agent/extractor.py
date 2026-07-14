import asyncio
import httpx
import trafilatura

# Realistic browser headers to bypass simple bot-blockers
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

def _httpx_fetch_and_extract(url: str) -> str | None:
    """
    Fetches a URL using httpx with realistic browser headers and then 
    extracts the main text content using trafilatura.
    """
    try:
        with httpx.Client(headers=_HEADERS, follow_redirects=True, timeout=15.0) as client:
            response = client.get(url)
            response.raise_for_status()
            return trafilatura.extract(response.text)
    except Exception as e:
        print(f"[extractor] httpx fetch failed for {url}: {e}")
        return None

async def extract_url(url: str, min_length: int = 200) -> str | None:
    """
    Extracts the main content from a URL.
    
    Strategy:
    1. Fast path: trafilatura's built-in fetcher (uses simple requests internally)
    2. Fallback: httpx with full browser-like headers to overcome bot-blockers
    
    Playwright has been removed entirely because it requires subprocess spawning
    which conflicts with Uvicorn's SelectorEventLoop on Windows.
    """
    
    # --- Primary Fast Path (Trafilatura) ---
    def _fetch_and_extract(u):
        downloaded = trafilatura.fetch_url(u)
        if downloaded:
            return trafilatura.extract(downloaded)
        return None
        
    text = await asyncio.to_thread(_fetch_and_extract, url)
    
    # If the text is meaningful enough, return it immediately
    if text and len(text.strip()) >= min_length:
        return text.strip()
        
    # --- Fallback Path (httpx with realistic headers) ---
    # Triggered if trafilatura returns None or very short text (bot-blocked / SPA)
    print(f"[extractor] Static extraction insufficient for {url}. Trying httpx with browser headers...")
    dynamic_text = await asyncio.to_thread(_httpx_fetch_and_extract, url)
    
    if dynamic_text and len(dynamic_text.strip()) >= min_length:
        return dynamic_text.strip()
        
    # If all else fails, return whatever was found initially, or None
    return text.strip() if text else None
