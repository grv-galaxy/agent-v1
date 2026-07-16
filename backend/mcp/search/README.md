# Search MCP Module

This directory contains the Search Model Context Protocol (MCP) implementations, primarily focusing on two main components: `searxng` (a robust search AI agent) and `wikipedia` (a targeted Wikipedia extraction tool).

## Directory Structure

```text
search/
├── searxng/          # Full-featured search AI agent pipeline (FastMCP + FastAPI)
└── wikipedia/        # Dedicated tool for extracting Wikipedia summaries and infoboxes
```

## SearXNG (`backend/mcp/search/searxng/`)

The `searxng` directory contains a highly complex search AI agent architecture that combines multiple search APIs, a local SearXNG instance (run via Docker), and advanced query routing, classification, bi-encoder/cross-encoder ranking, and LLM synthesis.

### Key Features:
- **FastMCP & FastAPI Orchestrator:** Uses a two-process split. A FastMCP server wraps the SearXNG search functionality, while a FastAPI orchestrator handles the core logic (classification, routing, ranking, synthesis, UI over WebSockets).
- **LLM Classification & Routing:** Classifies incoming queries using an LLM to decide the most relevant sources (e.g., SearXNG, Wikipedia, arXiv, GitHub, yfinance, etc.).
- **Ranker (Bi-Encoder + Cross-Encoder):** Uses ONNX-based sentence transformers (`all-MiniLM-L6-v2`) and cross-encoders to re-rank results from multiple sources.
- **Streaming LLM Synthesis:** Synthesizes the final answer with streaming to the UI.
- **Telemetry Funnel:** Utilizes SQLite and Redis to track query latency, routing decisions, tool contributions, and API interactions.
- **Diagnostics Mode:** Allows specific tool execution using `@tool_name` tags (e.g., `@wikipedia India`).
- **Web UI:** A real-time dashboard served via WebSockets.

### Main Files:
- `pyproject.toml` & `uv.lock`: Dependency management (uses Python >= 3.11 and libraries like `fastapi`, `fastmcp`, `onnxruntime`, `openai`).
- `docker-compose.yml`: For running the underlying local SearXNG search engine and Redis cache.
- `src/search_agent/orchestrator.py`: The main FastAPI orchestrator routing the pipeline.
- `src/search_agent/mcp_server.py`: The FastMCP server wrapper.
- `doc.md` / `tools_check_list.md`: Detailed documentation and build plans for the SearXNG pipeline.
- `src/search_agent/sources/`: Multiple source integrators including PyPI, npm, GitHub, Wikipedia, etc.

### Running SearXNG:
```bash
cd backend/mcp/search/searxng
uv run uvicorn src.search_agent.orchestrator:app --reload
```
Requires the local SearXNG docker container to be running (`docker-compose up`).

## Wikipedia (`backend/mcp/search/wikipedia/`)

The `wikipedia` directory contains a focused search tool specifically designed to extract high-quality, structured information from Wikipedia. It is integrated into the `searxng` orchestrator but can also be used as a standalone Python utility.

### Key Features:
- **Summary Extraction:** Retrieves the top results and pulls the cleaned summary of the Wikipedia page.
- **Infobox Extraction:** Parses the HTML of the Wikipedia page using `BeautifulSoup` to accurately extract key facts from the infobox (e.g., "Incumbent", "Formation", "Capital", etc.), as well as the main image URL.
- **Sentence Splitting:** Cleans up references (like `[1]`, `[citation needed]`) and breaks summaries into readable points.

### Main Files:
- `search_tool.py`: Contains the `wikipedia_search` function and `WikipediaSearchTool` class. Uses `requests` and `bs4` to scrape and parse Wikipedia pages and their Rest API.
- `wiki_notebook.ipynb`: A Jupyter Notebook demonstrating how to use the Wikipedia extraction tool and showing example outputs.

### Usage in SearXNG:
The Wikipedia tool is integrated via `searxng/src/search_agent/sources/wikipedia.py`, which asynchronously wraps the synchronous `wikipedia_search` function and maps it into the standard data format expected by the `searxng` ranker and synthesizer.
