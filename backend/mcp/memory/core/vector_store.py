"""
vector_store.py
----------------
Vector storage + in-memory similarity search for the Long-Term Memory (LTM)
system (per ltm_doc.md §9.1, §9.2, §10).

Two layers, working together:

  1. Durable storage: a `sqlite-vec` virtual table (`embeddings`) living in
     the SAME SQLite file as storage.py's `triples` table, but as its own
     table — so metadata-only reads never pay the cost of loading vectors,
     and vector-only reads never pay the cost of loading metadata.

  2. Within-run accelerator: `EmbeddingCache`, an in-memory, pre-normalized
     numpy matrix loaded ONCE per process invocation. Every similarity
     check in a pipeline run reuses this same matrix instead of
     re-querying SQLite per triple. This is what turns the dedup pass
     from an O(n) Python loop into a single BLAS matmul.

This module has zero knowledge of dedup/contradiction/confidence logic —
that lives in deduplicator.py / contradiction.py. This is storage +
search only.
"""

from __future__ import annotations

import sqlite3
import struct
from pathlib import Path

import numpy as np

EMBEDDING_DIM = 384  # all-MiniLM-L6-v2 / bge-small dimensionality


# ----------------------------------------------------------------------
# sqlite-vec extension loading
# ----------------------------------------------------------------------

def load_vec_extension(conn: sqlite3.Connection) -> bool:
    """
    Load the sqlite-vec extension into an existing connection.
    Returns True if loaded, False if sqlite-vec isn't installed —
    callers can fall back to the plain BLOB table in that case
    (see `_create_fallback_table`) rather than hard-failing, since
    this system has no hard latency/availability requirement that
    would justify crashing the whole pipeline over a missing extension.
    """
    try:
        import sqlite_vec  # type: ignore
    except ImportError:
        return False

    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)
    return True


def init_vector_table(conn: sqlite3.Connection, dim: int = EMBEDDING_DIM) -> bool:
    """
    Create the embeddings table. Prefers the sqlite-vec virtual table
    (real ANN search, single file on disk, no server/daemon — per
    ltm_doc.md §9.1 rationale for choosing sqlite-vec over
    Qdrant/Postgres/pgvector). Falls back to a plain BLOB table + the
    in-memory EmbeddingCache doing all the search work if sqlite-vec
    isn't available in this environment.

    Returns True if sqlite-vec backing is active, False if running on
    the fallback BLOB table.
    """
    has_vec = load_vec_extension(conn)
    if has_vec:
        conn.execute(
            f"CREATE VIRTUAL TABLE IF NOT EXISTS embeddings USING vec0("
            f"id TEXT PRIMARY KEY, vector FLOAT[{dim}])"
        )
    else:
        _create_fallback_table(conn)
    conn.commit()
    return has_vec


