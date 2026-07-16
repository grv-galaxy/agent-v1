import asyncio
from src.search_agent.extractor import extract_url

async def main():
    print("Extracting Yahoo Finance...")
    web_url = "https://finance.yahoo.com/quote/ADANIPOWER.NS"
    web_text = await extract_url(web_url)
    print(web_text[:500] if web_text else "None")

asyncio.run(main())
