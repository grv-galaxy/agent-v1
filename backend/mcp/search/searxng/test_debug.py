import asyncio
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

import json

for q in queries:
    print(f"\n--- QUERY: {q} ---")
    response = client.post("/debug/query", json={"query": q})
    if response.status_code == 200:
        data = response.json()
        print(f"Categories: {data.get('categories')}")
        for res in data.get('tool_results', []):
            sid = res.get('source_id')
            status = res.get('status')
            ems = res.get('elapsed_ms')
            if status == 'error':
                print(f"[{sid}] ERROR ({ems}ms): {res.get('error')}")
            else:
                raw = res.get('raw_output')
                if raw is None:
                    print(f"[{sid}] SUCCESS ({ems}ms): None")
                elif isinstance(raw, list):
                    print(f"[{sid}] SUCCESS ({ems}ms): {len(raw)} items returned.")
                    for i, item in enumerate(raw[:2]): # show up to 2 items
                        title = item.get('title', '')
                        content = item.get('content', '')[:100] # trim content
                        print(f"  - {title}: {content}...")
                else:
                    print(f"[{sid}] SUCCESS ({ems}ms): {str(raw)[:100]}...")
    else:
        print(f"HTTP ERROR: {response.status_code} {response.text}")