def _create_fallback_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS embeddings (
            id     TEXT PRIMARY KEY,
            vector BLOB NOT NULL
        )
        """
    )


# ----------------------------------------------------------------------
# Vector (de)serialization
# ----------------------------------------------------------------------

def _to_blob(vec: np.ndarray) -> bytes:
    return vec.astype(np.float32).tobytes()


def _from_blob(blob: bytes) -> np.ndarray:
    return np.frombuffer(blob, dtype=np.float32)


# ----------------------------------------------------------------------
# Durable batch writes — one transaction, executemany (mirrors storage.py)
# ----------------------------------------------------------------------

def bulk_insert_embeddings(
    conn: sqlite3.Connection, ids: list[str], vectors: np.ndarray
) -> None:
    """Single executemany insert for a whole batch, not one INSERT per
    triple (ltm_doc.md §8, step 10)."""
    if not ids:
        return
    rows = [(i, _to_blob(v)) for i, v in zip(ids, vectors)]
    with conn:
        conn.executemany(
            "INSERT INTO embeddings (id, vector) VALUES (?, ?)", rows
        )


def fetch_all_embeddings(conn: sqlite3.Connection) -> tuple[list[str], np.ndarray]:
    """One full read at process start, to seed the in-memory cache
    (ltm_doc.md §9.2). Not meant to be called per-triple."""
    rows = conn.execute("SELECT id, vector FROM embeddings").fetchall()
    if not rows:
        return [], np.empty((0, EMBEDDING_DIM), dtype=np.float32)
    ids = [r[0] for r in rows]
    matrix = np.vstack([_from_blob(r[1]) for r in rows])
    return ids, matrix


def native_vec_search(
    conn: sqlite3.Connection, query_vec: np.ndarray, k: int = 5
) -> list[tuple[str, float]]:
    """
    Use sqlite-vec's native ANN search directly (durable, sub-linear at
    scale). Only valid if init_vector_table() returned True for this
    connection — callers should prefer EmbeddingCache.top_matches() for
    within-a-single-run lookups (it's faster, no SQL round trip) and use
    this for cross-process / cold retrieval calls instead.
    """
    rows = conn.execute(
        """
        SELECT id, distance
        FROM embeddings
        WHERE vector MATCH ?
        ORDER BY distance
        LIMIT ?
        """,
        (_to_blob(query_vec), k),
    ).fetchall()
    # sqlite-vec returns L2 distance by default; convert to a similarity-
    # style score (higher = better) so callers don't have to care.
    return [(r[0], 1.0 / (1.0 + r[1])) for r in rows]


# ----------------------------------------------------------------------
# In-memory accelerator (ltm_doc.md §9.2)
# ----------------------------------------------------------------------

class EmbeddingCache:
    """
    Loaded ONCE per background-job invocation. Serves every similarity
    check for the rest of that run — including newly inserted triples
    appended mid-batch — without re-querying SQLite or re-deserializing
    BLOBs per triple.

    Because the memory MCP process is short-lived (spun up per trigger,
    exits when the batch job finishes), nothing about this cache stays
    resident between runs; RAM is freed the moment the process exits.
    """

    def __init__(self, conn: sqlite3.Connection, dim: int = EMBEDDING_DIM):
        self.dim = dim
        self.ids: list[str] = []
        self._subjects: np.ndarray = np.array([], dtype="<U200")  # vectorized namespace mask
        ids, matrix = fetch_all_embeddings(conn)
        self.ids = ids
        self.matrix_normed = self._normalize(matrix) if matrix.size else (
            np.empty((0, dim), dtype=np.float32)
        )

    @staticmethod
    def _normalize(matrix: np.ndarray) -> np.ndarray:
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        return matrix / np.clip(norms, 1e-8, None)

    def set_subjects(self, id_to_subject: dict[str, str]) -> None:
        """Optional: attach subject labels (lowercased) so top_matches()
        can restrict a search to the same subject namespace, per the
        semantic-check rule in ltm_doc.md §8b ('same subject namespace').
        Stored as a native numpy string array so the mask in top_matches()
        is a fully vectorized comparison, not a Python loop."""
        self._subjects = np.array(
            [id_to_subject.get(i, "").lower() for i in self.ids], dtype="<U200"
        )

    def append(self, new_ids: list[str], new_vecs: np.ndarray, subjects: list[str] | None = None) -> None:
        """Append a BATCH of newly inserted triples to the live cache in
        ONE vstack call, so later triples in the SAME pipeline batch see
        them without a SQLite round trip.

        IMPORTANT: callers must collect all new rows for the batch first
        and call this once at the end — calling append() per-triple in a
        loop repeatedly reallocates/copies the whole matrix (np.vstack
        needs contiguous memory), which defeats the point of caching."""
        if not new_ids:
            return
        normed = self._normalize(new_vecs.astype(np.float32))
        self.matrix_normed = (
            np.vstack([self.matrix_normed, normed]) if self.matrix_normed.size else normed
        )
        self.ids.extend(new_ids)
        if subjects is not None:
            new_subj = np.array([s.lower() for s in subjects], dtype="<U200")
        else:
            new_subj = np.array([""] * len(new_ids), dtype="<U200")
        self._subjects = (
            np.concatenate([self._subjects, new_subj]) if self._subjects.size else new_subj
        )

    def top_matches(
        self,
        query_vec: np.ndarray,
        k: int = 5,
        subject: str | None = None,
    ) -> list[tuple[str, float]]:
        """
        One matrix-vector dot product against the whole cache — a single
        BLAS call instead of a per-row Python loop (ltm_doc.md §8b).
        If `subject` is given and subjects have been attached via
        set_subjects()/append(), restricts the search to that namespace.
        """
        if self.matrix_normed.size == 0:
            return []

        q = query_vec.astype(np.float32)
        q = q / max(np.linalg.norm(q), 1e-8)
        sims = self.matrix_normed @ q

        if subject is not None and self._subjects.size:
            mask = self._subjects == subject.lower()
            sims = np.where(mask, sims, -1.0)

        n = len(sims)
        k = min(k, n)
        if k <= 0:
            return []
        top_idx = np.argpartition(-sims, k - 1)[:k]
        top_idx = top_idx[np.argsort(-sims[top_idx])]
        return [(self.ids[i], float(sims[i])) for i in top_idx if sims[i] > -1.0]

    def __len__(self) -> int:
        return len(self.ids)