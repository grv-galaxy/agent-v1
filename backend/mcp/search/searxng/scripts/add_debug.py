import os

path = 'src/search_agent/orchestrator.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

debug_endpoint = '''
from pydantic import BaseModel

class DebugQueryRequest(BaseModel):
    query: str

@app.post("/debug/query")
async def debug_query(req: DebugQueryRequest):
    query = req.query
    
    classifier_output = await classify_query(query)
    route_params = route_query(classifier_output)
    sources = route_params.get("sources", [])
    
    fetch_tasks = []
    
    async def track_source_debug(coro, source_id):
        t_start = time.perf_counter()
        try:
            res = await coro
            t_end = time.perf_counter()
            return {
                "source_id": source_id,
                "status": "success",
                "elapsed_ms": int((t_end - t_start) * 1000),
                "raw_output": res
            }
        except Exception as e:
            t_end = time.perf_counter()
            return {
                "source_id": source_id,
                "status": "error",
                "elapsed_ms": int((t_end - t_start) * 1000),
                "error": str(e)
            }
            
    if "searxng" in sources:
        fetch_tasks.append(track_source_debug(search_web(query, route_params), "searxng"))
    
    if "pypi" in sources: fetch_tasks.append(track_source_debug(search_pypi(query), "pypi"))
    if "npm" in sources: fetch_tasks.append(track_source_debug(search_npm(query), "npm"))
    if "github" in sources: fetch_tasks.append(track_source_debug(search_github(query), "github"))
    if "arxiv" in sources: fetch_tasks.append(track_source_debug(search_arxiv(query), "arxiv"))
    if "worldbank" in sources: fetch_tasks.append(track_source_debug(search_worldbank(query), "worldbank"))
    if "economic_databases" in sources: fetch_tasks.append(track_source_debug(search_economic_databases(query), "economic_databases"))
    if "yfinance" in sources: fetch_tasks.append(track_source_debug(search_yfinance(query), "yfinance"))
    if "nse" in sources: fetch_tasks.append(track_source_debug(search_nse(query), "nse"))
    if "bse" in sources: fetch_tasks.append(track_source_debug(search_bse(query), "bse"))
    if "indian_kanoon" in sources: fetch_tasks.append(track_source_debug(search_indian_kanoon(query), "indian_kanoon"))
    if "wipo" in sources: fetch_tasks.append(track_source_debug(search_wipo(query), "wipo"))
    if "wikipedia" in sources: fetch_tasks.append(track_source_debug(search_wikipedia(query), "wikipedia"))
    if "gdelt" in sources: fetch_tasks.append(track_source_debug(search_gdelt(query), "gdelt"))
    if "rss_global_news" in sources: fetch_tasks.append(track_source_debug(fetch_rss_feeds(["http://feeds.bbci.co.uk/news/rss.xml", "https://rss.nytimes.com/services/xml/rss/nyt/World.xml"]), "rss_global_news"))
    if "rss_india_news" in sources: fetch_tasks.append(track_source_debug(fetch_rss_feeds(["https://www.thehindu.com/news/national/feeder/default.rss", "https://timesofindia.indiatimes.com/rssfeeds/-2128936835.cms"]), "rss_india_news"))
    if "rss_india_finance" in sources: fetch_tasks.append(track_source_debug(fetch_rss_feeds(["https://www.moneycontrol.com/rss/MCtopnews.xml"]), "rss_india_finance"))
    if "rss_india_public" in sources: fetch_tasks.append(track_source_debug(fetch_rss_feeds(["https://pib.gov.in/newsite/rssenglish.aspx"]), "rss_india_public"))
    if "fallback_docs" in sources: fetch_tasks.append(track_source_debug(fallback_docs_search(query), "fallback_docs"))
    
    results = await asyncio.gather(*fetch_tasks, return_exceptions=True)
    
    tool_results = []
    for r in results:
        if isinstance(r, dict):
            tool_results.append(r)
        else:
            tool_results.append({"error": str(r)})
            
    # Simulate extract_fallback on the top SearXNG result
    searxng_res = next((t for t in tool_results if t.get("source_id") == "searxng"), None)
    if searxng_res and searxng_res.get("status") == "success" and searxng_res.get("raw_output"):
        first_url = searxng_res["raw_output"][0].get("url")
        if first_url:
            fb = await track_source_debug(extract_url(first_url), "extract_fallback")
            tool_results.append(fb)
            
    return {
        "query": query,
        "classified_fact_type": classifier_output.fact_type,
        "categories": classifier_output.categories,
        "tool_results": tool_results
    }
'''

content += "\n" + debug_endpoint + "\n"

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
