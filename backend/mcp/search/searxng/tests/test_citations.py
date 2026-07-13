from src.search_agent.citations import check_overlap, verify_citations

def test_check_overlap_pass():
    claim = "The Kansas City Chiefs won the Super Bowl in overtime."
    snippet = "The Kansas City Chiefs defeated the San Francisco 49ers 25-22 in overtime to win Super Bowl LVIII."
    
    assert check_overlap(claim, snippet, threshold=0.15) is True

def test_check_overlap_fail():
    claim = "The sky is green and grass is blue."
    snippet = "The Kansas City Chiefs defeated the San Francisco 49ers 25-22 in overtime to win Super Bowl LVIII."
    
    assert check_overlap(claim, snippet, threshold=0.15) is False

def test_verify_citations():
    synthesized = (
        "Here is what I found. The Chiefs won the game in overtime [1]. "
        "Also, Paris is the capital of France [2]. "
        "And aliens landed yesterday [3]."
    )
    
    top_results = [
        {"title": "Sports", "content": "The Chiefs won the game in overtime."},
        {"title": "Geo", "content": "Paris is the capital of France."},
    ]
    
    verifications = verify_citations(synthesized, top_results)
    
    assert len(verifications) == 3
    
    # Citation 1 should pass
    assert verifications[0]["citation_number"] == 1
    assert verifications[0]["passed"] is True
    
    # Citation 2 should pass
    assert verifications[1]["citation_number"] == 2
    assert verifications[1]["passed"] is True
    
    # Citation 3 should fail because snippet 3 doesn't exist
    assert verifications[2]["citation_number"] == 3
    assert verifications[2]["passed"] is False

def test_verify_citations_hallucination():
    synthesized = "The Chiefs won the game in overtime [1], but they cheated using magnets [1]."
    
    top_results = [
        {"title": "Sports", "content": "The Chiefs won the game in overtime."}
    ]
    
    verifications = verify_citations(synthesized, top_results)
    
    assert len(verifications) == 2
    
    # First claim passed
    assert verifications[0]["citation_number"] == 1
    assert verifications[0]["passed"] is True
    
    # Second claim failed (hallucinated)
    assert verifications[1]["citation_number"] == 1
    assert verifications[1]["passed"] is False
