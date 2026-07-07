"""
engine.py
---------
Orchestrates the complete batch-first memory pipeline (ltm_doc.md §8).

This is the only module that wires storage.py, vector_store.py,
deduplicator.py, contradiction.py, confidence.py, and importance.py
together into the actual sequence of steps. Nothing here owns its own
business logic — every decision (what counts as a match, what penalty
to apply, when something goes dormant) is delegated to the module that
owns that policy. engine.py is purely sequencing + batching discipline.

Maps directly onto ltm_doc.md §8's 13-step list:

    1.  Acquire lock                       -> caller's job (server.py),
                                               NOT this module
    2.  Determine new JSONL lines           -> caller's job (cursor logic
                                               lives at the process level,
                                               not inside the pipeline)
    3.  Fetch the latest facts file's lines -> fetcher.read_latest_facts()
                                               (called by THIS module now)
    4.  Read + canonicalize triples          -> extractor.parse_facts()
                                               (called by THIS module now)
    5.  Structural dedup, ONE query         -> deduplicator.dedup_batch()
    6.  Batch-embed only the new triples    -> deduplicator.dedup_batch()
                                               (calls embed_fn once)
    7.  Semantic + cross-namespace dedup    -> deduplicator.dedup_batch()
                                               (vectorized, in-memory cache)
    8.  Resolve contradictions              -> contradiction.check_batch()
    9.  Relation normalization              -> extractor.parse_facts()
                                               (sanitize_relation)
    10. Single bulk write, one transaction  -> run_batch_pipeline()
    11. Lifecycle sweep, every job          -> importance.run_lifecycle_sweep()
    12. Markdown projection (incremental)   -> caller's job (markdown.py),
                                               this module returns the
                                               dirty-triple-id list it needs
    13. Advance cursor, release lock        -> caller's job (server.py)

engine.py is intentionally NOT responsible for steps 1, 2, 12, 13 — those
are process-level concerns (lock files, cursor files, markdown rendering)
that belong in server.py / markdown.py, not buried inside the pipeline
function itself. This keeps run_batch_pipeline() a plain, testable
function with no filesystem/process side effects beyond the DB writes.

NOTE (this revision): engine.py now owns steps 3/4/9 itself, by calling
fetcher.py to get the latest file's lines and extractor.py to turn those
lines into CandidateTriple objects. engine.py no longer has its own
duplicate parse_facts() implementation — that logic lives in extractor.py
only, so there is exactly one place that does parsing/canonicalization,
not two. fetcher.py fetches, extractor.py parses, engine.py orchestrates
the call between them plus everything downstream (dedup, contradiction,
confidence, storage, lifecycle).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable
import traceback
import time
from pathlib import Path
import numpy as np

from . import storage
from . import vector_store
from . import deduplicator
from . import contradiction
from . import confidence
from . import importance
from . import extractor
from .fetcher import read_latest_facts
from .deduplicator import CandidateTriple, DedupOutcome

EmbedFn = Callable[[list[str]], np.ndarray]

@dataclass
class PipelineSummary:
    inserted: int = 0
    reinforced: int = 0
    contradicted: int = 0
    skipped: int = 0
    lifecycle_counts: dict[str, int] = field(default_factory=dict)
    dirty_triple_ids: list[str] = field(default_factory=list)

def run_batch_pipeline(
    conn,
    cache: "vector_store.EmbeddingCache",
    embed_fn: EmbedFn,
    raw_facts: list[dict] | None = None,
    *,
    compression_epoch: int | None = None,
    lifecycle_policy: importance.LifecyclePolicy = importance.DEFAULT_LIFECYCLE_POLICY,
    now_iso: str | None = None,
) -> PipelineSummary:
    """
    Run the full batch pipeline over one unprocessed range of facts.
    Safe to call repeatedly with the same input (idempotent).

    Steps 3/4/9 (fetch + parse + canonicalize + relation-normalize) are
    now handled by this function itself, by calling fetcher.py then
    extractor.py, instead of receiving already-parsed candidates.

    `raw_facts` is kept as an optional escape hatch for callers (e.g.
    tests, or handlers.py's cursor-based partial reads) that already have
    raw JSONL-shaped dicts in hand and want to skip the fetch+parse step.
    If `raw_facts` is given, it's used as-is (treated as already having
    gone through extractor-equivalent parsing upstream). If it's not
    given (the normal path), this function fetches the latest file's
    lines via fetcher.read_latest_facts() and parses them via
    extractor.parse_facts().
    """
    if now_iso is None:
        now_iso = storage._now_iso()

    summary = PipelineSummary()

    # ---- Steps 3/4/9: fetch (fetcher.py) + parse/canonicalize (extractor.py) ----
    current_file_path = None
    if raw_facts is None:
        lines, current_file_path = read_latest_facts()
        if not lines:
            return summary
        candidates = extractor.parse_facts(lines)
    else:
        # Escape hatch: raw_facts already provided by the caller.
        # extractor.parse_facts() expects raw JSONL text lines (each line
        # a JSON object with a "facts" section), so if the caller is
        # passing already-parsed dicts here instead, they're responsible
        # for shaping them correctly upstream.
        candidates = extractor.parse_facts(raw_facts)

    if not candidates:
        return summary

    # ---- Steps 5/6/7: structural -> batch embed -> semantic/cross-namespace ----
    dedup_result = deduplicator.dedup_batch(conn, cache, candidates, embed_fn)

    # ---- Step 8: contradiction check, only over genuinely NEW candidates ----
    new_results = dedup_result.by_outcome(DedupOutcome.NEW)
    contradiction_results = contradiction.check_batch(conn, dedup_result.results)
    contradiction_updates = contradiction.collect_confidence_updates(contradiction_results)

    # ---- Build reinforcement updates for REINFORCE/SEMANTIC/CROSS_NS ----
    reinforcement_updates = confidence.build_reinforcement_updates(conn, dedup_result.results)

    # ---- Build insert rows for genuinely NEW triples ----
    insert_rows: list[storage.TripleRow] = []
    insert_embed_ids: list[str] = []
    insert_embed_vecs: list[np.ndarray] = []
    
    for r in new_results:
        cand = r.candidate
        # Optional validation: if a candidate was completely tanked by a contradiction, 
        # you can handle alternative routing here. Default is standard insertion.
        insert_rows.append(
            storage.TripleRow(
                id=cand.id,
                subject=cand.subject,
                relation=cand.relation,
                object=cand.object,
                # raw_text_variants=[cand.raw_text],
                layer=cand.layer,
                confidence=cand.confidence,
                importance=cand.importance,
                frequency=1,
                status="active",
                conversation_id=cand.conversation_id,
                message_ids=[cand.message_id] if cand.message_id else [],
                compression_epoch=cand.compression_epoch,
                first_seen=now_iso,
                last_seen=now_iso,
                last_used=now_iso,
            )
        )
        insert_embed_ids.append(cand.id)
        insert_embed_vecs.append(r.embedding)

    # ---- Step 10: single bulk write, one transaction per write type ----
    storage.bulk_insert(conn, insert_rows)
    if insert_embed_ids:
        vector_store.bulk_insert_embeddings(
            conn, insert_embed_ids, np.vstack(insert_embed_vecs)
        )
    storage.bulk_reinforce(conn, reinforcement_updates)
    storage.bulk_contradict(conn, contradiction_updates)

    # ---- Step 11: lifecycle sweep + decay recompute, every job ----
    lifecycle_counts = importance.run_lifecycle_sweep(conn, lifecycle_policy)
    importance.recompute_decay_scores(conn)

    # ---- Assemble summary, including dirty ids for markdown projection ----
    dirty_ids = (
        insert_embed_ids
        + [u[0] for u in reinforcement_updates]
        + [u[0] for u in contradiction_updates]
    )

    summary.inserted = len(insert_rows)
    summary.reinforced = len(reinforcement_updates)
    
    # FIX: Calculate contradictions from batch result matches, not just database side-effects
    summary.contradicted = sum(1 for res in contradiction_results if res.is_contradiction)
    # "skipped" = raw input units that didn't make it into a candidate.
    # When raw_facts wasn't provided, that's fetched lines; when it was,
    # it's the raw_facts list itself.
    raw_input_count = len(lines) if raw_facts is None else len(raw_facts)
    summary.skipped = max(raw_input_count - len(candidates), 0)
    summary.lifecycle_counts = lifecycle_counts
    summary.dirty_triple_ids = list(dict.fromkeys(dirty_ids))

    # ---- Step 12: Work completed successfully! Archive the file now ----
    if current_file_path:
        from .fetcher import archive_processed_file
        archive_processed_file(current_file_path)

    return summary

def run_batch_pipeline_with_retry(
    conn,
    cache: "vector_store.EmbeddingCache",
    embed_fn: EmbedFn,
    # raw_facts: list[dict],
    *,
    max_attempts: int = 2,
    backoff_delay: float = 0.1,
    **kwargs,
) -> PipelineSummary:
    """
    Wraps the pipeline call in a retry loop (ltm_doc.md §7).
    Attempts execution up to max_attempts times. If a final failure occurs,
    writes a diagnostic crash log to backend/data/logs/ltm/ and re-raises the error
    so the upstream cursor remains untouched.
    """
    last_exception = None
    
    for attempt in range(1, max_attempts + 1):
        try:
            # Attempt to execute the pipeline loop
            return run_batch_pipeline(conn, cache, embed_fn, **kwargs)
        except Exception as e:
            last_exception = e
            if attempt < max_attempts:
                # Small backoff before the final retry attempt
                time.sleep(backoff_delay)
                
    # If we reached here, all attempts failed. Log diagnostic info on final failure.
    log_dir = Path("backend/data/logs/ltm")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    log_file = log_dir / f"failure_{timestamp}.log"
    
    with open(log_file, "w", encoding="utf-8") as f:
        f.write("=== LTM PIPELINE FAILURE LOG ===\n")
        f.write(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Attempt Count: {max_attempts}\n")
        f.write(f"Exception Type: {type(last_exception).__name__}\n")
        f.write(f"Exception Message: {str(last_exception)}\n\n")
        f.write("=== Stack Trace ===\n")
        f.write(traceback.format_exc())
        
    # Re-raise the exception so the calling process (cursor logic) knows not to advance
    raise last_exception