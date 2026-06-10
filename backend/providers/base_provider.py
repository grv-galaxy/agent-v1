from abc import ABC, abstractmethod
from typing import AsyncGenerator, Any, List, Dict

class BaseProvider(ABC):
    """
    Production-Grade Abstract Base Class (ABC) serving as the strict ASYNC blueprint 
    for all LLM providers. Enforces async execution, structured chat messages, 
    built-in error resilience, and standardized token tracking metadata.
    """

    def __init__(self, api_key: str, **kwargs: Any):
        """
        Initializes the provider with the user's custom API key and any 
        additional configuration parameters (e.g., base_url, organization_id).
        """
        self.api_key = api_key
        self.extra_config = kwargs

    @abstractmethod
    async def generate_response(self, model: str, messages: List[Dict[str, str]], **kwargs: Any) -> Dict[str, Any]:
        """
        Asynchronously executes a standard, non-streaming text generation request.

        Args:
            model (str): The specific model name string (e.g., 'gpt-4o', 'llama3-70b').
            messages (List[Dict[str, str]]): Full chat history structured with roles.
            **kwargs: Flexible, optional configurations (e.g., temperature, max_tokens).

        Returns:
            Dict[str, Any]: A standardized payload containing the text response and usage stats.
                Format: {
                    "text": "Hello world",
                    "usage": {"prompt_tokens": 12, "completion_tokens": 25, "total_tokens": 37}
                }
        """
        pass

    @abstractmethod
    async def generate_stream(self, model: str, messages: List[Dict[str, str]], **kwargs: Any) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Asynchronously executes a real-time streaming response request. 

        Args:
            model (str): The specific model name string.
            messages (List[Dict[str, str]]): Full chat history structured with roles.
            **kwargs: Flexible, optional configurations (e.g., temperature, max_tokens).

        Yields:
            Dict[str, Any]: Standardized payloads containing text chunks or real-time token tracking metadata.
                Format during generation: {"text": "chunk_data", "usage": None}
                Format at the end of generation (if supported): {"text": "", "usage": {"prompt_tokens": 12, ...}}
        """
        pass