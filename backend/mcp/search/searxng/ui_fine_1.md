# UI Plan — Tool Contribution Dashboard ("Real Workers vs Show Pieces")

Goal: a monitoring view, separate from the live per-query trace, that shows — across one query or aggregated over many — which tools/sources actually contribute to the final answer versus which get called but never survive ranking or get cited. This is what tells you which sources in your Domain Source Map are pulling real weight versus dead weight.

---

## 1. The core problem this solves

Right now your pipeline can call 5-6 sources on a query, but only 1-3 of them end up in the top-3 that actually feeds synthesis, and maybe only 1-2 of those get cited in the final answer with a passing citation check. A source can be **called constantly, cost latency every time, and never once actually contribute to an answer** — that's a "show piece": present, running, consuming your circuit-breaker budget and API quota, but not doing real work. This dashboard makes that visible instead of hidden inside logs.

---

## 2. The contribution funnel — per tool, per query

For every source called on a given query, track its position in this funnel:

```
Called → Returned results → Survived bi-encoder top-8 → Survived cross-encoder top-3
       → Cited in answer → Citation check passed
```

Each stage is a simple boolean/count per source per query. A source that gets called but stops at "Returned results" (never makes top-8) contributed nothing to that specific answer. A source that regularly stops there **across many queries** is a show piece, not a real worker.

---

## 3. New telemetry fields (extends the SQLite schema from the main build plan)

Add a `tool_contribution` table, one row per (query, source) pair:

```sql
CREATE TABLE tool_contribution (
  query_id TEXT,
  source_id TEXT,          -- e.g. "duckduckgo", "gdelt", "forbes_realtime"
  category TEXT,           -- which routing category it was called under
  elapsed_ms INTEGER,
  called BOOLEAN,
  returned_results BOOLEAN,
  result_count INTEGER,
  survived_biencoder BOOLEAN,
  survived_crossencoder BOOLEAN,
  cited_in_answer BOOLEAN,
  citation_check_passed BOOLEAN,
  circuit_breaker_state TEXT,   -- closed/open/half-open at call time
  timestamp TEXT
);
```

This is populated incrementally as the query moves through the pipeline (ranking stage writes `survived_biencoder`/`survived_crossencoder`, synthesis writes `cited_in_answer`, citation verification writes `citation_check_passed`) — one row per source per query, updated in place as each stage resolves, then finalized when the query completes. Same "avoid partial-row states on restart" principle as the main telemetry table — buffer in memory per query, single write (or a small batch of updates) at completion.

---

## 4. Two dashboard views

### View A — Per-query funnel (live, tied to the current query)

Shown alongside (or as a toggle next to) the existing live-status trace for the query just run:

```
Sources called this query:

duckduckgo    ●━━━●━━━●━━━○━━━○    stopped at: cross-encoder rerank
brave         ●━━━●━━━●━━━●━━━●    fully contributed — cited, verified
gdelt         ●━━━○━━━○━━━○━━━○    stopped at: returned results (low relevance)
forbes_rt     ●━━━●━━━●━━━●━━━○    cited but citation check FAILED
```

Each row is one source, rendered as a 5-segment progress track (called → returned → biencoder → crossencoder → cited+verified), filled segments showing how far it got. This is essentially a compact funnel/sparkline per source, immediately answering "did this tool actually matter for this specific answer."

### View B — Aggregate tool leaderboard (historical, across N queries)

A separate dashboard tab, querying the `tool_contribution` table over a time window (last 50/500 queries, or a date range):

| Source | Calls | Avg latency | Return rate | Top-8 rate | Top-3 rate | Cited rate | Citation pass rate | Breaker trips |
|---|---|---|---|---|---|---|---|---|
| brave | 340 | 310ms | 94% | 71% | 52% | 41% | 96% | 2 |
| duckduckgo | 340 | 280ms | 89% | 65% | 38% | 22% | 91% | 5 |
| gdelt | 120 | 420ms | 97% | 40% | 12% | 6% | 100% | 0 |
| forbes_rt | 45 | 850ms | 100% | 88% | 80% | 78% | 62% | 0 |

