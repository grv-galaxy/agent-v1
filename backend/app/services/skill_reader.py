"""
skill_reader.py
---------------
Resolves a skill name to its SKILL.md file on disk and returns the content.
Also provides a keyword-based search across the skill registry.
"""

import asyncio
from pathlib import Path
from typing import Optional

# ── Path resolution ────────────────────────────────────────────────────────────
# This file lives at: backend/app/services/skill_reader.py
# So BACKEND_ROOT resolves to:  backend/
_THIS_DIR    = Path(__file__).parent          # backend/app/services/
_BACKEND_ROOT = _THIS_DIR.parent.parent       # backend/

# ── Registry: skill name → absolute Path ───────────────────────────────────────
SKILL_REGISTRY: dict[str, Path] = {
    "docx":      _BACKEND_ROOT / "skills" / "docx" / "SKILL.md",
    "pptx":      _BACKEND_ROOT / "skills" / "pptx" / "SKILL.md",
    "xlsx":      _BACKEND_ROOT / "skills" / "xlsx" / "SKILL.md",
    "pdf":       _BACKEND_ROOT / "skills" / "pdf"  / "SKILL.md",
    "user_data": _BACKEND_ROOT / "data"   / "user" / "user_data.md",
}

# ── Short descriptions for search ─────────────────────────────────────────────
SKILL_DESCRIPTIONS: dict[str, str] = {
    "docx":      "Create, edit, or read Word documents (.docx) — formatting, tables, headers/footers.",
    "pptx":      "Create or edit PowerPoint presentations (.pptx) — slides, charts, speaker notes.",
    "xlsx":      "Create, edit, or analyze Excel spreadsheets (.xlsx, .csv) — formulas, charts, pivot tables.",
    "pdf":       "Create, read, merge, split, or watermark PDF files — OCR, forms, encryption.",
    "user_data": "Access user profile information, preferences, and background.",
}


async def read_skill(skill_name: str) -> Optional[str]:
    """
    Reads and returns the markdown content of the requested skill file.

    Args:
        skill_name: Key from SKILL_REGISTRY (e.g. 'pdf', 'docx').

    Returns:
        Raw markdown string, or None if the skill is unknown or file not found.
    """
    skill_path = SKILL_REGISTRY.get(skill_name.lower().strip())

    if skill_path is None:
        print(f"[skill_reader] Unknown skill: '{skill_name}'")
        return None

    if not skill_path.exists():
        print(f"[skill_reader] Skill file not found at: {skill_path}")
        return None

    # Run blocking I/O in a thread so we don't block the event loop
    loop = asyncio.get_event_loop()
    content = await loop.run_in_executor(None, skill_path.read_text, "utf-8")
    print(f"[skill_reader] Loaded skill '{skill_name}' ({len(content)} chars) from {skill_path}")
    return content


def search_skills(keywords: list[str]) -> list[str]:
    """
    Simple keyword search across skill names and descriptions.

    Args:
        keywords: List of keyword strings to search for.

    Returns:
        List of matching skill names (may be empty).
    """
    if not keywords:
        return list(SKILL_REGISTRY.keys())

    keywords_lower = [kw.lower() for kw in keywords]
    matches = []

    for name, description in SKILL_DESCRIPTIONS.items():
        combined = f"{name} {description}".lower()
        if any(kw in combined for kw in keywords_lower):
            matches.append(name)

    return matches


def list_skills() -> dict[str, str]:
    """Returns all registered skills with their descriptions."""
    return dict(SKILL_DESCRIPTIONS)
