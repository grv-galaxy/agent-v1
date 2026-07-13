import asyncio
import httpx
import feedparser

async def _fetch_single_feed(client: httpx.AsyncClient, url: str) -> list[dict]:
    """
    Fetches a single RSS XML and parses it with feedparser in a thread.
    """
    try:
        resp = await client.get(url)
        if resp.status_code == 200:
            xml_data = resp.text
            # Parse XML synchronously in a thread to avoid blocking the event loop
            feed = await asyncio.to_thread(feedparser.parse, xml_data)
            
            results = []
            feed_title = feed.feed.get("title", "Unknown Feed")
            
            # Take top 3 from each feed so we don't overwhelm the ranker
            for entry in feed.entries[:3]:
                title = entry.get("title", "Unknown Title")
                link = entry.get("link", url)
                
                # Try to get the best summary
                summary = entry.get("summary", "")
                if "content" in entry and entry.content:
                    summary = entry.content[0].get("value", summary)
                    
                # Clean up summary by stripping basic HTML (ranker handles plain text better)
                # But for now, just a simple slice
                if len(summary) > 500:
                    summary = summary[:497] + "..."
                    
                pub_date = entry.get("published", "Unknown Date")
                
                results.append({
                    "title": f"{feed_title}: {title}",
                    "url": link,
                    "content": f"Published: {pub_date}\n{summary}"
                })
            return results
        else:
            print(f"[rss_fetcher] Feed {url} returned {resp.status_code}")
            return []
    except Exception as e:
        print(f"[rss_fetcher] Error fetching {url}: {e}")
        return []

async def fetch_rss_feeds(feed_urls: list[str]) -> list[dict]:
    """
    Universally fetches and aggregates multiple RSS feeds concurrently.
    """
    all_results = []
    async with httpx.AsyncClient(timeout=7.0, follow_redirects=True) as client:
        # Create a task for each feed URL
        tasks = [_fetch_single_feed(client, url) for url in feed_urls]
        
        # Run all feed fetches in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for res in results:
            if isinstance(res, list):
                all_results.extend(res)
                
    return all_results
