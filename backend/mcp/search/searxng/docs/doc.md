# Search AI Agent — Build Plan v2 (SearXNG + FastMCP)

Changes from v1: classification now uses a real LLM API call (not embeddings) for reliable structured JSON output — latency is not a constraint on this stage. Added engine circuit breaker, bi-encoder→cross-encoder truncation, automated citation verification, SQLite telemetry, and an extraction-fallback UI state.

---

## Latency budget — revised

LLM classification is now explicitly **outside** the fast-path budget. Two budgets, not one:

| Stage | Realistic latency | Budget |
|---|---|---|
| Query classification (LLM API call, structured JSON) | 300ms–2s | Not constrained — accuracy over speed |
| Routing decision | <1ms | Fast path |
| SearXNG fetch (few engines, circuit-breaker protected) | 300ms–1.2s | Fast path target |
| Bi-encoder ranking (MiniLM, all results) | 10–20ms | Fast path |
| Cross-encoder rerank (top 8 only) | 15–40ms | Fast path |
| Extraction fallback (only when triggered) | 500ms–3s | Separate, shown as distinct UI state |
| LLM synthesis with citations | 500ms–3s+ | Streamed, non-blocking |

**Net picture:** classification + synthesis are both real LLM calls and both take real time — that's fine and expected. What stays fast and worth optimizing hard is routing → SearXNG → ranking, which is the part that determines what the LLM even gets to work with. The UI should reflect this honestly: classification shows as a stage with its own latency, not something hidden or assumed instant.

---

## Architecture overview

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────┐
│   Browser    │◄───►│   FastAPI (UI +   │◄───►│  FastMCP     │
│  (dashboard) │ WS  │   orchestrator)   │ MCP │  server      │
└─────────────┘     └──────────────────┘     │ (SearXNG tool)│
                       │      │    │           └──────┬───────┘
                       │      │    │                   │
                       ▼      ▼    ▼                   ▼
                  ┌─────────┐ ┌────────┐        ┌─────────────┐
                  │ LLM API  │ │ SQLite │        │  SearXNG     │
                  │ (classify│ │telemetry│        │  (Docker)    │
                  │ +synth)  │ └────────┘        └─────────────┘
                  └─────────┘
                       │
                       ▼
                 ┌─────────────┐
                 │ Local models │
                 │ (MiniLM +    │
                 │  reranker)   │
                 └─────────────┘
