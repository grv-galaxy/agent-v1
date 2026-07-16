# Deep Research Mode — Build Plan (Multi-Hop Reasoning) — v2

Extends the single-pass pipeline (classify → route → fetch → rank → synthesize) with an optional multi-hop mode for complex queries. Deep Research mode is triggered either by explicit user intent or intelligent upfront auto-detection by the Planner — never by post-hoc quality signals (citation-check pass rate, cross-encoder scores), since those signals are already known to have false negatives (e.g. correct-but-paraphrased answers failing lexical citation checks) and would produce an unreliable trigger.

Build order matters here more than in earlier docs. Follow the phases in order — do not build Phase 4 before Phase 3's per-sub-query ranking is confirmed working, and do not add recursion/multi-round logic unless a later, separate doc explicitly reintroduces it — this version is intentionally single-round.

---

## Design decisions locked in

- **Trigger: Pro Toggle + Intelligent Planner (upfront, not post-hoc).** Determined by two conditions:
  1. **User Override:** The user clicks a "Deep Research" toggle in the frontend, sending `deep_research: true` in the initial payload. This forces the mode unconditionally.
  2. **Planner Fallback (auto-detection):** If the user leaves it in auto, the initial query is passed to the Classifier/Planner. The Planner evaluates query complexity and outputs `requires_deep_research: true` if it determines the query needs multi-hop searching (e.g., comparative analysis, long-term trends, multi-entity questions).
- **UI Transparency:** The user must be notified immediately when the Planner auto-upgrades a query to Deep Research, via a dedicated WebSocket event — never a silent upgrade.
- **Sub-query decomposition:** Once triggered, the original query is broken into 3-4 distinct, non-overlapping sub-queries executed in parallel.
- **Ranking happens per sub-query, not on a flattened global pool.** Each sub-query's results are ranked against that sub-query's own text, producing a guaranteed top-2/top-3 per sub-query, before combining into the final set passed to synthesis. This guarantees every sub-question is represented in the final context — a global flatten-then-rank step risks one "easy" sub-query's strong results crowding out a "hard" sub-query's necessary-but-fewer results, silently producing an incomplete answer that still looks well-cited.
- **Global citation numbering across all sub-queries** — `[1]` through `[n]` must stay unique across the whole multi-hop session.
- **No recursion in this version.** Single round only. Recursive/iterative follow-up rounds are deliberately out of scope here and would be a separate, later addition — do not build a second round into this pass.

---

## Phase 1 — The Intelligent Planner & UI Notification

**Goal:** Determine if a query requires Deep Research upfront, and notify the frontend — no retrieval-quality signals involved in this decision at all.

1. **Modify the Classifier Schema:** Update `src/search_agent/schemas.py` to add two fields to `ClassifierOutput`:
   - `requires_deep_research: bool`
   - `deep_research_reasoning: str`
2. **Update the Prompt:** Modify `prompts/classify.txt` to instruct the LLM on when to flip the boolean to true (comparative questions, multi-entity questions, questions requiring synthesis across distinct fact types, etc.).
3. **Orchestrator Logic:** In `orchestrator.py`, parse the incoming WebSocket payload for `deep_research`.
   - If `deep_research: true` (user override): skip only the `requires_deep_research` judgment — the query still goes through the normal classifier call for category/fact_type detection, since that's needed by each sub-query's own routing in Phase 3 regardless of how deep research was triggered. Only the auto-detection judgment is skipped, not classification as a whole.
   - If `deep_research` is false or missing: run the classifier as normal and read `requires_deep_research` from its output.
4. **WebSocket Notification:** If Deep Research is activated (either path), immediately emit:
   `{"type": "deep_research_activated", "trigger": "user_override" | "planner", "reason": "<reasoning>"}`
   so the UI can show a visual indicator and, for the planner-triggered case, explain why.

**Checkpoint before Phase 2:** Send varied queries (simple vs complex) and confirm the Classifier correctly auto-flags complex ones without over-triggering on simple ones. Confirm the WebSocket event fires correctly for both trigger paths, and confirm the manual override correctly skips only the auto-detection judgment, not full classification.

---

## Phase 2 — Sub-query generation

**Goal:** Given a query flagged for deep research, generate 3-4 sub-queries — verified in isolation before any fetching.

