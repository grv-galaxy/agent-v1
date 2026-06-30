"""
importance.py
--------------
Importance, frequency, and decay scoring POLICY for the Long-Term
Memory (LTM) system (ltm_doc.md §8f, §8g).

storage.py already implements the SQL mechanics for the lifecycle sweep
(sweep_lifecycle) and decay recompute (recompute_decay_scores) as single
batched UPDATE statements. This module owns the actual POLICY values
those mechanics run on — the tunable constants and the small amount of
non-SQL logic (e.g. classifying extraction-time importance) that doesn't
belong inside storage.py's pure-mechanics layer.

Two knobs, never conflated (ltm_doc.md §8f):
  - IMPORTANCE : set once at extraction time (LLM-assigned prior).
                 Gates whether a fact can ever be purged. High-importance
                 facts are NEVER purged, only archived.
  - FREQUENCY  : reinforcement count, owned by confidence.py's
                 build_reinforcement_updates() / storage.bulk_reinforce().
                 Used only for ranking within retained facts, never for
                 deciding what to keep.

DECAY SCORE is derived (recency * frequency_weight * confidence),
computed by storage.recompute_decay_scores() and used only for ranking/
lifecycle decisions, never as a gate on its own.
"""

from __future__ import annotations

from dataclasses import dataclass

import storage

# ----------------------------------------------------------------------
# Importance bands (ltm_doc.md §3 — LLM-assigned prior at extraction time)
# ----------------------------------------------------------------------
# Identity / stable facts = 80-100, one-off events/trivia = 1-20.
# These bands are reference points for validating/clamping LLM output,
# not a re-scoring step — the LLM sets the actual value at extraction.

IMPORTANCE_HIGH = 80     # identity / stable facts — never purged
IMPORTANCE_MEDIUM = 40   # general preferences / recurring facts
IMPORTANCE_LOW = 20      # one-off events / trivia — eligible for purge

PURGE_IMPORTANCE_THRESHOLD = 20  # storage.sweep_lifecycle() purge cutoff


def clamp_importance(value: int) -> int:
    """Defensive clamp in case the LLM returns something outside 1-100 —
    never trust extraction output blindly when it gates a destructive
    operation (purge eligibility)."""
    return max(1, min(100, int(value)))


def is_purge_eligible(importance: int) -> bool:
    """High-importance facts are NEVER purged, only archived
    (ltm_doc.md §8g). This is the single source of truth for that gate —
    storage.sweep_lifecycle() is called with this threshold, never a
    hardcoded value duplicated elsewhere."""
    return clamp_importance(importance) < PURGE_IMPORTANCE_THRESHOLD


# ----------------------------------------------------------------------
# Lifecycle sweep policy (ltm_doc.md §8g)
# ----------------------------------------------------------------------
# Episodic facts (one-off events) go dormant/archived faster than
# factual facts (stable identity/preference info). Semantic facts sit
# in between. These are starting points per the doc's "tune empirically"
# guidance (§14/§16) — adjust against real usage.

@dataclass(frozen=True)
class LifecyclePolicy:
    dormant_after_days: dict[str, int]
    archive_after_days: dict[str, int]
    purge_importance_threshold: int = PURGE_IMPORTANCE_THRESHOLD


DEFAULT_LIFECYCLE_POLICY = LifecyclePolicy(
    dormant_after_days={
        "episodic": 14,
        "semantic": 30,
        "factual": 90,
    },
    archive_after_days={
        "episodic": 28,   # 2x dormant window, per §8g
        "semantic": 60,
        "factual": 180,
    },
    purge_importance_threshold=PURGE_IMPORTANCE_THRESHOLD,
)


def run_lifecycle_sweep(conn, policy: LifecyclePolicy = DEFAULT_LIFECYCLE_POLICY) -> dict[str, int]:
    """Thin wrapper around storage.sweep_lifecycle() so callers (engine.py)
    depend on a policy object here rather than hardcoding day thresholds
    at the call site. Runs every job, over the WHOLE store, not just the
    newly ingested batch (ltm_doc.md §8g)."""
    return storage.sweep_lifecycle(
        conn,
        dormant_after_days=policy.dormant_after_days,
        archive_after_days=policy.archive_after_days,
        purge_importance_threshold=policy.purge_importance_threshold,
    )


# ----------------------------------------------------------------------
# Decay score policy (ltm_doc.md §8f)
# ----------------------------------------------------------------------

DEFAULT_FREQUENCY_WEIGHT = 0.1  # weight applied to frequency in decay_score


def recompute_decay_scores(conn, frequency_weight: float = DEFAULT_FREQUENCY_WEIGHT) -> None:
    """Thin wrapper, same rationale as run_lifecycle_sweep() above —
    keeps the tunable constant here instead of inline at every call site."""
    storage.recompute_decay_scores(conn, frequency_weight=frequency_weight)


# ----------------------------------------------------------------------
# Retrieval ranking weight (ltm_doc.md §12 — used by retrieval.py)
# ----------------------------------------------------------------------

def success_rate(successful_answer_count: int, retrieval_count: int) -> float:
    """successful_answer_count / max(retrieval_count, 1) — exposed here
    since it's part of the same "how do we weigh a fact" policy family,
    even though the actual re-rank formula lives in retrieval.py."""
    return successful_answer_count / max(retrieval_count, 1)