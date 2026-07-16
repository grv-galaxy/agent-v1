# Diagnostic Mode (Tool Override Implementation)

Understood. Instead of changing the architecture right now, we will build a **Diagnostic Mode** so you can manually test and inspect each tool's lifecycle (fetching ➔ extraction ➔ ranking ➔ synthesis) one by one.

## 1. List of Available Tools
Here are all the available tools in the current pipeline that we will be testing:
- **Search & Web**: `searxng`, `wikipedia`, `gdelt`, `fallback_docs`
- **Finance & Markets**: `yfinance`, `nse`, `bse`, `economic_databases`, `worldbank`
- **Code & Academic**: `arxiv`, `github`, `npm`, `pypi`
- **Legal & Public**: `indian_kanoon`, `wipo`
- **RSS Feeds**: `rss_global_news`, `rss_india_news`, `rss_india_public`, `rss_india_finance`

## 2. Proposed Changes

### Backend (`orchestrator.py`)
We will add a bypass mechanism in the main `process_query` pipeline:
- Before running the Classifier, the orchestrator will check if the query starts with an `@` mention (e.g., `@yfinance TSLA` or `@wikipedia India`).
- If an `@tool` tag is detected:
  1. The **Classifier will be skipped**.
  2. The router's target source list will be forced to ONLY include the specified tool (e.g., `sources = ["yfinance"]`).
  3. The `@tool` tag will be stripped from the query so the tool just receives the raw text (e.g., `TSLA`).

This guarantees that only the tool you want to diagnose is executed, and you can watch exactly how it behaves in the telemetry funnel.

### Frontend (`index.html` & `app.js`)
- **Diagnostic Cheat Sheet**: I will add a small "Available Tools" helper below the search bar in the UI. You can click on any tool name, and it will automatically inject `@tool_name ` into your search box.
- **Funnel Visibility**: Your recently built Telemetry Funnel is already perfectly equipped for this. When you run `@yfinance AAPL`, the funnel will immediately show you if it returned results, if those results survived the Bi-encoder, and if it was cited in the final synthesis.

## 3. Workflow for Diagnosis
Once this is implemented, you can diagnose failures like this:
1. Type `@yfinance TSLA` ➔ Watch if it survives the Bi-encoder.
2. Type `@gdelt US elections` ➔ Check the fetched snippets in the terminal/funnel.
3. If a tool consistently fails at the Bi-encoder, we will know its prompt or data parsing needs to be fixed.
