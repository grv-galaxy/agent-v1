import asyncio
from src.search_agent.extractor import extract_url

async def main():
    print("Extracting BSE India...")
    web_url = "https://www.bseindia.com/stock-share-price/r-m-drip-and-sprinklers-systems-ltd/rmdrip/544456/"
    web_text = await extract_url(web_url)
    print(web_text[:500] if web_text else "None")

asyncio.run(main())
