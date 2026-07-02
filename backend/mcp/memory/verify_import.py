import sys
from pathlib import Path

root = Path(__file__).resolve().parent
core = root / 'core'
for p in (root, core):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import config
import handlers
import storage
print('import ok')
print(config.LOCK_PATH)
print(config.CURSOR_PATH)
print(storage.get_connection.__name__)
