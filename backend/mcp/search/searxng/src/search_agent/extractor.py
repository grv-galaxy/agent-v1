import asyncio
import trafilatura
from playwright.async_api import async_playwright

async def extract_url(url: str, min_length: int = 200) -> str | None:
    """
    Extracts the main content from a URL.
    Attempts a fast static fetch first. If that fails or yields very little text 
    (indicating a possible JS-heavy SPA), falls back to Playwright.
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
        
    # --- Fallback Path (Playwright) ---
    # Triggered if trafilatura returns None or very short text
    print(f"[extractor] Static extraction yielded insufficient data for {url}. Falling back to Playwright...")
    try:
        async with async_playwright() as p:
            # Launch headless chromium
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            
            # Wait for network idle to ensure JS has rendered
            await page.goto(url, wait_until="networkidle", timeout=15000)
            html = await page.content()
            
            await browser.close()
            
            # Extract content from the JS-rendered HTML
            if html:
                def _extract_html(h):
                    return trafilatura.extract(h)
                
                dynamic_text = await asyncio.to_thread(_extract_html, html)
                if dynamic_text:
                    return dynamic_text.strip()
                    
    except Exception as e:
        print(f"[extractor] Playwright fallback failed for {url}: {e}")
        
    # If all else fails, return whatever trafilatura found initially (even if short), or None
    return text.strip() if text else None
