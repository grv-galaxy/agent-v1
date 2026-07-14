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

def _fetch_and_extract_sync(url: str, timeout: int = 10) -> str:
    """
    Fetches URL with realistic browser headers and extracts main text via trafilatura.
    Playwright has been removed — it conflicts with Uvicorn's SelectorEventLoop on Windows.
    """
    try:
        with httpx.Client(headers=_HEADERS, follow_redirects=True, timeout=float(timeout)) as client:
            response = client.get(url)
            response.raise_for_status()
            extracted = trafilatura.extract(response.text)
            if extracted:
                return extracted
            return "No readable text found on page."
    except Exception as e:
        print(f"[extractor] httpx fetch failed for {url}: {e}")
        return f"Error extracting content: {e}"

async def extract_text_from_url(url: str, timeout: int = 10000) -> str:
    """
    Extracts the core article text from a URL using httpx + trafilatura.
    Runs in a background thread to avoid blocking the async event loop.
    
    timeout is in milliseconds (kept for API compatibility) and converted to seconds internally.
    """
    return await asyncio.to_thread(_fetch_and_extract_sync, url, timeout // 1000)
