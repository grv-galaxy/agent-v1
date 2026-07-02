"""
memory_trigger.py
------------------
Fire-and-forget triggers for the Long-Term Memory MCP server.
Runs as an async background task so it never blocks chat responses,
compression cycles, or app startup/shutdown.
"""

import asyncio
import logging
from app.services.ltm_client import call_ltm_tool

logger = logging.getLogger("chat.memory_trigger")


async def _sync_now() -> None:
    try:
        result = await call_ltm_tool("sync_memory_now")
        logger.info(f"LTM background sync completed: {result}")
    except Exception as e:
        # Never let a memory-sync failure affect chat/compression services.
        logger.warning(f"LTM background sync failed (non-fatal): {e}")


def trigger_sync_background() -> None:
    """
    Schedules a memory sync without blocking the caller.
    Safe to call from a chat handler, compression cycle, startup, or shutdown —
    returns immediately; the actual network call happens on the event loop
    in the background.
    """
    asyncio.create_task(_sync_now())


async def trigger_sync_and_wait(timeout: float = 5.0) -> None:
    """
    Same as above, but waits up to `timeout` seconds — only meant for
    shutdown, where we want a best-effort final flush without risking
    hanging the process indefinitely if the MCP server is slow/unreachable.
    """
    try:
        await asyncio.wait_for(_sync_now(), timeout=timeout)
    except asyncio.TimeoutError:
        logger.warning(f"LTM shutdown sync did not complete within {timeout}s — skipping.")