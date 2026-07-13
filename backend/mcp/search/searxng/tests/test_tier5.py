import asyncio
import pytest
from src.search_agent.sources.extraction import search_indian_kanoon, search_wipo, fallback_docs_search

@pytest.mark.asyncio
async def test_tier5():
    print("Testing Indian Kanoon Extraction (Kesavananda Bharati)...")
    try:
        res = await search_indian_kanoon("Kesavananda Bharati")
        print(f"Kanoon: {len(res)} results")
        if res:
            print(f"URL: {res[0]['url']}")
            print(f"Content snippet: {res[0]['content'][:300]}...\n")
    except Exception as e:
        print(f"Kanoon failed: {e}")

    print("Testing WIPO Extraction (CRISPR)...")
    try:
        res = await search_wipo("CRISPR Cas9")
        print(f"WIPO: {len(res)} results")
        if res:
            print(f"URL: {res[0]['url']}")
            print(f"Content snippet: {res[0]['content'][:300]}...\n")
    except Exception as e:
        print(f"WIPO failed: {e}")

    print("Testing Generic Docs Fallback (FastAPI docs)...")
    try:
        res = await fallback_docs_search("FastAPI advanced middleware docs")
        print(f"Fallback Docs: {len(res)} results")
        if res:
            print(f"URL: {res[0]['url']}")
            print(f"Content snippet: {res[0]['content'][:300]}...\n")
    except Exception as e:
        print(f"Fallback failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_tier5())
