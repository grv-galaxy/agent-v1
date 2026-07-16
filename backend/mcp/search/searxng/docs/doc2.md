# UI Plan — Live "Behind the Scenes" Status View

Goal: a modern, animated status stream (like Claude/Perplexity/You.com) that shows exactly what the agent is doing in real time — which sources it's hitting, with their logos/favicons, parallel fetches shown simultaneously, extraction fallback states, and the streamed synthesized answer with citations — all driven by the JSON events the backend already emits over the WebSocket.

---

## 1. Event schema — what the backend emits

Every stage change becomes one WebSocket JSON event. This is an *extension* of the event schema from the main build plan, now with enough detail per event to render a rich UI, not just a latency bar.

```json
// Classification starts
{"type": "stage_start", "stage": "classify", "label": "Understanding your question", "timestamp": ...}

// Classification result
{"type": "stage_done", "stage": "classify", "elapsed_ms": 640,
 "result": {"categories": ["news", "india"], "params": {...}}}

// Routing decision (near-instant, can merge with classify_done in UI, but keep separate event)
{"type": "stage_start", "stage": "route", "label": "Choosing sources"}
{"type": "stage_done", "stage": "route", "elapsed_ms": 1,
 "result": {"sources": ["searxng:duckduckgo", "searxng:brave", "gdelt"]}}

// Each source fetch — THIS is the key event type for the "visiting pages" UI
{"type": "source_start", "source_id": "duckduckgo", "domain": "duckduckgo.com",
 "label": "Searching DuckDuckGo", "category": "search_engine"}

{"type": "source_done", "source_id": "duckduckgo", "elapsed_ms": 340, "status": "success",
 "result_count": 8}

{"type": "source_start", "source_id": "gdelt", "domain": "gdeltproject.org",
 "label": "Searching GDELT", "category": "news"}

{"type": "source_error", "source_id": "brave", "elapsed_ms": 2100, "status": "timeout",
 "circuit_breaker_tripped": true}

// Individual page visits during extraction fallback (distinct from source_start above —
// this is fetching ONE specific URL's full content, not a whole search engine)
{"type": "page_visit_start", "url": "https://reuters.com/...", "domain": "reuters.com",
 "label": "Reading full article"}

{"type": "page_visit_done", "url": "https://reuters.com/...", "elapsed_ms": 1200,
 "status": "success", "extraction_method": "trafilatura"}

// Ranking
{"type": "stage_start", "stage": "rank", "label": "Ranking results"}
{"type": "stage_done", "stage": "rank", "elapsed_ms": 28, "result": {"top_urls": [...]}}

// Synthesis — streamed
{"type": "stage_start", "stage": "synthesize", "label": "Writing answer"}
{"type": "synthesis_token", "text": "India's "}
{"type": "synthesis_token", "text": "central bank "}
{"type": "citation_marker", "n": 1, "url": "https://rbi.org.in/..."}
{"type": "stage_done", "stage": "synthesize", "elapsed_ms": 1850}

// Citation verification (background, updates UI after the fact)
{"type": "citation_check", "n": 1, "passed": true}
{"type": "citation_check", "n": 2, "passed": false}

{"type": "done", "total_elapsed_ms": 3200}
```

**Why `source_start`/`source_done` is separate from `page_visit_start`/`page_visit_done`:** a "source" is a whole engine/API call (DuckDuckGo, GDELT, PyPI) that returns multiple results; a "page visit" is fetching one specific URL's full content during extraction fallback. They render as different UI elements (source = a chip with an engine logo; page visit = a distinct "reading" indicator with a favicon), so the backend should keep them as distinct event types rather than overloading one shape for both.

**Every source/domain event carries a `domain` field** — that's the hook the frontend uses to fetch/display the right favicon, described in section 3.

---

## 2. Visual language — overall design direction

Since you mentioned "premium, dark mode, glassmorphism" in your folder structure earlier, that's the direction to build toward:

- **Dark background** (near-black, not pure black — something like `#0a0a0f`–`#111114`) with a subtle vignette or gradient, matching Claude/Perplexity/ChatGPT's dark modes.
- **Glassmorphism cards** for each event: `backdrop-filter: blur(...)`, semi-transparent background (`rgba(255,255,255,0.04)`–`0.08`), a thin 1px border at low opacity (`rgba(255,255,255,0.08)`), subtle box-shadow. This is what gives the "premium" feel rather than flat cards.
- **Accent color** — pick one (electric blue, violet, or amber all read as "AI product" without being generic) used sparingly: active-state glows, the streaming cursor, citation numbers, progress rings. Not overused across the whole UI or it stops feeling premium.
- **Typography** — a clean sans (Inter, or a similar geometric sans) for UI chrome, and a slightly warmer serif or humanist sans for the synthesized answer text itself — this is a small trick that makes the "answer" visually distinct from the "process" chrome, similar to how Perplexity differentiates its process trace from its answer typography.
- **Motion, not flashiness** — every state transition should animate (fade+slight vertical slide-in for new event chips, smooth width/opacity transitions for progress), but nothing bounces or overshoots. Claude/Perplexity's motion language is calm and fast (150-250ms eased transitions), not playful.