This table is the actual "real workers vs show pieces" answer: sort by **cited rate** (the truest measure of contribution) rather than call count or return rate — a source with a 97% return rate but 6% cited rate is a show piece; a source with fewer calls but a high cited rate is a real worker.

**Visual treatment:** color/highlight rows by a computed tier —
- 🟢 **Core worker**: high cited rate, low breaker-trip rate — trust this source
- 🟡 **Situational**: decent cited rate but only for specific categories — keep, but check it's routed correctly
- 🔴 **Show piece**: consistently low top-8/cited rate despite being called often — candidate for removal or a routing fix
- ⚫ **Unreliable**: high breaker-trip rate — needs the engine/wrapper investigated (matches Section on unofficial wrappers from the Domain Source Map doc)

---

## 5. Why "citation pass rate" matters as its own column, separate from "cited rate"

A source can be cited often but still be low-quality if its citation-check pass rate is poor (per the accuracy fix-plan doc's Step 7 numeric-consistency check) — this is exactly the `forbes_rt` row above: high cited rate (78%) but a noticeably lower citation pass rate (62%) than the other sources, meaning when it does get cited, the LLM's claim frequently doesn't precisely match what that source actually said. That's a distinct signal from "does this source get used" — it's "when used, is it used *correctly*" — and the dashboard needs both columns to tell the difference between a show piece and a worker that's contributing but noisily.

---

## 6. Breakdown by category (avoid one global misleading average)

A source's contribution rate should be viewable **filtered by routing category**, not just as one blended number — a source might be a strong worker for `news` queries but a total show piece for `finance` queries it also happens to get called on. The aggregate table (View B) needs a category filter/dropdown, and ideally the leaderboard is computable per-category as well as globally, since a source with a mediocre global cited-rate might actually be excellent within its one correct category and just poorly routed elsewhere — that's a routing bug to fix, not a reason to drop the source.

---

## 9. LLM call tracking — the missing half of "real contribution"

Tool contribution alone doesn't tell the full story — your pipeline has **two LLM calls per query** (classification, synthesis) that are themselves black boxes right now: no visibility into what was actually sent, what came back, how many tokens it cost, or how long it took relative to everything else. Without this, "tracking" is incomplete — you can see which search sources contributed, but not what the LLM itself was actually working with or costing you at each step.

### 9a. New telemetry table — one row per LLM call, not per query

A query has 2+ LLM calls (classify, synthesize — plus citation-verification if you upgrade that to a tiny NLI model later), so this needs its own table, not just more columns bolted onto the main query row:

```sql
CREATE TABLE llm_calls (
  query_id TEXT,
  step TEXT,                 -- "classify" | "synthesize" | "citation_check"
  model TEXT,                -- e.g. "claude-sonnet-4-6", "qwen2.5:7b"
  provider TEXT,             -- "api" | "ollama_local"
  prompt_text TEXT,          -- full input prompt actually sent (system + user combined, or store separately)
  system_prompt_text TEXT,
  response_text TEXT,        -- full raw output actually returned
  input_tokens INTEGER,
  output_tokens INTEGER,
  total_tokens INTEGER,
  elapsed_ms INTEGER,
  cost_usd REAL,             -- computed from provider's per-token pricing, null for local models
  temperature REAL,
  timestamp TEXT
);
```

- Store `prompt_text` and `response_text` in full — this is what makes debugging real. If classification misroutes a query, you need to see exactly what the classifier was given and exactly what JSON it returned, not just "classify: 640ms, success."
- `input_tokens`/`output_tokens` — API providers return this directly in the response metadata (e.g. `usage.input_tokens`/`usage.output_tokens` on Claude/OpenAI-style APIs); for local Ollama models, use the tokenizer to count, or Ollama's own returned `eval_count`/`prompt_eval_count` fields.
- `cost_usd` — only meaningful for API calls; compute from the provider's published per-token rate at call time. Leave null for local models (their "cost" is compute/electricity, not per-call — track separately if you care, but don't conflate it with API cost).

