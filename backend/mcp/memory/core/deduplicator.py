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

from . import storage
from . import vector_store

# Cosine similarity threshold for "same fact" — ltm_doc.md §8b
SEMANTIC_MATCH_THRESHOLD = 0.85
# Slightly stricter bar for the cross-namespace safety-net check,
# since it's comparing across subjects rather than within one.
CROSS_NAMESPACE_THRESHOLD = 0.92


RELATION_MAP = {
    # ---- Location / residence ----
    "lives": "lives_in",
    "lives_in": "lives_in",
    "lives in": "lives_in",
    "from": "lives_in",
    "is from": "lives_in",
    "comes from": "lives_in",
    "resides": "lives_in",
    "resides_in": "lives_in",
    "resides in": "lives_in",
    "residing_in": "lives_in",
    "located_in": "lives_in",
    "located in": "lives_in",
    "based_in": "lives_in",
    "based in": "lives_in",
    "stays_in": "lives_in",
    "stays in": "lives_in",
    "hails_from": "lives_in",
    "hails from": "lives_in",
    "is_from": "lives_in",
    "belong_to": "lives_in",
    "belongs_to": "lives_in",
    "native_of": "born_in",
    "native of": "born_in",
    "born_in": "born_in",
    "born in": "born_in",
    "from_city": "lives_in",
    "location": "lives_in",

    # ---- Name / identity ----
    "is_called": "name",
    "is called": "name",
    "called": "name",
    "named": "name",
    "goes_by": "name",
    "known_as": "name",
    "known as": "known_as",
    "prefers_to_be_called": "name",
    "gave_nickname": "name",
    "nickname": "name",
    "user_nickname": "name",

    # ---- Occupation / work ----
    "works_as": "occupation",
    "works as": "occupation",
    "is_a": "occupation",
    "is a": "occupation",
    "profession": "occupation",
    "role": "occupation",
    "job": "occupation",
    "employed_as": "occupation",
    "employed as": "occupation",
    "works_at": "employed_by",
    "works at": "employed_by",
    "works_for": "employed_by",
    "works for": "employed_by",

    # ---- Age ----
    "is_age": "age",
    "is age": "age",
    "aged": "age",
    "years_old": "age",

    # ---- Language ----
    "speaks": "speaks",
    "fluent_in": "speaks",
    "fluent in": "speaks",

    # ---- Preferences / likes ----
    "loves": "likes",
    "enjoys": "likes",
    "adores": "likes",
    "is_interested_in": "likes",
    "interested_in": "likes",
    "interested": "likes",
    "is interested in": "likes",
    "fond_of": "likes",
    "fond of": "likes",
    "passionate_about": "likes",
    "passionate about": "likes",
    "into": "likes",
    "hobbies": "likes",
    "hobby": "likes",
    "prefers": "likes",
    "hates": "dislikes",
    "dislikes": "dislikes",
    "does_not_like": "dislikes",
    "does not like": "dislikes",
    "favourite": "favorite_of",
    "favorite": "favorite_of",
    "favors": "favorite_of",

    # ---- Relationships ----
    "married_to": "married_to",
    "married to": "married_to",
    "spouse": "married_to",
    "parent_of": "parent_of",
    "parent of": "parent_of",
    "child_of": "child_of",
    "child of": "child_of",
    "sibling_of": "sibling_of",
    "sibling of": "sibling_of",
    "friend_of": "friend_of",
    "friend of": "friend_of",
    "friends_with": "friend_of",
    "friends with": "friend_of",
    "knows": "knows",
    "works_with": "works_with",
    "works with": "works_with",
    "colleague_of": "works_with",

    # ---- Task progress ----
    "started": "started",
    "working_on": "working_on",
    "working on": "working_on",
    "blocked_on": "blocked_on",
    "blocked on": "blocked_on",
    "completed": "completed",
    "paused": "paused",
    "finished": "completed",
    "done_with": "completed",
}

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
    # raw_text: str
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
        in_batch_match_found = False

        # 3a. Cross-check against genuinely new items already collected in this SAME batch
        if to_append_ids:
            batch_vecs = np.vstack(to_append_vecs)
            norms = np.linalg.norm(batch_vecs, axis=1, keepdims=True)
            normed_batch = batch_vecs / np.clip(norms, 1e-8, None)
            
            q = np.array(vec, dtype=np.float32)
            q = q / max(np.linalg.norm(q), 1e-8)
            sims = normed_batch @ q
            
            # Same subject check within batch
            mask = np.array([s.lower() == cand.subject.lower() for s in to_append_subjects])
            masked_sims = np.where(mask, sims, -1.0)
            
            if masked_sims.size > 0:
                best_idx = np.argmax(masked_sims)
                if masked_sims[best_idx] >= SEMANTIC_MATCH_THRESHOLD:
                    results[idx] = DedupResult(
                        candidate=cand,
                        outcome=DedupOutcome.SEMANTIC_MATCH,
                        matched_id=to_append_ids[best_idx],
                        similarity=float(masked_sims[best_idx]),
                    )
                    in_batch_match_found = True
            
            # Cross-namespace check within batch
            if not in_batch_match_found and sims.size > 0:
                best_idx_any = np.argmax(sims)
                if sims[best_idx_any] >= CROSS_NAMESPACE_THRESHOLD:
                    results[idx] = DedupResult(
                        candidate=cand,
                        outcome=DedupOutcome.CROSS_NAMESPACE_MATCH,
                        matched_id=to_append_ids[best_idx_any],
                        similarity=float(sims[best_idx_any]),
                    )
                    in_batch_match_found = True

        if in_batch_match_found:
            continue

        # 3b. Check the global cache
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

def normalize_relation(relation: str) -> str:
    """
    Normalizes a relational string to its canonical equivalent using a 
    dictionary mapping look-up (§8d). Returns lowered, stripped clean string.
    """
    cleaned = relation.strip().lower()
    return RELATION_MAP.get(cleaned, cleaned)