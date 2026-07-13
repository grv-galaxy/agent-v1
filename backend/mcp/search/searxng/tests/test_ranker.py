import os
import pytest
from src.search_agent.ranker import ONNXRanker

BI_ENCODER_PATH = r"C:\Users\kumar\Documents\agent-v1\backend\mcp\memory\model"
CROSS_ENCODER_PATH = r"C:\Users\kumar\Documents\agent-v1\backend\mcp\memory\cross-encoder-ms-marco-MiniLM-L-6-v2"

@pytest.fixture(scope="module")
def ranker():
    # Only load the models once for the test module
    return ONNXRanker(BI_ENCODER_PATH, CROSS_ENCODER_PATH)

def test_bi_encoder(ranker):
    query = "How to install python"
    results = [
        {"title": "Unrelated", "content": "The quick brown fox jumps over the lazy dog."},
        {"title": "Python Install", "content": "Download the installer from python.org and run it."},
        {"title": "Baking a cake", "content": "Preheat oven to 350 degrees."}
    ]
    
    ranked = ranker.bi_encoder_rank(query, results)
    
    # Check that sorting applied
    assert len(ranked) == 3
    assert ranked[0]["title"] == "Python Install"
    assert "_bi_score" in ranked[0]
    
def test_cross_encoder(ranker):
    query = "Best CPU for gaming"
    results = [
        {"title": "Car guide", "content": "The best v8 engine for speed."},
        {"title": "AMD Ryzen 7800X3D", "content": "Currently the top pick for PC gaming and raw frame rates."},
        {"title": "Intel Core i3", "content": "A good budget chip for office work."}
    ]
    
    ranked = ranker.cross_encoder_rerank(query, results)
    
    assert len(ranked) == 3
    assert "Ryzen" in ranked[0]["title"]
    assert "_cross_score" in ranked[0]

def test_rank_results_pipeline(ranker):
    query = "Python exception handling"
    
    # 10 mock results
    results = [
        {"title": f"Garbage Result {i}", "content": "Nothing useful here."} for i in range(10)
    ]
    
    # Inject the good one at the end
    results.append({
        "title": "Try Except",
        "content": "Use try/except blocks to catch Python exceptions safely."
    })
    
    final_top_3 = ranker.rank_results(query, results, top_k=3)
    
    # Should only return 3
    assert len(final_top_3) == 3
    
    # The injected correct result should have floated to #1 through both stages
    assert final_top_3[0]["title"] == "Try Except"