### 9b. Extend the per-query funnel view (View A) with an LLM panel

Alongside the source funnel rows from Section 4, add a compact LLM call panel for the same query:

```
LLM calls this query:

classify     model: claude-sonnet-4-6   340 in / 85 out tokens   640ms   $0.0009
synthesize   model: claude-sonnet-4-6   1,850 in / 420 out tokens 1.9s   $0.0071
                                                          ─────────────────────
                                                          total: $0.0080, 2.5s
```

Each row expandable (click to reveal) into the actual prompt/response text — this is your debugging surface when an answer looks wrong: you can immediately see whether the classifier mis-labeled the query, or whether synthesis was given good ranked sources but still produced a bad answer, rather than guessing which stage failed.

### 9c. Extend the aggregate leaderboard (View B) with an LLM cost/token table

Separate small table alongside the tool leaderboard, aggregated the same way (time range, optional category filter):

| Step | Calls | Avg input tokens | Avg output tokens | Avg latency | Total cost | Avg cost/call |
|---|---|---|---|---|---|---|
| classify | 340 | 310 | 78 | 590ms | $2.14 | $0.0006 |
| synthesize | 340 | 1,720 | 410 | 1.8s | $18.90 | $0.0556 |

This answers questions like "is classification's token usage creeping up as I add more categories to the prompt" or "which step is actually driving my API bill" — synthesis will almost always dominate cost/tokens since it carries the full ranked source content, but you want that confirmed with real numbers, not assumed.

### 9d. Token budget alerting (optional, worth flagging)

If `input_tokens` for synthesis starts trending upward over time (e.g. because ranked source snippets are getting longer, or more sources are being included than intended), that's a signal worth surfacing — a simple threshold check (e.g. flag if avg input tokens exceeds some ceiling you set) written into the aggregate view, rather than only discovering it via a surprise bill.

### 9e. Privacy/storage note

Storing full prompt/response text for every call will grow your SQLite file quickly, especially with long ranked-source content in synthesis prompts. Reasonable options: keep full text only for a rolling recent window (e.g. last 7 days) and drop to token counts/metadata-only for older rows, or cap `prompt_text`/`response_text` storage length with a truncation note. Decide this based on how much you actually need to review historically versus just needing the aggregate numbers to persist.

---

## 10. Updated component inventory

| Component | Responsibility |
|---|---|
| `ContributionFunnelRow` | One source's 5-segment funnel track for the current query (View A) |
| `PerQueryFunnelPanel` | Container for all sources' funnel rows on the current/last query |
| `ToolLeaderboardTable` | Aggregate historical table (View B), sortable columns |
| `TierBadge` | 🟢/🟡/🔴/⚫ tier indicator per row, computed client-side or server-side from the rates |
| `CategoryFilterDropdown` | Filters the leaderboard to one routing category or "all" |
| `TimeRangeSelector` | Last 50 queries / last 7 days / custom range, drives the SQL query window |
| `LLMCallPanel` | Per-query panel listing classify/synthesize (and citation_check if upgraded) calls with token/cost/latency summary |
| `LLMCallRow` | One LLM call, collapsed summary + expandable full prompt/response text |
| `LLMCostTable` | Aggregate token/cost/latency table per step (View B addition) |

---

## 11. Micro-steps to build this

### Phase A — Backend telemetry (tool contribution)
1. Create the `tool_contribution` table (schema above) alongside the existing telemetry table from the main build plan.
2. Add write points at each relevant pipeline stage: after source call (`called`, `returned_results`, `result_count`), after bi-encoder ranking (`survived_biencoder`), after cross-encoder ranking (`survived_crossencoder`), after synthesis (`cited_in_answer` — parse which citation numbers ended up in the final answer and map back to source_id), after citation verification (`citation_check_passed`).
3. Run 10-15 varied real queries, then manually query the SQLite table to confirm rows are complete and the funnel stages make logical sense (nothing marked `cited_in_answer=true` without `survived_crossencoder=true`, etc. — a basic sanity/consistency check).

