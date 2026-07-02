"""
config.py
---------
Central configuration for the Long-Term Memory (LTM) MCP server
(ltm_doc.md §4, §5, §6, §7, §10, §11).

This is the ONLY place filesystem paths and process-level tunables are
defined. server.py / handlers.py / markdown.py / engine.py's caller all
import from here rather than hardcoding paths, so there's a single
source of truth for where the lock file, cursor file, logs, and
markdown projections live.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

# ----------------------------------------------------------------------
# Root paths and explicit backend/data directory configuration
# ----------------------------------------------------------------------

_CURRENT_FILE = Path(__file__).resolve()

# Dynamically scan upwards to find the true 'backend' directory root
_BACKEND_ROOT = None
for parent in _CURRENT_FILE.parents:
    if parent.name == "backend":
        _BACKEND_ROOT = parent
        break

# Fallback mechanism if 'backend' is not explicitly found in parent hierarchy
if _BACKEND_ROOT is None:
    # If nested deep inside mcp/memory/core, go up to backend
    _BACKEND_ROOT = _CURRENT_FILE.parents[3] if "core" in _CURRENT_FILE.parts else _CURRENT_FILE.parents[2]

# Force the data directory to live strictly inside backend/data/
DATA_DIR = Path(os.environ.get("LTM_DATA_DIR", _BACKEND_ROOT / "data"))

# Target database name inside backend/data/ folder
DB_PATH = DATA_DIR / "ltm_memory.db"

FACTS_DIR = DATA_DIR / "facts"
FACTS_JSONL_PATH = FACTS_DIR / "facts.jsonl"

LOCKS_DIR = DATA_DIR / "locks"
CURSORS_DIR = DATA_DIR / "cursors"
LOGS_DIR = DATA_DIR / "logs" / "ltm"
USER_DIR = DATA_DIR / "user"
TASK_DIR = DATA_DIR / "task"
ARCHIVE_DIR = DATA_DIR / "archieve"
TASK_ARCHIVE_DIR = ARCHIVE_DIR / "tasks"

LOCK_FILE = LOCKS_DIR / "memory_manager.lock"
CURSOR_FILE = CURSORS_DIR / "facts_cursor.json"
USER_DATA_MD = USER_DIR / "user_data.md"

# Compatibility aliases used by older entry points and test clients
LOCK_PATH = LOCK_FILE
CURSOR_PATH = CURSOR_FILE


def ensure_data_dirs() -> None:
    """Idempotent. Called once at server startup (server.py) before
    anything tries to read/write a lock, cursor, log, or markdown file."""
    for d in (DATA_DIR, LOCKS_DIR, CURSORS_DIR, LOGS_DIR, USER_DIR, TASK_DIR, ARCHIVE_DIR, FACTS_DIR, TASK_ARCHIVE_DIR):
        d.mkdir(parents=True, exist_ok=True)


ensure_data_dirs()


def setup_logging() -> None:
    """Attach a rotating file handler to the ltm.* logger hierarchy so
    every pipeline run writes structured logs to backend/data/logs/ltm/ltm.log.
    Safe to call multiple times — idempotent."""
    import logging
    import logging.handlers

    ltm_logger = logging.getLogger("ltm")
    if any(isinstance(h, logging.handlers.RotatingFileHandler) for h in ltm_logger.handlers):
        return  # already installed

    log_file = LOGS_DIR / "ltm.log"
    handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,  # 5 MB per file
        backupCount=5,
        encoding="utf-8",
    )
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    handler.setFormatter(formatter)

    ltm_logger.setLevel(logging.DEBUG)
    ltm_logger.addHandler(handler)

    # Also emit to stderr so server console shows logs
    if not any(isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler)
               for h in ltm_logger.handlers):
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        console.setFormatter(formatter)
        ltm_logger.addHandler(console)


# ----------------------------------------------------------------------
# Trigger tunables (ltm_doc.md §4)
# ----------------------------------------------------------------------

# Threshold trigger: fire the background process every N new lines
# appended to facts.jsonl during an active session.
THRESHOLD_TRIGGER_N = int(os.environ.get("LTM_THRESHOLD_N", "8"))


# ----------------------------------------------------------------------
# Retry tunables (ltm_doc.md §7)
# ----------------------------------------------------------------------

MAX_ATTEMPTS = 2
RETRY_BACKOFF_SECONDS = (2, 5)  # uniform random backoff range between attempts


# ----------------------------------------------------------------------
# Embedding backend (ltm_doc.md §10)
# ----------------------------------------------------------------------

@dataclass(frozen=True)
class EmbeddingConfig:
    backend: str = os.environ.get("LTM_EMBEDDING_BACKEND", "local")  # "local" | "api"
    dim: int = 384
    # The models directory root remains tracked relative to the agent repository structure
    local_model_path: str = os.environ.get(
        "LTM_LOCAL_MODEL_PATH", str(_BACKEND_ROOT / "mcp" / "memory" / "models" / "all-MiniLM-L6-v2-int8.onnx")
    )
    local_tokenizer_path: str = os.environ.get(
        "LTM_LOCAL_TOKENIZER_PATH", str(_BACKEND_ROOT / "mcp" / "memory" / "models" / "tokenizer.json")
    )
    # Only used when backend == "api" — same provider as the extraction
    # LLM, per §10's recommendation to avoid maintaining a second model.
    api_model: str = os.environ.get("LTM_EMBEDDING_API_MODEL", "voyage-3-lite")


EMBEDDING = EmbeddingConfig()


# ----------------------------------------------------------------------
# Lifecycle / dedup tunables that live elsewhere but are surfaced here
# for discoverability — the actual values are owned by their respective
# modules (importance.py, deduplicator.py, confidence.py) per ltm_doc.md's
# "tune in one place" principle. Do NOT duplicate the values here; this
# section is documentation-only, pointing at the source of truth.
# ----------------------------------------------------------------------
#
#   - SEMANTIC_MATCH_THRESHOLD, CROSS_NAMESPACE_THRESHOLD -> deduplicator.py
#   - REINFORCE_RATE, CONTRADICTION_PENALTY                -> confidence.py
#   - DEFAULT_LIFECYCLE_POLICY, PURGE_IMPORTANCE_THRESHOLD -> importance.py
#
# §13's periodic relation-normalization job interval:

RELATION_NORMALIZATION_INTERVAL_RUNS = int(os.environ.get("LTM_RELNORM_INTERVAL_RUNS", "20"))