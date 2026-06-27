import asyncio
import time
from typing import Dict, Any, List

# 🛑 DEMAND 1: Global Master Gate. Completely False/Off by default.
IS_TELEMETRY_ON: bool = False

# ⚡ The Fire-and-Forget Ingestion Queue
_stats_queue: asyncio.Queue = asyncio.Queue()
_worker_task: asyncio.Task = None

# 📊 DEMAND 3 & 6: Clean, Extensible RAM Cache optimized for O(1) mutations
_stats_matrix: Dict[str, Any] = {
    # Summary Counters (For Settings UI Panel)
    "active_sessions": 0,
    "total_messages": 0,
    "total_compressions": 0,
    "estimated_tokens_saved": 0,
    "current_epoch": 0,
    
    # DEMAND 4: Future-Ready Rolling Time-Series Arrays (Max capped to prevent memory leaks)
    "timeline": {
        "timestamps": [],
        "message_latencies_ms": [],
        "prompt_tokens": [],
        "completion_tokens": [],
        "compression_ratios": [],
        "grounding_epoch_markers": []
    }
}

# Max capacity for structural array logging lists to bound RAM usage over days of running
MAX_HISTORY_LEN = 500

def set_telemetry_state(enabled: bool):
    """Dynamically open or close the Master Gate via API configuration."""
    global IS_TELEMETRY_ON, _worker_task
    IS_TELEMETRY_ON = enabled
    
    # Lazily spin up the consumer task loop only if turned on
    if IS_TELEMETRY_ON and (_worker_task is None or _worker_task.done()):
        _worker_task = asyncio.create_task(_stats_worker())
    elif not IS_TELEMETRY_ON and _worker_task is not None:
        _worker_task.cancel()

def dispatch_stats_event(event_type: str, data: Dict[str, Any]):
    """
    ⚡ DEMAND 2: Zero-Friction Entry Gate. 
    Exits instantly in 0ms if toggled off. Non-blocking queue push if on.
    """
    if not IS_TELEMETRY_ON:
        return
        
    try:
        # put_nowait drops payload into the buffer array with 0 execution wait time
        _stats_queue.put_nowait({"type": event_type, "data": data, "time": time.time()})
    except Exception as e:
        # Failsafe to guarantee telemetry structural failures never take down the system
        print(f"[Telemetry Ingestion Error]: {e}")

async def _stats_worker():
    """
    Consumes background telemetry entries sequentially.
    Keeps heavy parsing and array mutations entirely out of the user chat pathways.
    """
    while True:
        try:
            event = await _stats_queue.get()
            event_type = event["type"]
            data = event["data"]
            
            # Pure O(1) Arithmetic Math Operations based on Event Types
            if event_type == "session_increment":
                _stats_matrix["active_sessions"] += 1
                
            elif event_type == "session_decrement":
                _stats_matrix["active_sessions"] = max(0, _stats_matrix["active_sessions"] - 1)
                
            elif event_type == "chat_message":
                _stats_matrix["total_messages"] += 1
                
                # Append performance metrics to timeline arrays
                t_log = _stats_matrix["timeline"]
                t_log["timestamps"].append(event["time"])
                t_log["message_latencies_ms"].append(data.get("latency_ms", 0.0))
                t_log["prompt_tokens"].append(data.get("prompt_tokens", 0))
                t_log["completion_tokens"].append(data.get("completion_tokens", 0))
                
                # Memory cleanup guard: truncate lists if they breach maximum threshold
                if len(t_log["timestamps"]) > MAX_HISTORY_LEN:
                    for key in t_log:
                        t_log[key] = t_log[key][-MAX_HISTORY_LEN:]
                        
            elif event_type == "compression":
                _stats_matrix["total_compressions"] += 1
                _stats_matrix["estimated_tokens_saved"] += data.get("tokens_saved", 0)
                _stats_matrix["current_epoch"] = data.get("epoch", _stats_matrix["current_epoch"])
                
                # Log metrics for data science tracking charts
                t_log = _stats_matrix["timeline"]
                tokens_before = data.get("tokens_before", 1)
                tokens_after = data.get("tokens_after", 0)
                ratio = round(tokens_after / max(1, tokens_before), 3)
                
                t_log["compression_ratios"].append(ratio)
                if data.get("grounding_applied", False):
                    t_log["grounding_epoch_markers"].append(data.get("epoch", 0))
            
            _stats_queue.task_done()
            
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"[Telemetry Worker Execution Error]: {e}")
            _stats_queue.task_done()

def get_all_stats() -> Dict[str, Any]:
    """
    Instantly hands back the cache map copy for direct JSON extraction.
    Ensures O(1) reads for API calls.
    """
    if not IS_TELEMETRY_ON:
        return {"telemetry_enabled": False, "message": "Telemetry is turned off."}
        
    # Return a clean copy of the data layout matrix
    data_snapshot = _stats_matrix.copy()
    data_snapshot["telemetry_enabled"] = True
    return data_snapshot