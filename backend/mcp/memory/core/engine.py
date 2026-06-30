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
    3.  Read new triple-shaped facts        -> parse_facts()
    4.  Canonicalize subjects (whole batch) -> parse_facts()
    5.  Structural dedup, ONE query         -> deduplicator.dedup_batch()
    6.  Batch-embed only the new triples    -> deduplicator.dedup_batch()
                                               (calls embed_fn once)
    7.  Semantic + cross-namespace dedup    -> deduplicator.dedup_batch()
                                               (vectorized, in-memory cache)
    8.  Resolve contradictions              -> contradiction.check_batch()
    9.  Relation normalization              -> parse_facts() (alias lookup)
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
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import numpy as np

import storage
import vector_store
import deduplicator
import contradiction
import confidence
import importance
from deduplicator import CandidateTriple, DedupOutcome

EmbedFn = Callable[[list[str]], np.ndarray]


# ----------------------------------------------------------------------
# Step 3/4/9: parse + canonicalize + relation-normalize a raw fact batch
# ----------------------------------------------------------------------

# Minimal starter alias table (ltm_doc.md §8d). In production this grows
# over time via the periodic relation-normalization maintenance job
# (§13) and should be loaded from storage rather than hardcoded — kept
# inline here as the v1 seed set.
RELATION_ALIASES: dict[str, str] = {
    "loves": "likes",
    "enjoys": "likes",
    "prefers": "likes",
    "is_located_in": "lives_in",
    "resides_in": "lives_in",
    "works_at": "employed_by",
    "works_for": "employed_by",
}


def normalize_relation(relation: str) -> str:
    key = relation.strip().lower().replace(" ", "_")
    return RELATION_ALIASES.get(key, key)


def parse_facts(
    raw_facts: list[dict],
    *,
    default_subject: str = "User",
    compression_epoch: int | None = None,
) -> list[CandidateTriple]:
    """Steps 3/4/9: turn raw JSONL-shaped dicts into canonicalized,
    relation-normalized CandidateTriple objects for the WHOLE batch at
    once. No SQLite or embedding work happens here — pure parsing."""
    candidates: list[CandidateTriple] = []
    for raw in raw_facts:
        subject = (raw.get("subject") or default_subject).strip() or default_subject
        relation = normalize_relation(raw.get("relation", ""))
        obj = (raw.get("object") or "").strip()
        if not obj or obj.lower() in {"it", "him", "her", "them", "himself", "herself"}:
            # Skip triples where the object carries no real meaning
            # (ltm_doc.md §3 extraction rule, enforced again here as a
            # safety net in case the extractor slips one through).
            continue

        candidates.append(
            CandidateTriple(
                subject=subject,
                relation=relation,
                object=obj,
                raw_text=raw.get("raw_text") or f"{subject} {relation} {obj}",
                layer=raw.get("layer", "factual"),
                importance=importance.clamp_importance(raw.get("importance", 50)),
                confidence=float(raw.get("confidence", 0.5)),
                conversation_id=raw.get("conversation_id"),
                message_id=raw.get("message_id"),
                compression_epoch=compression_epoch,
            )
        )
    return candidates


# ----------------------------------------------------------------------
# Pipeline result
# ----------------------------------------------------------------------

@dataclass
class PipelineSummary:
    inserted: int = 0
    reinforced: int = 0
    contradicted: int = 0
    skipped: int = 0
    lifecycle_counts: dict[str, int] = field(default_factory=dict)
    dirty_triple_ids: list[str] = field(default_factory=list)


# ----------------------------------------------------------------------
# The pipeline itself (steps 5-11)
# ----------------------------------------------------------------------

def run_batch_pipeline(
    conn,
    cache: "vector_store.EmbeddingCache",
    embed_fn: EmbedFn,
    raw_facts: list[dict],
    *,
    compression_epoch: int | None = None,
    lifecycle_policy: importance.LifecyclePolicy = importance.DEFAULT_LIFECYCLE_POLICY,
    now_iso: str | None = None,
) -> PipelineSummary:
    """
    Run the full batch pipeline over one unprocessed range of facts.
    Safe to call repeatedly with the same input (idempotent) — re-running
    an already-processed batch just re-classifies everything as
    REINFORCE/SEMANTIC_MATCH and bumps frequency, it never duplicates
    rows. This is what makes the retry-on-failure story in ltm_doc.md §7
    safe without needing per-fact cursor tracking.
    """
    if now_iso is None:
        now_iso = storage._now_iso()

    summary = PipelineSummary()

    # ---- Steps 3/4/9: parse + canonicalize + relation-normalize ----
    candidates = parse_facts(raw_facts, compression_epoch=compression_epoch)
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
        insert_rows.append(
            storage.TripleRow(
                id=cand.id,
                subject=cand.subject,
                relation=cand.relation,
                object=cand.object,
                raw_text_variants=[cand.raw_text],
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
    # (cache.append() for these vectors already happened inside
    # deduplicator.dedup_batch() — here we only persist to SQLite.)
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
    summary.contradicted = len(contradiction_updates)
    summary.skipped = len(raw_facts) - len(candidates)
    summary.lifecycle_counts = lifecycle_counts
    summary.dirty_triple_ids = list(dict.fromkeys(dirty_ids))  # de-dup, preserve order

    return summary