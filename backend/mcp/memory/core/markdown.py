"""
markdown.py
-----------
Incremental markdown projection writer (ltm_doc.md §11, §11.1).

SQLite is the single source of truth; these files are a generated,
human/model-readable projection — regenerated from SQLite, never
edited independently. This module only re-renders the sections/files
that engine.py's PipelineSummary.dirty_triple_ids actually touched this
run, not a full table scan every pass (§11.1).

NOTE on section classification: ltm_doc.md §17 flags the "OKF
architecture" reference for markdown structure as an open item never
clarified. classify_dirty_sections() below is a relation-keyword
heuristic standing in for that until it's resolved — it is the
placeholder structure the doc itself describes as provisional (§11),
not a finalized design. Update RELATION_SECTION_MAP first if/when that
gets clarified.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from memory import config
from . import storage
from .models import DirtySection, DirtySet, SectionKind

# ----------------------------------------------------------------------
# Relation -> section classification (placeholder, see module docstring)
# ----------------------------------------------------------------------

IDENTITY_RELATIONS = {"name", "lives_in", "born_in", "age", "occupation", "employed_by", "speaks"}
PREFERENCE_RELATIONS = {"likes", "dislikes", "prefers_not", "favorite_of"}
RELATIONSHIP_RELATIONS = {"married_to", "parent_of", "child_of", "sibling_of", "friend_of", "knows", "works_with"}
# Anything not in the three sets above, on an episodic-layer triple,
# is treated as task-progress and routed to a per-task file instead of
# user_data.md. The object is used as the task slug.
TASK_PROGRESS_RELATIONS = {"started", "working_on", "blocked_on", "completed", "paused"}
TASK_COMPLETION_RELATIONS = {"completed"}


def _slugify(text: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in text.strip().lower()).strip("_")


def classify_dirty_sections(conn, dirty_triple_ids: list[str]) -> DirtySet:
    """Look up just the dirty rows (cheap, id IN (...) — same pattern as
    storage.get_by_ids) and bucket each into the section(s) it affects.
    This is what turns engine.py's flat dirty_triple_ids list into the
    section-level diff markdown.project_markdown_incremental() needs."""
    if not dirty_triple_ids:
        return DirtySet(sections=set())

    rows = storage.get_by_ids(conn, dirty_triple_ids)
    sections: set[DirtySection] = set()
    for row in rows.values():
        relation = row.relation.lower()
        if relation in IDENTITY_RELATIONS:
            sections.add(DirtySection(SectionKind.IDENTITY))
        elif relation in PREFERENCE_RELATIONS:
            sections.add(DirtySection(SectionKind.PREFERENCES))
        elif relation in RELATIONSHIP_RELATIONS:
            sections.add(DirtySection(SectionKind.RELATIONSHIPS))
        elif row.layer == "episodic" and relation in TASK_PROGRESS_RELATIONS:
            sections.add(DirtySection(SectionKind.TASK, task_slug=_slugify(row.object)))
        # else: relation doesn't map to a known section yet (placeholder
        # heuristic, see module docstring) — skipped, not an error.

    return DirtySet(sections=sections)


# ----------------------------------------------------------------------
# Rendering helpers
# ----------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _bullet_lines(rows: list[storage.TripleRow]) -> str:
    lines = []
    for r in sorted(rows, key=lambda r: (-r.importance, r.relation)):
        lines.append(f"- {r.relation.replace('_', ' ')}: {r.object} (confidence: {r.confidence:.2f})")
    return "\n".join(lines) if lines else "- (none recorded yet)"


def _splice_section(doc: str, heading: str, body: str) -> str:
    """Replace the content under `## {heading}` up to the next `## ` or
    EOF, preserving everything else in the file untouched. If the
    heading doesn't exist yet, append it."""
    marker = f"## {heading}"
    start = doc.find(marker)
    new_block = f"{marker}\n{body}\n"
    if start == -1:
        return doc.rstrip() + "\n\n" + new_block
    after_heading = start + len(marker)
    next_heading = doc.find("\n## ", after_heading)
    end = next_heading if next_heading != -1 else len(doc)
    return doc[:start] + new_block + doc[end:].lstrip("\n")


def _active_relations(conn, relation_set: set[str]) -> list[storage.TripleRow]:
    all_active = storage.get_all_metadata(conn, status="active")
    return [r for r in all_active if r.relation.lower() in relation_set]


