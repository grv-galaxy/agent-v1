"""
deduplicator.py
----------------
Structural + semantic + cross-namespace deduplication, batch-first
(ltm_doc.md §8, §8a, §8b).

This module takes a whole batch of new (already-canonicalized, already
relation-normalized) triples and classifies each one into exactly one of:

  - REINFORCE   : structural match (exact hash) -> bump frequency/confidence
                  on the existing row, no new row, no embedding needed.
  - SEMANTIC_MATCH : no structural match, but cosine similarity vs. an
                  existing embedding in the SAME subject namespace exceeds
                  the threshold -> treat as the same fact, reinforce the
                  existing row instead of inserting.
  - CROSS_NAMESPACE_MATCH : no same-subject match, but a near-duplicate
                  exists elsewhere in the store (catches aliasing cases
                  canonicalization missed) -> also reinforced, not inserted.
  - NEW         : genuinely new fact -> insert.

It does NOT decide contradictions (that's contradiction.py) and does NOT
write confidence values (that's confidence.py) — this module only
classifies and hands back the groups; engine.py wires the rest together
and storage.py/vector_store.py do the actual writes.

Everything here operates on the WHOLE BATCH at once:
  - one structural lookup query for all candidate ids
  - one batched embed call for everything that needs a vector
  - one EmbeddingCache.top_matches() call per genuinely-new triple,
    using the in-memory matrix (not a Python loop over SQLite rows)
  - the cache is appended to ONCE per batch at the end, not per triple
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable

import numpy as np

import storage
import vector_store

# Cosine similarity threshold for "same fact" — ltm_doc.md §8b
SEMANTIC_MATCH_THRESHOLD = 0.85
# Slightly stricter bar for the cross-namespace safety-net check,
# since it's comparing across subjects rather than within one.
CROSS_NAMESPACE_THRESHOLD = 0.92


class DedupOutcome(str, Enum):
    REINFORCE = "reinforce"
    SEMANTIC_MATCH = "semantic_match"
    CROSS_NAMESPACE_MATCH = "cross_namespace_match"
    NEW = "new"


@dataclass
class CandidateTriple:
    """One incoming triple, already canonicalized + relation-normalized,
    not yet checked against the store."""
    subject: str
    relation: str
    object: str
    raw_text: str
    layer: str = "factual"
    importance: int = 50
    confidence: float = 0.5
    conversation_id: str | None = None
    message_id: str | None = None
    compression_epoch: int | None = None

    @property
    def id(self) -> str:
        return storage.make_id(self.subject, self.relation, self.object)


@dataclass
class DedupResult:
    candidate: CandidateTriple
    outcome: DedupOutcome
    matched_id: str | None = None       # existing row this matches, if any
    similarity: float | None = None     # similarity score, if semantic match
    embedding: np.ndarray | None = None  # filled in for NEW / cache-appendable rows


@dataclass
class DedupBatchResult:
    results: list[DedupResult]

    def by_outcome(self, outcome: DedupOutcome) -> list[DedupResult]:
        return [r for r in self.results if r.outcome == outcome]


# ----------------------------------------------------------------------
# Main entry point
# ----------------------------------------------------------------------

def dedup_batch(
    conn,
    cache: "vector_store.EmbeddingCache",
    candidates: list[CandidateTriple],
    embed_fn: Callable[[list[str]], np.ndarray],
) -> DedupBatchResult:
    """
    Classify a whole batch of candidate triples against the store in one
    pass. `embed_fn` is something like LocalEmbedder.encode_batch or a
    hosted-API equivalent — called ONCE for the whole batch, never per
    triple (ltm_doc.md §8, step 6 / §10).
    """
    results: list[DedupResult] = [None] * len(candidates)  # type: ignore

    # ---- Step 1: structural check, ONE query for the whole batch (§8a) ----
    candidate_ids = [c.id for c in candidates]
    existing = storage.get_by_ids(conn, candidate_ids)

    needs_embedding: list[tuple[int, CandidateTriple]] = []
    for idx, cand in enumerate(candidates):
        if cand.id in existing:
            results[idx] = DedupResult(
                candidate=cand,
                outcome=DedupOutcome.REINFORCE,
                matched_id=cand.id,
            )
        else:
            needs_embedding.append((idx, cand))

    if not needs_embedding:
        return DedupBatchResult(results=results)

    # ---- Step 2: batch-embed everything that survived structural check ----
    texts = [f"{c.subject} {c.relation} {c.object}" for _, c in needs_embedding]
    vectors = embed_fn(texts)  # one call, shape (n, dim)

    # ---- Step 3: semantic + cross-namespace check, vectorized, per-row ----
    # (a single embed call already happened above; the search itself below
    # is a matmul against the in-memory cache, not a Python loop over rows)
    to_append_ids: list[str] = []
    to_append_vecs: list[np.ndarray] = []
    to_append_subjects: list[str] = []

    for (idx, cand), vec in zip(needs_embedding, vectors):
        same_subject_matches = cache.top_matches(vec, k=1, subject=cand.subject)
        if same_subject_matches and same_subject_matches[0][1] >= SEMANTIC_MATCH_THRESHOLD:
            matched_id, sim = same_subject_matches[0]
            results[idx] = DedupResult(
                candidate=cand,
                outcome=DedupOutcome.SEMANTIC_MATCH,
                matched_id=matched_id,
                similarity=sim,
            )
            continue

        # fall through: stricter cross-namespace safety-net search
        any_matches = cache.top_matches(vec, k=1, subject=None)
        if any_matches and any_matches[0][1] >= CROSS_NAMESPACE_THRESHOLD:
            matched_id, sim = any_matches[0]
            results[idx] = DedupResult(
                candidate=cand,
                outcome=DedupOutcome.CROSS_NAMESPACE_MATCH,
                matched_id=matched_id,
                similarity=sim,
            )
            continue

        # genuinely new
        results[idx] = DedupResult(
            candidate=cand,
            outcome=DedupOutcome.NEW,
            embedding=vec,
        )
        to_append_ids.append(cand.id)
        to_append_vecs.append(vec)
        to_append_subjects.append(cand.subject)

    # ---- Step 4: append all genuinely-new vectors to the cache ONCE ----
    # (collected above, NOT appended per-triple inside the loop, per the
    # np.vstack fragmentation fix applied to vector_store.py)
    if to_append_ids:
        cache.append(
            to_append_ids,
            np.vstack(to_append_vecs),
            subjects=to_append_subjects,
        )

    return DedupBatchResult(results=results)