import asyncio
from src.search_agent.sources.wikipedia import search_wikipedia

async def main():
    res = await search_wikipedia("President of Ukraine")
    print(res)

asyncio.run(main())