# ----------------------------------------------------------------------
# user_data.md (Identity / Preferences / Relationships)
# ----------------------------------------------------------------------

def _read_or_init_user_data_md() -> str:
    if config.USER_DATA_MD.exists():
        return config.USER_DATA_MD.read_text(encoding="utf-8")
    return (
        "---\n"
        "entity: User\n"
        f"last_updated: {_now_iso()}\n"
        "source_facts: []\n"
        "---\n"
    )


def _write_user_data_md(conn, sections: set[SectionKind]) -> None:
    doc = _read_or_init_user_data_md()

    if SectionKind.IDENTITY in sections:
        rows = _active_relations(conn, IDENTITY_RELATIONS)
        doc = _splice_section(doc, "Identity", _bullet_lines(rows))
    if SectionKind.PREFERENCES in sections:
        rows = _active_relations(conn, PREFERENCE_RELATIONS)
        doc = _splice_section(doc, "Preferences", _bullet_lines(rows))
    if SectionKind.RELATIONSHIPS in sections:
        rows = _active_relations(conn, RELATIONSHIP_RELATIONS)
        doc = _splice_section(doc, "Relationships", _bullet_lines(rows))

    # Update the metadata header's last_updated timestamp.
    if doc.startswith("---\n"):
        end_of_header = doc.find("\n---\n", 4)
        if end_of_header != -1:
            header = doc[: end_of_header + 5]
            import re

            header = re.sub(r"last_updated: .*", f"last_updated: {_now_iso()}", header)
            doc = header + doc[end_of_header + 5 :]

    config.USER_DATA_MD.write_text(doc, encoding="utf-8")


# ----------------------------------------------------------------------
# Task files (active_<task>.md / archive_<task>.md) — §11 task lifecycle
# ----------------------------------------------------------------------

def _task_path(task_slug: str, archived: bool) -> Path:
    if archived:
        return config.TASK_ARCHIVE_DIR / f"archive_{task_slug}.md"
    return config.TASK_DIR / f"active_{task_slug}.md"


def _render_task_md(task_slug: str, rows: list[storage.TripleRow], status: str) -> str:
    progress_lines = "\n".join(f"- {r.relation}: {r.object}" for r in rows) or "- (no progress recorded)"
    return (
        "---\n"
        f'task: "{task_slug}"\n'
        f"status: {status}\n"
        f"created: {min((r.first_seen or _now_iso()) for r in rows) if rows else _now_iso()}\n"
        f"last_updated: {_now_iso()}\n"
        "---\n"
        "## Goal\n"
        f"- {task_slug.replace('_', ' ')}\n"
        "## Progress\n"
        f"{progress_lines}\n"
        "## Open Questions\n"
        "- (none recorded)\n"
    )


def _write_task_md(conn, task_slug: str) -> None:
    """Re-render one task file from its episodic triples. If a
    `completed` triple exists for this task, move it from
    active_<task>.md to archive/archive_<task>.md per §11's task
    lifecycle rule, removing the stale active file."""
    all_active = storage.get_all_metadata(conn, status="active")
    task_rows = [
        r for r in all_active
        if r.layer == "episodic"
        and r.relation.lower() in TASK_PROGRESS_RELATIONS
        and _slugify(r.object) == task_slug
    ]
    is_completed = any(r.relation.lower() in TASK_COMPLETION_RELATIONS for r in task_rows)

    status = "archived" if is_completed else "active"
    content = _render_task_md(task_slug, task_rows, status)

    target = _task_path(task_slug, archived=is_completed)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")

    if is_completed:
        stale_active = _task_path(task_slug, archived=False)
        if stale_active.exists():
            stale_active.unlink()


# ----------------------------------------------------------------------
# Entry point
# ----------------------------------------------------------------------

def project_markdown_incremental(conn, dirty: DirtySet) -> None:
    """ltm_doc.md §11.1 — only re-render the sections/files this run's
    dirty_triple_ids actually touched. O(facts changed), not
    O(total facts in store)."""
    if dirty.is_empty():
        return

    user_data_kinds = {
        s.kind for s in dirty.sections
        if s.kind in (SectionKind.IDENTITY, SectionKind.PREFERENCES, SectionKind.RELATIONSHIPS)
    }
    if user_data_kinds:
        _write_user_data_md(conn, user_data_kinds)

    for task_slug in dirty.task_slugs():
        _write_task_md(conn, task_slug)