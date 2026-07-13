import pytest
from src.search_agent.extractor import extract_url

@pytest.mark.asyncio
async def test_extract_url_static():
    """Test standard static extraction (Wikipedia). Should not need fallback."""
    # A known static page that Trafilatura handles perfectly
    url = "https://en.wikipedia.org/wiki/Python_(programming_language)"
    
    text = await extract_url(url)
    assert text is not None
    assert len(text) > 1000
    assert "Python" in text
    
@pytest.mark.asyncio
async def test_extract_url_dynamic():
    """Test JS-heavy extraction fallback."""
    # Note: For a reliable unit test without flakiness, we use a site known to 
    # require JS rendering for its core content, or just ensure the fallback 
    # executes without crashing.
    # We will use a typical SPA or a page that loads content dynamically.
    url = "https://example.com/" # Very short text, will trigger fallback
    
    text = await extract_url(url, min_length=500) # Force fallback by requiring high min_length
    assert text is not None
    assert len(text) > 50
    assert "documentation examples" in text
