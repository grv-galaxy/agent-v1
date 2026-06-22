# SYNAPSE
### Synthesis Network for Advanced Problem Solving & Execution

> A high-fidelity, real-time AI memory telemetry and observability engine built for engineers who refuse to let their LLM context window be a black box.

---

## What is SYNAPSE?

Modern LLM-powered agents face a fundamental engineering problem — the context window is finite. As conversations grow longer, token consumption compounds, costs spike, and eventually the model silently loses the beginning of the conversation entirely. To combat this, production systems implement rolling compression, sliding message buffers, and historical summary chains. But these systems are almost entirely invisible at runtime. You trigger a compression, something happens inside the model, and you get a summary back. What was evicted? When exactly did it fire? What did the rolling summary look like before and after? Without instrumentation, you are flying blind.

SYNAPSE is the instrumentation layer.

It connects directly to your agent's live payload stream via `sessionStorage`, captures every atomic state frame as the conversation evolves, and renders that raw engineering data into a structured, real-time diagnostic terminal. It is not a chat UI. It is not a user-facing product. It is the cockpit view — built specifically for the engineer who is building the agent, so they can see exactly what is happening inside the memory system at every single moment.

SYNAPSE was designed alongside a production AI agent architecture (`agent-v1`) that implements a multi-layer memory system including:

- A sliding raw message buffer with configurable threshold triggering
- An LLM-powered compression pass that produces structured `rolling_summary` chains
- A grounding pass that fires every N epochs to reconcile semantic drift across summary versions
- A background fact extraction pipeline that persists empirical memory to disk
- A RAG injection layer that retrieves relevant facts before every LLM call

SYNAPSE gives you real-time visibility into every layer of that system as it runs.

---

## The Problem It Solves

Without a tool like SYNAPSE, debugging a memory-managed LLM agent looks like this:

- You add a `print()` statement to see when compression fires
- You paste the rolling summary into a text editor and read it manually
- You guess whether the model is actually receiving the summary in its context
- You have no idea whether the grounding pass changed anything or not
- You cannot see which messages were in the compression chunk vs the live buffer
- You find out something went wrong only when the model starts giving wrong answers

SYNAPSE replaces all of that guesswork with a live, structured, searchable telemetry console that updates in real time as your agent processes messages.

---

## Architecture

```
┌──────────────────────────────────────────┐
│            LLM Chat Interface            │
│   (Streams tokens, triggers compression) │
└───────────────────┬──────────────────────┘
                    │
       Writes atomic state payload frames
                    ▼
┌──────────────────────────────────────────┐
│             sessionStorage               │
│      ['agent.live_payload_stream']       │
└───────────────────┬──────────────────────┘
                    │
    Hybrid listener — custom event dispatch
    + 1000ms polling fallback (same-tab fix)
                    ▼
┌──────────────────────────────────────────────────────────────────────┐
│                        SYNAPSE TERMINAL                              │
│                                                                      │
│  ┌─────────────────┐  ┌──────────────────┐  ┌────────────────────┐  │
│  │  Context Dial   │  │ Transcript Viewer │  │  Compression Log   │  │
│  │  (% allocated)  │  │ (live messages)   │  │  (epoch ledger)    │  │
│  └─────────────────┘  └──────────────────┘  └────────────────────┘  │
│                                                                      │
│  ┌─────────────────┐  ┌──────────────────┐  ┌────────────────────┐  │
│  │  Rolling Summary│  │  Raw JSON Matrix  │  │  Session Identity  │  │
│  │  Tree Viewer    │  │  (searchable)     │  │  & Provider Info   │  │
│  └─────────────────┘  └──────────────────┘  └────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
```

### The Same-Tab Storage Sync Problem

The standard JavaScript `storage` event only fires across different browser tabs. It does not fire when the same tab updates `sessionStorage`. This is a well-known browser limitation that breaks most naive implementations of local state observation.

SYNAPSE solves this with a hybrid sync architecture — a custom `storage_update` event dispatch hook that fires immediately on every write, combined with a 1000ms polling fallback engine that catches any mutations the event system misses. The result is true same-tab real-time sync with no race conditions and no missed frames.

---

## Key Features

**Real-Time Context Allocation Dial** — A circular gauge showing exactly what percentage of the context window is currently consumed, updated on every message. You can see the number climbing toward the compression threshold in real time.

**Compression Epoch Tracking** — Every time the compression system fires, SYNAPSE logs the epoch number, the event type (compression pass or grounding pass), and the resulting rolling summary. You can see the entire compression history for a session as a sequential ledger.

