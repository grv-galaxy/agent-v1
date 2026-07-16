import time
import json
import asyncio
import os
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
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
from src.search_agent.telemetry import log_query, init_db, log_tool_contributions, log_llm_call
from src.search_agent.extractor import extract_url
import uuid
import hashlib
import redis.asyncio as aioredis
import numpy as np

# Federated API sources
from src.search_agent.sources.pypi import search_pypi
from src.search_agent.sources.npm import search_npm
from src.search_agent.sources.github import search_github
from src.search_agent.sources.arxiv import search_arxiv
from src.search_agent.sources.wikipedia import search_wikipedia
from src.search_agent.sources.worldbank import search_worldbank

from src.search_agent.sources.markets import search_indian_markets, search_yfinance
from src.search_agent.sources.extraction import search_indian_kanoon, search_wipo, fallback_docs_search
from src.search_agent.sources.gdelt import search_gdelt
from src.search_agent.sources.economics import search_economic_databases

# Initialize globals
app = FastAPI()
breaker = CircuitBreaker()
ranker = None  # Loaded on startup to avoid blocking module import
redis_client = None

# Mount static files for the dashboard
static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.on_event("startup")
async def health_check_loop():
    async def probe():
        while True:
            await asyncio.sleep(120)  # every 2 minutes
            for (engine, cat) in breaker.get_open_engines():
                breaker.mark_half_open(engine, cat)
    asyncio.create_task(probe())

@app.on_event("startup")
async def startup_event():
    global ranker, redis_client
    
    print("\n--- System Startup Checks ---")
    
    # 1. Check Redis
    try:
        redis_client = aioredis.from_url("redis://localhost:6379", decode_responses=True)
        await redis_client.ping()
        print("[OK] Redis: Connected successfully")
    except Exception as e:
        print(f"[FAIL] Redis: Failed to connect ({e})")
        redis_client = None

    # 2. Check SearXNG
    import httpx
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get("http://localhost:8080/")
            resp.raise_for_status()
        print("[OK] SearXNG: Up and running (http://localhost:8080/)")
    except Exception as e:
        print(f"[FAIL] SearXNG: Unreachable! Ensure Docker container is running ({e})")

    # 3. Check SQLite DB
    init_db()
    print("[OK] Database: Initialized")

    # 4. Load Ranker Models
    try:
        print("[WAIT] Loading ONNX Rankers...")
        ranker = ONNXRanker(BI_ENCODER_PATH, CROSS_ENCODER_PATH)
        print("[OK] Rankers: Loaded (Bi-Encoder + Cross-Encoder)")
    except Exception as e:
        print(f"[FAIL] Rankers: Failed to load ({e})")

    # 5. Load NLI Citation Model
    try:
        print("[WAIT] Loading ONNX NLI Citations Model...")
        from src.search_agent.citations import init_nli
        init_nli()
        print("[OK] NLI Model: Loaded successfully")
    except Exception as e:
        print(f"[FAIL] NLI Model: Failed to load ({e})")
        
    print("-----------------------------\n")

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

def compute_tier(cited_rate: float, calls: int, breaker_trip_rate: float) -> str:
    if breaker_trip_rate > 0.15:
        return "unreliable"
    if cited_rate > 0.30:
        return "core"
    if 0.10 <= cited_rate <= 0.30:
        return "situational"
    if cited_rate < 0.10 and calls > 5:
        return "show_piece"
    return "unknown"

