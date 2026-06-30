# Long-Term Memory (LTM) System — Full Architecture & Production Design Doc

**Status:** Final architecture plan, merged with performance/scalability hardening

**Scope:** Local, single-user, FastMCP background process that converts raw compression-pass output into a deduplicated, self-decaying, self-improving long-term memory store.

**Supersedes:** `memory_manager_demo.ipynb` (logic prototype, no batching/indexing/process model)

---

## 1. Goal & Positioning

Convert raw compression-pass output (`facts.jsonl`) into a clean, deduplicated, structured long-term memory store that lives entirely on the user's local machine. No server, no multi-tenancy. Only the LLM extraction call (and optionally embeddings) goes out over the network via API key — storage, dedup, decay, and retrieval all run locally.

This is a **long-term** memory layer. It does **not** feed the active chat context window directly and has **no hard latency requirement** on the chat path — short-term memory (the rolling summary) handles the live session. This system exists purely to make the agent smarter over time, asynchronously, in the background.

Because there's no latency pressure on the chat path, the performance work in this doc is not about "making memory writes feel instant" — it's about making sure a background job that runs once per threshold/close/startup trigger stays fast and lightweight even as a user accumulates years of facts, so it never becomes a noticeable drag on app startup or a meaningful resource hog while running.

---

## 2. Data Flow Overview

```
[Chat happens] → [Compression LLM call] → appends triple-shaped
facts to facts.jsonl (raw, unprocessed, append-only log)

                        │
                        ▼

[FastMCP Memory Manager — separate, detached background process]
Triggered by: threshold / app-close / app-startup
Reads unprocessed JSONL range → runs full batch pipeline → writes to:
   - SQLite + sqlite-vec   (structured long-term store, source of truth)
   - Markdown files        (human/model-readable projection)

                        │
                        ▼

[Main app, anytime] → reads SQLite+sqlite-vec or markdown files
for retrieval → injects into agent context as needed
(Main process NEVER writes to the structured store directly)
```

Single-writer / multi-reader is the core invariant: only the background memory manager ever writes to SQLite or markdown. The main app process only reads. This eliminates an entire class of write-contention bugs and lets the structured store use SQLite's WAL mode for fully non-blocking concurrent reads during a background write.

---

## 3. Extraction Format (Already Implemented in Prompts)

`FIRST_EPOCH_PROMPT` and `ANCHORED_COMPRESSION_PROMPT` output triples directly:

```json
{
  "subject": "...",      // canonical, always "User" for the human
                          // unless multiple named people are
                          // explicitly being discussed
  "relation": "...",     // open vocabulary, lowercase snake_case
  "object": "...",       // must carry real meaning (never a bare
                          // pronoun like "himself")
  "importance": 1-100,   // prior set by LLM: identity/stable facts
                          // = 80-100, one-off events/trivia = 1-20
  "confidence": 0-1      // how explicitly the fact was stated
}
```

Rules already baked into the extraction prompts:
- Always use `"User"` as the canonical subject for the human.
- Skip triples where the object is a pronoun or otherwise carries no meaning.
- `factual_traits` and `episodic_events` use triple shape; `semantic_concepts` stay as plain strings; `entities` stay as categorized lists (existing schema).
- `GROUNDING_PROMPT` is currently summary-only — facts reconciliation is deferred entirely to the background memory manager, not the grounding LLM call.

No NER/dependency-parsing pipeline is used as the primary extractor — LLM extraction is more accurate for this use case. A cheap spaCy NER pass is an optional future validation guard rail, not required for v1.

---

## 4. Trigger Mechanism (No Latency Pressure, Self-Healing)

Three independent triggers, each firing the **same** background process:

