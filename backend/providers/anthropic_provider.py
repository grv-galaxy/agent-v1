import anthropic
from anthropic import AsyncAnthropic
from typing import AsyncGenerator, Any, List, Dict
from .base_provider import BaseProvider
from fastapi import HTTPException

class AnthropicProvider(BaseProvider):
    """
    Production-Grade asynchronous implementation of the Anthropic (Claude) provider.
    Fully satisfies the BaseProvider blueprint with async execution, structured messages,
    robust error interception, and standardized token tracking metadata.
    """

    def _get_client(self) -> AsyncAnthropic:
        """
        Helper method to initialize the official AsyncAnthropic client on-the-fly.
        """
        return AsyncAnthropic(
            api_key=self.api_key,
            base_url=self.extra_config.get("base_url")
        )

    async def generate_response(self, model: str, messages: List[Dict[str, str]], **kwargs: Any) -> Dict[str, Any]:
        """
        Asynchronously executes a standard non-streaming message request.
        Safely captures usage stats and translates API exceptions to clean HTTP statuses.
        """
        client = self._get_client()
        
        # Anthropic REQUIRES max_tokens explicitly set per-request.
        max_tokens = kwargs.get("max_tokens", 4096)
        temperature = kwargs.get("temperature", 0.7)

        try:
            response = await client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=messages,  # type: ignore (handles List[Dict[str, str]])
                **{k: v for k, v in kwargs.items() if k not in ["max_tokens", "temperature"]}
            )
            
            # Extract standard content text safely
            text_content = response.content[0].text if response.content else ""
            
            # Extract token metrics directly from Anthropic's usage block
            usage_data = {
                "prompt_tokens": response.usage.input_tokens if response.usage else 0,
                "completion_tokens": response.usage.output_tokens if response.usage else 0,
                "total_tokens": (response.usage.input_tokens + response.usage.output_tokens) if response.usage else 0
            }

            return {
                "text": text_content,
                "usage": usage_data
            }

        except anthropic.AuthenticationError:
            raise HTTPException(status_code=401, detail="Anthropic Authentication Failed: The provided API key is invalid.")
        except anthropic.RateLimitError:
            raise HTTPException(status_code=429, detail="Anthropic Rate Limit Exceeded: Please slow down your requests.")
        except anthropic.BadRequestError as e:
            raise HTTPException(status_code=400, detail=f"Anthropic Bad Request: {str(e)}")
        except anthropic.AnthropicError as e:
            raise HTTPException(status_code=502, detail=f"Anthropic Gateway API Error: {str(e)}")

    async def generate_stream(self, model: str, messages: List[Dict[str, str]], **kwargs: Any) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Asynchronously executes a context-managed text stream.
        Yields tokens instantly during generation, and delivers token usage calculations at the final event.
        """
        client = self._get_client()
        
        max_tokens = kwargs.get("max_tokens", 4096)
        temperature = kwargs.get("temperature", 0.7)

        try:
            # Using client.messages.stream handles context framing over an async context manager
            async with client.messages.stream(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=messages,  # type: ignore
                **{k: v for k, v in kwargs.items() if k not in ["max_tokens", "temperature"]}
            ) as stream:
                
                # Stream out raw text updates instantly to ChatPage.jsx
                async for text in stream.text_stream:
                    yield {"text": text, "usage": None}
                
                # Once text generation finishes, pull final stream event usage metrics accumulated by the SDK
                final_message = await stream.get_final_message()
                if final_message and final_message.usage:
                    yield {
                        "text": "",
                        "usage": {
                            "prompt_tokens": final_message.usage.input_tokens,
                            "completion_tokens": final_message.usage.output_tokens,
                            "total_tokens": final_message.usage.input_tokens + final_message.usage.output_tokens
                        }
                    }

        except anthropic.AnthropicError as e:
            # Streams require structural error forwarding to prevent closing the WebSocket blindly
            yield {"text": f"[ERROR: Anthropic stream interrupted: {str(e)}]", "usage": None}