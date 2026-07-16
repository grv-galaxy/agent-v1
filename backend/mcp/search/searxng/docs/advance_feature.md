# Upgrading the Search Agent: Strategic Plan

Since we are keeping the Search Agent as a dedicated microservice, we have the freedom to push its capabilities to the absolute limit without worrying about bloating the main backend. 

Here are the most impactful architectural, tooling, and intelligence upgrades we can implement to make the agent feel like a true "Pro" research assistant (similar to Perplexity Pro or OpenAI Deep Research).

## 1. Deep Research Mode (Multi-Hop Reasoning)
**Current State:** The agent does a single-pass search (classify -> route -> fetch -> rank -> synthesize). If a query is highly complex, it might fail to find everything in one go.
**The Upgrade:** Implement an iterative "Deep Research" loop.
- **Sub-Query Generation:** The LLM breaks a complex question down into 3-4 distinct sub-queries.
- **Parallel Fetching:** It searches all sub-queries simultaneously across different tools.
- **Recursive Extraction:** If the first batch of results is insufficient, the agent automatically triggers a second search based on what it learned.

## 2. Advanced Document & Web Scraping
**Current State:** We use `trafilatura` for fallback extraction, which fails on modern JavaScript-heavy websites (like Twitter/X, SPAs, or dynamic dashboards).
**The Upgrade:**
- **Headless Browser Fallback:** Integrate `Playwright` so the agent can actually "render" and read complex JavaScript websites when standard scraping fails.
- **On-the-fly RAG for Massive PDFs:** Right now, if a PDF is 100 pages long, the LLM context window might choke. We can implement local chunking and vector-search (using FAISS) so the agent only reads the 5 pages of the PDF that actually matter to the query.

## 3. Conversational Memory (Follow-Up Queries)
**Current State:** The search agent treats every query as a completely new session. You cannot say "elaborate on that second point."
**The Upgrade:** 
- Allow the WebSocket to accept `chat_history`. 
- The Classifier LLM will first rewrite the user's follow-up question (e.g., "tell me more about it" -> "tell me more about the quantum computing breakthrough").

## 4. Expanding Specialized Tools
**Current State:** We have great tools for finance, code, law, and academia.
**The Upgrade:** Add highly requested domains:
- **YouTube Transcripts:** A tool that takes a YouTube URL from the search results and instantly downloads the transcript to read the video's content.
- **Wolfram Alpha / Math:** For solving complex mathematical, physics, or unit conversion queries accurately without LLM hallucinations.
- **Weather & Local Maps:** Connecting to open weather APIs or local routing/places APIs for hyper-local queries.

## 5. UI/UX: Rich Media Synthesis
**Current State:** The agent streams plain text and markdown.
**The Upgrade:**
- **Image Support:** Configure SearXNG to fetch image thumbnails and have the Synthesizer embed relevant images directly into the Markdown answer.
- **Data Visualization:** Prompt the LLM to generate `Mermaid.js` charts or structured Tables when comparing items (e.g., "Compare iPhone 15 vs S24" returns a clean spec table).

## User Review Required
> [!IMPORTANT]
> Which of these upgrades excites you the most? 
> 
> If you want the agent to be **smarter and more thorough**, I highly recommend starting with **1. Deep Research Mode** or **3. Conversational Memory**.
> 
> If you want it to have **more capabilities**, we can start adding the new tools in **4. Expanding Specialized Tools** (like YouTube transcripts).
> 
> Let me know your priority and we will begin!