1. **Threshold trigger** — every N new lines appended to `facts.jsonl` (e.g. N=5–10) during an active session fires the background process. Purpose: batch work during long sessions, keep the store reasonably fresh without per-fact overhead.
2. **App-close trigger** — on app close, fire the background process best-effort (not guaranteed if force-killed/crashed). The app does **not** wait for it — fire-and-forget, app closes instantly.
3. **App-startup trigger (the actual guarantee)** — on every app launch, check the cursor file against `facts.jsonl` length. If unprocessed lines exist (because the threshold wasn't hit and/or the close trigger never fired due to a crash, force-kill, or power loss), fire the background process immediately, non-blocking, before or alongside the UI becoming interactive.

Why three: threshold = efficiency, close = best-effort speed, startup = guarantee. Nothing is ever permanently lost because `facts.jsonl` is append-only and durable regardless of how the app died — the startup trigger always reconciles.

---

## 5. Process Isolation (FastMCP, Detached)

- The background memory manager runs as a separate FastMCP-callable process, **not** inside the same process as the chat/compression LLM call.
- The process is **detached** from the main app's process tree (`subprocess.Popen(..., start_new_session=True)` on Linux/Mac, `DETACHED_PROCESS` flag on Windows) so it survives after the main app process exits.
- The main process never blocks on it — fire the trigger, move on.
- The FastMCP wrapper also makes the memory manager callable on-demand as a tool if needed (e.g. "force sync memory now" from a debug menu), not just silently triggered.
- The process is intentionally short-lived: it loads what it needs, runs the batch pipeline, writes, and exits. Nothing about this design keeps an embedding model or process resident in memory between runs (see §9 for the resource footprint this implies).

---

## 6. Lock + Cursor (Concurrency & Idempotency Safety)

**Lock file:** `backend/data/locks/memory_manager.lock`
- Acquired at the start of every run.
- If already held, a new trigger no-ops (another run is already in progress).
- Released on exit, success or final failure.

**Cursor file:** `backend/data/cursors/facts_cursor.json`
- Tracks the last successfully processed line/byte-offset in `facts.jsonl`.
- The cursor only advances if the entire run succeeds cleanly. No partial/per-fact cursor advancement — this keeps the logic simple and safe, because retrying the same range on failure is itself safe: dedup logic naturally absorbs any partially-completed work from a failed prior attempt (reprocessing an already structurally/semantically-matched fact just increments frequency, it doesn't duplicate it).

---

## 7. Retry + Failure Logging

```
attempt = 1
while attempt <= 2:
  try:
    acquire lock
    run full batch pipeline (§8) on unprocessed JSONL range
    on success:
      advance cursor
      release lock
      exit(0)
  except Exception as e:
    if attempt == 2:
      write failure log to:
        backend/data/logs/ltm/<YYYY-MM-DD>_<HH-MM-SS>.log
      contents:
        - timestamp
        - JSONL range attempted (line numbers / byte offsets)
        - exception type + message
        - attempt count exhausted (2/2)
      release lock (cursor NOT advanced)
      exit(1)
    else:
      brief backoff (2-5 sec) before retry
      attempt += 1
```

Failure after 2 attempts is not permanent. The cursor stays put, so the next natural trigger (threshold, close, or startup) retries the same unprocessed range automatically — self-healing, no manual intervention or separate retry-scheduler needed.

---

## 8. Pipeline Steps — Batch-First Design

The original step-by-step plan describes the logic per new triple. In production this logic runs as **one batched pass over the whole unprocessed range**, not as N sequential per-triple operations — this is the single biggest lever for keeping the background job fast and light as the store grows into the thousands of facts.

```
1. Acquire lock (abort if already held)
2. Read cursor → determine new JSONL lines since last successful run
3. Read those new triple-shaped facts from facts.jsonl
4. Parse + canonicalize subjects for the WHOLE batch at once
5. Run structural dedup for the whole batch as ONE SQL query
   (WHERE id IN (...)), not N separate lookups
6. Batch-embed only the genuinely new (non-structurally-matched)
   triples in a SINGLE encode() call, not one call per triple
7. Run semantic + cross-namespace dedup as a vectorized similarity
   pass against an in-memory embedding cache (one matrix multiply,
   not a per-triple Python loop)
8. Resolve contradictions for the batch
9. Apply relation normalization (alias table lookup)
10. Single bulk write: one SQLite transaction, executemany for
    inserts/updates, one commit — not commit-per-row
11. Run the lifecycle sweep (state machine, every job)
12. Update markdown projections incrementally — only the files/
    sections actually touched by this batch
13. Advance cursor, release lock, exit(0)
```

### 8a. Structural check (cheap, exact)

`hash(subject, relation, object)` match in store?
- **Yes:** increment frequency, update `last_seen`, append the raw-text variant, no new row.
- **No:** continue to semantic check.

In production, all candidate IDs for the batch are checked in one query (`SELECT id, confidence, raw_text_variants FROM triples WHERE id IN (...)`) instead of one query per triple.

### 8b. Semantic check (vector similarity, same subject namespace)

Embed the triple as `"<subject> <relation> <object>"`. If cosine similarity vs. an existing embedding in the same subject namespace exceeds `0.85`:
- Treat as the same fact: append raw-text variant, increment frequency, run confidence reinforcement (§8e).
- If the new phrasing is more complete, promote it to canonical.
- If the relation differs but subject+object match, normalize the relation via the alias table (§8d).

If no match, fall through to a stricter cross-namespace safety-net check (catches aliasing cases canonicalization missed), then insert as a new row.

**Performance:** this is where the prototype broke down — it ran this check as a Python `for` loop over every stored row, per triple. Production instead:
- Loads all active embeddings **once** at process start into a single in-memory numpy matrix, pre-normalized, with a parallel `id` index array.
- Runs the similarity search as **one matrix-vector dot product per query triple** (`matrix_normed @ query_vec`) — a single BLAS call instead of a Python loop, ~50–100x faster at scale.
- Appends newly inserted embeddings to that same in-memory matrix as the batch proceeds, so later triples in the same batch see earlier ones without re-querying SQLite.
- If `sqlite-vec` is used as the storage-layer vector index (see §10), this in-memory cache acts as a fast pre-filter / batch accelerator on top of it — sqlite-vec handles durable ANN search across runs, the in-memory matrix avoids re-deserializing BLOBs and re-running per-triple queries within a single batch.

### 8c. Contradiction check

Same subject + relation, different object?
- Penalize the **old** fact's confidence (contradiction penalty, §8e), insert the **new** fact with its own confidence, keep both. Recency + confidence decide which surfaces at retrieval time — this correctly handles facts that genuinely change over time (e.g. the user moved cities) rather than treating the new statement as an error.

### 8d. Relation normalization

Check the relation-alias table (e.g. `loves`/`enjoys`/`prefers` → canonical `likes`); apply the canonical form before storing. Open vocabulary is preserved at extraction time — this is **not** a fixed ontology. The alias table itself grows over time via periodic batch clustering of relation strings by embedding similarity (§13, a separate maintenance job, not run on every pass).

### 8e. Confidence update (asymmetric, not static)

- On reinforcement: `confidence = confidence + (1 - confidence) * REINFORCE_RATE` (diminishing returns toward 1.0; `REINFORCE_RATE ≈ 0.2`)
- On contradiction: `confidence = confidence * CONTRADICTION_PENALTY` (penalty heavier than the reinforcement gain; `CONTRADICTION_PENALTY ≈ 0.5`)

Both constants are tunable empirically over time (§14).

### 8f. Importance vs. frequency — two separate knobs, never conflated

- **Importance:** set at extraction time (LLM-assigned prior based on fact type). Gates whether a fact can ever be purged — high-importance facts are never purged, only archived.
- **Frequency:** reinforcement count. Used only for ranking within retained facts, never for deciding what to keep.
- **Decay score:** `decay_score = recency * frequency_weight * confidence`, computed for ranking/lifecycle decisions only.

### 8g. Lifecycle sweep (state machine, runs every job, not just on new facts)

```
active   → dormant  : no reinforcement + no retrieval hit
                       for N days (N depends on layer —
                       episodic = short window, factual =
                       long window)
dormant  → archived : unused for 2N days
archived → purged   : ONLY if importance is LOW.
                       High-importance facts are NEVER purged,
                       only ever archived (kept for audit/history)
```

This sweep runs as a single batched SQL operation (a `WHERE last_used < ? AND status = ?` update, not a per-row Python loop) over the whole store each job, not just over the newly ingested batch.

---

## 9. Storage Layer

### 9.1 Schema — split metadata from embeddings, indexed

```sql
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;   -- safe with WAL, much faster than FULL

CREATE TABLE IF NOT EXISTS triples (
    id                      TEXT PRIMARY KEY,     -- hash(subject, relation, object)
    subject                 TEXT NOT NULL,
    relation                TEXT NOT NULL,
    object                  TEXT NOT NULL,
    raw_text_variants       TEXT,                 -- JSON array
    layer                   TEXT,                 -- factual | episodic | semantic
    confidence              REAL,
    importance              INTEGER,
    frequency               INTEGER,
    decay_score             REAL,
    retrieval_count         INTEGER DEFAULT 0,
    successful_answer_count INTEGER DEFAULT 0,
    status                  TEXT DEFAULT 'active', -- active | dormant | archived
    conversation_id         TEXT,
    message_ids             TEXT,                 -- JSON array, provenance
    compression_epoch       INTEGER,
    extractor_version       TEXT,
    first_seen              TEXT,
    last_seen               TEXT,
    last_used               TEXT
);

-- Vector index, local-first: sqlite-vec keeps this a single file on disk,
-- no server/daemon process — the right fit for an end-user app.
CREATE VIRTUAL TABLE IF NOT EXISTS embeddings USING vec0(
    id TEXT PRIMARY KEY,
    vector FLOAT[384]
);

CREATE INDEX IF NOT EXISTS idx_subject  ON triples(subject COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS idx_relation ON triples(relation COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS idx_status   ON triples(status);
CREATE INDEX IF NOT EXISTS idx_subj_rel ON triples(subject COLLATE NOCASE, relation COLLATE NOCASE);
```

Why `sqlite-vec` specifically, not Qdrant/Postgres/pgvector: those need a running server process — the wrong fit for an end-user app that should just be a file on disk. `sqlite-vec` keeps the vector index inside the same single SQLite file as everything else, with no daemon to manage, while still giving real ANN search instead of a brute-force scan once the store grows large.

Splitting `triples` (metadata) from the vector table means metadata-only queries (markdown projection, lifecycle sweep, inspection/debug tools) never have to drag 384-float vectors along for the ride. `COLLATE NOCASE` indexes mean subject/relation lookups hit the index directly instead of forcing a full scan via `lower(subject) = ?`. `idx_subj_rel` specifically accelerates the contradiction check (§8c), which is a `subject + relation` lookup.

### 9.2 In-memory embedding cache (within-run accelerator)

On process start, load all active embeddings once into a single pre-normalized numpy matrix plus a parallel `id` array:

```python
class EmbeddingCache:
    def __init__(self, conn, dim=384):
        self.dim = dim
        self.ids: list[str] = []
        rows = conn.execute("SELECT id, vector FROM embeddings").fetchall()
        if not rows:
            self.matrix_normed = np.empty((0, dim), dtype=np.float32)
            return
        self.ids = [r[0] for r in rows]
        mat = np.vstack([np.frombuffer(r[1], dtype=np.float32) for r in rows])
        norms = np.linalg.norm(mat, axis=1, keepdims=True)
        self.matrix_normed = mat / np.clip(norms, 1e-8, None)

    def append(self, new_ids: list[str], new_vecs: np.ndarray):
        norms = np.linalg.norm(new_vecs, axis=1, keepdims=True)
        normed = new_vecs / np.clip(norms, 1e-8, None)
        self.matrix_normed = (
            np.vstack([self.matrix_normed, normed]) if self.matrix_normed.size else normed
        )
        self.ids.extend(new_ids)

    def top_matches(self, query_vec: np.ndarray, k: int = 5, subject_mask: np.ndarray | None = None):
        if self.matrix_normed.size == 0:
            return []
        q = query_vec / max(np.linalg.norm(query_vec), 1e-8)
        sims = self.matrix_normed @ q                       # one BLAS call
        if subject_mask is not None:
            sims = np.where(subject_mask, sims, -1.0)
        top_idx = np.argpartition(-sims, min(k, len(sims) - 1))[:k]
        top_idx = top_idx[np.argsort(-sims[top_idx])]
        return [(self.ids[i], float(sims[i])) for i in top_idx]
```

This cache is built once at process start (a one-time O(n) cost paid per background-job invocation, not per triple) and serves every similarity check in that run, including newly inserted triples appended mid-batch. Because the process is short-lived (§5), nothing about this stays resident between runs — RAM is freed the moment the job exits.

### 9.3 Realistic resource footprint at this scale

Single user, realistic years of usage, low tens of thousands of facts at most:
- SQLite + sqlite-vec file: a few MB to low tens of MB.
- RAM during active background job: roughly 50–300MB depending on embedding choice (§10).
- RAM when idle: near-zero — the process exits after each run, nothing stays resident.

---

## 10. Embedding Strategy (Local-First, Two Options)

Given the fully local, single-user constraint, there are two viable embedding sources:

**a. Local small model** (`all-MiniLM-L6-v2` / `bge-small`, 384-dim) — fully offline, ~90MB on disk, ~200–300MB RAM only while actively embedding (load on-demand, unload after — don't keep resident permanently). For the lightest possible footprint, prefer a quantized ONNX build over the full PyTorch `sentence-transformers` runtime:

```python
import onnxruntime as ort
from tokenizers import Tokenizer
import numpy as np

class LocalEmbedder:
    """Quantized MiniLM via ONNX Runtime — no torch, ~25MB model, CPU-only, fast cold start."""
    def __init__(self, model_path="all-MiniLM-L6-v2-int8.onnx", tokenizer_path="tokenizer.json"):
        self.session = ort.InferenceSession(model_path, providers=["CPUExecutionProvider"])
        self.tokenizer = Tokenizer.from_file(tokenizer_path)

    def encode_batch(self, texts: list[str]) -> np.ndarray:
        encodings = [self.tokenizer.encode(t) for t in texts]
        input_ids = _pad([e.ids for e in encodings])
        attn_mask = _pad([e.attention_mask for e in encodings])
        outputs = self.session.run(None, {"input_ids": input_ids, "attention_mask": attn_mask})
        return _mean_pool(outputs[0], attn_mask).astype(np.float32)
```

Swapping `sentence-transformers`/PyTorch (multi-hundred-MB dependency, slower cold start) for a quantized ONNX runtime keeps the local-model option lightweight enough to load on-demand and discard, consistent with the "near-zero RAM when idle" goal in §9.3.

**b. API-based embeddings** (same provider as the extraction LLM, if available) — near-zero local resource cost, needs network plus a tiny per-call cost.

**Recommendation:** if an external LLM API is already being called for extraction, reuse that provider's embedding endpoint to avoid maintaining a second local model. If fully offline operation is a hard requirement, use the local ONNX-quantized model instead. Either backend implements the same `encode_batch(texts)` interface so the pipeline doesn't care which one is active.

**Batching matters regardless of backend:** embed all new triples in a batch in a single `encode_batch()` call per pipeline run (§8, step 6), not one call per triple — this is true whether the call goes to a local ONNX session or a hosted API, and it's the difference between one round trip per background job and N round trips.

---

## 11. Markdown File Projections

```
backend/data/user/user_data.md
backend/data/task/active_<task_name>.md
backend/data/task/archive/archive_<task_name>.md
backend/data/logs/ltm/<YYYY-MM-DD>_<HH-MM-SS>.log
backend/data/locks/memory_manager.lock
backend/data/cursors/facts_cursor.json
```

> **Open item carried over from the architecture plan:** an "OKF architecture" was referenced for markdown file structure but not yet clarified. The structure below is the working placeholder until that's confirmed.

Each markdown file carries a metadata header plus structured sections so the model can locate information by position/heading:

```
user_data.md:
---
entity: User
last_updated: <timestamp>
source_facts: [fact_id_1, fact_id_2, ...]
---
## Identity
- Name: ...
- Location: ...
## Preferences
- ... (confidence, importance shown inline or as metadata)
## Relationships
- ...
```

```
active_<task>.md / archive_<task>.md:
---
task: "<task_name>"
status: active | archived
created: <timestamp>
last_updated: <timestamp>
---
## Goal
...
## Progress
...
## Open Questions
...
```

**Task lifecycle:** when an episodic-event triple indicates completion (e.g. `subject=User, relation=completed, object=<task>`), the background manager moves the file from `active_` to `archive/archive_` and updates its `status` field.

**SQLite + sqlite-vec is the single source of truth.** Markdown files are a generated projection for human/model readability — regenerated from SQLite data, never edited independently, never allowed to diverge as a second source of truth.

### 11.1 Incremental regeneration, not full rewrite

A naive implementation regenerates every markdown file from a full table scan on every single pipeline run, even when only one fact changed. Production tracks a **dirty set** during the pipeline batch — which triples were inserted/updated, and which logical section (Identity / Preferences / Relationships, or a specific task file) each belongs to — and only re-renders those sections:

```python
def ingest_and_project(conn, cache, embedder, facts, epoch):
    summary, dirty_triples = run_batch_pipeline(conn, cache, embedder, facts, epoch)
    dirty_sections = classify_dirty_sections(dirty_triples)  # {"identity", "preferences", task_slug, ...}
    if dirty_sections:
        project_markdown_incremental(conn, dirty_sections)
    return summary
```

`project_markdown_incremental` re-queries only the rows relevant to each dirty section and rewrites only that block/file — `user_data.md` gets one section spliced and rewritten rather than the whole document recomputed, and only the task files whose underlying episodic event actually changed get touched. This turns projection cost from O(total facts in store) per run into O(facts changed in this run) — which matters once a user has hundreds or thousands of stored facts but a typical compression pass only touches a handful.

---

## 12. Retrieval (Main Process, Read-Only)

```
get_facts(query, layer?, subject?, top_k, min_confidence)
  1. Embed query
  2. Vector similarity search (filtered: status=active,
     importance >= threshold if specified)
  3. Re-rank by:
       final_rank_score = vector_similarity
                         * confidence
                         * decay_score
                         * (0.5 + 0.5 * success_rate)
     where success_rate = successful_answer_count
                           / max(retrieval_count, 1)
  4. Return top_k triples (+ raw_text for natural display)
  5. Increment retrieval_count on returned facts
  6. (Async, after response used) update successful_answer_count
     based on whether the fact was actually referenced/useful
```

The main process also reads `user_data.md` / `active_<task>.md` directly for fast context injection without a vector query, when the relevant info is already known to live in those files.

**The main process never writes to SQLite or markdown directly — only the background memory manager writes; the main process only reads.** This is what makes WAL-mode concurrent reads safe and simple: there's exactly one writer, ever.

The vector similarity step reuses the same `EmbeddingCache.top_matches()` (or, once `sqlite-vec` is populated, its native ANN query) used during ingestion — one embed call for the query, one vectorized search, one batched update of `retrieval_count` via `executemany` rather than per-row commits.

---

## 13. Relation Normalization Maintenance (Periodic, Separate Job)

Not run on every memory-manager pass — run occasionally (e.g. weekly, or after every N memory-manager runs):
- Pull all distinct relation strings used so far.
- Cluster them by embedding similarity.
- Propose/apply merges into the relation-alias table (e.g. `likes`/`loves`/`enjoys`/`prefers` → canonical `likes`).

This keeps the relation vocabulary clean over time without blocking new relation types at ingestion time — the open vocabulary is preserved; cleanup happens out-of-band.

---

## 14. Performance Characteristics — Before vs. After

| Operation | Naive / prototype | Production |
|---|---|---|
| Structural dedup for a batch | N separate `SELECT` queries | one `WHERE id IN (...)` query |
| Semantic dedup (cross-namespace check) | O(n) full table scan, Python loop, per triple | one vectorized numpy matmul against an in-memory, pre-normalized matrix |
| Embedding generation | per-triple call, full PyTorch model | batched `encode_batch()`, ONNX-int8 quantized model |
| Write pattern | commit-per-row | single transaction, `executemany`, one commit per run |
| Markdown regeneration | full rewrite of every file, every run | dirty-section diffing, only touched files/blocks rewritten |
| Metadata-only queries (lifecycle sweep, inspection) | drag 384-float vector BLOB per row | separate `embeddings` table, no vector cost on metadata reads |
| Concurrent reads during a write | blocked | WAL mode, readers unaffected |
| Idle resource usage | N/A (no process model) | near-zero — process exits after each run |

---

## 15. Scaling Tiers — When to Move Beyond This Design

This design (sqlite-vec + an in-memory numpy accelerator) is appropriate up to roughly **10k–50k facts per user**, which comfortably covers the stated target of "low tens of thousands of facts at most" over realistic years of single-user usage. If a user's store ever regularly exceeds that range:
- `sqlite-vec`'s ANN index already gives sub-linear lookup at the storage layer, so the main thing to revisit is the in-memory cache's per-run rebuild cost (§9.2) — consider persisting the normalized matrix to disk between runs instead of rebuilding from BLOBs every invocation.
- Consider sharding the embedding cache by subject namespace so cross-namespace checks only scan a relevant subset rather than the whole store.
- None of this is needed at launch — it's a deliberate upgrade path, not a blocker, given the single-user, local-first scope of this system.

---

## 16. Build Order

1. Finalize prompt changes (triple shape) — **done**
2. Set up SQLite + sqlite-vec schema, including indexes and the split metadata/embeddings tables (§9.1)
3. Implement lock + cursor mechanism (§6)
4. Implement trigger wiring: threshold counter, app-close hook, app-startup check (§4)
5. Implement the FastMCP detached background process wrapper (§5)
6. Implement the batched pipeline: structural/semantic/contradiction/relation-normalization checks, using the in-memory embedding cache and batched writes (§8, §9.2)
7. Implement confidence update + importance/frequency logic (§8e, §8f)
8. Implement the lifecycle sweep (§8g)
9. Implement the incremental markdown projection writer (§11.1)
10. Implement retry + failure logging (§7)
11. Implement the read-only retrieval API (§12)
12. Implement the periodic relation-normalization maintenance job (§13)
13. Test end-to-end: simulate a threshold trigger, force-kill mid-run (verify the cursor doesn't advance and retry on next launch works), verify dedup against existing JSONL logs as seed data
14. Tune thresholds (similarity 0.85, reinforce/contradiction rates, decay windows, N for the threshold trigger) against real usage

---

## 17. Open Items

- **"OKF architecture" reference** for markdown file structure (§11) needs clarification before that section is finalized — the structure documented here is a placeholder until confirmed.
