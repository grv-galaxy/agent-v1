"""
retrieval.py
------------
Handles high-performance, unified semantic and exact retrieval from the 
Long-Term Memory store (ltm_doc.md §12).

Scoring Strategy:
  - Extracts active triples.
  - Scores via derived decay_score = (recency * frequency_weight * confidence).
  - Integrates feedback metrics (success_rate = successful_answers / total_retrievals).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable

import numpy as np
from . import storage
from . import importance
from .vector_store import EmbeddingCache

logger = logging.getLogger("ltm.retrieval")

@dataclass
class MemoryMatch:
    id: str
    subject: str
    relation: str
    object: str
    layer: str
    confidence: float
    importance: int
    frequency: int
    decay_score: float
    retrieval_count: int
    successful_answer_count: int
    score: float  # Final adjusted retrieval score used for ranking


def retrieve_memories(
    conn: storage.sqlite3.Connection,
    cache: EmbeddingCache,
    query_text: str,
    embed_fn: Callable[[list[str]], np.ndarray],
    subject_filter: str | None = None,
    limit: int = 10,
    similarity_threshold: float = 0.40,
) -> list[MemoryMatch]:
    """
    Retrieves and ranks the top matching active memories for a given query string.
    
    Workflow:
      1. Generates an embedding for the query string.
      2. Runs a fast matrix-vector dot product against the pre-loaded in-memory cache.
      3. Gathers the underlying metadata rows via a single batched SQLite lookup.
      4. Adjusts scores based on the operational retrieval_count feedback loop.
    """
    # Guard against completely empty memory stores
    if cache.matrix_normed.size == 0:
        return []

    # Step 1: Embed the query string using the runtime service worker
    try:
        query_vecs = embed_fn([query_text])
        # Safe check for NumPy arrays or standard lists without using truth value evaluation
        if query_vecs is None:
            return []
        if hasattr(query_vecs, "size") and query_vecs.size == 0:
            return []
        if not hasattr(query_vecs, "size") and not query_vecs:
            return []
            
        query_vec = query_vecs[0]
    except Exception as e:
        logger.error(f"Failed to generate query embedding during retrieval: {e}")
        return []

    # Step 2: Use the BLAS-accelerated dot product matrix operation
    # If a subject namespace constraint is passed, the cache masks out other namespaces
    matches = cache.top_matches(
        query_vec=query_vec,
        k=limit * 3,  # Over-sample candidates to handle potential dormant/archived status filtering
        subject=subject_filter
    )

    if not matches:
        return []

    # Map candidate IDs and keep track of their cosine similarity metrics
    matched_ids = [m[0] for m in matches]
    sim_map = {m[0]: m[1] for m in matches}

    # Step 3: Fetch full metadata matrices in one query scan
    rows_map = storage.get_by_ids(conn, matched_ids)

    results = []
    for m_id in matched_ids:
        row = rows_map.get(m_id)
        if not row:
            continue

        # Filter: Exclude dormant, archived, or soft-purged entities from active context windows
        if row.status != "active":
            continue
            
        # Filter: Enforce semantic proximity boundary limits
        similarity = sim_map[m_id]
        if similarity < similarity_threshold:
            continue

        # Step 4: Calculate final composite dynamic ranking score (ltm_doc.md §12)
        # score = decay_score * (1.0 + success_rate)
        succ_rate = importance.success_rate(row.successful_answer_count, row.retrieval_count)
        final_score = row.decay_score * (1.0 + succ_rate)

        results.append(
            MemoryMatch(
                id=row.id,
                subject=row.subject,
                relation=row.relation,
                object=row.object,
                layer=row.layer,
                confidence=row.confidence,
                importance=row.importance,
                frequency=row.frequency,
                decay_score=row.decay_score,
                retrieval_count=row.retrieval_count,
                successful_answer_count=row.successful_answer_count,
                score=final_score,
            )
        )

    # Re-rank elements by their composite score descending
    results.sort(key=lambda x: x.score, reverse=True)
    return results[:limit]


def increment_retrieval_metrics(
    conn: storage.sqlite3.Connection,
    retrieved_ids: list[str],
    successful_ids: list[str] | None = None,
) -> None:
    """
    Updates the operational feedback loops inside the metadata store (ltm_doc.md §12).
    
    Increments total retrieval counts for hit facts, and updates successful response
    counters for facts that directly contributed to an accurate execution layer answer.
    """
    if not retrieved_ids:
        return

    with storage.transaction(conn):
        # 1. Update retrieval tracking counts for hit identifiers
        placeholders = ",".join(["?"] * len(retrieved_ids))
        conn.execute(
            f"UPDATE triples SET retrieval_count = retrieval_count + 1 WHERE id IN ({placeholders})",
            retrieved_ids,
        )

        # 2. Update accuracy counters if a positive response marker is given
        if successful_ids:
            s_placeholders = ",".join(["?"] * len(successful_ids))
            conn.execute(
                f"UPDATE triples SET successful_answer_count = successful_answer_count + 1 WHERE id IN ({s_placeholders})",
                successful_ids,
            )