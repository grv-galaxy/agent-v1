from typing import AsyncGenerator, Any, List, Dict
from .base_provider import BaseProvider
from fastapi import HTTPException

# Handle the mistralai v1.x vs v2.x breaking client import shift dynamically
try:
    from mistralai.client import Mistral
except ImportError:
    from mistralai import Mistral

class MistralProvider(BaseProvider):
    """
    Production-Grade asynchronous implementation of the Mistral AI provider.
    Fully satisfies the BaseProvider blueprint with async executions, structured messages,
    robust exception parsing, and standardized token tracking metadata.
    """

    def _get_client(self) -> Mistral:
        """
        Helper method to initialize the official Mistral client on-the-fly.
        """
        return Mistral(
            api_key=self.api_key,
            endpoint=self.extra_config.get("base_url")  # Injects alternative endpoint overrides smoothly
        )

    async def generate_response(self, model: str, messages: List[Dict[str, str]], **kwargs: Any) -> Dict[str, Any]:
        """
        Asynchronously executes a standard non-streaming text completion via chat.complete_async.
        Extracts token analytics safely and bubbles errors to standardized HTTP exception objects.
        """
        client = self._get_client()
        
        temperature = kwargs.get("temperature", 0.7)
        max_tokens = kwargs.get("max_tokens")

        try:
            # Native asynchronous call method provided by the mistralai library
            response = await client.chat.complete_async(
                model=model,
                messages=messages,  # type: ignore (handles List[Dict[str, str]])
                temperature=temperature,
                max_tokens=max_tokens,
                **{k: v for k, v in kwargs.items() if k not in ["temperature", "max_tokens"]}
            )
            
            text_content = response.choices[0].message.content if response.choices else ""
            
            # Map Mistral's usage block to our standardized blueprint structure
            usage_data = {
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                "total_tokens": response.usage.total_tokens if response.usage else 0
            }

            return {
                "text": text_content,
                "usage": usage_data
            }

        except SDKError as e:
            # Trap authorization blocks (401) and rate limits (429) out of the Mistral SDK engine
            if e.status_code == 401:
                raise HTTPException(status_code=401, detail="Mistral Authentication Failed: The provided API key is invalid.")
            elif e.status_code == 429:
                raise HTTPException(status_code=429, detail="Mistral Rate Limit Exceeded: Please slow down requests.")
            raise HTTPException(status_code=e.status_code or 502, detail=f"Mistral Gateway API Error: {str(e)}")

    async def generate_stream(self, model: str, messages: List[Dict[str, str]], **kwargs: Any) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Asynchronously executes a streaming request via chat.stream_async.
        Pushes out raw content updates instantly, and delivers aggregated usage summaries upon stream completion.
        """
        client = self._get_client()
        
        temperature = kwargs.get("temperature", 0.7)
        max_tokens = kwargs.get("max_tokens")

        try:
            # Dynamic asynchronous stream engine loop execution
            response_stream = await client.chat.stream_async(
                model=model,
                messages=messages,  # type: ignore
                temperature=temperature,
                max_tokens=max_tokens,
                **{k: v for k, v in kwargs.items() if k not in ["temperature", "max_tokens"]}
            )

            async for chunk in response_stream:
                # Intercept normal string generation tokens inside chunk data frames
                if chunk.data.choices and chunk.data.choices[0].delta.content:
                    yield {"text": chunk.data.choices[0].delta.content, "usage": None}
                
                # Check if this frame contains the final token counter payload dropped by Mistral at the end
                if hasattr(chunk.data, 'usage') and chunk.data.usage is not None:
                    yield {
                        "text": "",
                        "usage": {
                            "prompt_tokens": chunk.data.usage.prompt_tokens,
                            "completion_tokens": chunk.data.usage.completion_tokens,
                            "total_tokens": chunk.data.usage.total_tokens
                        }
                    }

        except SDKError as e:
            yield {"text": f"[ERROR: Mistral stream interrupted: {str(e)}]", "usage": None}