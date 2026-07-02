"""
utils.py
--------
Generic shared system helpers providing locking mechanisms and cursor persistence.
"""

import os
import time
import json
from pathlib import Path
from typing import Any

class FileLockError(Exception):
    pass

class FileLock:
    """
    A simple cross-platform file-based lock helper to prevent concurrent
    write conflicts across multiple instances of memory modules.
    """
    def __init__(self, lock_path: str | Path, timeout_seconds: float = 2.0):
        self.lock_path = Path(lock_path)
        self.timeout_seconds = timeout_seconds
        self.is_locked = False

    def acquire(self) -> bool:
        """Attempts to acquire the file lock. Returns True if successful, False if blocked."""
        start_time = time.time()
        while True:
            try:
                # Exclusive creation mode (x) guarantees atomic file creation at OS level
                with open(self.lock_path, "x") as f:
                    f.write(str(os.getpid()))
                self.is_locked = True
                return True
            except FileExistsError:
                # If timeout is reached, stop waiting and return False
                if (time.time() - start_time) > self.timeout_seconds:
                    return False
                time.sleep(0.1)

    def release(self) -> None:
        """Releases the lock by deleting the lock file safely."""
        if self.is_locked:
            try:
                self.lock_path.unlink(missing_ok=True)
            finally:
                self.is_locked = False


class CursorManager:
    """
    Manages state persistence (like LLM message offset positions or last processed timestamps)
    so ingestion tasks can resume perfectly from where they left off.
    """
    def __init__(self, state_path: str | Path):
        self.state_path = Path(state_path)
        # Ensure parent directory exists
        self.state_path.parent.mkdir(parents=True, exist_ok=True)

    def get_cursor(self, key: str, default: Any = None) -> Any:
        """Reads a value back from the state manager file safely."""
        if not self.state_path.exists():
            return default
        try:
            with open(self.state_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get(key, default)
        except (json.JSONDecodeError, IOError):
            return default

    def set_cursor(self, key: str, value: Any) -> None:
        """Saves a key-value cursor pair safely using atomic overwriting."""
        data = {}
        if self.state_path.exists():
            try:
                with open(self.state_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except (json.JSONDecodeError, IOError):
                data = {}

        data[key] = value
        
        # Write to a temporary file first then rename to avoid corruption on crashes
        temp_file = self.state_path.with_suffix(".tmp")
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        temp_file.replace(self.state_path)