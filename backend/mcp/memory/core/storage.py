"""
storage.py
----------
SQLite metadata storage layer for the Long-Term Memory (LTM) system.

Responsibilities (per ltm_doc.md §9.1):
  - Own the `triples` table (metadata) — embeddings live in vector_store.py,
    NOT here, so metadata-only reads (markdown projection, lifecycle sweep,
    inspection/debug tools) never drag 384-float vectors along with them.
  - Apply WAL mode + indexes so subject/relation/status lookups hit an
    index instead of a full table scan.
  - Expose batch-first operations only: callers should never loop and
    call single-row methods per triple — every method here is designed
    to take a whole batch and do ONE query / ONE transaction.

This module deliberately has zero knowledge of embeddings, dedup logic,
or the markdown projection — it is the storage layer only. Orchestration
lives in engine.py.
"""

from __future__ import annotations

import sqlite3
import json
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Iterator


# ----------------------------------------------------------------------
# Schema
# ----------------------------------------------------------------------

SCHEMA_SQL = """
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;

CREATE TABLE IF NOT EXISTS triples (
    id                      TEXT PRIMARY KEY,      -- hash(subject, relation, object)
    subject                 TEXT NOT NULL,
    relation                TEXT NOT NULL,
    object                  TEXT NOT NULL,
    raw_text_variants       TEXT,                   -- JSON array of strings
    layer                   TEXT,                   -- factual | episodic | semantic
    confidence              REAL,
    importance              INTEGER,
    frequency               INTEGER DEFAULT 1,
    decay_score             REAL,
    retrieval_count         INTEGER DEFAULT 0,
    successful_answer_count INTEGER DEFAULT 0,
    status                  TEXT DEFAULT 'active',  -- active | dormant | archived
    conversation_id         TEXT,
    message_ids             TEXT,                   -- JSON array, provenance
    compression_epoch       INTEGER,
    extractor_version       TEXT,
    first_seen              TEXT,
    last_seen               TEXT,
    last_used                TEXT
);

CREATE INDEX IF NOT EXISTS idx_subject  ON triples(subject COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS idx_relation ON triples(relation COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS idx_status   ON triples(status);
CREATE INDEX IF NOT EXISTS idx_subj_rel ON triples(subject COLLATE NOCASE, relation COLLATE NOCASE);
"""


# ----------------------------------------------------------------------
# Data model
# ----------------------------------------------------------------------

@dataclass
class TripleRow:
    """One row of the `triples` table, as a typed convenience wrapper."""
    id: str
    subject: str
    relation: str
    object: str
    raw_text_variants: list[str] = field(default_factory=list)
    layer: str = "factual"
    confidence: float = 0.5
    importance: int = 50
    frequency: int = 1
    decay_score: float = 0.0
    retrieval_count: int = 0
    successful_answer_count: int = 0
    status: str = "active"
    conversation_id: str | None = None
    message_ids: list[str] = field(default_factory=list)
    compression_epoch: int | None = None
    extractor_version: str | None = None
    first_seen: str | None = None
    last_seen: str | None = None
    last_used: str | None = None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "TripleRow":
        d = dict(row)
        d["raw_text_variants"] = json.loads(d["raw_text_variants"] or "[]")
        d["message_ids"] = json.loads(d["message_ids"] or "[]")
        return cls(**d)

    def to_insert_tuple(self) -> tuple:
        return (
            self.id, self.subject, self.relation, self.object,
            json.dumps(self.raw_text_variants), self.layer,
            self.confidence, self.importance, self.frequency,
            self.decay_score, self.retrieval_count, self.successful_answer_count,
            self.status, self.conversation_id, json.dumps(self.message_ids),
            self.compression_epoch, self.extractor_version,
            self.first_seen, self.last_seen, self.last_used,
        )


# ----------------------------------------------------------------------
# Connection management
# ----------------------------------------------------------------------

def connect(db_path: str | Path) -> sqlite3.Connection:
    """Open a connection with the schema applied. Safe to call every run —
    CREATE TABLE/INDEX IF NOT EXISTS makes this idempotent."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA_SQL)
    return conn


@contextmanager
def transaction(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """One transaction, one commit — wrap a whole batch of writes in this,
    never call conn.commit() per row (ltm_doc.md §8, step 10)."""
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


# ----------------------------------------------------------------------
# Batch reads
# ----------------------------------------------------------------------

def get_by_ids(conn: sqlite3.Connection, ids: list[str]) -> dict[str, TripleRow]:
    """Structural-dedup check for a whole batch in ONE query
    (ltm_doc.md §8a) instead of one SELECT per candidate id."""
    if not ids:
        return {}
    placeholders = ",".join("?" * len(ids))
    rows = conn.execute(
        f"SELECT * FROM triples WHERE id IN ({placeholders})", ids
    ).fetchall()
    return {r["id"]: TripleRow.from_row(r) for r in rows}


def get_by_subject_relation(
    conn: sqlite3.Connection, subject: str, relation: str
) -> list[TripleRow]:
    """Used for the contradiction check (§8c). Hits idx_subj_rel."""
    rows = conn.execute(
        "SELECT * FROM triples WHERE subject = ? COLLATE NOCASE "
        "AND relation = ? COLLATE NOCASE AND status = 'active'",
        (subject, relation),
    ).fetchall()
    return [TripleRow.from_row(r) for r in rows]


def get_active_ids_and_subjects(conn: sqlite3.Connection) -> list[tuple[str, str]]:
    """Lightweight metadata-only read (no vectors) used to build the
    subject-namespace mask for the in-memory embedding cache."""
    rows = conn.execute(
        "SELECT id, subject FROM triples WHERE status = 'active'"
    ).fetchall()
    return [(r["id"], r["subject"]) for r in rows]


def get_all_metadata(conn: sqlite3.Connection, status: str | None = None) -> list[TripleRow]:
    """Metadata-only fetch (no embeddings) — used by markdown projection
    and the lifecycle sweep. Cheap because embeddings live elsewhere."""
    if status:
        rows = conn.execute(
            "SELECT * FROM triples WHERE status = ?", (status,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM triples").fetchall()
    return [TripleRow.from_row(r) for r in rows]


# ----------------------------------------------------------------------
# Batch writes — one transaction, executemany, never commit-per-row
# ----------------------------------------------------------------------

def bulk_insert(conn: sqlite3.Connection, rows: list[TripleRow]) -> None:
    if not rows:
        return
    with transaction(conn):
        conn.executemany(
            """
            INSERT INTO triples (
                id, subject, relation, object, raw_text_variants, layer,
                confidence, importance, frequency, decay_score,
                retrieval_count, successful_answer_count, status,
                conversation_id, message_ids, compression_epoch,
                extractor_version, first_seen, last_seen, last_used
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            [r.to_insert_tuple() for r in rows],
        )


