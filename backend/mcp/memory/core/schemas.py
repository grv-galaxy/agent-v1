"""
schemas.py
----------
Pydantic schemas for data crossing a process/serialization boundary in
the Long-Term Memory (LTM) system: the raw facts.jsonl extraction
format (ltm_doc.md §3) on the way in, and the FastMCP tool request/
response shapes on the way out (§5, §12).

This module is intentionally separate from models.py:
  - schemas.py  = validated, serializable I/O contracts (Pydantic).
  - models.py   = internal domain objects used between core/ modules
                   that never cross a serialization boundary.

engine.py / deduplicator.py / storage.py do NOT depend on this module —
they work with plain dicts (raw_facts) and their own dataclasses
(CandidateTriple, TripleRow). This module sits at the edges: parsing
facts.jsonl lines, and shaping tools.py's request/response payloads.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

Layer = Literal["factual", "episodic", "semantic"]


# ----------------------------------------------------------------------
# Raw extraction format (ltm_doc.md §3) — one line of facts.jsonl
# ----------------------------------------------------------------------

class FactTriple(BaseModel):
    """Validates one raw triple as written by FIRST_EPOCH_PROMPT /
    ANCHORED_COMPRESSION_PROMPT before it's handed to
    engine.parse_facts(). This is a validation gate, not a storage
    model — once accepted, engine.py converts these into
    CandidateTriple objects (deduplicator.py), not into FactTriple
    instances."""

    subject: str = Field(default="User", min_length=1)
    relation: str = Field(..., min_length=1)
    object: str = Field(..., min_length=1)
    importance: int = Field(default=50, ge=1, le=100)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    layer: Layer = "factual"
    # raw_text: Optional[str] = None
    conversation_id: Optional[str] = None
    message_id: Optional[str] = None

    _BARE_PRONOUNS = {"it", "him", "her", "them", "himself", "herself", "itself", "themselves"}

    @field_validator("object")
    @classmethod
    def reject_bare_pronoun(cls, v: str) -> str:
        # Safety-net re-check of the extraction-prompt rule (§3): the
        # object must carry real meaning. engine.parse_facts() also
        # checks this, but failing fast at the schema boundary means a
        # malformed line never even reaches the pipeline.
        if v.strip().lower() in cls._BARE_PRONOUNS:
            raise ValueError(f"object '{v}' carries no meaning (bare pronoun)")
        return v

    @field_validator("subject", "relation", "object")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        return v.strip()


class FactBatch(BaseModel):
    """A parsed slice of facts.jsonl between the cursor and EOF —
    what server.py hands to engine.run_batch_pipeline() after reading
    + validating raw lines."""

    facts: list[FactTriple]
    start_line: int  # inclusive, 0-indexed into facts.jsonl
    end_line: int     # exclusive
    compression_epoch: Optional[int] = None


# ----------------------------------------------------------------------
# FastMCP tool I/O (ltm_doc.md §5, §12) — used by tools.py
# ----------------------------------------------------------------------

class GetFactsRequest(BaseModel):
    query: str = Field(..., min_length=1)
    layer: Optional[Layer] = None
    subject: Optional[str] = None
    top_k: int = Field(default=5, ge=1, le=50)
    min_confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class RetrievedFactOut(BaseModel):
    id: str
    subject: str
    relation: str
    object: str
    # raw_text: str
    confidence: float
    importance: int
    layer: str
    final_rank_score: float


class GetFactsResponse(BaseModel):
    results: list[RetrievedFactOut]


class ForceSyncResponse(BaseModel):
    """Result of the on-demand 'force sync memory now' tool (§5)."""
    ran: bool
    reason: Optional[str] = None  # e.g. "lock_held", "no_unprocessed_lines"
    inserted: int = 0
    reinforced: int = 0
    contradicted: int = 0
    skipped: int = 0
    lifecycle_counts: dict[str, int] = Field(default_factory=dict)