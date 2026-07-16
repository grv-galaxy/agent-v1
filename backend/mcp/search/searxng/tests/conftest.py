import pytest
from src.search_agent.schemas import ClassifierOutput

@pytest.fixture
def mock_classifier_output() -> ClassifierOutput:
    return ClassifierOutput(
        categories=["news", "finance"],
        confidence=0.95,
        entities=["test company", "earnings"],
        date_range="past week",
        language_hint="en-US",
        requires_deep_research=True,
        deep_research_reasoning="Requires comparative financial deep dive"
    )

@pytest.fixture
def mock_classifier_json() -> str:
    return """
    {
      "categories": ["news", "finance"],
      "confidence": 0.95,
      "entities": ["test company", "earnings"],
      "date_range": "past week",
      "language_hint": "en-US",
      "requires_deep_research": true,
      "deep_research_reasoning": "Requires comparative financial deep dive"
    }
    """
