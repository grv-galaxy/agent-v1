# 🔍 Project Audit — Search AI Agent
### Cross-referencing `doc.md`, `doc1.md`, `doc2.md` against the actual codebase

---

## ✅ What You Have Achieved

### `doc.md` — Build Plan v2 (Core Architecture)

| Step | Description | Status |
|------|-------------|--------|
| Step 0 | SearXNG via Docker + Redis cache | ✅ Done |
| Step 1 | LLM Query Classification (Groq/structured JSON) | ✅ Done — `classifier.py` with few-shot prompt |
| Step 2 | Routing (pure function, category → sources) | ✅ Done — `router.py` with 11 category mappings |
| Step 3 | FastMCP server wrapping SearXNG | ✅ Done — `mcp_server.py` |
| Step 3b | Circuit breaker (per-engine, per-category) | ✅ Done — `breaker.py` (CLOSED/OPEN/HALF_OPEN states) |
| Step 4 | Extraction fallback (Trafilatura + Playwright) | ✅ Done — `utils/extractor.py` |
| Step 5 | Bi-encoder ranking (MiniLM ONNX, local) | ✅ Done — `ranker.py` |
| Step 5b | Cross-encoder rerank (top-8 only) | ✅ Done — `ranker.py` (ms-marco cross-encoder) |
| Step 6 | Synthesis with citations (streamed via Groq) | ✅ Done — `synthesizer.py` |
| Step 7 | Automated citation verification (n-gram overlap) | ✅ Done — `citations.py` |
| Step 8 | SQLite telemetry (one row per query) | ✅ Done — `telemetry.py` |
| Dashboard | FastAPI + WebSocket server | ✅ Done — `orchestrator.py` |

**`doc.md` completion: ~95%** — Only minor gap is the background health-check task for auto-recovering tripped circuit-breaker engines (Step 3b, point 4).

---

### `doc1.md` — Domain Source Map (Tiered Source Integration)

| Tier | Sources | Status |
|------|---------|--------|
| **Tier 1** — Pure APIs, no auth | PyPI, npm, GitHub, arXiv, Wikipedia, WorldBank | ✅ All 6 done |
| **Tier 2** — APIs needing free keys | Semantic Scholar, FRED, SEC EDGAR, CourtListener, data.gov.in | ⏭️ **Intentionally skipped** (require API keys) |
| **Tier 3** — RSS Feeds | BBC, NYTimes, The Hindu, Times of India, PIB, Moneycontrol | ✅ All done — `rss_fetcher.py` |
| **Tier 4** — Unofficial wrappers + circuit breaker | NSE (`nsepython`), BSE (`bsedata`), yfinance | ✅ All done — `markets.py` |
| **Tier 5** — Full extraction pipeline | Indian Kanoon, WIPO Patentscope, Generic Docs fallback | ✅ All done — `sources/extraction.py` |

**Extra sources implemented beyond `doc1.md`:**
- GDELT (referenced in doc1.md but not in a tier) → *Not yet wired in*

**`doc1.md` completion: ~80%** (Tier 2 excluded by choice; GDELT, IMF, PubMed, bioRxiv, crates.io, etc. not wired yet)

---

### `doc2.md` — UI / Live Trace Frontend

| Phase | Description | Status |
|-------|-------------|--------|
| Phase A | Backend WebSocket event richness (labels, domain, group_id) | ✅ Done — `orchestrator.py` rewritten |
| Phase B | Static UI shell (dark mode, glassmorphism, animations) | ✅ Done — `static/styles.css` |
| Phase C | Live WebSocket wiring (DOM factories, real-time rendering) | ✅ Done — `static/app.js` |
| Phase D | History Panel (SQLite-backed `/api/history` endpoint + tab UI) | ✅ Done |

**doc2.md completion: ~90%** — The sections below are not yet implemented:

| Gap in doc2.md | Details |
|----------------|---------|
| Engine Status Panel | doc.md dashboard asks for a live "which engines are `CLOSED`/`OPEN`/`HALF_OPEN`" panel per category |
| Waterfall bar visualization | Per-stage latency bars (e.g., Classify: ▓▓▓░ 640ms, Rank: ▓░ 28ms) |
| Citation click-to-scroll | Clicking a `[1]` pill should scroll to / highlight the SourceChip that originated it |
| `PageVisitRow` in UI | `page_visit_start` events are emitted by backend but not yet rendered with a distinct "Reading full article" row |
| Historical aggregate stats | The History tab shows individual queries but not the aggregate charts (avg latency per stage, engine trip-rate over time) |
| Responsive/mobile polish | `@media` queries for narrow-viewport chip wrapping not yet added |

---

## ❌ What Is Still Left

### Critical Missing Pieces (functional gaps)

1. **Circuit Breaker auto-recovery task** — `doc.md` Step 3b says a background `asyncio` task should periodically probe `OPEN` engines and promote them to `HALF_OPEN`. The `mark_half_open()` method exists in `breaker.py` but nothing calls it automatically. Right now, an engine that trips stays tripped until the server restarts.

