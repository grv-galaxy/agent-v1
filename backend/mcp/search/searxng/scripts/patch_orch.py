import os

with open("src/search_agent/orchestrator.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []
skip = False

for i, line in enumerate(lines):
    if "top_3 = [] # Flattened combined top_3" in line:
        skip = True
        
        # Insert our new logic here
        new_lines.append("""                    parallel_results_top_3 = []
                    top_3 = [] # Flattened combined top_3
                    for p_res in parallel_results:
                        if isinstance(p_res, dict):
                            res_top_3 = p_res.get("top_3", [])
                            parallel_results_top_3.append(res_top_3)
                            top_3.extend(res_top_3)
                            tool_contributions.update(p_res.get("tool_contributions", {}))
                            llm_calls_to_log.extend(p_res.get("llm_calls_to_log", []))
                    
                    await ws.send_json({"type": "stage_done", "stage": "deep_research_fetch", "elapsed_ms": 0})
                else:
                    # Single pass
                    top_3 = res["top_3"]
                    metrics.update(res["metrics"])
                    
            # --- 6. Synthesize (Streaming) ---
            await ws.send_json({"type": "stage_start", "stage": "synthesize", "label": "Writing answer"})
            t0 = time.perf_counter()
            
            from src.search_agent.synthesizer import synthesize, synthesize_deep_research, format_context, load_prompt
            
            if is_diagnostic_mode:
                context_str = format_context(top_3)
                diagnostic_trace["synthesizer_context"] = context_str
                
                # Use a barebones prompt for diagnostic mode
                system_message = "Synthesize the following context to answer the user query exactly based on the text. If not present, say so.\\n\\n" + context_str
                diagnostic_trace["synthesizer_system_prompt"] = system_message
                
                import src.search_agent.config
                from openai import AsyncOpenAI
                temp_client = AsyncOpenAI(base_url="https://api.groq.com/openai/v1", api_key=src.search_agent.config.settings.groq_api_key)
                
                async def custom_synth():
                    resp = await temp_client.chat.completions.create(
                        model=src.search_agent.config.settings.groq_model,
                        messages=[{"role": "system", "content": system_message}, {"role": "user", "content": query}],
                        stream=True, temperature=0.0
                    )
                    async for c in resp:
                        if c.choices and c.choices[0].delta.content:
                            yield c.choices[0].delta.content
                
                synth_generator = custom_synth()
            else:
                if 'is_deep_research' in locals() and is_deep_research and 'planner_out' in locals() and planner_out.sub_queries:
                    # Phase 4 Map-Reduce
                    synth_generator = synthesize_deep_research(query, planner_out.sub_queries, parallel_results_top_3)
                else:
                    synth_generator = synthesize(query, top_3)
""")
    if skip and "synth_generator = synthesize(query, top_3)" in line:
        skip = False
        continue
        
    if not skip:
        new_lines.append(line)

with open("src/search_agent/orchestrator.py", "w", encoding="utf-8") as f:
    f.writelines(new_lines)
print("Updated orchestrator!")
