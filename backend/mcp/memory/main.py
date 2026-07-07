"""
main.py
-------
Root orchestrator and lifecycle execution hook node for the Long-Term Memory (LTM) system.

Responsibilities:
  - Coordinate execution passes exclusively during lifecycle hooks (Startup / Shutdown / Manual Trigger).
  - Dispatches the execution request over the network to the active MCP server's sync tool.
  - Completely detached from parsing or monitoring file line sub-counters.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# Add mcp/memory path to sys.path to resolve internal module configurations cleanly
sys.path.append(str(Path(__file__).resolve().parent))
import config

# Add backend/ path so app.services is importable (needed to reach the live MCP server)
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from app.services.ltm_client import call_ltm_tool

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("ltm.main_orchestrator")


def trigger_background_worker() -> bool:
    """
    Calls sync_memory_now on the already-running SSE MCP server (server.py).
    """
    logger.info("[*] Dispatching memory synchronization signal to LTM server...")
    success = call_ltm_tool(tool_name="sync_memory_now", arguments={})
    
    if success:
        logger.info("[+] LTM Server successfully accepted the sync instruction.")
    else:
        logger.error("[-] Failed to broadcast sync instruction to the LTM server.")
    return success


def on_app_startup() -> None:
    """Executed during desktop application initialization sequences."""
    logger.info("=== [LTM LIFECYCLE] App Startup Detected ===")
    
    # Clean out unexpected dead lock tokens left behind by sudden host crashes
    lock_path = Path(config.LOCK_PATH)
    if lock_path.exists():
        try:
            lock_path.unlink(missing_ok=True)
            logger.info("[+] Stale file lock cleared successfully.")
        except Exception:
            pass
            
    # Fire the sync instruction on boot to clear out any un-archived batch remnants
    trigger_background_worker()


def on_app_close() -> None:
    """Executed during graceful main chat application shutdown windows."""
    logger.info("=== [LTM LIFECYCLE] App Shutdown Detected ===")
    # Final flush sweep to clean out outstanding transactions before termination
    trigger_background_worker()


if __name__ == "__main__":
    # Local CLI driver to manually trigger sequences or test server integration
    import argparse
    parser = argparse.ArgumentParser(description="LTM Host Orchestration Node")
    parser.add_argument("--startup", action="store_true", help="Simulate desktop app initialization sequence.")
    parser.add_argument("--close", action="store_true", help="Simulate application termination sequence.")
    parser.add_argument("--trigger", action="store_true", help="Force an immediate background execution pass manually.")
    args = parser.parse_args()

    if args.startup:
        on_app_startup()
    elif args.close:
        on_app_close()
    elif args.trigger:
        logger.info("=== [LTM LIFECYCLE] Manual Execution Triggered ===")
        trigger_background_worker()
    else:
        print("LTM Host Coordinator active. Control via lifecycle parameters: --startup, --close, or --trigger")