5. Write a dedicated planning prompt `prompts/plan.txt`. Force structured JSON output: `{"sub_queries": ["...", "...", "..."], "reasoning": "..."}`. Explicitly instruct: sub-queries must be non-overlapping and individually answerable, not rephrasings of the same question.
6. Add this as a new `step: "plan"` row type in your `llm_calls` telemetry table — same token/cost/latency tracking already in place for classify/synthesize.
7. Test standalone: feed 5-10 real complex queries into this prompt only (no retrieval yet), log the generated sub-queries, and manually judge quality — are they genuinely distinct and useful, or padding to hit 3-4 items?

**Checkpoint before Phase 3:** Confirm the generated sub-queries are clearly better than just re-running the original query 4 times, across all 5-10 test cases, not just a couple.

---

## Phase 3 — Parallel fetch + per-sub-query ranking

**Goal:** Execute classify→route→fetch→rank independently for each sub-query, concurrently — with ranking scoped to each sub-query's own text, guaranteeing every sub-question is represented before combining.

8. Extend the event schema and `tool_contribution` telemetry table with a `sub_query_id` column, so every source/result is traceable to which sub-query it came from.
9. Implement the fan-out: `asyncio.gather` across N independent sub-pipeline runs, each sub-query going through the existing classify→route→fetch code as its own call — reuse existing single-pass logic rather than writing new retrieval code.
10. **Rank each sub-query's results against that sub-query's own text** (not the original combined question) — run your existing bi-encoder + cross-encoder ranking per sub-query, producing a guaranteed top-2 or top-3 for each sub-query individually.
11. **Combine** each sub-query's guaranteed top-N into one final set (e.g. 3 sub-queries × top-3 = up to 9 sources) — this is a concatenation of already-ranked, already-guaranteed-relevant results, not a second global ranking pass. No sub-query's results should be able to be entirely crowded out by another's.

**Checkpoint before Phase 4:** Manually inspect a few runs — confirm every sub-query contributed at least one result to the final combined set (i.e. no sub-query got fully crowded out), and confirm the combined set collectively covers more ground than a single-pass search would have.

---

## Phase 4 — Multi-source synthesis with global citation numbering

**Goal:** Combine the per-sub-query-ranked, guaranteed-coverage results into one synthesis call that reasons across sub-queries, with citation numbers staying globally unique.

12. Write the multi-hop synthesis prompt (`prompts/synthesize_multihop.txt`) as its own file — the input shape (up to ~9 sources spanning multiple sub-topics) and reasoning demands are different enough from single-pass synthesis to warrant a dedicated prompt rather than reusing/overloading the existing one.
13. **Context size:** pass the combined per-sub-query top-N set (from Phase 3, step 11) to the LLM — expect roughly 8-10 sources for a 3-4 sub-query breakdown at top-2/top-3 each, not a fixed arbitrary "top 8-10 of a global pool."
14. Implement global citation numbering: assign citation numbers sequentially across the full combined set (`[1]`-`[9]`, etc.), regardless of which sub-query each source came from — this keeps the existing `SourcesSection`/`CitationPill` UI components working without modification.
15. Reuse the cross-source agreement check and citation verification (Step 7) unchanged — both already operate per-citation-number regardless of how many total citations exist or which sub-query they originated from.

**Checkpoint after Phase 4:** Run full queries end-to-end. Compare the multi-hop answer against what single-pass originally produced for the same query on your known-hard cases. Confirm citations map correctly back to the right sub-query's source in the combined list, and confirm no sub-question from the original decomposition is left unaddressed in the final answer.

---

## Summary — sequencing table

| Phase | What it adds | Depends on |
|---|---|---|
| 1 | Upfront Planner, manual override, UI notification | Existing Classifier infrastructure |
| 2 | Sub-query generation (isolated, no fetch) | Phase 1's trigger logic |
| 3 | Parallel fetch + **per-sub-query ranking** (guaranteed coverage) | Phase 2's sub-queries; reuses existing fetch/rank code, called per sub-query |
| 4 | Multi-source synthesis, global citations, combined per-sub-query top-N | Phase 3's per-sub-query ranked results |

**Explicitly out of scope for this version:** recursive/iterative second-round searching, post-hoc escalation triggers based on citation-check or ranking-score telemetry. Both were considered and deliberately excluded — the former as a later, separate addition once this single-round version is proven; the latter because those signals are known to have false negatives and would make the trigger unreliable.