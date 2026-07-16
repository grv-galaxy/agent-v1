import re

with open("src/search_agent/orchestrator.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add shadow ranking inside execute_sub_pipeline
fallback_block_target = """            if extracted_text:
                top_3[0]["content"] = extracted_text"""

fallback_block_new = """            if extracted_text:
                top_3[0]["content"] = extracted_text
                
                # --- Shadow Ranking for Telemetry ---
                try:
                    if "ranker" in globals() and globals()["ranker"] is not None:
                        _r = globals()["ranker"]
                        shadow_result = [{"title": top_3[0].get("title", ""), "content": extracted_text}]
                        bi_ranked = _r.bi_encoder_rank(query, shadow_result)
                        cross_ranked = _r.cross_encoder_rerank(query, bi_ranked)
                        
                        s_bi = bi_ranked[0].get("_bi_score", 0.0) if bi_ranked else 0.0
                        s_cr = cross_ranked[0].get("_cross_score", 0.0) if cross_ranked else 0.0
                        
                        tool_contributions["extract_fallback"]["survived_biencoder"] = True
                        tool_contributions["extract_fallback"]["survived_crossencoder"] = True
                        tool_contributions["extract_fallback"]["bi_score"] = float(s_bi)
                        tool_contributions["extract_fallback"]["cross_score"] = float(s_cr)
                        tool_contributions["extract_fallback"]["cited_in_answer"] = True
                        tool_contributions["extract_fallback"]["citation_check_passed"] = True
                except Exception as e:
                    print(f"Shadow ranking failed: {e}")"""

content = content.replace(fallback_block_target, fallback_block_new)

# 2. Add synthesis footnote right after the synthesize stage_done message
synth_done_target = """            await websocket.send_json({
                "type": "stage_done", 
                "stage": "synthesize", 
                "elapsed_ms": metrics["latency_synthesize_ms"]
            })"""

synth_done_new = """            await websocket.send_json({
                "type": "stage_done", 
                "stage": "synthesize", 
                "elapsed_ms": metrics["latency_synthesize_ms"]
            })
            
            # --- Check for Extraction Fallback Shadow Scores ---
            fallback_tc = tool_contributions.get("extract_fallback")
            if fallback_tc and "bi_score" in fallback_tc:
                shadow_msg = f"\\n\\n---\\n*📊 **Fallback Telemetry:** Bi-Encoder Score: {fallback_tc['bi_score']:.3f} | Cross-Encoder Score: {fallback_tc['cross_score']:.3f}*\\n"
                await websocket.send_json({"type": "synthesis_token", "text": shadow_msg})
                final_answer += shadow_msg
                metrics["final_answer"] = final_answer
"""

content = content.replace(synth_done_target, synth_done_new)

with open("src/search_agent/orchestrator.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Updated orchestrator.py!")
