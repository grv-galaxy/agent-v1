import httpx
import json
from fastmcp import FastMCP
from src.search_agent.http_client import http_client

# Initialize the FastMCP server
mcp = FastMCP("SearXNG Search Agent")

# SearXNG local endpoint
SEARXNG_URL = "http://localhost:8080/search"

@mcp.tool()
async def search_web(
    query: str, 
    categories: str = "", 
    time_range: str = "", 
    language: str = "en-US", 
    engines: str = ""
) -> str:
    """
    Executes a web search against the local SearXNG instance.
    Returns the JSON payload of the search results.
    """
    params = {
        "q": query,
        "format": "json",
    }
    
    # Add optional parameters only if provided
    if categories:
        params["categories"] = categories
    if time_range:
        params["time_range"] = time_range
    if language:
        params["language"] = language
    if engines:
        params["engines"] = engines

    # We use a strict timeout to fail fast so the orchestrator's circuit breaker can react.
    # The timeout should be slightly higher than SearXNG's internal timeout (which we set to 2.5s)
    try:
        response = await http_client.get(SEARXNG_URL, params=params)
        response.raise_for_status()
        
        # We return it as a formatted string rather than raw JSON because 
        # MCP tools typically return strings, but since we will parse it 
        # in the orchestrator, we just return the text payload directly.
        return response.text
        
    except httpx.TimeoutException:
        # MCP tools can return error strings or raise exceptions
        # The orchestrator will catch this to trip the circuit breaker
        raise RuntimeError(f"Timeout connecting to SearXNG")
    except httpx.HTTPStatusError as e:
        raise RuntimeError(f"HTTP Error from SearXNG: {e.response.status_code}")
    except httpx.RequestError as e:
        raise RuntimeError(f"Request Error connecting to SearXNG: {str(e)}")

# This allows running via `fastmcp dev src/search_agent/mcp_server.py`
if __name__ == "__main__":
    mcp.run(transport="stdio")

# --- ADVANCED SCRAPING & RAG RESOURCES ---
import asyncio
from typing import Optional

import sys
import threading

# Lazy-loaded globals to keep FastMCP boot fast and memory usage efficient
_playwright = None
_browser_context = None

_onnx_ranker = None
_playwright_loop: Optional[asyncio.AbstractEventLoop] = None
_playwright_thread: Optional[threading.Thread] = None

def _run_playwright_thread():
    """Runs a dedicated ProactorEventLoop for Playwright on Windows."""
    global _playwright_loop
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    _playwright_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_playwright_loop)
    _playwright_loop.run_forever()

def _ensure_playwright_thread():
    global _playwright_thread
    if _playwright_thread is None or not _playwright_thread.is_alive():
        _playwright_thread = threading.Thread(target=_run_playwright_thread, daemon=True)
        _playwright_thread.start()
        import time
        time.sleep(0.1)

async def _get_browser_context():
    global _playwright, _browser_context
    if _browser_context is None:
        from playwright.async_api import async_playwright
        _playwright = await async_playwright().start()
        browser = await _playwright.chromium.launch(headless=True)
        _browser_context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
        )
    return _browser_context

def get_ranker():
    global _onnx_ranker
    if _onnx_ranker is None:
        from src.search_agent.ranker import ONNXRanker, BI_ENCODER_PATH, CROSS_ENCODER_PATH
        _onnx_ranker = ONNXRanker(BI_ENCODER_PATH, CROSS_ENCODER_PATH)
    return _onnx_ranker

async def _do_extract_webpage(url: str) -> str:
    from playwright_stealth import Stealth
    import trafilatura
    
    context = await _get_browser_context()
    page = await context.new_page()
    await Stealth().apply_stealth_async(page)
    
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=10000)
        # Give it a tiny bit of time for initial JS frameworks to render the DOM
        import asyncio
        await asyncio.sleep(1.5)
        html_content = await page.content()
    except Exception as e:
        await page.close()
        return f"Error extracting page: {str(e)}"
        
    await page.close()
    
    clean_text = trafilatura.extract(html_content)
    if clean_text:
        return clean_text
    
    return "Failed to extract clean text from the rendered page."

@mcp.tool()
async def extract_webpage(url: str) -> str:
    """
    Called by FastAPI/Uvicorn (SelectorEventLoop).
    Dispatches the actual extraction to the Playwright thread (ProactorEventLoop).
    """
    _ensure_playwright_thread()
    # Threadsafe execution
    future = asyncio.run_coroutine_threadsafe(_do_extract_webpage(url), _playwright_loop)
    return await asyncio.wrap_future(future)


@mcp.tool()
async def extract_pdf_rag(url: str, query: str) -> str:
    import fitz
    import httpx
    import faiss
    import numpy as np
    import io
    
    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            resp = await client.get(url, timeout=15.0)
            resp.raise_for_status()
            pdf_bytes = resp.content
            
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        blocks = []
        for page in doc:
            page_blocks = page.get_text("blocks")
            for b in page_blocks:
                text = b[4].strip()
                if len(text.split()) > 5:
                    blocks.append(text)
        doc.close()
        
        if not blocks:
            return "PDF contained no readable text blocks."
            
        chunks = []
        current_chunk = []
        current_length = 0
        
        for block in blocks:
            words = block.split()
            current_chunk.append(block)
            current_length += len(words)
            
            if current_length >= 500:
                chunks.append("\n\n".join(current_chunk))
                overlap_words = 0
                overlap_chunk = []
                for b in reversed(current_chunk):
                    if overlap_words >= 150:
                        break
                    overlap_chunk.insert(0, b)
                    overlap_words += len(b.split())
                    
                current_chunk = overlap_chunk
                current_length = overlap_words
                
        if current_chunk and len(current_chunk) > 0:
            chunks.append("\n\n".join(current_chunk))
            
        if not chunks:
            return "Failed to chunk PDF."
            
        ranker = get_ranker()
        
        query_emb = ranker.get_query_embedding(query)
        query_emb = query_emb.reshape(1, -1)
        
        encoded = ranker.bi_tokenizer.encode_batch(chunks)
        input_ids = np.array([e.ids for e in encoded], dtype=np.int64)
        attention_mask = np.array([e.attention_mask for e in encoded], dtype=np.int64)
        inputs = {'input_ids': input_ids, 'attention_mask': attention_mask}
        expected_inputs = [i.name for i in ranker.bi_session.get_inputs()]
        if 'token_type_ids' in expected_inputs:
            inputs['token_type_ids'] = np.array([e.type_ids for e in encoded], dtype=np.int64)
            
        outputs = ranker.bi_session.run(None, inputs)
        token_embeddings = outputs[0]
        pooled = ranker._mean_pooling(token_embeddings, attention_mask)
        norms = np.linalg.norm(pooled, axis=1, keepdims=True)
        chunk_embs = pooled / np.clip(norms, a_min=1e-9, a_max=None)
        
        dimension = chunk_embs.shape[1]
        index = faiss.IndexFlatIP(dimension)
        index.add(chunk_embs)
        
        k = min(3, len(chunks))
        distances, indices = index.search(query_emb, k)
        
        top_chunks = []
        for idx in indices[0]:
            top_chunks.append(chunks[idx])
            
        return "\n\n---\n\n".join(top_chunks)
        
    except Exception as e:
        return f"Error extracting PDF: {str(e)}"