2. **Extraction fallback trigger** — `doc.md` Step 4 says extraction should auto-trigger when ranked snippet relevance is below a threshold. Currently, the Tier 5 sources (Indian Kanoon, WIPO, etc.) only fire based on routing category — the document-score-based automatic fallback for *any* category isn't wired in.

3. **`group_id` for parallel source events** — Every source emits `group_id: "fetch-1"` (hardcoded). This means the UI always collapses everything into one group. The orchestrator should generate a fresh unique `group_id` per query (e.g., `f"fetch-{uuid4().hex[:8]}"`) so parallel events across multiple queries don't collide.

### UI Gaps

4. **Engine Status Panel** — There is no live panel showing which circuit breaker states are currently `OPEN`. This is explicitly called out in `doc.md` and is important for debugging.

5. **Per-stage latency waterfall bars** — The plan calls for visual bars (not just text like "640ms"). Right now, the History tab only shows raw numbers.

6. **`PageVisitRow`** — When WIPO/Kanoon are being deep-read, the UI emits `page_visit_start` from the backend, but `app.js` handles it the same as a `source_start`, so there is no distinct "Reading full article..." row with a different visual treatment.

7. **Aggregate historical charts** — The History tab is cards only; no aggregate views (avg latency, engine trip rate over time, citation pass rate trend).

---

## 💡 What You Should Add to Make This System Much Better

### 🔴 High Priority (Fixes real functionality gaps)

**1. Auto-recovery background task for circuit breaker**
```python
@app.on_event("startup")
async def health_check_loop():
    async def probe():
        while True:
            await asyncio.sleep(120)  # every 2 minutes
            for (engine, cat) in breaker.get_open_engines():
                breaker.mark_half_open(engine, cat)
    asyncio.create_task(probe())
```

**2. Score-based extraction fallback**
After ranking, check if `top_3[0]["score"] < threshold`. If yes, automatically run `trafilatura` on that URL before synthesis — this is what makes the extraction pipeline truly "smart" instead of just category-gated.

**3. Unique `group_id` per query run**
```python
import uuid
group_id = f"fetch-{uuid.uuid4().hex[:8]}"
```
Pass this into every `track_source` call in that query's run.

---

### 🟡 Medium Priority (Significantly improves the system)

**4. Add GDELT for Global News**
It's listed in `doc1.md` under Category 2 as the best free global breadth source with 100+ languages. Currently not wired — just needs a simple `httpx` call to `https://api.gdeltproject.org/api/v2/search/search?query=...&format=json&mode=artlist`.

**5. Caching layer (Redis)**
Redis is already in the `docker-compose.yml` but not actually used for caching query results. Adding a simple hash-based cache (`MD5(query) → results`) with a 5-minute TTL would dramatically reduce latency on repeated or similar queries.

**6. Rate limiting on the WebSocket endpoint**
Currently a single client could spam queries. Add a simple token-bucket or per-IP rate limiter using `slowapi` to protect the backend.

**7. Add remaining Tier 1 sources from doc1.md that aren't wired yet:**
- `crates.io` (Rust packages)
- `pkg.go.dev` (Go modules)
- `rubygems.org` (Ruby gems)
- IMF Data API

---

### 🟢 Nice-to-Have (Polish and future-proofing)

**8. Engine Status Panel in the UI**
A small sidebar or collapsed widget showing live circuit-breaker state per engine. Read from a new `GET /api/breaker-status` endpoint.

**9. Historical aggregate charts (Chart.js)**
Add a lightweight `Chart.js` chart to the History tab showing:
- Average latency per stage over time
- Engine trip-rate bars
- Citation pass-rate trend line

**10. Full-text search on history**
The `/api/history` endpoint currently just sorts by timestamp. Add a `?q=` search parameter to do `LIKE '%query%'` filtering on past queries.

**11. NLI-based citation verification**
The current `citations.py` uses n-gram overlap, which is fragile. Upgrade to a tiny entailment model (e.g. `cross-encoder/nli-deberta-v3-small` via ONNX) for much more accurate hallucination detection.

**12. Query deduplication / fuzzy cache**
Before classifying a query, check if a semantically similar query was recently answered (using bi-encoder cosine similarity against a cache of recent queries). If similarity > 0.95, return the cached answer instantly.

**13. Streaming `PageVisitRow` in the UI**
Give the "Reading full article…" state its own distinct glassmorphism card with a `📖` icon, domain name, and animated "wave" loading indicator instead of the standard spinner — this is what `doc2.md` originally asked for.

---

## 📊 Overall Completion Summary

| Document | Completion |
|----------|-----------|
| `doc.md` — Core Backend Architecture | **~95%** |
| `doc1.md` — Domain Source Integration | **~80%** (Tier 2 skipped by choice) |
| `doc2.md` — UI / Live Trace Frontend | **~90%** |
| **Overall** | **~88%** |

> [!TIP]
> The highest-value single next action is implementing the **circuit breaker auto-recovery background task** — it's ~10 lines of code and fixes a real production reliability gap where tripped engines never recover.

> [!NOTE]
> Tier 2 sources (`doc1.md`) are the biggest functional gap in terms of source coverage, but they all require API key registration. When you're ready, GDELT and WorldBank IMF APIs have the highest value-to-effort ratio among those.