### Phase A2 — Backend telemetry (LLM call tracking)
4. Create the `llm_calls` table (schema in Section 9a).
5. Wrap the classification LLM call: capture `prompt_text`/`system_prompt_text` before the call, `response_text` after, pull `input_tokens`/`output_tokens` from the provider's response metadata (or Ollama's `eval_count`/`prompt_eval_count` for local models), compute `cost_usd` from provider pricing if applicable, write one row.
6. Do the same wrap for the synthesis call — note synthesis is streamed, so token counts/cost need to be finalized once the stream completes, not mid-stream.
7. Run the same 10-15 queries from step 3, manually inspect a few `llm_calls` rows — confirm prompt/response text is captured in full and token counts look plausible (roughly matching rough word-count expectations) before trusting the numbers.

### Phase B — Aggregate query layer
8. Write the SQL (or a small Python aggregation function) that computes the View B leaderboard columns (rates, averages) from raw `tool_contribution` rows, parameterized by time range and optional category filter.
9. Write the equivalent aggregation for `llm_calls` (Section 9c's table) — same time range/category parameterization.
10. Add a `/dashboard/tool-contribution` and `/dashboard/llm-calls` FastAPI endpoint (or one combined endpoint) returning both aggregates as JSON — test with curl against your seeded queries before building any frontend.
11. Write the tier-computation logic (🟢/🟡/🔴/⚫ thresholds) as a small pure function — pick initial thresholds (e.g. cited rate >30% = core, 10-30% = situational, <10% with >20 calls = show piece, breaker-trip rate >15% = unreliable), expect to tune these once you have real data volume.

### Phase C — Frontend, View A (per-query funnel + LLM panel)
12. Build `ContributionFunnelRow` static with hardcoded segment-fill states, get the visual track right before real data.
13. Wire it to the current query's `tool_contribution` rows (can reuse the same WebSocket connection as the live-status trace, or a lightweight follow-up fetch once the query completes) — confirm segments fill correctly matching what actually happened in that query.
14. Build `LLMCallPanel`/`LLMCallRow` static first (hardcoded classify+synthesize example rows, collapsed/expanded states), then wire to real `llm_calls` data for the current query — confirm expanding a row shows the actual full prompt/response text correctly, not truncated unexpectedly.

### Phase D — Frontend, View B (aggregate leaderboard + cost table)
15. Build `ToolLeaderboardTable` static with hardcoded rows matching the example table above, get sorting/column layout right first.
16. Wire it to the `/dashboard/tool-contribution` endpoint, confirm real aggregate numbers render correctly.
17. Build `LLMCostTable` static, then wire to the `/dashboard/llm-calls` endpoint — confirm totals/averages match what you'd expect from manually summing a few known rows (a quick spot-check, not full reconciliation).
18. Add `CategoryFilterDropdown` and `TimeRangeSelector`, confirm both tables (tool leaderboard and LLM cost table) re-query and update correctly on filter change.
19. Add `TierBadge` coloring driven by the Phase B tier function's output.

### Phase E — Validate against your actual net-worth/GDP failure case
20. Once all views are working, deliberately re-run the net-worth/GDP queries from your earlier bad runs and check the funnel/leaderboard/LLM panel together — confirm you can now see, concretely, that (for example) a low-authority aggregator source made it to top-3 and got cited while Forbes/World Bank either weren't called or were correctly force-routed, **and** inspect the actual synthesis prompt/response from that query to see exactly what the LLM was given and whether it followed the date/recency instructions from the accuracy fix-plan doc. This is the real test of whether the dashboard is doing its job — full visibility into both the retrieval side and the LLM side of a bad answer, not just one or the other.