def bulk_reinforce(
    conn: sqlite3.Connection, updates: list[tuple[str, float, str, str]]
) -> None:
    """updates: list of (id, new_confidence, raw_text_variants_json, last_seen)
    Used for structural/semantic-match reinforcement (§8e)."""
    if not updates:
        return
    with transaction(conn):
        conn.executemany(
            """
            UPDATE triples
            SET frequency = frequency + 1,
                confidence = ?,
                raw_text_variants = ?,
                last_seen = ?
            WHERE id = ?
            """,
            [(conf, variants, last_seen, _id) for _id, conf, variants, last_seen in updates],
        )


def bulk_contradict(conn: sqlite3.Connection, updates: list[tuple[str, float]]) -> None:
    """updates: list of (id, new_confidence) — penalize old facts (§8c, §8e)."""
    if not updates:
        return
    with transaction(conn):
        conn.executemany(
            "UPDATE triples SET confidence = ? WHERE id = ?",
            [(conf, _id) for _id, conf in updates],
        )


def bulk_touch_retrieval(conn: sqlite3.Connection, ids: list[str]) -> None:
    """Increment retrieval_count + last_used for facts returned by
    get_facts() (§12, step 5) — one batched update, not per-row."""
    if not ids:
        return
    with transaction(conn):
        conn.executemany(
            "UPDATE triples SET retrieval_count = retrieval_count + 1, "
            "last_used = ? WHERE id = ?",
            [(_now_iso(), _id) for _id in ids],
        )


# ----------------------------------------------------------------------
# Lifecycle sweep (§8g) — single batched SQL operation, not a Python loop
# ----------------------------------------------------------------------

def sweep_lifecycle(
    conn: sqlite3.Connection,
    *,
    dormant_after_days: dict[str, int],
    archive_after_days: dict[str, int],
    purge_importance_threshold: int = 20,
) -> dict[str, int]:
    """
    active -> dormant -> archived -> purged, run every job (not just on
    new facts). dormant_after_days / archive_after_days are keyed by
    `layer` (episodic gets a short window, factual a long one), per
    ltm_doc.md §8g.

    Returns counts of rows affected per transition, for logging.
    """
    counts = {"dormant": 0, "archived": 0, "purged": 0}
    with transaction(conn):
        for layer, days in dormant_after_days.items():
            cur = conn.execute(
                """
                UPDATE triples SET status = 'dormant'
                WHERE status = 'active' AND layer = ?
                  AND julianday('now') - julianday(last_used) > ?
                """,
                (layer, days),
            )
            counts["dormant"] += cur.rowcount

        for layer, days in archive_after_days.items():
            cur = conn.execute(
                """
                UPDATE triples SET status = 'archived'
                WHERE status = 'dormant' AND layer = ?
                  AND julianday('now') - julianday(last_used) > ?
                """,
                (layer, days),
            )
            counts["archived"] += cur.rowcount

        # Purge ONLY low-importance archived facts. High-importance facts
        # are NEVER purged, only archived (kept for audit/history).
        cur = conn.execute(
            "DELETE FROM triples WHERE status = 'archived' AND importance < ?",
            (purge_importance_threshold,),
        )
        counts["purged"] += cur.rowcount

    return counts


def recompute_decay_scores(
    conn: sqlite3.Connection, frequency_weight: float = 0.1
) -> None:
    """decay_score = recency * frequency_weight * confidence (§8f).
    Computed in one batched UPDATE using SQLite's own date math,
    not a Python loop over rows."""
    with transaction(conn):
        conn.execute(
            """
            UPDATE triples
            SET decay_score = (
                (1.0 / (1.0 + (julianday('now') - julianday(last_used)))) *
                (1.0 + ? * frequency) *
                confidence
            )
            WHERE status = 'active'
            """,
            (frequency_weight,),
        )


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------

def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def make_id(subject: str, relation: str, obj: str) -> str:
    """hash(subject, relation, object) — the structural-match key (§8a)."""
    import hashlib
    key = f"{subject.strip().lower()}|{relation.strip().lower()}|{obj.strip().lower()}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]