import asyncio
import json
from fastapi.testclient import TestClient
from src.search_agent.orchestrator import app

client = TestClient(app)

queries = [
    "top 10 richest person of india",
    "who is the current defence minister of india",
    "current NSA director usa",
    "Adani Power stock price",
    "current GDP of india"
]

all_results = []
for q in queries:
    response = client.post("/debug/query", json={"query": q})
    if response.status_code == 200:
        data = response.json()
        
        # Parse searxng json string back to dict so it renders nicely in output
        for r in data.get("tool_results", []):
            if r.get("source_id") == "searxng" and isinstance(r.get("raw_output"), str):
                try:
                    r["raw_output"] = json.loads(r["raw_output"])
                except:
                    pass
        
        all_results.append(data)
    else:
        all_results.append({"query": q, "error": f"HTTP {response.status_code}"})

with open("debug_results.json", "w", encoding="utf-8") as f:
    json.dump(all_results, f, indent=2)
