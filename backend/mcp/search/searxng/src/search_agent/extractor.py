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

def _fast_trafilatura_extract(u):
    downloaded = trafilatura.fetch_url(u)
    if downloaded:
        return trafilatura.extract(downloaded)
    return None

async def extract_url(url: str, query: str = "", min_length: int = 200) -> str | None:
    """
    Extracts the main content from a URL using SOTA methods via the FastMCP engine.
    """
    # --- PDF RAG Path ---
    if url.lower().endswith('.pdf'):
        print(f"[extractor] PDF detected for {url}. Routing to FastMCP RAG...")
        from src.search_agent.mcp_server import extract_pdf_rag
        pdf_text = await extract_pdf_rag(url, query)
        if pdf_text and not pdf_text.startswith("Error"):
            return pdf_text.strip()
        return None

    # --- Primary Fast Path (Trafilatura) ---
    text = await asyncio.to_thread(_fast_trafilatura_extract, url)
    
    if text and len(text.strip()) >= min_length:
        return text.strip()
        
    # --- Fallback Path (Playwright Stealth MCP Tool) ---
    print(f"[extractor] Static extraction insufficient for {url}. Routing to FastMCP Playwright...")
    from src.search_agent.mcp_server import extract_webpage
    dynamic_text = await extract_webpage(url)
    
    if dynamic_text and not dynamic_text.startswith("Error"):
        return dynamic_text.strip()
        
    return text.strip() if text else None