```

Same two-process split as before: FastMCP server wraps SearXNG as an MCP tool; the FastAPI orchestrator does classification, routing, ranking, extraction fallback, synthesis, telemetry, and serves the dashboard over WebSocket.

---

## Step 0: SearXNG setup

- Docker-compose, official SearXNG image, JSON output format enabled.
- Trim engine list to 3–4 reliable ones to start (e.g. DuckDuckGo, Brave, Startpage).
- Set `request_timeout` low (2–3s) — this bounds a single request, but does **not** replace the circuit breaker below; the two solve different problems (one request being slow vs. one engine being reliably bad over time).
- Redis caching enabled for repeated/similar queries during dev.

## Step 1: Query classification — LLM API call

- Call a real LLM API (not local embeddings) with a prompt instructing strict JSON-only output: category label(s), confidence, and extracted structured params (entities, date range, region/language hint — e.g. detecting an India-specific query and setting `language=en-IN`).
- Multi-label: a query can span categories (e.g. finance + patents) — the JSON schema should support an array of labels, not force single-label.
- No latency constraint here — prioritize prompt reliability (few-shot examples of correct JSON in the system prompt, explicit "respond with JSON only, no preamble") over speed. Log this stage's latency anyway, purely for visibility on the dashboard — not to optimize against.
- This stage's output feeds directly into Step 2 routing.

## Step 2: Routing

- Pure function, near-zero cost: classifier output → SearXNG query params (`categories`, `time_range`, `language`).
- Since only SearXNG is wired up right now, routing's job is mapping your label schema onto SearXNG's built-in categories (`general`, `news`, `science`, `it`, etc.) — designed so adding new tools later (arXiv, EDGAR, etc.) is just new branches in this same lookup, not a rewrite.

## Step 3: FastMCP server + resilient engine selection

**FastMCP server:** one `search_web(query, category, time_range, language, engines)` tool, `@mcp.tool` decorator, async `httpx` call to SearXNG's `/search?format=json`. Test standalone via `fastmcp dev server.py` before wiring the orchestrator.

**Circuit breaker (new):** implemented in the orchestrator, not inside SearXNG or the MCP server — it decides *which engines to pass* as the `engines` parameter on each `search_web` call.

- Track failures **per engine, per category** (an engine can be reliable for `general` but flaky for `news` — a global counter would over-penalize it).
- Rolling window: e.g. 3 failures/timeouts in 10 minutes → mark engine "open" (excluded) for that category.
- Background health-check task periodically probes excluded engines with a cheap query; on success, moves them to "half-open" → re-admit after one more clean result.
- State (per engine/category: `closed`/`open`/`half-open`, failure timestamps) can live in-memory for v1; log transitions to SQLite telemetry (Step 7) so you can see engine reliability over time, not just live.

## Step 4: Extraction (with fallback UI state)

- Default: use SearXNG's returned snippets directly — no full-page fetch in the hot path.
- Fallback trigger: if ranked snippet relevance (Step 5 score) falls below a threshold, trigger full-page extraction (trafilatura, Playwright fallback for JS-heavy pages) on the top 1–2 URLs only, not all results.
- **UI must show a distinct "Reading full page…" state** when this fires, not a generic spinner — this is a real, variable-length delay (500ms–3s) and the UI should communicate *why* the wait is happening rather than leaving it ambiguous.


## Step 5: Ranking — bi-encoder first pass, cross-encoder truncated
 
- **Bi-encoder pass (MiniLM, already available locally):** embed the query and all ~20 SearXNG results, cosine-rank, take top 8. Cheap, O(N), always run on the full result set.
  - Model already present locally at:
    `C:\Users\kumar\Documents\agent-v1\backend\mcp\memory\model`
    (MiniLM-L12-style BERT encoder, `hidden_size=384`, 12 layers — ships with pre-converted ONNX weights including `model_quantized.onnx` / `model_q4.onnx`).
  - Load via `onnxruntime` (prefer the quantized/q4 variant for speed) — **no `torch` dependency needed for this stage**, since the ONNX export is already provided.
  - No download step required for this model — point the loader at the path above instead of pulling from Hugging Face.
- **Cross-encoder pass, truncated to top 8 only — model still needed, not yet chosen:** cross-encoders are O(N) but computationally heavy per comparison, so this must never run on the full raw result set, only the 8 bi-encoder finalists, re-ordered into a final top 3 for the LLM.
  - Candidates (ONNX-available, no torch required): `cross-encoder/ms-marco-MiniLM-L-6-v2` (smaller, faster, good default) or `BAAI/bge-reranker-base` (larger, stronger relevance quality — upgrade path if the smaller one underperforms in testing).
  - This model is not yet downloaded/placed locally — decide and add its path alongside the bi-encoder path above once chosen.
- This two-stage structure bounds Step 5's cost regardless of how many raw results SearXNG returns on a given query.

## Step 6: Synthesis with citations (streamed)

- LLM call (API or local), streamed token-by-token over the same WebSocket as the rest of the pipeline.
- Prompt: numbered snippets (`[1]`–`[3]`, post-rerank), instruct inline citation by number, instruct the model to only claim what the snippets support.
- UI shows ranked results immediately after Step 5 completes; synthesized answer streams in below.

## Step 7: Automated citation verification (new, post-stream)

- Background task runs after the synthesis stream finishes — does not block the user-visible response.
- For each cited number (`[2]`, etc.), check whether the claim text near that citation actually overlaps with snippet 2's content — start with lightweight n-gram/string overlap matching; a tiny local NLI/entailment model is a reasonable upgrade later, not required for v1.
- Result (`citation_check_passed: true/false` per citation) gets logged to SQLite and can be surfaced in the dashboard (e.g. a small ✓/⚠ marker next to each citation) — this is what stops you from silently optimizing for speed at the expense of grounding accuracy.

## Step 8: SQLite telemetry (new, replaces "WebSocket-only" from v1)

- Background thread writes one row per query with: query text, per-stage latency (classify/route/searxng/rank/extract/synthesize), which engines were used vs. circuit-broken, top snippet URLs, final answer, citation-check results, timestamp.
- WebSocket still drives the *live* dashboard view; SQLite is what makes the data queryable after the fact — e.g. "show me the latency waterfall for the last 50 queries routed to `news`," or "which engine has the highest circuit-breaker trip rate this week."
- Single write per query (one row, all fields) rather than scattering writes across stages — simpler and avoids partial-row states if the process restarts mid-query.

---

## The evaluation dashboard

**Backend:** FastAPI, `/query` POST kicks off the pipeline, WebSocket streams staged events:
```
{"stage": "classify", "elapsed_ms": 640, "result": {...}}
{"stage": "route", "elapsed_ms": 1, "result": {...}}
{"stage": "searxng", "elapsed_ms": 340, "engines_used": [...], "engines_skipped": [...], "result": [...]}
{"stage": "rank", "elapsed_ms": 28, "result": [...]}
{"stage": "extract_fallback", "elapsed_ms": 1400, "triggered": true, "url": "..."}
{"stage": "synthesis_token", "text": "..."}
{"stage": "citation_check", "results": [{"n": 1, "passed": true}, {"n": 2, "passed": false}]}
{"stage": "done", "total_elapsed_ms": 2900}
```

**Frontend (simple HTML/JS is enough for v1):**
- Query input box
- Waterfall/timeline bar per stage — now with classification shown honestly as its own (larger) bar rather than assumed-instant
- Engine status panel: which engines are currently `closed`/`open`/`half-open` per category (makes the circuit breaker visible, not just log lines)
- "Reading full page…" indicator when extraction fallback fires
- Raw SearXNG + reranked results panel
- Synthesized answer with numbered citations, each marked ✓/⚠ from Step 7's check
- Historical view querying SQLite: average latency per stage over last N queries, engine trip-rate over time, citation pass-rate over time

---

## Micro-step execution plan

Each numbered item below is small enough to finish and *verify* in one sitting — you should be able to say "done, confirmed working" before moving to the next one. Grouped under the same 11 phases as the build order, but broken down further.

### Phase 1 — SearXNG running
1. Install Docker + docker-compose if not already set up.
2. Pull SearXNG's official docker-compose file, `docker-compose up`, confirm the web UI loads in a browser at `localhost`.
3. Edit `settings.yml`: cut engine list down to 3–4 (DuckDuckGo, Brave, Startpage).
4. Set `request_timeout` to 2–3s in settings, restart container.
5. Confirm `format=json` works: `curl "localhost:8080/search?q=test&format=json"`, verify you get parseable JSON back, not HTML.
6. Add Redis to the compose file, confirm SearXNG connects to it (check logs for cache hits on a repeated query).

### Phase 2 — FastMCP server
7. `pip install fastmcp` (or `uv pip install fastmcp`) in a fresh venv, confirm `fastmcp version` runs.
8. Write a minimal `server.py` with one `@mcp.tool` that just returns a hardcoded string — confirm `fastmcp dev server.py` launches the Inspector and you can call it successfully.
9. Replace the hardcoded tool with `search_web(query, category, time_range, language)` that calls SearXNG's JSON endpoint via `httpx.AsyncClient`.
10. Test via the Inspector: call `search_web` with a real query, confirm you get back parsed SearXNG results through the MCP protocol.
11. Switch transport from stdio (Inspector default) to Streamable HTTP, confirm the server starts and responds to a raw HTTP request.

### Phase 3 — Orchestrator skeleton (no UI yet)
12. New script/process: connect to the FastMCP server as an MCP client, call `search_web` with a hardcoded query, print the raw result.
13. Write the LLM classification call: one function, takes a query string, returns parsed JSON (label array + params). Test on 3–4 sample queries by hand, eyeball the JSON.
14. Write the routing function: pure function, classifier JSON in → SearXNG query params out. Unit-test it with a few hardcoded classifier outputs (no live LLM call needed for this test).
15. Wire classify → route → `search_web` call in sequence, print each stage's output and `time.perf_counter()` elapsed for that stage to console.
16. Run 5 different real queries end-to-end through this console version, confirm each produces sane routing + sane SearXNG results.

### Phase 4 — Circuit breaker
17. Write the circuit breaker as a standalone class (state per engine+category: closed/open/half-open, failure timestamps) with no dependency on the rest of the pipeline yet. Unit test: feed it 3 fake failures, confirm it flips to "open."
18. Wire it into the `search_web` call in the orchestrator: before calling, ask the breaker which engines are eligible; after calling, report success/failure back to it.
19. Force a failure artificially (e.g. temporarily point one "engine" at a bad port, or mock a timeout) and confirm the breaker excludes it after 3 failures within the console-logged output.
20. Add the background health-check task that periodically retries excluded engines; confirm an excluded engine gets re-admitted after a manual fix.

### Phase 5 — Bi-encoder ranking
21. `pip install sentence-transformers`, load `all-MiniLM-L6-v2` once at startup, confirm it embeds a test string without error.
22. Write the ranking function: embed query + all SearXNG snippet texts, cosine similarity, sort, return top 8. Test on one real query, eyeball whether the top 8 look relevant.

### Phase 6 — Cross-encoder rerank
23. Load `bge-reranker-base`, confirm it scores a single (query, snippet) pair without error.
24. Wire it to run only on the top-8 output from Phase 5, re-sort, take top 3. Confirm on the same test query that the top 3 look at least as good as before, ideally better-ordered.

### Phase 7 — Synthesis (streamed)
25. Write a non-streamed synthesis call first: numbered top-3 snippets in the prompt, ask for a cited answer, print the full response once it returns. Confirm citations reference real snippet numbers.
26. Convert to streaming: print tokens as they arrive instead of waiting for the full response. Confirm it visibly streams in the console.
27. Run the full pipeline end-to-end (classify → route → search → breaker → rank → rerank → stream synthesis) on 5 queries, console-only, confirm no stage crashes and citations look grounded.

### Phase 8 — Citation verification
28. Write the overlap-check function standalone: given a claim string and a snippet string, return a pass/fail. Unit test with one obviously-matching pair and one obviously-mismatching pair.
29. Wire it as a post-stream step: parse the synthesized answer for `[n]` markers, run the check against snippet n for each, print pass/fail per citation to console.

### Phase 9 — SQLite telemetry
30. Create the SQLite schema (one table, one row per query) with the fields listed in the plan.
31. Write the single insert call, wire it to fire once at the end of a completed pipeline run.
32. Run a handful of queries, then manually query the SQLite file (`sqlite3` CLI or a quick script) to confirm rows look correct and complete.

### Phase 10 — Dashboard
33. Minimal FastAPI app: one `/query` POST endpoint that runs the pipeline synchronously and returns the final JSON (no WebSocket yet). Confirm you can hit it with curl/Postman and get a full result back.
34. Add the WebSocket endpoint, emit one hardcoded fake stage event, confirm a plain JS client can connect and receive it.
35. Wire real stage events into the WebSocket, one stage at a time (classify first, confirm it shows up in browser console, then add route, then searxng, etc.) rather than wiring all stages at once.
36. Build the static HTML page: query box + a `<div>` per stage that fills in as events arrive. No styling yet — just confirm data is landing in the right places.
37. Add the waterfall bar visualization once the raw data is confirmed flowing correctly.
38. Add the engine status panel, reading current breaker state.
39. Add the citation ✓/⚠ markers next to the rendered answer.
40. Add the historical view: a second page/tab that queries SQLite and renders simple aggregate stats (avg latency per stage, engine trip-rate, citation pass-rate).

### Phase 11 — Extraction fallback (last, optional for v1)
41. Write the fallback trigger check: if top-1 rerank score is below a threshold, flag `needs_extraction`.
42. Write the trafilatura extraction call on a single URL, test standalone against a real page.
43. Add the Playwright fallback path for when trafilatura returns empty (JS-heavy page), test against one known JS-rendered page.
44. Wire the "Reading full page…" WebSocket event to fire when extraction triggers, confirm it shows in the UI before the extracted content/synthesis follows.

---

## Suggested build order

1. SearXNG via Docker, confirm `format=json`, tune engines/timeout.
2. FastMCP server wrapping `search_web`, test via `fastmcp dev`.
3. Orchestrator skeleton: LLM classify → route → call MCP tool → console-print timings (no UI, no circuit breaker yet).
4. Add circuit breaker around engine selection — test by deliberately blocking one engine and confirming failover.
5. Add bi-encoder ranking, confirm snippet quality before adding cross-encoder or any LLM synthesis.
6. Add cross-encoder truncation on top 8.
7. Add Ollama/API synthesis, streamed.
8. Add citation verification as a post-stream background task.
9. Add SQLite telemetry — single row per completed query.
10. Build the FastAPI + WebSocket dashboard last, observing an already-working pipeline rather than driving its design.
11. Add extraction fallback + its dedicated UI state once the core loop is stable — it's the one component that's optional for a first working version.



---


# Search AI Agent — Folder Structure


```text
search-agent/
├── .gitignore
├── README.md
├── docker-compose.yml           # Runs SearXNG and Redis
├── searxng/
│   └── settings.yml             # SearXNG configuration (timeout, engines)
├── pyproject.toml               # UV package config & dependencies
├── uv.lock                      # UV lockfile (auto-generated)
├── .env.example                 # Environment variables template
├── data/
│   └── .gitkeep                 # Telemetry SQLite database directory
├── src/
│   └── search_agent/
│       ├── __init__.py
│       ├── config.py            # Configuration & environment settings
│       ├── schemas.py           # Shared Pydantic models (ClassifierOutput, etc.)
│       ├── mcp_server.py        # FastMCP server wrapping SearXNG
│       ├── orchestrator.py      # FastAPI backend and WebSocket server
│       ├── classifier.py        # LLM query classifier (structured JSON)
│       ├── router.py            # Category routing logic (pure functions)
│       ├── breaker.py           # In-memory + SQLite-logged circuit breaker
│       ├── ranker.py            # Bi-encoder + Cross-encoder rankers
│       ├── extractor.py         # Trafilatura + Playwright fallback extractor
│       ├── synthesizer.py       # LLM streaming synthesis
│       ├── citations.py         # Citation verification check
│       ├── telemetry.py         # SQLite logging client
│       ├── prompts/             # External LLM prompt templates
│       │   ├── classify.txt     # Few-shot query classification prompt
│       │   └── synthesize.txt   # Answer synthesis and citation prompt
│       └── static/              # Dashboard frontend
│           ├── index.html       # Web dashboard HTML
│           ├── css/
│           │   └── styles.css   # Premium CSS styling (dark mode, glassmorphism)
│           └── js/
│               └── app.js       # WebSocket handler & UI logic
└── tests/
    ├── __init__.py
    ├── conftest.py              # Shared pytest fixtures (mocks, etc.)
    ├── test_router.py           # Unit tests for routing
    ├── test_breaker.py          # Unit tests for circuit breaker
    ├── test_ranker.py           # Unit tests for ranker models
    ├── test_classifier.py       # Stub unit tests for classification
    └── test_citations.py        # Stub unit tests for citations
```