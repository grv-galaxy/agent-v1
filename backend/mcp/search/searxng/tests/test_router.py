import pytest
from src.search_agent.schemas import ClassifierOutput
from src.search_agent.router import route_query

def test_route_query_basic(mock_classifier_output):
    """Test standard mapping using the conftest fixture."""
    params = route_query(mock_classifier_output)
    
    assert params["categories"] == "news,finance"
    assert params["time_range"] == "week"
    assert params["language"] == "en-US"

def test_route_query_defaults():
    """Test defaults when categories are empty or date_range is null."""
    output = ClassifierOutput(
        categories=[],
        confidence=0.5,
        entities=[],
        date_range=None,
        language_hint=None
    )
    
    params = route_query(output)
    
    assert params["categories"] == "general"
    assert params["time_range"] == ""
    assert params["language"] == "en-US"

def test_route_query_invalid_category():
    """Test that invalid categories fall back to general."""
    output = ClassifierOutput(
        categories=["unknown_category", "made_up_stuff"],
        confidence=0.5,
        entities=[],
        date_range=None,
        language_hint=None
    )
    
    params = route_query(output)
    assert params["categories"] == "general"

def test_route_query_time_ranges():
    """Test various date string mappings."""
    output = ClassifierOutput(
        categories=["news"],
        confidence=0.9,
        entities=[],
        date_range="past 24 hours",
        language_hint="de-DE"
    )
    
    params = route_query(output)
    assert params["time_range"] == "day"
    assert params["language"] == "de-DE"
