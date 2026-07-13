import time
import json
import asyncio
import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Import all our modules
from src.search_agent.classifier import classify_query
from src.search_agent.router import route_query
from src.search_agent.breaker import CircuitBreaker
from src.search_agent.mcp_server import search_web
from src.search_agent.ranker import ONNXRanker, BI_ENCODER_PATH, CROSS_ENCODER_PATH
from src.search_agent.synthesizer import synthesize
from src.search_agent.citations import verify_citations
from src.search_agent.telemetry import log_query, init_db

# Federated API sources
from src.search_agent.sources.pypi import search_pypi
from src.search_agent.sources.npm import search_npm
from src.search_agent.sources.github import search_github
from src.search_agent.sources.arxiv import search_arxiv
from src.search_agent.sources.wikipedia import search_wikipedia
from src.search_agent.sources.worldbank import search_worldbank
from src.search_agent.sources.rss_fetcher import fetch_rss_feeds
from src.search_agent.sources.markets import search_nse, search_bse, search_yfinance
from src.search_agent.sources.extraction import search_indian_kanoon, search_wipo, fallback_docs_search

# Initialize globals
app = FastAPI()
breaker = CircuitBreaker()
ranker = None  # Loaded on startup to avoid blocking module import

# Mount static files for the dashboard
static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.on_event("startup")
async def startup_event():
    global ranker
    # Initialize SQLite db
    init_db()
    # Load ranker models into memory
    print("Loading ONNX rankers...")
    ranker = ONNXRanker(BI_ENCODER_PATH, CROSS_ENCODER_PATH)
    print("Models loaded.")

@app.get("/")
async def get_index():
    return FileResponse(os.path.join(static_dir, "index.html"))

