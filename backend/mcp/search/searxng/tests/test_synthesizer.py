import pytest
from unittest.mock import AsyncMock, patch
from src.search_agent.synthesizer import synthesize

@pytest.mark.asyncio
async def test_synthesize_stream():
    class MockDelta:
        def __init__(self, content):
            self.content = content
            
    class MockChoice:
        def __init__(self, content):
            self.delta = MockDelta(content)
            
    class MockChunk:
        def __init__(self, content):
            self.choices = [MockChoice(content)]

    async def mock_stream():
        yield MockChunk("The ")
        yield MockChunk("answer ")
        yield MockChunk("is ")
        yield MockChunk("42 ")
        yield MockChunk("[1].")
        # Final chunk usually has None for content
        yield MockChunk(None)

    with patch("src.search_agent.synthesizer.client.chat.completions.create", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_stream()
        
        query = "What is the answer to the ultimate question?"
        results = [
            {"title": "Hitchhiker's Guide", "content": "The answer is 42.", "url": "https://example.com/hgttg"}
        ]
        
        chunks = []
        # Since the mock returns an async generator, we don't need to await the create call in the test,
        # it is awaited in the synthesize function. Oh wait, client.chat.completions.create is awaited
        # so mock_create needs to be an AsyncMock.
        # But wait! For streaming, it returns an AsyncStream directly, it's NOT awaited if we just do:
        # response = await client.chat.completions.create(stream=True)
        # So mock_create must be an AsyncMock that returns an async generator.
        
        async for chunk in synthesize(query, results):
            chunks.append(chunk)
            
        full_text = "".join(chunks)
        assert full_text == "The answer is 42 [1]."
        
        mock_create.assert_called_once()
        kwargs = mock_create.call_args.kwargs
        assert kwargs["stream"] is True
        assert any("Source [1]" in m["content"] for m in kwargs["messages"] if m["role"] == "system")