**Live Transcript Viewer** — A segregated view of user frames and assistant frames with color-coded indicator ribbons (indigo for user, cyan for assistant). Shows the live buffer messages separately from the compression chunk so you can see exactly what is in the active window vs what has been evicted.

**Rolling Summary Tree** — Renders the structured rolling summary output at each epoch so you can visually inspect what the compression model decided to preserve, what it added, and what entity categories it tracked.

**Compression Alert Flags** — When `should_compress` flips to `true` in the payload, the dashboard immediately surfaces a visual alert so you can see exactly which message triggered the threshold.

**Raw JSON Matrix** — A searchable, copy-to-clipboard explorer of the full raw payload at any point in the session. Useful for verifying field values, debugging payload structure, and capturing exact state snapshots for bug reports.

**Mission Control Strip** — Pause and resume background telemetry tracking at any time. Force-refresh the view manually. All control state is persisted to `localStorage` so it survives page reloads.

**Zero Backend Dependency** — SYNAPSE reads entirely from `sessionStorage`. It requires no server, no websocket, no additional API endpoint. If your agent writes its payload state to `sessionStorage`, SYNAPSE works.

---

## Expected Payload Schema

SYNAPSE reads from `sessionStorage['agent.live_payload_stream']` and maps the following fields:

```json
{
  "provider": "groq",
  "api_key": "",
  "model_name": "openai/gpt-oss-120b",
  "compression_chunk": [],
  "compression_epoch": 0,
  "memory_grounding_interval": 5,
  "memory_model": "llama-3.1-8b-instant",
  "memory_preset": "balanced",
  "memory_provider": "groq",
  "memory_raw_buffer": 10,
  "memory_summary_cap_tokens": 800,
  "memory_trigger_threshold": 30,
  "messages": [{ "role": "user", "content": "hey" }],
  "rolling_summary": "",
  "session_id": "session_1781537243442_jn9kava9f",
  "should_compress": false,
  "summary_history": [],
  "use_memory": true
}
```

All fields are optional with safe fallbacks — SYNAPSE degrades gracefully if fields are missing or malformed.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | React 18+ (Vite) |
| Styling | Tailwind CSS — Obsidian/Slate dark theme |
| Animations | Framer Motion |
| Icons | Lucide React |
| Storage | sessionStorage (read) + localStorage (control state) |
| Sync Engine | Custom event dispatch + polling hybrid |

---

## Getting Started

**1. Clone the repository**

```bash
git clone https://github.com/YOUR_USERNAME/synapse.git
cd synapse
```

**2. Install dependencies**

```bash
npm install
```

Ensure `framer-motion` and `lucide-react` are present in your `package.json`.

**3. Start the dev server**

```bash
npm run dev
```

**4. Connect your agent**

In your LLM agent frontend, write the current payload state to sessionStorage on every message cycle:

```javascript
sessionStorage.setItem('agent.live_payload_stream', JSON.stringify(currentPayload));
window.dispatchEvent(new Event('storage_update'));
```

SYNAPSE picks it up instantly.

**5. Test without a backend**

Open browser DevTools (F12) on your running SYNAPSE instance and paste this into the console to simulate a live payload:

```javascript
sessionStorage.setItem('agent.live_payload_stream', JSON.stringify({
  provider: "groq",
  model_name: "openai/gpt-oss-120b",
  memory_model: "llama-3.1-8b-instant",
  memory_trigger_threshold: 30,
  messages: [
    { role: "user", content: "Hello agent, let's process this token window map." },
    { role: "assistant", content: "Understood. Monitoring sliding constraints now." }
  ],
  use_memory: true,
  session_id: "session_debug_test_node_99",
  compression_epoch: 0,
  should_compress: false,
  rolling_summary: "",
  summary_history: []
}));

window.dispatchEvent(new Event('storage_update'));
```

---

## Who This Is For

SYNAPSE is built for engineers building production LLM agents — specifically anyone implementing context window management, rolling compression, or multi-layer memory systems. If you are building an agent that needs to handle conversations longer than its context window, and you want to actually see what your memory system is doing at runtime, SYNAPSE is the observability layer you were missing.

It is not a product demo. It is a professional engineering tool.

---

## Roadmap

- Persistent session replay — load and replay any past session from the fact ledger
- Multi-session comparison view — compare compression behavior across different sessions side by side
- Fact extraction telemetry — visualize the empirical memory layer as facts are extracted and confidence scores update
- RAG injection trace — show exactly which facts were retrieved and injected before each LLM call
- Export to JSONL — dump any session's full telemetry to a file for offline analysis

---

## License

MIT License. See `LICENSE` for full terms.

---

*SYNAPSE — because if you can't observe it, you can't engineer it.*
