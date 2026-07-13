import asyncio
import pytest
from src.search_agent.sources.rss_fetcher import fetch_rss_feeds

@pytest.mark.asyncio
async def test_tier3():
    print("Testing Global News RSS (BBC, NYT)...")
    try:
        urls = [
            "http://feeds.bbci.co.uk/news/rss.xml",
            "https://rss.nytimes.com/services/xml/rss/nyt/World.xml"
        ]
        res = await fetch_rss_feeds(urls)
        print(f"Global News: {len(res)} results")
        if res: print(f"Sample: {res[0]['title']}")
    except Exception as e:
        print(f"Global News failed: {e}")

    print("\nTesting India News RSS (The Hindu, TOI)...")
    try:
        urls = [
            "https://www.thehindu.com/news/national/feeder/default.rss",
            "https://timesofindia.indiatimes.com/rssfeeds/-2128936835.cms"
        ]
        res = await fetch_rss_feeds(urls)
        print(f"India News: {len(res)} results")
        if res: print(f"Sample: {res[0]['title']}")
    except Exception as e:
        print(f"India News failed: {e}")

    print("\nTesting India Finance RSS (Moneycontrol)...")
    try:
        urls = [
            "https://www.moneycontrol.com/rss/MCtopnews.xml"
        ]
        res = await fetch_rss_feeds(urls)
        print(f"India Finance: {len(res)} results")
        if res: print(f"Sample: {res[0]['title']}")
    except Exception as e:
        print(f"India Finance failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_tier3())
