import os

with open("src/search_agent/orchestrator.py.bak", "r", encoding="utf-8") as f:
    lines = f.readlines()

# Extract lines from --- 1. Classify --- to --- 6. Synthesize (Streaming) ---
start_idx = 0
end_idx = 0
for i, line in enumerate(lines):
    if "            # --- 1. Classify ---" in line:
        start_idx = i
    if "            # --- 6. Synthesize (Streaming) ---" in line:
        end_idx = i
        break

extracted_block = "".join(lines[start_idx:end_idx])

# We need to de-indent it by 1 level (12 spaces to 4 spaces, wait, 12 spaces in websocket_endpoint)
# 12 spaces -> 4 spaces means removing 8 spaces
new_block_lines = []
for line in extracted_block.split("\n"):
    if line.startswith("            "):
        new_block_lines.append(line[8:])
    elif line.startswith("        ") and len(line.strip()) == 0:
        new_block_lines.append(line[8:])
    elif line == "":
        new_block_lines.append("")
    else:
        # Just strip what we can or keep
        if line.startswith(" " * 8):
            new_block_lines.append(line[8:])
        else:
            new_block_lines.append(line)

extracted_block_deindented = "\n".join(new_block_lines)

# Create the execute_sub_pipeline function
function_header = """
async def execute_sub_pipeline(
    websocket: WebSocket,
    query: str,
    query_id: str,
    is_diagnostic_mode: bool,
    diagnostic_tool: str,
    deep_research_override: bool,
    sub_query_id: str = None,
    emit_ws_events: bool = True
) -> dict:
    group_id = f"fetch-{uuid.uuid4().hex[:8]}"
    if sub_query_id:
        group_id = f"{group_id}-{sub_query_id}"
        
    metrics = {"query": query}
    tool_contributions = {}
    llm_calls_to_log = []
    top_3 = []
    
    # Custom websocket wrapper to optionally suppress events during parallel runs
    class WsWrapper:
        async def send_json(self, data):
            # Always send errors or citations.
            # Suppress stage events if emit_ws_events is False.
            if not emit_ws_events and data.get("type") in ["stage_start", "stage_done", "source_start", "source_done", "page_visit_start", "page_visit_done"]:
                return
            await websocket.send_json(data)
            
    ws = WsWrapper()
    
    # Redefine websocket inside the block to use our wrapper
    websocket = ws
    start_total = time.perf_counter()
"""

# Now we need to modify the extracted block slightly if necessary, but it's mostly self-contained.
# Let's replace return [] with returning the structure on failure
extracted_block_deindented = extracted_block_deindented.replace("continue", "return {'top_3': [], 'metrics': metrics, 'tool_contributions': tool_contributions, 'llm_calls_to_log': llm_calls_to_log}")
extracted_block_deindented = extracted_block_deindented.replace("await websocket.send_json", "await ws.send_json")
# Fix the tool_contributions sub_query_id
extracted_block_deindented = extracted_block_deindented.replace('"query_id": query_id,', '"query_id": query_id,\n                "sub_query_id": sub_query_id,')
# Fix the llm_calls_to_log sub_query_id
extracted_block_deindented = extracted_block_deindented.replace('classify_telemetry["query_id"] = query_id', 'classify_telemetry["query_id"] = query_id\n        classify_telemetry["sub_query_id"] = sub_query_id')
extracted_block_deindented = extracted_block_deindented.replace('plan_telemetry["query_id"] = query_id', 'plan_telemetry["query_id"] = query_id\n        plan_telemetry["sub_query_id"] = sub_query_id')

function_footer = """
    return {
        "top_3": top_3,
        "metrics": metrics,
        "tool_contributions": tool_contributions,
        "llm_calls_to_log": llm_calls_to_log,
        "planner_out": planner_out if 'planner_out' in locals() else None,
        "is_deep_research": is_deep_research if 'is_deep_research' in locals() else False
    }
"""

full_function = function_header + extracted_block_deindented + function_footer

main_loop_replacement = """
            # --- PHASE 3: execute_sub_pipeline (Fan-out) ---
            if is_diagnostic_mode:
                # Diagnostic mode implies single pass
                res = await execute_sub_pipeline(websocket, query, query_id, is_diagnostic_mode, diagnostic_tool, deep_research_override, emit_ws_events=True)
                top_3 = res["top_3"]
                tool_contributions.update(res["tool_contributions"])
                llm_calls_to_log.extend(res["llm_calls_to_log"])
                metrics.update(res["metrics"])
            else:
                # First run to classify and potentially plan
                await websocket.send_json({"type": "stage_start", "stage": "plan", "label": "Analyzing query complexity"})
                res = await execute_sub_pipeline(websocket, query, query_id, is_diagnostic_mode, diagnostic_tool, deep_research_override, emit_ws_events=True)
                
                is_deep_research = res.get("is_deep_research", False)
                planner_out = res.get("planner_out")
                
                tool_contributions.update(res["tool_contributions"])
                llm_calls_to_log.extend(res["llm_calls_to_log"])
                
                if is_deep_research and planner_out and planner_out.sub_queries:
                    await websocket.send_json({
                        "type": "stage_start", 
                        "stage": "deep_research_fetch", 
                        "label": f"Deep Research: Running {len(planner_out.sub_queries)} queries in parallel"
                    })
                    
                    # Fan-out!
                    tasks = []
                    for i, sq in enumerate(planner_out.sub_queries):
                        sq_id = f"sq-{i+1}"
                        # Execute with emit_ws_events=False so we don't spam the UI with 4 concurrent progress bars
                        tasks.append(execute_sub_pipeline(
                            websocket, sq, query_id, is_diagnostic_mode, diagnostic_tool, 
                            deep_research_override=False, sub_query_id=sq_id, emit_ws_events=False
                        ))
                        
                    parallel_results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    top_3 = [] # Flattened combined top_3
                    for p_res in parallel_results:
                        if isinstance(p_res, dict):
                            top_3.extend(p_res.get("top_3", []))
                            tool_contributions.update(p_res.get("tool_contributions", {}))
                            llm_calls_to_log.extend(p_res.get("llm_calls_to_log", []))
                    
                    await websocket.send_json({"type": "stage_done", "stage": "deep_research_fetch", "elapsed_ms": 0})
                else:
                    # Single pass
                    top_3 = res["top_3"]
                    metrics.update(res["metrics"])
"""

with open("src/search_agent/orchestrator.py", "r", encoding="utf-8") as f:
    target_code = f.read()

# Insert the function just before @app.websocket
target_code = target_code.replace('@app.websocket("/ws/query")', full_function + '\n@app.websocket("/ws/query")')

# Replace the marker
target_code = target_code.replace('# --- MULTI_REPLACE_TARGET ---', main_loop_replacement)

with open("src/search_agent/orchestrator.py", "w", encoding="utf-8") as f:
    f.write(target_code)

print("Refactoring complete.")
