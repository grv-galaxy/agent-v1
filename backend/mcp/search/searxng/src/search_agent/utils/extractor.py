import asyncio
from playwright.async_api import async_playwright
import trafilatura

async def extract_text_from_url(url: str, timeout: int = 10000) -> str:
    """
    Uses Playwright to render a webpage (executing Javascript) and 
    Trafilatura to extract the core article text from the rendered HTML.
    """
    html_content = ""
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            
            # Block media to speed up load times
            await page.route("**/*", lambda route: route.abort() 
                if route.request.resource_type in ["image", "media", "font"] 
                else route.continue_()
            )
            
            # Go to the URL and wait for it to load
            await page.goto(url, wait_until="domcontentloaded", timeout=timeout)
            
            # Give it a tiny bit of time for dynamic JS content to settle
            await asyncio.sleep(1)
            
            html_content = await page.content()
            await browser.close()
            
    except Exception as e:
        print(f"[extractor] Playwright failed for {url}: {e}")
        return f"Error extracting content: {e}"
        
    if html_content:
        # Run trafilatura synchronously in a thread because it can be CPU intensive
        extracted_text = await asyncio.to_thread(trafilatura.extract, html_content)
        return extracted_text or "No readable text found on page."
        
    return "Failed to retrieve page content."
