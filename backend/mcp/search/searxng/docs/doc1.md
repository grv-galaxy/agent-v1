# Domain Source Map — API vs Non-API Tools per Category

This doc is the authoritative source list for the router (Step 2 in the main build plan). For each domain/category, it specifies: the exact tool/source, whether it has a free official API, auth requirements, and — for non-API sources — which extraction method (Step 4) is required to use it.

Legend: **API** = official structured endpoint, no scraping needed → skips extraction entirely (fast path). **No API** = requires the extraction pipeline (trafilatura → Playwright fallback).

---

## 1. General Web
| Source | API? | Auth | Notes |
|---|---|---|---|
| SearXNG (federated: DuckDuckGo, Brave, Startpage, Bing) | **API** (SearXNG's own JSON endpoint) | None | Already wired up (v1 scope). Underlying engines are scraped by SearXNG itself, not by you. |
| Google (via SearXNG engine) | **API** (via SearXNG, unofficially) | None | Optional/low-priority — circuit-breaker protected, expect frequent trips. Not core. |
| Common Crawl | **API** (bulk data access) | None | For building your own index later, not live query. |
| Wikipedia / Wikidata | **API** | None | Entity grounding, disambiguation. |

## 2. Global News
| Source | API? | Auth | Notes |
|---|---|---|---|
| GDELT Project | **API** | None | Best free global breadth, 100+ languages, 15-min refresh. |
| BBC / Al Jazeera / DW / Reuters / NHK / Le Monde RSS | **No API** (RSS feed, not scraping) | None | RSS is structured XML, not HTML scraping — treat as near-API-tier, no extraction pipeline needed, just `feedparser`. |
| SearXNG news category | **API** (via SearXNG) | None | Fallback if RSS feed list is insufficient. |

## 3. India — Government & Public Data
| Source | API? | Auth | Notes |
|---|---|---|---|
| data.gov.in (OGD Platform) | **API** | Free API key | Use `datagovindia` PyPI client for resource discovery. |
| API Setu | **API** | Varies by dataset | MeitY cross-department gateway. |
| RBI DBIE | **API** | None | Macro/finance stats. |
| PIB (Press Information Bureau) | **No API** (RSS feed) | None | Official releases, structured RSS — same near-API tier as global news RSS. |

## 4. India — Finance/Markets
| Source | API? | Auth | Notes |
|---|---|---|---|
| NSE (via `nsepython`) | **No official API** (unofficial wrapper scrapes NSE endpoints) | None | Treat as semi-structured — wrapper handles parsing, but it's not an official contract; can break on NSE-side changes. |
| BSE (via `bsedata`) | **No official API** (same caveat) | None | Same as above. |
| Moneycontrol | **No API** (RSS feed) | None | Structured RSS, near-API tier. |

## 5. India — General News
| Source | API? | Auth | Notes |
|---|---|---|---|
| The Hindu / Indian Express / LiveMint RSS | **No API** (RSS) | None | Near-API tier, no scraping pipeline needed. |
| GDELT filtered `country=IN` | **API** | None | Fallback for breadth beyond the RSS outlet list. |
| Indian news sites not offering RSS | **No API** | None | Full extraction pipeline required (trafilatura → Playwright). |

## 6. Academic / Scientific Papers
| Source | API? | Auth | Notes |
|---|---|---|---|
| arXiv | **API** | None | Preprints, physics/CS/math. |
| Semantic Scholar | **API** | Free tier key (higher limits) | Cross-discipline, citation graph. |
| CORE | **API** | Free key | Aggregates open-access repositories. |
| CrossRef | **API** | None | DOI metadata. |
| OpenAlex | **API** | None | Large open scholarly graph. |

## 7. Biomedical / Clinical
| Source | API? | Auth | Notes |
|---|---|---|---|
| PubMed (E-utilities) | **API** | Free key optional (higher rate limit) | Biomedical literature. |
| bioRxiv / medRxiv | **API** | None | Preprints. |
| ClinicalTrials.gov | **API** | None | Trial registry, official NIH source, includes non-US trials. |
| ChEMBL | **API** | None | Bioactive compounds/drug data. |

## 8. Finance (Global/US)
| Source | API? | Auth | Notes |
|---|---|---|---|
| SEC EDGAR full-text search | **API** | None | Official 10-K/10-Q/8-K filings. |
| yfinance | **No official API** (unofficial wrapper) | None | Stock/fundamentals — same caveat as NSE/BSE wrappers. |
| FRED | **API** | Free key | US economic indicators. |

## 9. Patents
| Source | API? | Auth | Notes |
|---|---|---|---|
| USPTO PatentsView | **API** | None | US patents. |
| EPO Open Patent Services | **API** | Free key | European + global. |
| WIPO Patentscope | **No API** (limited/no public API) | None | Requires extraction pipeline for non-US/non-EU patent coverage. |

## 10. Legal / Case Law
| Source | API? | Auth | Notes |
|---|---|---|---|
| CourtListener | **API** | Free key | US case law. |
| Indian Kanoon | **No API** | None | Best free Indian case-law source — full extraction pipeline required (trafilatura, respect robots.txt/rate limits). |

## 11. Economic Indicators / Macro (Global)
| Source | API? | Auth | Notes |
|---|---|---|---|
| World Bank | **API** | None | Country-level indicators, includes India. |
| IMF Data | **API** | None | Global macro/financial stats. |
| FRED | **API** | Free key | US-focused, some global series. |

## 12. Package Registries / Latest Versions
| Source | API? | Auth | Notes |
|---|---|---|---|
| PyPI | **API** | None | `pypi.org/pypi/{pkg}/json` |
| npm | **API** | None | `registry.npmjs.org/{pkg}` |
| crates.io | **API** | None | Rust |
| pkg.go.dev + Go module proxy | **API** | None | Go |
| Maven Central Search | **API** | None | Java/Kotlin |
| RubyGems | **API** | None | Ruby |
| Docker Hub / GHCR | **API** | None / token | Container images |
| GitHub Releases | **API** | Free token (higher rate limit) | Covers most OSS tools/providers directly via `/releases/latest` |

All entries in this category are structured JSON — **always skip the extraction pipeline entirely** for this category, no exceptions.

## 13. Docs Pages / Provider Version Tracking (no registry exists)
| Source | API? | Auth | Notes |
|---|---|---|---|
| Provider/SaaS docs sites (no package registry presence) | **No API** | None | Full extraction pipeline required: Playwright (render) → trafilatura (extract) → cache+diff against previous crawl to detect changes. |

This category is the fallback of last resort — only route here if Category 12's registries don't cover the provider.

---

## Summary: fast-path vs extraction-pipeline categories

**Always fast-path (structured API, skip extraction):** 1 (mostly), 2 (GDELT + RSS), 3 (mostly), 6, 7, 8 (EDGAR/FRED), 9 (USPTO/EPO), 10 (CourtListener), 11, 12 (always).

**Always extraction-pipeline (no API exists):** 5 (non-RSS Indian sites), 9 (WIPO), 10 (Indian Kanoon), 13 (all).

**Mixed / caveated (unofficial wrapper, not a true contract):** 4 (NSE/BSE via wrappers), 8 (yfinance) — these return structured data in practice but aren't official APIs, so treat them as lower-reliability than the true-API sources: wrap them with the same circuit-breaker pattern used for SearXNG engines, since they can silently break when the underlying site changes.

---

## Micro-step integration plan

Same principle as the main build plan: each step should be small enough to finish and verify in one sitting. Since you're SearXNG-only right now, treat everything below as the **future onboarding checklist** — work through it one source at a time, in the priority order suggested, not all at once.

### The repeatable pattern (applies to every source below)

For **any** new API source, the steps are always the same four:
1. Get the API key if one's required (skip if none needed) — store it in `.env.example` with a placeholder, actual key in `.env`.
2. Write one small wrapper function (e.g. in a new `sources/` module) that calls the endpoint and returns raw JSON — test it standalone with one hardcoded query first, confirm you get real data back.
3. Map the response into your shared `schemas.py` result type (same shape ranking/synthesis already expects from SearXNG) — confirm one parsed result looks correct.
4. Register the source in `router.py`'s lookup table under its category label — confirm the orchestrator can now route a real classified query to it end-to-end.

For **non-API / extraction-pipeline** sources, insert one extra step between 2 and 3:
2b. Run the URL through trafilatura standalone first, confirm it extracts clean text (not boilerplate/nav junk) before wiring it into the pipeline.

For **unofficial-wrapper / mixed** sources (NSE, BSE, yfinance), insert one extra step after 4:
4b. Wire it into the circuit breaker the same way SearXNG engines are — confirm a forced failure gets it excluded, same as Phase 4 in the main build plan.

---

### Suggested onboarding order (easiest/highest-value first)

**Tier 1 — pure structured APIs, no auth, no extraction (do these first, fastest wins)**
1. PyPI — one wrapper function, test on 2-3 known packages, register under Category 12.
2. npm — same pattern.
3. GitHub Releases — same pattern, needs a free token for higher rate limits but works without one at low volume.
4. arXiv — same pattern, register under Category 6.
5. Wikipedia/Wikidata — same pattern, register under Category 1 (entity grounding use case).
6. World Bank — same pattern, register under Category 11.

Each of these should take you well under an hour once the pattern from step 1 above is fresh — they're the same four steps repeated with a different base URL.

**Tier 2 — structured APIs requiring a free key (slightly more setup, still simple)**
7. Semantic Scholar — request key, wrapper, register under Category 6.
8. FRED — request key, wrapper, register under Category 8/11.
9. SEC EDGAR full-text search — confirm no key needed (check current docs), wrapper, register under Category 8.
10. CourtListener — request key, wrapper, register under Category 10.
11. data.gov.in — request key, use `datagovindia` client instead of hand-rolling, register under Category 3.

**Tier 3 — RSS feeds (near-API, but different parsing library)**
12. Pick 2-3 global news RSS feeds first (e.g. BBC, Reuters) — `feedparser` wrapper, confirm structured entries come back, register under Category 2.
13. Add India-specific RSS feeds (The Hindu, Indian Express, LiveMint) one at a time — same pattern, register under Category 5.
14. Add PIB RSS — same pattern, register under Category 3.
15. Add Moneycontrol RSS — register under Category 4.

**Tier 4 — unofficial wrappers (need circuit-breaker wiring)**
16. `nsepython` — wrapper, test on one known stock symbol, then do the 4b circuit-breaker step before considering it done.
17. `bsedata` — same pattern.
18. `yfinance` — same pattern, register under Category 8.

**Tier 5 — full extraction-pipeline sources (most setup effort, do last)**
19. Indian Kanoon — confirm robots.txt allows the access pattern you intend, run one URL through trafilatura standalone (2b), then wire the full pipeline path, register under Category 10.
20. WIPO Patentscope — same pattern, register under Category 9.
21. Generic provider docs pages (Category 13) — build this as a reusable fallback function (Playwright → trafilatura → cache/diff) rather than a per-source integration, since it's meant to catch anything not covered elsewhere, not a fixed source list.

---

### After each tier

Pause and run a handful of real classified queries that should route to the newly-added sources, and confirm in the dashboard (once built) that: the source shows up in the waterfall, latency looks reasonable for its category (API sources should stay fast-path, extraction sources should show the "Reading full page…" state), and results actually make it into the ranking/synthesis stages correctly. Don't move to the next tier until one tier's sources are confirmed working end-to-end — this keeps failures isolated to whatever you just added, rather than debugging five new sources at once.