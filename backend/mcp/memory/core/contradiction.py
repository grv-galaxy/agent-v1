"""
contradiction.py
-----------------
Contradiction detection for the Long-Term Memory (LTM) system
(ltm_doc.md §8c).

Rule: same subject + relation, different object -> the OLD fact's
confidence is penalized (not deleted), the NEW fact is inserted with its
own confidence, and BOTH are kept. Recency + confidence decide which one
surfaces at retrieval time. This deliberately handles facts that
genuinely change over time (e.g. "User lives_in Mumbai" later becoming
"User lives_in Delhi") without treating the new statement as an error or
silently overwriting history.

Scope: this module only runs against candidates that deduplicator.py
already classified as DedupOutcome.NEW — a REINFORCE or SEMANTIC_MATCH
candidate is, by definition, the SAME fact as something already stored,
so it cannot also be a contradiction of it. Only genuinely new facts can
contradict an existing one.

This module does NOT write to the database — it classifies and computes
the penalty value; engine.py wires the actual storage.bulk_contradict()
and storage.bulk_insert() calls using these results.
"""

from __future__ import annotations

from dataclasses import dataclass

import storage
import confidence
from deduplicator import CandidateTriple, DedupOutcome, DedupResult


@dataclass
class ContradictionResult:
    candidate: CandidateTriple
    contradicted_ids: list[str]          # existing rows this candidate contradicts (usually 0 or 1, can be >1)
    old_confidence_updates: list[tuple[str, float]]  # (existing_id, penalized_confidence)

    @property
    def is_contradiction(self) -> bool:
        return bool(self.contradicted_ids)


# ----------------------------------------------------------------------
# Main entry point
# ----------------------------------------------------------------------

def check_batch(
    conn,
    new_results: list[DedupResult],
) -> list[ContradictionResult]:
    """
    Run the contradiction check over a batch of dedup results. Only
    candidates with outcome == NEW are checked (see module docstring for
    why). For each, look up existing ACTIVE rows sharing the same
    subject + relation (one indexed query per candidate, hitting
    idx_subj_rel — see storage.get_by_subject_relation) and flag any
    whose object differs as a contradiction.

    Note: this still issues one query per distinct (subject, relation)
    pair rather than a single batched query, because SQLite has no clean
    way to batch "group of (subject, relation) pairs -> matching rows"
    without building a temp table. In practice the NEW group per pipeline
    run is small (a handful of genuinely new facts out of a batch), so
    this stays cheap; if NEW batches ever grow large, switch this to a
    single query against a temp table of (subject, relation) pairs.
    """
    new_candidates = [r for r in new_results if r.outcome == DedupOutcome.NEW]
    if not new_candidates:
        return []

    # Avoid re-querying the same (subject, relation) pair twice within
    # one batch (e.g. two new facts about the same subject+relation
    # landing in the same pipeline run).
    seen_pairs: dict[tuple[str, str], list[storage.TripleRow]] = {}

    results: list[ContradictionResult] = []
    for dedup_result in new_candidates:
        cand = dedup_result.candidate
        key = (cand.subject.lower(), cand.relation.lower())

        if key not in seen_pairs:
            seen_pairs[key] = storage.get_by_subject_relation(
                conn, cand.subject, cand.relation
            )
        existing_rows = seen_pairs[key]

        contradicted_ids: list[str] = []
        updates: list[tuple[str, float]] = []
        for row in existing_rows:
            if row.object.strip().lower() != cand.object.strip().lower():
                contradicted_ids.append(row.id)
                updates.append((row.id, confidence.penalize(row.confidence)))

        results.append(
            ContradictionResult(
                candidate=cand,
                contradicted_ids=contradicted_ids,
                old_confidence_updates=updates,
            )
        )

    return results


def collect_confidence_updates(
    contradiction_results: list[ContradictionResult],
) -> list[tuple[str, float]]:
    """Flatten all old-fact penalty updates across the batch into a single
    list, ready for ONE storage.bulk_contradict() call (ltm_doc.md §8,
    step 10 — single transaction, not commit-per-row)."""
    updates: list[tuple[str, float]] = []
    for r in contradiction_results:
        updates.extend(r.old_confidence_updates)
    return updates