@app.get("/api/dashboard/tool-contribution")
async def get_tool_contribution(days: int = 7, category: str = "all"):
    import sqlite3
    from src.search_agent.telemetry import DEFAULT_DB_PATH
    
    conn = sqlite3.connect(DEFAULT_DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.cursor()
        
        # Build query
        query = """
            SELECT 
                source_id,
                COUNT(*) as total_calls,
                SUM(CASE WHEN returned_results THEN 1 ELSE 0 END) as returned_count,
                SUM(CASE WHEN survived_biencoder THEN 1 ELSE 0 END) as biencoder_count,
                SUM(CASE WHEN survived_crossencoder THEN 1 ELSE 0 END) as crossencoder_count,
                SUM(CASE WHEN cited_in_answer THEN 1 ELSE 0 END) as cited_count,
                SUM(CASE WHEN citation_check_passed THEN 1 ELSE 0 END) as verified_count,
                SUM(CASE WHEN circuit_breaker_state = 'tripped' THEN 1 ELSE 0 END) as trip_count,
                AVG(elapsed_ms) as avg_latency
            FROM tool_contribution
            WHERE timestamp >= datetime('now', ?)
        """
        params = [f'-{days} days']
        
        if category and category != "all":
            query += " AND category = ?"
            params.append(category)
            
        query += " GROUP BY source_id"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        results = []
        for r in rows:
            calls = r["total_calls"]
            if calls == 0:
                continue
                
            returned_rate = r["returned_count"] / calls
            top3_rate = r["crossencoder_count"] / calls
            cited_rate = r["cited_count"] / calls
            trip_rate = r["trip_count"] / calls
            
            verified_rate = 0.0
            if r["cited_count"] > 0:
                verified_rate = r["verified_count"] / r["cited_count"]
                
            tier = compute_tier(cited_rate, calls, trip_rate)
            
            results.append({
                "source_id": r["source_id"],
                "calls": calls,
                "avg_latency_ms": round(r["avg_latency"] or 0, 2),
                "returned_rate": round(returned_rate, 4),
                "top3_rate": round(top3_rate, 4),
                "cited_rate": round(cited_rate, 4),
                "verified_rate": round(verified_rate, 4),
                "trip_rate": round(trip_rate, 4),
                "tier": tier
            })
            
        return {"data": results}
    except Exception as e:
        return {"error": str(e)}
    finally:
        conn.close()

@app.get("/api/dashboard/llm-calls")
async def get_llm_calls(days: int = 7):
    import sqlite3
    from src.search_agent.telemetry import DEFAULT_DB_PATH
    
    conn = sqlite3.connect(DEFAULT_DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.cursor()
        query = """
            SELECT 
                step,
                COUNT(*) as calls,
                AVG(input_tokens) as avg_in_tokens,
                AVG(output_tokens) as avg_out_tokens,
                AVG(elapsed_ms) as avg_latency,
                SUM(cost_usd) as total_cost
            FROM llm_calls
            WHERE timestamp >= datetime('now', ?)
            GROUP BY step
        """
        cursor.execute(query, [f'-{days} days'])
        rows = cursor.fetchall()
        
        results = []
        for r in rows:
            calls = r["calls"]
            if calls == 0:
                continue
                
            avg_cost_per_call = r["total_cost"] / calls
            results.append({
                "step": r["step"],
                "calls": calls,
                "avg_input_tokens": round(r["avg_in_tokens"] or 0, 2),
                "avg_output_tokens": round(r["avg_out_tokens"] or 0, 2),
                "avg_latency_ms": round(r["avg_latency"] or 0, 2),
                "total_cost_usd": round(r["total_cost"] or 0, 4),
                "avg_cost_per_call_usd": round(avg_cost_per_call, 4)
            })
            
        return {"data": results}
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
                
            group_id = f"fetch-{uuid.uuid4().hex[:8]}"
                
            metrics = {"query": query}
            top_urls = []
            final_answer = ""
            citation_pass_rate = 0.0
            
            query_id = uuid.uuid4().hex
            tool_contributions = {} # source_id -> dict
            llm_calls_to_log = []
            
            is_diagnostic_mode = False
            diagnostic_tool = None
            diagnostic_trace = {
                "raw_tool_output": [],
                "ranked_output": [],
                "synthesizer_context": ""
            }
            
            if query.startswith("@"):
                parts = query.split(" ", 1)
                diagnostic_tool = parts[0][1:] # Strip "@"
                query = parts[1] if len(parts) > 1 else ""
                is_diagnostic_mode = True
            
            start_total = time.perf_counter()
            
            # --- 0. Check Cache ---
            query_hash = hashlib.md5(query.encode("utf-8")).hexdigest()
            if redis_client and ranker:
                try:
                    query_emb = ranker.get_query_embedding(query)
                    cache_keys = await redis_client.keys("cache:*")
                    
                    best_match_key = None
                    best_score = 0.0
                    
                    for key in cache_keys:
                        cached_data_str = await redis_client.get(key)
                        if cached_data_str:
                            cached_data = json.loads(cached_data_str)
                            if "embedding" in cached_data:
                                cached_emb = np.array(cached_data["embedding"])
                                score = np.dot(query_emb, cached_emb)
                                if score > best_score:
                                    best_score = score
                                    best_match_key = key
                                    
                    if best_match_key and best_score > 0.95:
                        cached_data_str = await redis_client.get(best_match_key)
                        cached_data = json.loads(cached_data_str)
                        await websocket.send_json({"type": "stage_start", "stage": "cache", "label": "Getting from Knowledge Base..."})
                        await asyncio.sleep(0.05)
                        await websocket.send_json({"type": "stage_done", "stage": "cache", "elapsed_ms": 15})
                        
                        await websocket.send_json({"type": "synthesis_token", "text": cached_data.get("final_answer", "")})
                        
                        cit_verifs = cached_data.get("cit_verifications", [])
                        for cit in cit_verifs:
                            await websocket.send_json({
                                "type": "citation_check",
                                "n": cit["citation_number"],
                                "passed": cit["passed"]
                            })
                            
                        # Re-emit the sources_final event from cache
                        if "sources_final_payload" in cached_data:
                            await websocket.send_json({
                                "type": "sources_final",
                                "sources": cached_data["sources_final_payload"]
                            })
                            
                        metrics["latency_classify_ms"] = 0
                        metrics["latency_route_ms"] = 0
                        metrics["latency_searxng_ms"] = 0
                        metrics["latency_rank_ms"] = 0
                        metrics["latency_synthesize_ms"] = 15
                        metrics["citation_pass_rate"] = cached_data.get("citation_pass_rate", 1.0)
                        metrics["final_answer"] = cached_data.get("final_answer", "")
                        metrics["top_urls"] = cached_data.get("top_urls", [])
                        
                        log_query(**metrics)
                        
                        total_time = int((time.perf_counter() - start_total) * 1000)
                        await websocket.send_json({"type": "done", "total_elapsed_ms": total_time})
                        continue
                except Exception as e:
                    print(f"Error parsing cache: {e}")

            # --- 1. Classify ---
            if is_diagnostic_mode:
                class MockClassifier:
                    def __init__(self):
                        self.entities = []
                        self.categories = ["diagnostic"]
                        self.language_hint = "en-US"
                        self.date_range = None
                classifier_out = MockClassifier()
                await websocket.send_json({"type": "stage_start", "stage": "classify", "label": f"Diagnostic Mode: Forcing {diagnostic_tool}"})
                await asyncio.sleep(0.1)
                metrics["latency_classify_ms"] = 0
                await websocket.send_json({"type": "stage_done", "stage": "classify", "elapsed_ms": 0, "result": {"diagnostic": True}})
            else:
                await websocket.send_json({"type": "stage_start", "stage": "classify", "label": "Understanding your question"})
                t0 = time.perf_counter()
                classifier_out, classify_telemetry = await classify_query(query)
                classify_telemetry["query_id"] = query_id
                llm_calls_to_log.append(classify_telemetry)
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
            if is_diagnostic_mode:
                route_params = {"categories": "diagnostic", "sources": [diagnostic_tool]}
            else:
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
                
                tool_contributions[source_id] = {
                    "query_id": query_id,
                    "source_id": source_id,
                    "category": category,
                    "called": True,
                    "elapsed_ms": 0,
                    "returned_results": False,
                    "result_count": 0,
                    "survived_biencoder": False,
                    "survived_crossencoder": False,
                    "cited_in_answer": False,
                    "citation_check_passed": False,
                    "circuit_breaker_state": "closed"
                }
                
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
                    elapsed = int((s1 - s0) * 1000)
                    rcount = len(res) if isinstance(res, list) else 1
                    
                    tool_contributions[source_id]["elapsed_ms"] = elapsed
                    tool_contributions[source_id]["returned_results"] = True
                    tool_contributions[source_id]["result_count"] = rcount
                    
                    if isinstance(res, list):
                        for item in res:
                            if isinstance(item, dict):
                                item["source_id"] = source_id
                        if len(res) > 0 and isinstance(res[0], dict):
                            tool_contributions[source_id]["raw_content"] = str(res[0].get("content", "")) # Truncation removed as per user request
                    elif isinstance(res, str):
                        tool_contributions[source_id]["raw_content"] = res
                    
                    await websocket.send_json({
                        "type": done_type,
                        "source_id": source_id,
                        "url": domain if is_page_visit else None,
                        "elapsed_ms": elapsed,
                        "status": "success",
                        "result_count": rcount,
                        "extraction_method": "trafilatura" if is_page_visit else None
                    })
                    return res
                except Exception as e:
                    s1 = time.perf_counter()
                    elapsed = int((s1 - s0) * 1000)
                    
                    tool_contributions[source_id]["elapsed_ms"] = elapsed
                    if "timeout" in str(e).lower() or "circuit" in str(e).lower():
                        tool_contributions[source_id]["circuit_breaker_state"] = "tripped"
                        
                    await websocket.send_json({
                        "type": "source_error",
                        "source_id": source_id,
                        "elapsed_ms": elapsed,
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
                fetch_tasks.append(track_source(do_searxng(), "searxng", "duckduckgo.com", "Searching Web", category, group_id=group_id))
            if "pypi" in sources:
                fetch_tasks.append(track_source(search_pypi(query, classifier_out.entities), "pypi", "pypi.org", "Searching PyPI", category, group_id=group_id))
            if "npm" in sources:
                fetch_tasks.append(track_source(search_npm(query, classifier_out.entities), "npm", "npmjs.com", "Searching NPM", category, group_id=group_id))
            if "github" in sources:
                fetch_tasks.append(track_source(search_github(query, classifier_out.entities), "github", "github.com", "Searching GitHub", category, group_id=group_id))
            if "arxiv" in sources:
                fetch_tasks.append(track_source(search_arxiv(query, classifier_out.entities), "arxiv", "arxiv.org", "Searching arXiv", category, group_id=group_id))
            if "wikipedia" in sources:
                fetch_tasks.append(track_source(search_wikipedia(query, classifier_out.entities), "wikipedia", "wikipedia.org", "Searching Wikipedia", category, group_id=group_id))
            if "worldbank" in sources:
                fetch_tasks.append(track_source(search_worldbank(query, classifier_out.entities), "worldbank", "worldbank.org", "Searching WorldBank", category, group_id=group_id))
                
            if "economic_databases" in sources:
                fetch_tasks.append(track_source(search_economic_databases(query), "economics", "imf.org", "Querying Economic Databases", category, group_id=group_id))
                
            if "gdelt" in sources:
                fetch_tasks.append(track_source(search_gdelt(query), "gdelt", "gdeltproject.org", "Fetching Global News", category, group_id=group_id))
                
            if "indian_markets" in sources:
                fetch_tasks.append(track_source(search_indian_markets(query, classifier_out.entities), "indian_markets", "yahoo.com", "Fetching Indian Markets", category, group_id=group_id))
            if "yfinance" in sources:
                fetch_tasks.append(track_source(search_yfinance(query, classifier_out.entities), "yfinance", "yahoo.com", "Fetching Yahoo Finance", category, group_id=group_id))
            if "wipo" in sources:
                fetch_tasks.append(track_source(search_wipo(query, classifier_out.entities), "wipo", "wipo.int", "Reading Patent Data", category, group_id=group_id, is_page_visit=True))
            if "indian_kanoon" in sources:
                fetch_tasks.append(track_source(search_indian_kanoon(query, classifier_out.entities), "indian_kanoon", "indiankanoon.org", "Reading Legal Case", category, group_id=group_id, is_page_visit=True))
            if "fallback_docs" in sources:
                fetch_tasks.append(track_source(fallback_docs_search(query, classifier_out.entities), "fallback_docs", "docs.python.org", "Deep Reading Docs", category, group_id=group_id, is_page_visit=True))
                
            raw_results = await asyncio.gather(*fetch_tasks, return_exceptions=True)
            
            search_results = []
            for res in raw_results:
                if isinstance(res, list):
                    search_results.extend(res)
                    
            if is_diagnostic_mode:
                diagnostic_trace["raw_tool_output"] = search_results

            # --- Speculative PDF Extraction ---
            speculative_extract_task = None
            speculative_extract_url = None
            
            searxng_results = [r for r in search_results if r.get("source_id") == "searxng"]
            if searxng_results and searxng_results[0].get("url", "").lower().endswith(".pdf"):
                speculative_extract_url = searxng_results[0].get("url")
                speculative_extract_task = asyncio.create_task(extract_url(speculative_extract_url))
            if not search_results:
                if is_diagnostic_mode:
                    await websocket.send_json({
                        "type": "telemetry_dump",
                        "diagnostic_trace": diagnostic_trace,
                        "tool_contributions": list(tool_contributions.values()),
                        "llm_calls": llm_calls_to_log
                    })
                await websocket.send_json({"error": "All search sources failed or returned empty."})
                continue
                
            t1 = time.perf_counter()
            metrics["latency_searxng_ms"] = int((t1 - t0) * 1000)
            
            # --- 4. Rank ---
            await websocket.send_json({"type": "stage_start", "stage": "rank", "label": "Ranking results"})
            t0 = time.perf_counter()
            if is_diagnostic_mode:
                # Bypass ranking mostly so we can see what the tool actually passed
                ranked_results = search_results
                top_3 = ranked_results[:3]
                diagnostic_trace["ranked_output"] = top_3
            else:
                bi_ranked = ranker.bi_encoder_rank(query, search_results)
                for idx, r in enumerate(bi_ranked):
                    sid = r.get("source_id")
                    if sid and sid in tool_contributions:
                        current_bi_rank = tool_contributions[sid].get("bi_rank")
                        if current_bi_rank is None or (idx + 1) < current_bi_rank:
                            tool_contributions[sid]["bi_score"] = round(r.get("_bi_score", 0), 4)
                            tool_contributions[sid]["bi_rank"] = idx + 1
                            if idx < 8:
                                tool_contributions[sid]["survived_biencoder"] = True
                        
                top_8_bi_ranked = bi_ranked[:8]
                cross_ranked = ranker.cross_encoder_rerank(query, top_8_bi_ranked)
                for idx, r in enumerate(cross_ranked):
                    sid = r.get("source_id")
                    if sid and sid in tool_contributions:
                        current_cross_rank = tool_contributions[sid].get("cross_rank")
                        if current_cross_rank is None or (idx + 1) < current_cross_rank:
                            tool_contributions[sid]["cross_score"] = round(r.get("_cross_score", 0), 4)
                            tool_contributions[sid]["cross_rank"] = idx + 1
                            if (idx + 1) <= 3:
                                tool_contributions[sid]["survived_crossencoder"] = True
                            
                ranked_results = cross_ranked
                top_3 = cross_ranked[:3]
                
            top_urls = [r.get("url", "") for r in top_3]
            metrics["top_urls"] = top_urls
            
            # --- 4.5 Normalize Metadata ---
            import urllib.parse
            for i, res in enumerate(top_3):
                url = res.get("url", "")
                domain = res.get("domain", "")
                if not domain and url:
                    parsed_uri = urllib.parse.urlparse(url)
                    domain = parsed_uri.netloc.replace("www.", "")
                res["domain"] = domain
                
                if not res.get("favicon") and domain:
                    res["favicon"] = f"https://www.google.com/s2/favicons?domain={domain}&sz=64"
                    
                if not res.get("title"):
                    res["title"] = f"Source {i+1}"
                    
                if not res.get("published_date"):
                    res["published_date"] = "Date not clear"
            
            t1 = time.perf_counter()
            metrics["latency_rank_ms"] = int((t1 - t0) * 1000)
            
            await websocket.send_json({
                "type": "stage_done",
                "stage": "rank",
                "elapsed_ms": metrics["latency_rank_ms"],
                "result": {"top_urls": top_urls}
            })
            
            # --- 5. Extraction Fallback ---
            FALLBACK_THRESHOLD = 0.5
            if not is_diagnostic_mode and top_3 and top_3[0].get("score", 0) < FALLBACK_THRESHOLD:
                fallback_url = top_3[0].get("url")
                if fallback_url:
                    if speculative_extract_task and fallback_url == speculative_extract_url:
                        await websocket.send_json({"type": "stage_start", "stage": "extract_fallback", "label": "Waiting for background PDF extraction"})
                        
                        fallback_domain = fallback_url.split('/')[2] if '//' in fallback_url else fallback_url
                        await websocket.send_json({
                            "type": "page_visit_start",
                            "source_id": "extract_fallback",
                            "domain": fallback_domain,
                            "label": "Fallback Extraction",
                            "category": category,
                            "group_id": group_id,
                            "url": fallback_url
                        })
                        
                        t0_ext = time.perf_counter()
                        try:
                            extracted_text = await asyncio.wait_for(speculative_extract_task, timeout=10.0)
                        except Exception as e:
                            print(f"Speculative extraction failed: {e}")
                            extracted_text = None
                            
                        tool_contributions["extract_fallback"] = {
                            "query_id": query_id,
                            "source_id": "extract_fallback",
                            "category": category,
                            "called": True,
                            "elapsed_ms": int((time.perf_counter() - t0_ext) * 1000),
                            "returned_results": bool(extracted_text),
                            "result_count": 1 if extracted_text else 0,
                            "raw_content": str(extracted_text) if extracted_text else "",
                            "survived_biencoder": False,
                            "survived_crossencoder": False,
                            "cited_in_answer": False,
                            "citation_check_passed": False,
                            "circuit_breaker_state": "closed"
                        }
                        
                        await websocket.send_json({
                            "type": "page_visit_done",
                            "source_id": "extract_fallback"
                        })
                    else:
                        if speculative_extract_task:
                            speculative_extract_task.cancel()
                            
                        await websocket.send_json({"type": "stage_start", "stage": "extract_fallback", "label": "Deep reading top source"})
                        t0_ext = time.perf_counter()
                        
                        extracted_text = await track_source(
                            extract_url(fallback_url),
                            source_id="extract_fallback",
                            domain=fallback_url.split('/')[2] if '//' in fallback_url else fallback_url,
                            label="Fallback Extraction",
                            category=category,
                            group_id=group_id,
                            is_page_visit=True
                        )
                    
                    if extracted_text:
                        top_3[0]["content"] = extracted_text
                        
                    t1_ext = time.perf_counter()
                    await websocket.send_json({
                        "type": "stage_done",
                        "stage": "extract_fallback",
                        "elapsed_ms": int((t1_ext - t0_ext) * 1000)
                    })
            else:
                if speculative_extract_task:
                    speculative_extract_task.cancel()
            # --- 6. Synthesize (Streaming) ---
            await websocket.send_json({"type": "stage_start", "stage": "synthesize", "label": "Writing answer"})
            t0 = time.perf_counter()
            
            from src.search_agent.synthesizer import synthesize, format_context, load_prompt
            
            if is_diagnostic_mode:
                context_str = format_context(top_3)
                diagnostic_trace["synthesizer_context"] = context_str
                
                # Use a barebones prompt for diagnostic mode
                system_message = "Synthesize the following context to answer the user query exactly based on the text. If not present, say so.\n\n" + context_str
                diagnostic_trace["synthesizer_system_prompt"] = system_message
                
                # Mock the generator manually for diagnostic
                import src.search_agent.config
                from openai import AsyncOpenAI
                temp_client = AsyncOpenAI(base_url="https://api.groq.com/openai/v1", api_key=src.search_agent.config.settings.groq_api_key)
                
                async def custom_synth():
                    resp = await temp_client.chat.completions.create(
                        model=src.search_agent.config.settings.groq_model,
                        messages=[{"role": "system", "content": system_message}, {"role": "user", "content": query}],
                        stream=True, temperature=0.0
                    )
                    async for c in resp:
                        if c.choices and c.choices[0].delta.content:
                            yield c.choices[0].delta.content
                
                synth_generator = custom_synth()
            else:
                synth_generator = synthesize(query, top_3)
            
            answer_chunks = []
            async for chunk in synth_generator:
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
                    "n": cit["citation_number"],
                    "passed": cit["passed"]
                })
                
            # Compute Final Sources List for UI
            source_pass_map = {}
            for v in cit_verifications:
                n = v["citation_number"]
                if n not in source_pass_map:
                    source_pass_map[n] = []
                source_pass_map[n].append(v["passed"])
                
            sources_final_payload = []
            for i, res in enumerate(top_3):
                cit_n = i + 1
                sid = res.get("source_id")
                is_cited = cit_n in source_pass_map
                
                # If cited multiple times, all checks must pass for the source to be marked as fully verified
                if is_cited:
                    passed = all(source_pass_map[cit_n])
                else:
                    passed = True  # Not cited, so didn't fail
                    
                if sid and sid in tool_contributions:
                    if is_cited:
                        tool_contributions[sid]["cited_in_answer"] = True
                        tool_contributions[sid]["citation_check_passed"] = passed
                    
                sources_final_payload.append({
                    "citation_n": cit_n,
                    "url": res.get("url", ""),
                    "title": res.get("title", ""),
                    "domain": res.get("domain", ""),
                    "favicon": res.get("favicon", ""),
                    "published_date": res.get("published_date", ""),
                    "citation_check_passed": passed
                })
                
            await websocket.send_json({
                "type": "sources_final",
                "sources": sources_final_payload
            })
            
            # --- 8. Telemetry Logging ---
            log_query(**metrics)
            
            try:
                from src.search_agent.synthesizer import format_context, load_prompt
                synth_system = load_prompt().replace("{context}", format_context(top_3))
                in_toks = len(synth_system + query) // 4
                out_toks = len(final_answer) // 4
                llm_calls_to_log.append({
                    "query_id": query_id,
                    "step": "synthesize",
                    "model": "groq_model",
                    "provider": "api",
                    "prompt_text": query,
                    "system_prompt_text": synth_system,
                    "response_text": final_answer,
                    "input_tokens": in_toks,
                    "output_tokens": out_toks,
                    "total_tokens": in_toks + out_toks,
                    "elapsed_ms": metrics.get("latency_synthesize_ms", 0),
                    "cost_usd": 0.0,
                    "temperature": 0.2
                })
            except Exception as e:
                print(f"Error computing synthesis telemetry: {e}")
                
            log_tool_contributions(list(tool_contributions.values()))
            for call in llm_calls_to_log:
                log_llm_call(**call)
            
            if redis_client and ranker:
                try:
                    query_emb = ranker.get_query_embedding(query)
                    cache_payload = {
                        "embedding": query_emb.tolist(),
                        "final_answer": final_answer,
                        "top_urls": top_urls,
                        "citation_pass_rate": citation_pass_rate,
                        "cit_verifications": cit_verifications,
                        "sources_final_payload": sources_final_payload
                    }
                    await redis_client.setex(f"cache:{query_hash}", 300, json.dumps(cache_payload))
                except Exception as e:
                    print(f"Failed to set cache: {e}")
            
            total_time = int((time.perf_counter() - start_total) * 1000)
            
            await websocket.send_json({
                "type": "telemetry_dump",
                "tool_contributions": list(tool_contributions.values()),
                "llm_calls": llm_calls_to_log,
                "diagnostic_trace": diagnostic_trace if is_diagnostic_mode else None
            })
            
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