@app.get("/api/history")
async def get_history():
    import sqlite3
    from src.search_agent.telemetry import DEFAULT_DB_PATH
    import json
    
    conn = sqlite3.connect(DEFAULT_DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM queries ORDER BY timestamp DESC LIMIT 50")
        rows = cursor.fetchall()
        
        history = []
        for r in rows:
            history.append({
                "id": r["id"],
                "timestamp": r["timestamp"],
                "query": r["query"],
                "final_answer": r["final_answer"],
                "engines_used": json.loads(r["engines_used"]) if r["engines_used"] else [],
                "latency_total_ms": (r["latency_classify_ms"] or 0) + 
                                    (r["latency_route_ms"] or 0) + 
                                    (r["latency_searxng_ms"] or 0) + 
                                    (r["latency_rank_ms"] or 0) + 
                                    (r["latency_synthesize_ms"] or 0),
                "citation_pass_rate": r["citation_pass_rate"]
            })
        return {"history": history}
    except Exception as e:
        return {"error": str(e)}
    finally:
        conn.close()

@app.websocket("/ws/query")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    try:
        while True:
            # Wait for query from client
            data = await websocket.receive_text()
            payload = json.loads(data)
            query = payload.get("query", "")
            if not query:
                continue
                
            metrics = {"query": query}
            top_urls = []
            final_answer = ""
            citation_pass_rate = 0.0
            
            start_total = time.perf_counter()
            
            # --- 1. Classify ---
            await websocket.send_json({"type": "stage_start", "stage": "classify", "label": "Understanding your question"})
            t0 = time.perf_counter()
            classifier_out = await classify_query(query)
            t1 = time.perf_counter()
            metrics["latency_classify_ms"] = int((t1 - t0) * 1000)
            await websocket.send_json({
                "type": "stage_done", 
                "stage": "classify", 
                "elapsed_ms": metrics["latency_classify_ms"],
                "result": classifier_out.model_dump()
            })
            
            # --- 2. Route ---
            await websocket.send_json({"type": "stage_start", "stage": "route", "label": "Choosing sources"})
            t0 = time.perf_counter()
            route_params = route_query(classifier_out)
            t1 = time.perf_counter()
            metrics["latency_route_ms"] = int((t1 - t0) * 1000)
            await websocket.send_json({
                "type": "stage_done",
                "stage": "route",
                "elapsed_ms": metrics["latency_route_ms"],
                "result": route_params
            })
            
            # --- 3. Federated Fetch ---
            t0 = time.perf_counter()
            category = route_params.get("categories", "general")
            sources = route_params.get("sources", ["searxng"])
            
            fetch_tasks = []
            metrics["engines_used"] = []
            metrics["engines_skipped"] = []
            
            async def track_source(coro, source_id, domain, label, category, group_id="fetch-1", is_page_visit=False):
                start_type = "page_visit_start" if is_page_visit else "source_start"
                done_type = "page_visit_done" if is_page_visit else "source_done"
                
                await websocket.send_json({
                    "type": start_type,
                    "source_id": source_id,
                    "domain": domain,
                    "label": label,
                    "category": category,
                    "group_id": group_id,
                    "url": domain if is_page_visit else None
                })
                
                s0 = time.perf_counter()
                try:
                    res = await coro
                    s1 = time.perf_counter()
                    await websocket.send_json({
                        "type": done_type,
                        "source_id": source_id,
                        "url": domain if is_page_visit else None,
                        "elapsed_ms": int((s1 - s0) * 1000),
                        "status": "success",
                        "result_count": len(res) if isinstance(res, list) else 1,
                        "extraction_method": "trafilatura" if is_page_visit else None
                    })
                    return res
                except Exception as e:
                    s1 = time.perf_counter()
                    await websocket.send_json({
                        "type": "source_error",
                        "source_id": source_id,
                        "elapsed_ms": int((s1 - s0) * 1000),
                        "status": "timeout" if "timeout" in str(e).lower() else "error",
                        "circuit_breaker_tripped": True
                    })
                    return []
            
            async def do_searxng():
                all_engines = ["duckduckgo", "brave", "startpage"]
                engines_used = breaker.get_eligible_engines(all_engines, category)
                metrics["engines_used"] = engines_used
                metrics["engines_skipped"] = [e for e in all_engines if e not in engines_used]
                engine_str = ",".join(engines_used)
                try:
                    raw_json_str = await search_web(
                        query=query,
                        categories=route_params.get("categories", ""),
                        time_range=route_params.get("time_range", ""),
                        language=route_params.get("language", ""),
                        engines=engine_str
                    )
                    for eng in engines_used:
                        breaker.record_success(eng, category)
                    return json.loads(raw_json_str).get("results", [])
                except Exception as e:
                    for eng in engines_used:
                        breaker.record_failure(eng, category)
                    raise e
                    
            if "searxng" in sources:
                fetch_tasks.append(track_source(do_searxng(), "searxng", "duckduckgo.com", "Searching Web", category))
            if "pypi" in sources:
                fetch_tasks.append(track_source(search_pypi(query, classifier_out.entities), "pypi", "pypi.org", "Searching PyPI", category))
            if "npm" in sources:
                fetch_tasks.append(track_source(search_npm(query, classifier_out.entities), "npm", "npmjs.com", "Searching NPM", category))
            if "github" in sources:
                fetch_tasks.append(track_source(search_github(query, classifier_out.entities), "github", "github.com", "Searching GitHub", category))
            if "arxiv" in sources:
                fetch_tasks.append(track_source(search_arxiv(query, classifier_out.entities), "arxiv", "arxiv.org", "Searching arXiv", category))
            if "wikipedia" in sources:
                fetch_tasks.append(track_source(search_wikipedia(query, classifier_out.entities), "wikipedia", "wikipedia.org", "Searching Wikipedia", category))
            if "worldbank" in sources:
                fetch_tasks.append(track_source(search_worldbank(query, classifier_out.entities), "worldbank", "worldbank.org", "Searching WorldBank", category))
                
            if "rss_global_news" in sources:
                fetch_tasks.append(track_source(fetch_rss_feeds(["http://feeds.bbci.co.uk/news/rss.xml", "https://rss.nytimes.com/services/xml/rss/nyt/World.xml"]), "rss_global", "bbc.com", "Fetching Breaking News", category))
            if "rss_india_news" in sources:
                fetch_tasks.append(track_source(fetch_rss_feeds(["https://www.thehindu.com/news/national/feeder/default.rss", "https://timesofindia.indiatimes.com/rssfeeds/-2128936835.cms"]), "rss_india", "thehindu.com", "Fetching Indian News", category))
            if "rss_india_finance" in sources:
                fetch_tasks.append(track_source(fetch_rss_feeds(["https://www.moneycontrol.com/rss/MCtopnews.xml"]), "rss_finance", "moneycontrol.com", "Fetching Financial News", category))
            if "rss_india_public" in sources:
                fetch_tasks.append(track_source(fetch_rss_feeds(["https://pib.gov.in/newsite/rssenglish.aspx"]), "rss_public", "pib.gov.in", "Fetching Press Releases", category))
                
            if "nse" in sources:
                fetch_tasks.append(track_source(search_nse(query, classifier_out.entities), "nse", "nseindia.com", "Fetching Live NSE", category))
            if "bse" in sources:
                fetch_tasks.append(track_source(search_bse(query, classifier_out.entities), "bse", "bseindia.com", "Fetching Live BSE", category))
            if "yfinance" in sources:
                fetch_tasks.append(track_source(search_yfinance(query, classifier_out.entities), "yfinance", "yahoo.com", "Fetching Yahoo Finance", category))
            if "wipo" in sources:
                fetch_tasks.append(track_source(search_wipo(query, classifier_out.entities), "wipo", "wipo.int", "Reading Patent Data", category, is_page_visit=True))
            if "indian_kanoon" in sources:
                fetch_tasks.append(track_source(search_indian_kanoon(query, classifier_out.entities), "indian_kanoon", "indiankanoon.org", "Reading Legal Case", category, is_page_visit=True))
            if "fallback_docs" in sources:
                fetch_tasks.append(track_source(fallback_docs_search(query, classifier_out.entities), "fallback_docs", "docs.python.org", "Deep Reading Docs", category, is_page_visit=True))
                
            raw_results = await asyncio.gather(*fetch_tasks, return_exceptions=True)
            
            search_results = []
            for res in raw_results:
                if isinstance(res, list):
                    search_results.extend(res)
                    
            if not search_results:
                await websocket.send_json({"error": "All search sources failed or returned empty."})
                continue
                
            t1 = time.perf_counter()
            metrics["latency_searxng_ms"] = int((t1 - t0) * 1000)
            
            # --- 4. Rank ---
            await websocket.send_json({"type": "stage_start", "stage": "rank", "label": "Ranking results"})
            t0 = time.perf_counter()
            ranked_results = ranker.rank_results(query, search_results)
            # Take top 3 for the LLM
            top_3 = ranked_results[:3]
            top_urls = [r.get("url", "") for r in top_3]
            metrics["top_urls"] = top_urls
            
            t1 = time.perf_counter()
            metrics["latency_rank_ms"] = int((t1 - t0) * 1000)
            
            await websocket.send_json({
                "type": "stage_done",
                "stage": "rank",
                "elapsed_ms": metrics["latency_rank_ms"],
                "result": {"top_urls": top_urls}
            })
            
            # --- 6. Synthesize (Streaming) ---
            await websocket.send_json({"type": "stage_start", "stage": "synthesize", "label": "Writing answer"})
            t0 = time.perf_counter()
            answer_chunks = []
            async for chunk in synthesize(query, top_3):
                answer_chunks.append(chunk)
                await websocket.send_json({
                    "type": "synthesis_token",
                    "text": chunk
                })
            
            final_answer = "".join(answer_chunks)
            metrics["final_answer"] = final_answer
            t1 = time.perf_counter()
            metrics["latency_synthesize_ms"] = int((t1 - t0) * 1000)
            await websocket.send_json({
                "type": "stage_done", 
                "stage": "synthesize", 
                "elapsed_ms": metrics["latency_synthesize_ms"]
            })
            
            # --- 7. Citation Verification ---
            cit_verifications = verify_citations(final_answer, top_3)
            
            passed = sum(1 for v in cit_verifications if v["passed"])
            total = len(cit_verifications)
            citation_pass_rate = (passed / total) if total > 0 else 1.0
            metrics["citation_pass_rate"] = citation_pass_rate
            
            for idx, cit in enumerate(cit_verifications):
                await websocket.send_json({
                    "type": "citation_check",
                    "n": idx + 1,
                    "passed": cit["passed"]
                })
            
            # --- 8. Telemetry Logging ---
            log_query(**metrics)
            
            total_time = int((time.perf_counter() - start_total) * 1000)
            await websocket.send_json({
                "type": "done",
                "total_elapsed_ms": total_time
            })
            
    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"Error in websocket: {e}")
        try:
            await websocket.send_json({"error": str(e)})
        except:
            pass
