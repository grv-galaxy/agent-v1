"""
server.py
---------
Entrypoint to run the FastMCP Long-Term Memory (LTM) server over standard I/O pipes.
"""

import sys
import sqlite3
import sqlite_vec
from pathlib import Path
from mcp.server.fastmcp import FastMCP


# Resolve paths safely
current_dir = Path(__file__).parent.resolve()      # C:\...\mcp\memory
parent_dir = current_dir.parent.resolve()          # C:\...\mcp

# 1. Inject parent directory so 'from memory import ...' works smoothly
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

# 2. Safety fallback alias if executed inside the directory directly
import handlers
import sqlite_vec
sys.modules['memory'] = handlers.sys.modules[handlers.__package__ or 'handlers']

# 💡 EXPLICIT EXTENSION AUTHORIZATION: Force the built-in sqlite3 factory 
# to ALWAYS authorize and load the vec0 extension for every connection created by this process.
def _connection_factory(*args, **kwargs):
    # This matches your existing line 327
    conn = sqlite3.Connection(*args, **kwargs)
    
    # CRUCIAL FIX: Force the factory interceptor to load the vec extension! ⚡
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    
    return conn

# Your existing line 336 remains right below it:
sqlite3.connect = _connection_factory

# Import tools module safely matching layout
from core import tools

# Initialize the official FastMCP server instance
# Initialize the official FastMCP server instance
mcp = FastMCP(
    "Long-Term-Memory-Server",
    host="0.0.0.0",       # must bind to all interfaces inside a container
    port=8765,             # pick any free port, make it configurable via env if you like
)

# Bind and register tools
tools.register_ltm_tools(mcp)

if __name__ == "__main__":
    mcp.run(transport="sse")   # <-- was "stdio"