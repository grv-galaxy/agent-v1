# UI Plan — Answer + Backend-Built Sources List (Google AI Mode style)

Goal: keep the current synthesized-answer UX exactly as it is, but add a **deterministic, backend-assembled sources section below it** — favicon, headline, domain, link — built from your actual ranking/retrieval data structures, never from LLM text generation.

---

## 1. Why this must be backend-built, not LLM-generated

The LLM's job stays exactly what it already is: write the answer paragraph with inline `[n]` citation markers. It should **never** be asked to also output the sources list as text — that reintroduces the exact hallucination risk the accuracy fix-plan doc addressed (LLM inventing or mis-stating a title/URL). The sources list must instead be assembled mechanically from data your pipeline already has by the time synthesis finishes:

- The ranked top-3 (post cross-encoder, from Step 5)
- Each result's real `url`, `title`/headline, `domain`, `favicon`, `published_date`/`retrieved_date` (already required fields per the accuracy fix-plan doc)
- The citation-check pass/fail status per source (Step 7)

Since all of this already exists as structured data in the orchestrator by the time the answer finishes streaming, rendering it is a pure data-to-UI mapping — no generation step, no hallucination surface.

---

## 2. New/extended backend event

Add one new event type, emitted once synthesis + citation verification are both complete:

```json
{
  "type": "sources_final",
  "sources": [
    {
      "citation_n": 1,
      "url": "https://www.rbi.org.in/...",
      "title": "RBI Monetary Policy Report — July 2026",
      "domain": "rbi.org.in",
      "favicon": "https://www.google.com/s2/favicons?domain=rbi.org.in&sz=64",
      "published_date": "2026-07-10",
      "citation_check_passed": true
    },
    {
      "citation_n": 2,
      "url": "https://reuters.com/...",
      "title": "India's economy grows at fastest pace in six quarters",
      "domain": "reuters.com",
      "favicon": "https://www.google.com/s2/favicons?domain=reuters.com&sz=64",
      "published_date": "2026-07-12",
      "citation_check_passed": false
    }
  ]
}
```

This event is separate from the streamed `synthesis_token` events — it fires once, after `stage_done` for `synthesize` and after Step 7's citation checks resolve, carrying the complete, final, verified source list in one payload. The frontend doesn't need to reconstruct this from earlier per-source events; it's handed the finished list directly.

**Field notes:**
- `title` is the source page's actual headline/title (from the extraction stage's metadata — trafilatura and most RSS parsers already extract this; for API sources, use the API's own title/name field) — **not** something the LLM writes.
- `favicon` — same Google favicon-service pattern already used in the live-status UI doc, so this is consistent across both UI surfaces.
- `citation_check_passed` — reused directly from Step 7, now surfaced in the final sources list too, not just as a citation pill during streaming.

---

## 3. Layout — matching Google AI Mode / Perplexity's pattern

```
┌─────────────────────────────────────────────┐
│  [Answer text, streamed, same as today]       │
│  India's GDP grew 6.8% in Q2 2026 [1][2].     │
│  The RBI's latest report...                   │
└─────────────────────────────────────────────┘

  Sources

┌───────────────┐ ┌───────────────┐ ┌───────────────┐
│ [🏦] rbi.org.in │ │ [📰] reuters   │ │ [📊] worldbank │
│ RBI Monetary    │ │ India's econ-  │ │ GDP growth     │
│ Policy Report   │ │ omy grows at   │ │ rate — India   │
│ Jul 10, 2026  ✓ │ │ Jul 12, 2026 ⚠ │ │ Jul 2026     ✓ │
└───────────────┘ └───────────────┘ └───────────────┘
```

- **Answer stays exactly as-is** — no layout change to the streaming answer itself.
- **"Sources" section header**, visually separated (subtle divider or spacing gap), appears once `sources_final` arrives — not before, since it needs the complete verified list.
- **Card grid**, 3-4 cards per row on desktop, wrapping to fewer on narrower viewports — each card: favicon + domain (top row), headline/title (main text, 1-2 lines, truncated with ellipsis if long), published date + citation-check indicator (bottom row).
- **Citation-check indicator** on each card: small ✓ (verified) or ⚠ (flagged — claim didn't fully match source text) — consistent with the citation pill treatment from the live-status doc, giving you the same "sources disagree/unverified" visual signal here too.
- **Whole card is a clickable link** (`target="_blank"`, opens the real source URL) — this is the actual point of the section, matching how Google AI Mode's source cards work.
- **Card order matches citation number order** (`[1]`, `[2]`, `[3]`), not arbitrary — so a user reading "...grew 6.8% [1]" can immediately find card 1 below.

---

## 4. Linking answer text to source cards (optional but valuable polish)

Reuse the `CitationPill` component from the live-status UI doc: clicking a `[1]` in the answer text scrolls to/briefly highlights source card 1 below, and hovering a `[1]` could show a small tooltip preview of that card. This ties the two UI pieces together as one coherent system rather than two disconnected sections.

---

## 5. Component additions (extends the inventory from the live-status UI doc)

| Component | Responsibility |
|---|---|
| `SourcesSection` | Container, renders once `sources_final` event arrives, owns the "Sources" header |
| `SourceCard` | One card: favicon, domain, title, date, citation-check indicator, full-card link |
| (reused) `CitationPill` | Now also handles scroll-to-card-on-click, linking answer text to `SourceCard` |
| (reused) `FaviconResolver` | Same utility as live-status doc — no new logic needed, same domain→favicon mapping |

---

## 6. Micro-steps to build this

### Phase A — Backend
1. Confirm every source object flowing into synthesis already carries `url`, `title`, `domain`, `published_date`/`retrieved_date` — if any extractor/API wrapper is missing `title` specifically, add it now (this is the one field most likely to be missing, since ranking/synthesis mainly cared about content text before, not display title).
2. Add the `sources_final` event emission in the orchestrator, firing after both `stage_done: synthesize` and all `citation_check` results for that query have resolved — confirm via a raw WebSocket log that the event fires exactly once, with the complete list, in the right order (matching citation numbers).
3. Unit-test the event payload shape against 2-3 real queries, confirm `citation_check_passed` values match what Step 7 actually determined (no mismatches from a race condition between streaming completion and verification completion).

### Phase B — Frontend, static shell first
4. Build `SourceCard` as a static component, hardcode 3 example cards, get the visual layout (favicon/title/date/check-mark grid) right before any real data.
5. Build `SourcesSection` static with 3 hardcoded cards, confirm the wrapping/responsive grid behavior at different viewport widths.

### Phase C — Wire real data
6. Wire the `sources_final` WebSocket event to `SourcesSection`, confirm real cards render with correct favicons/titles/links once a query completes.
7. Confirm click-through actually opens the real source URL correctly (new tab, not navigating away from the app).
8. Wire the citation-number linking (clicking `[1]` in the answer scrolls to card 1) — confirm this works for both same-viewport and scrolled-out-of-view cases.

### Phase D — Polish
9. Add hover states, card entrance animation (consistent fade/slide-in timing with the rest of the UI per the live-status doc's motion language) once `sources_final` arrives.
10. Handle the empty/edge case: what renders if a query had zero valid sources (e.g. all sources failed) — show an explicit "no verified sources found" state rather than an empty section, consistent with the "don't answer from memory silently" instruction in the accuracy fix-plan doc.