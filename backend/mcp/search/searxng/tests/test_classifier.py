import json
import pytest
from unittest.mock import AsyncMock, patch
from src.search_agent.classifier import classify_query
from src.search_agent.schemas import ClassifierOutput

@pytest.mark.asyncio
async def test_classify_query_parses_json_correctly(mock_classifier_json):
    # Create a mock for the AsyncOpenAI client's chat.completions.create method
    with patch("src.search_agent.classifier.client.chat.completions.create", new_callable=AsyncMock) as mock_create:
        # Set up the mock response to return our mock JSON
        mock_message = AsyncMock()
        mock_message.content = mock_classifier_json
        
        mock_choice = AsyncMock()
        mock_choice.message = mock_message
        
        mock_response = AsyncMock()
        mock_response.choices = [mock_choice]
        
        mock_create.return_value = mock_response
        
        # Run the function
        result = await classify_query("test query about earnings")
        
        # Verify the result is parsed correctly into the Pydantic model
        assert isinstance(result, ClassifierOutput)
        assert result.categories == ["news", "finance"]
        assert result.confidence == 0.95
        assert result.entities == ["test company", "earnings"]
        assert result.date_range == "past week"
        assert result.language_hint == "en-US"
        
        # Verify the API was called with the correct parameters
        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args.kwargs
        assert call_kwargs["response_format"] == {"type": "json_object"}
        assert any(m["role"] == "user" and m["content"] == "test query about earnings" for m in call_kwargs["messages"])
