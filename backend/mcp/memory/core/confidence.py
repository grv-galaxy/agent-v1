"""
confidence.py
-------------
Confidence score management for the Long-Term Memory (LTM) system
(ltm_doc.md §8e).

This is the SINGLE place the two confidence formulas live:

  - Reinforcement (asymmetric, diminishing returns toward 1.0):
        confidence = confidence + (1 - confidence) * REINFORCE_RATE
  - Contradiction penalty (heavier than the reinforcement gain):
        confidence = confidence * CONTRADICTION_PENALTY

deduplicator.py and contradiction.py import these functions rather than
each defining their own copy of the math, so the constants only ever
need tuning in one place (ltm_doc.md §14/§16: "tune thresholds ...
against real usage").

This module also turns dedup CLASSIFICATIONS into the concrete batched
update tuples storage.py expects (bulk_reinforce), so engine.py doesn't
have to know the formula itself — it just calls
build_reinforcement_updates() and passes the result straight to
storage.bulk_reinforce().
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import storage
from deduplicator import DedupOutcome, DedupResult

# Tunable constants (ltm_doc.md §8e, §14, §16)
REINFORCE_RATE = 0.2
CONTRADICTION_PENALTY = 0.5


# ----------------------------------------------------------------------
# Pure formulas
# ----------------------------------------------------------------------

def reinforce(old_confidence: float, rate: float = REINFORCE_RATE) -> float:
    """Diminishing returns toward 1.0 — repeated reinforcement of an
    already-high-confidence fact has less and less effect."""
    return old_confidence + (1.0 - old_confidence) * rate


def penalize(old_confidence: float, penalty: float = CONTRADICTION_PENALTY) -> float:
    """Heavier than the reinforcement gain on purpose, so a single
    contradiction meaningfully demotes the old fact's rank without
    erasing it outright."""
    return old_confidence * penalty


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ----------------------------------------------------------------------
# Batch update builder — turns classifications into storage.py-ready tuples
# ----------------------------------------------------------------------

def build_reinforcement_updates(
    conn,
    dedup_results: list[DedupResult],
) -> list[tuple[str, float, str, str]]:
    """
    Build the update tuples for storage.bulk_reinforce() from every
    REINFORCE / SEMANTIC_MATCH / CROSS_NAMESPACE_MATCH result in a dedup
    batch — one lookup of all matched rows (ONE query, not N), one pass
    to compute new confidence + append the raw-text variant, ready for a
    single bulk_reinforce() call.

    Returns: list of (id, new_confidence, raw_text_variants_json, last_seen)
    """
    reinforce_results = [
        r for r in dedup_results
        if r.outcome in (
            DedupOutcome.REINFORCE,
            DedupOutcome.SEMANTIC_MATCH,
            DedupOutcome.CROSS_NAMESPACE_MATCH,
        )
        and r.matched_id is not None
    ]
    if not reinforce_results:
        return []

    matched_ids = list({r.matched_id for r in reinforce_results})
    existing_rows = storage.get_by_ids(conn, matched_ids)

    now = _now_iso()
    updates: list[tuple[str, float, str, str]] = []
    for r in reinforce_results:
        existing = existing_rows.get(r.matched_id)
        if existing is None:
            # Matched id vanished between dedup and here (shouldn't happen
            # within a single pipeline run, but don't crash the whole
            # batch over one inconsistent row).
            continue

        new_confidence = reinforce(existing.confidence)
        variants = existing.raw_text_variants
        if r.candidate.raw_text not in variants:
            variants = variants + [r.candidate.raw_text]

        updates.append(
            (r.matched_id, new_confidence, json.dumps(variants), now)
        )

    return updates