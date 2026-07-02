"""
models.py
---------
Internal domain objects used BETWEEN core/ modules — distinct from
schemas.py (external I/O contracts) and from the per-module dataclasses
that already live where they're owned (CandidateTriple/DedupResult in
deduplicator.py, TripleRow in storage.py, ContradictionResult in
contradiction.py).

This module exists for objects that don't belong to any single owning
module because they're produced by one module and consumed by another
that shouldn't need to import the producer's internals just to use the
shape:

  - DirtySection / DirtySet : produced by engine.py (via
    classify_dirty_sections in markdown.py) from PipelineSummary.dirty_triple_ids,
    consumed by markdown.py's incremental projection writer (§11.1).
  - RankedFact : produced by retrieval.py's get_facts(), the shape
    handed back to the main app process (read-only, §12).

Nothing here owns SQL, embedding, or scoring logic — it's pure data.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


# ----------------------------------------------------------------------
# Markdown projection (ltm_doc.md §11, §11.1)
# ----------------------------------------------------------------------

class SectionKind(str, Enum):
    IDENTITY = "identity"
    PREFERENCES = "preferences"
    RELATIONSHIPS = "relationships"
    TASK = "task"  # parametrized by task_slug, see DirtySection.task_slug


@dataclass(frozen=True)
class DirtySection:
    """One section/file that needs re-rendering this run. For TASK
    sections, task_slug identifies which active_<task>.md / archive_<task>.md
    pair is affected; for the other kinds it's None (they all live inside
    the single user_data.md)."""

    kind: SectionKind
    task_slug: str | None = None

    def __hash__(self) -> int:
        return hash((self.kind, self.task_slug))


@dataclass
class DirtySet:
    """Output of markdown.classify_dirty_sections() — the set of
    sections engine.py's dirty_triple_ids touched this run, ready to
    hand to markdown.project_markdown_incremental()."""

    sections: set[DirtySection]

    def is_empty(self) -> bool:
        return not self.sections

    def task_slugs(self) -> list[str]:
        return [s.task_slug for s in self.sections if s.kind == SectionKind.TASK and s.task_slug]


# ----------------------------------------------------------------------
# Retrieval (ltm_doc.md §12)
# ----------------------------------------------------------------------

@dataclass
class RankedFact:
    """One triple returned from retrieval.get_facts(), already carrying
    its computed final_rank_score so tools.py doesn't need to recompute
    or know the ranking formula."""

    id: str
    subject: str
    relation: str
    object: str
    # raw_text: str
    confidence: float
    importance: int
    layer: str
    final_rank_score: float