---

## 3. Component: Source/Domain chip (the "small logo + label" element)

This is the core visual unit you described — "small github logo, small X logo," etc.

**Structure of one chip:**
```
[favicon/logo]  Searching DuckDuckGo          [spinner/check/✕]
```

- **Favicon/logo source:** simplest reliable approach is Google's favicon service: `https://www.google.com/s2/favicons?domain={domain}&sz=64`, keyed off the `domain` field in the event. This gets you every site's real favicon without maintaining a logo asset library yourself — GitHub, Reuters, PyPI, arXiv, NSE, etc. all resolve automatically.
  - For sources without a real "domain" in the traditional sense (e.g. a raw API like FRED), fall back to a small curated icon set for known API categories (a generic "database" or "chart" icon), and only hit the favicon service for actual web-facing domains.
  - Cache resolved favicon URLs client-side (they don't change) so repeated queries against the same sources don't re-fetch.
- **Label:** the human-readable `label` field from the event ("Searching DuckDuckGo," "Reading full article," "Searching GDELT") — keep these short, present-tense, active verbs, matching Claude's own phrasing style ("Searching the web," "Reading page").
- **Status indicator (right side):**
  - In-flight: small spinning ring (not a generic spinner — a thin animated arc in the accent color, like Claude's own loading indicators)
  - Success: checkmark, brief green flash then settles to neutral
  - Failure/circuit-breaker trip: small ✕ or warning icon, chip dims/greys out rather than disappearing (you still want to see it was attempted)

**Chip states over its lifetime:** `pending → in-flight (animated) → done (settled)`. Each transition should be a smooth animation, not an abrupt swap.

---

## 4. Parallel execution — the "Claude-style" multi-source animation

This is the part you specifically flagged. When multiple sources fire simultaneously (e.g. DuckDuckGo + Brave + GDELT all called in parallel by the orchestrator), the UI should show this **as a group appearing together, animating in with a slight stagger**, not as a single sequential list growing one at a time.

**Recommended pattern:**
- Render all simultaneously-started sources as a **horizontal row of chips** (or a wrapped grid if more than ~4), all fading/sliding in within the same ~100-150ms window with a tiny stagger (20-30ms offset each) — this staggered-group entrance is exactly the visual cue that reads as "these are happening at once," which is what Claude's own tool-call UI does when multiple tools fire in parallel.
- Each chip in the row independently transitions `in-flight → done` on its own timeline (some sources return faster than others) — don't wait for the slowest one to update the whole row, update each chip individually as its `source_done`/`source_error` event lands.
- Once a group is fully resolved (all chips settled), it **collapses into a single summary line** — e.g. "Searched 4 sources · 6 results" — rather than staying expanded forever, keeping the trace compact as the conversation progresses. This is the same pattern Claude uses: expanded activity while working, collapsed summary once done, expandable again if the user clicks it.

**Sequential vs parallel — the UI needs to know which is which** from the backend: add a lightweight `group_id` field to `source_start`/`page_visit_start` events. Events sharing a `group_id` render as one animated row; events without a shared group (i.e. genuinely sequential stages like classify → route → rank) render as the vertical stacked timeline instead.

```json
{"type": "source_start", "source_id": "duckduckgo", "group_id": "fetch-1", ...}
{"type": "source_start", "source_id": "brave", "group_id": "fetch-1", ...}
{"type": "source_start", "source_id": "gdelt", "group_id": "fetch-1", ...}
```

---

## 5. Full vertical trace structure (top to bottom, one query)

```
● Understanding your question              [640ms]
● Choosing sources                          [1ms]
┌─────────────────────────────────────────────┐
│ [🦆] Searching DuckDuckGo  ✓   [🦁] Searching │  ← parallel group, animated row
│ Brave  ✓   [📰] Searching GDELT  ✓            │
└─────────────────────────────────────────────┘
  → collapses to: "Searched 3 sources · 14 results"
● Ranking results                           [28ms]
[📖] Reading full article — reuters.com     [1.2s]   ← only if extraction fallback triggers
● Writing answer...
  [streamed answer text appears here, growing]
  [1] [2] ✓ [3] ⚠                                    ← citation markers, verified async
```

Each `●` is a simple stage (classify/route/rank) rendered as a compact single-line row with an icon + label + elapsed time, right-aligned, fading to a muted color once done (only the currently active stage is "bright"). Source groups and page-visit reads get the richer chip treatment from sections 3-4.

---

## 6. Streamed answer + citations

- Answer text streams in below the trace, using the distinct typography from section 2.
- Citation markers (`[1]`, `[2]`...) render as small superscript pills, not just plain bracketed numbers — clicking one scrolls to/highlights the corresponding source chip above, tying the answer back to the trace visually (this is the "grounding" feeling that makes these UIs trustworthy).
- When a `citation_check` event arrives (async, after streaming finishes), update that citation pill in place: green check for `passed: true`, subtle amber warning for `passed: false` — don't block the initial render waiting for verification, update it live as the background check completes.

---

## 7. Component inventory (for `static/js/app.js` + `static/css/styles.css`)

| Component | Responsibility |
|---|---|
| `TraceContainer` | Vertical scrollable list, owns the WebSocket connection, dispatches events to child components by `type` |
| `StageRow` | Simple single-line stage (classify/route/rank) — icon, label, elapsed time, active/done state |
| `SourceGroup` | Renders one `group_id`'s chips as an animated row, handles collapse-on-complete |
| `SourceChip` | Single source: favicon, label, status indicator, in-flight animation |
| `PageVisitRow` | Extraction fallback "Reading full article" state, favicon + domain + elapsed |
| `FaviconResolver` | Small utility: domain → favicon URL, with client-side caching |
| `AnswerStream` | Renders streamed tokens, manages citation pill insertion |
| `CitationPill` | Superscript citation marker, updates state on `citation_check` events, click-to-scroll |
| `HistoryPanel` | Separate view querying the SQLite-backed history endpoint (from the main build plan) — not part of the live trace, a secondary tab/panel |

---

## 8. Micro-steps to build this UI

### Phase A — Backend event richness (before touching frontend at all)
1. Extend the WebSocket event emitter to include `label`, `domain`, and `group_id` fields as shown in section 1 — confirm via a raw WebSocket client (e.g. `websocat` or a tiny test script) that events look exactly like the schema above.
2. Add `group_id` generation in the orchestrator wherever sources are fired concurrently (e.g. `asyncio.gather` calls) — confirm sequential stages (classify/route/rank) do NOT get a `group_id`, only truly parallel fetches do.
3. Add the `page_visit_start`/`page_visit_done` events into the extraction fallback code path specifically (separate from `source_start`/`source_done`) — confirm both event shapes coexist correctly in one run's event log.

### Phase B — Static shell, no live data
4. Build the dark-mode base layout (background, card container, typography) in `styles.css` with no live data — just a hardcoded example trace to design against.
5. Build `StageRow` as a static component first, hardcode 3 example rows, confirm the visual states (active/done) look right before wiring real data.
6. Build `SourceChip` static, hardcode one example with a real favicon URL, confirm the favicon loads and the spinner/check states look right.
7. Build `SourceGroup` static with 3 hardcoded chips side by side, confirm the staggered fade-in animation and the collapse-to-summary behavior both work with fake data before any WebSocket is involved.

### Phase C — Wire real data in, one event type at a time
8. Connect the WebSocket, log raw incoming events to console only (no rendering yet) — confirm real events match the schema from Phase A.
9. Wire `stage_start`/`stage_done` events to `StageRow` only — confirm classify/route/rank show up correctly, ignore all other event types for now.
10. Wire `source_start`/`source_done`/`source_error` to `SourceGroup`/`SourceChip` — confirm a real parallel SearXNG call renders as an animated group, collapses correctly on completion.
11. Wire `page_visit_start`/`page_visit_done` to `PageVisitRow` — trigger a real extraction fallback (force a low-relevance query) and confirm the "Reading full article" state appears and resolves correctly.
12. Wire `synthesis_token` events to `AnswerStream` — confirm streamed text renders progressively, not all-at-once.
13. Wire `citation_marker` and `citation_check` events to `CitationPill` — confirm pills appear during streaming and update (✓/⚠) after the async check completes.

### Phase D — Polish pass (do last, only once data flow is fully correct)
14. Tune animation timings (stagger delays, fade durations) — this is where you actually make it "feel like Claude," and it's much easier to tune once real data is already flowing correctly than to guess at timings against fake data.
15. Add the glassmorphism treatment (blur, transparency, borders) across all card components consistently.
16. Add the `HistoryPanel` tab, wired to the SQLite-backed endpoint from the main build plan — separate from the live trace, doesn't need any of the animation work above.
17. Cross-browser/responsive pass — confirm the parallel chip rows wrap sensibly on a narrower viewport instead of overflowing.