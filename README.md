# Agent-v1: Advanced LLM Agent with Multi-Layer Memory

Agent-v1 is an advanced, local-first LLM agent architecture featuring a robust multi-layer memory system, a highly modular FastAPI backend, and a real-time telemetry dashboard (SYNAPSE). It is designed to solve the context window limitations of modern LLMs by implementing continuous memory compression and asynchronous long-term memory extraction.

---

## 🌟 Key Features

*   **Multi-Layer Memory System**:
    *   **Short-Term Memory (Working Memory)**: Implements a sliding window with automatic, threshold-triggered LLM compression passes.
    *   **Long-Term Memory (LTM)**: A detached FastMCP background process that extracts facts, deduplicates them, and stores them locally using `sqlite-vec` for fast, private vector search.
*   **SYNAPSE Telemetry & Observability**:
    *   A real-time, high-fidelity memory telemetry engine.
    *   Provides visual dials for context allocation, compression epoch tracking, and raw JSON payload matrices.
    *   Synchronizes seamlessly with browser `sessionStorage` to monitor the agent's internal state.
*   **Provider Agnostic Backend**:
    *   Integrates with numerous AI providers (OpenAI, Anthropic, Groq, Gemini, Local models, etc.) via a unified Factory pattern.
    *   Easily switch models and providers for different tasks (e.g., chat vs. memory compression).
*   **Local-First & Privacy Focused**:
    *   All memory storage, including vector embeddings and SQLite databases, resides entirely on the user's local machine.

---

## 🏗️ Architecture

The project is divided into three main components:

### 1. Backend (`/backend`)
A layered FastAPI application designed for maintainability and clear separation of concerns:
*   **API Layer (`app/api/routes`)**: Thin REST endpoints for chat, memory, and configuration.
*   **Services (`app/services`)**: Core business logic, including the critical `compression.py` for handling rolling summaries and grounding passes.
*   **Providers (`app/providers`)**: Adapter implementations for 15+ external LLM APIs.
*   **MCP (`mcp/`)**: FastMCP-based background processes, specifically the detached Long-Term Memory (LTM) manager.

### 2. Frontend (`/frontend` & `/electron`)
A React-based interface (built with Vite and Tailwind CSS) that provides:
*   The primary Chat UI.
*   The SYNAPSE diagnostic terminal for real-time observability of the agent's memory payload.
*   Optionally packageable as a desktop application via Electron.

### 3. Documentation (`/docs`)
Extensive architectural documentation, including:
*   `backend_folder.md`: Backend structure and design philosophy.
*   `ltm_doc.md`: The complete Long-Term Memory background process architecture.
*   `memory_layer_architecture_audit.md`: Current audit reports on memory implementation.

---

## 🚀 Getting Started

### Prerequisites
*   **Python 3.11+**
*   **Node.js 18+**
*   **uv** (Python package installer and resolver)

### Backend Setup

1.  Navigate to the backend directory or project root:
    ```bash
    cd agent-v1
    ```
2.  Install dependencies using `uv`:
    ```bash
    uv pip install -e .
    ```
3.  Set up your environment variables:
    *   Copy the example `.env` file or create one in the `backend/` directory.
    *   Add your API keys (e.g., `OPENAI_API_KEY`, `GROQ_API_KEY`).
4.  Start the FastAPI server:
    ```bash
    cd backend
    python main.py
    # or uvicorn app.main:app --reload
    ```

### Frontend Setup

1.  Navigate to the frontend directory:
    ```bash
    cd frontend
    ```
2.  Install Node dependencies:
    ```bash
    npm install
    ```
3.  Start the Vite development server:
    ```bash
    npm run dev
    ```

---

## 🧠 How the Memory System Works

1.  **Chat Stream**: As the user chats, messages accumulate in the `frontend`.
2.  **Trigger Threshold**: When the raw message count hits a configured threshold, the frontend triggers a compression pass via the `/api/compress` endpoint.
3.  **Compression (Epoch N)**: The backend `compression.py` service uses an LLM to generate a rolling summary and extract structured facts.
4.  **Logging**: The raw output is appended to a local JSONL file (`facts.jsonl`).
5.  **LTM Processing (Background)**: The FastMCP memory manager asynchronously reads the JSONL, dedupes facts, generates embeddings (via local ONNX models or API), and updates the local SQLite vector database (`sqlite-vec`).

---

## 📝 License

See the `LICENSE` file for full terms.
