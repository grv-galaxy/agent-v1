"""
fetcher.py
----------
Fetches the latest facts.jsonl file from the backend/data/facts/ directory.
Once processing is completed by the engine, provides functionality to move
the handled file safely into the backend/data/archieve/ folder.
"""

import os
import shutil
from pathlib import Path

# Track paths dynamically by going up to the backend root directory
_CURRENT_FILE = Path(__file__).resolve()

# Find the absolute 'backend' root directory safely
_BACKEND_ROOT = None
for parent in _CURRENT_FILE.parents:
    if parent.name == "backend":
        _BACKEND_ROOT = parent
        break

if _BACKEND_ROOT is None:
    # Fallback to older nested structure logic if backend is not explicitly found
    _BACKEND_ROOT = _CURRENT_FILE.parent.parent.parent.parent

# Centralized data directory pointers matching config.py
FACTS_DIR = _BACKEND_ROOT / "data" / "facts"
ARCHIVE_DIR = _BACKEND_ROOT / "data" / "archieve"

def get_latest_facts_file() -> Path | None:
    """
    Returns the Path of the latest facts.jsonl file in the directory,
    based on the filename's timestamp (YYYYMMDD_HHMM_*.jsonl) or basic alphabetical sort.
    Returns None if no files are found.
    """
    if not FACTS_DIR.exists():
        return None

    # Get all .jsonl files in the directory
    jsonl_files = list(FACTS_DIR.glob("*.jsonl"))
    if not jsonl_files:
        return None

    import re
    def get_timestamp(p):
        match = re.search(r'_session_(\d+)_', p.name)
        if match:
            return int(match.group(1))
        return int(p.stat().st_mtime * 1000)

    # Sort by the extracted session timestamp to handle different date prefixes correctly
    jsonl_files.sort(key=get_timestamp)
    latest_file = jsonl_files[-1]
    return latest_file

def read_latest_facts() -> tuple[list[str], Path | None]:
    """
    Reads and returns the lines of the latest facts.jsonl file along with its file path.
    Returns an empty list and None if no file is found.
    
    NOTE: Changed return type to a tuple so the Engine knows WHICH file path it needs
    to archive later once the pipeline runs successfully.
    """
    latest_file = get_latest_facts_file()
    if not latest_file:
        return [], None

    with open(latest_file, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]
        
    return lines, latest_file

def archive_processed_file(file_path: Path) -> bool:
    """
    Moves a processed file out of backend/data/facts/ and places it securely
    inside backend/data/archieve/. If a file with the same name exists there,
    it avoids overwriting by appending a small counter suffix.
    """
    try:
        if not file_path or not file_path.exists():
            return False

        # Ensure the archive target destination directory exists
        ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
        
        target_path = ARCHIVE_DIR / file_path.name
        
        # Avoid overriding file collisions if the same file gets double-processed
        counter = 1
        while target_path.exists():
            target_path = ARCHIVE_DIR / f"{file_path.stem}_{counter}{file_path.suffix}"
            counter += 1

        # Atomically move the file from facts to archive folder
        shutil.move(str(file_path), str(target_path))
        print(f"[+] Fetcher successfully archived: {file_path.name} -> {target_path.name}")
        return True

    except Exception as e:
        print(f"[-] Fetcher failed to archive file {file_path.name}: {str(e)}")
        return False