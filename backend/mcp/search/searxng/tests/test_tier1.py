import asyncio
import pytest
from src.search_agent.sources.pypi import search_pypi
from src.search_agent.sources.npm import search_npm
from src.search_agent.sources.github import search_github
from src.search_agent.sources.arxiv import search_arxiv
from src.search_agent.sources.wikipedia import search_wikipedia
from src.search_agent.sources.worldbank import search_worldbank

@pytest.mark.asyncio
async def test_all():
    print("Testing PyPI...")
    try:
        res = await search_pypi("fastapi", ["fastapi"])
        print(f"PyPI: {len(res)} results")
        if res: print(res[0]['title'])
    except Exception as e:
        print(f"PyPI failed: {e}")

    print("\nTesting NPM...")
    try:
        res = await search_npm("react")
        print(f"NPM: {len(res)} results")
        if res: print(res[0]['title'])
    except Exception as e:
        print(f"NPM failed: {e}")

    print("\nTesting GitHub...")
    try:
        res = await search_github("fastapi")
        print(f"GitHub: {len(res)} results")
        if res: print(res[0]['title'])
    except Exception as e:
        print(f"GitHub failed: {e}")

    print("\nTesting arXiv...")
    try:
        res = await search_arxiv("attention is all you need")
        print(f"arXiv: {len(res)} results")
        if res: 
            print(res[0]['title'])
        else:
            import httpx
            async with httpx.AsyncClient() as client:
                print((await client.get("http://export.arxiv.org/api/query?search_query=all:attention%20is%20all%20you%20need&max_results=5")).text)
    except Exception as e:
        print(f"arXiv failed: {e}")

    print("\nTesting Wikipedia...")
    try:
        res = await search_wikipedia("quantum mechanics")
        print(f"Wikipedia: {len(res)} results")
        if res: 
            print(res[0]['title'])
        else:
            import httpx
            async with httpx.AsyncClient() as client:
                print((await client.get("https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch=quantum%20mechanics&utf8=&format=json&srlimit=5")).text)
    except Exception as e:
        print(f"Wikipedia failed: {e}")

    print("\nTesting World Bank...")
    try:
        res = await search_worldbank("education")
        print(f"World Bank: {len(res)} results")
        if res: print(res[0]['title'])
    except Exception as e:
        print(f"World Bank failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_all())
