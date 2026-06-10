import cerebras
from cerebras.cloud.sdk import AsyncCerebras
from typing import AsyncGenerator, Any, List, Dict
from .base_provider import BaseProvider
from fastapi import HTTPException

class CerebrasProvider(BaseProvider):
    """
    Production-Grade asynchronous implementation of the Cerebras Cloud provider.
    Fully satisfies the BaseProvider blueprint with AsyncCerebras execution, 
    structured messages, robust error interception, and standardized token tracking metadata.
    """

    def _get_client(self) -> AsyncCerebras:
        """
        Helper method to initialize the official AsyncCerebras client on-the-fly.
        """
        return AsyncCerebras(
            api_key=self.api_key,
            base_url=self.extra_config.get("base_url")  # Overrides API host endpoint if utilizing a custom network proxy
        )

    async def generate_response(self, model: str, messages: List[Dict[str, str]], **kwargs: Any) -> Dict[str, Any]:
        """
        Asynchronously executes a standard non-streaming chat completion request.
        Perfect for rapid API key verification setups during configuration onboarding.
        """
        client = self._get_client()
        
        temperature = kwargs.get("temperature", 0.7)
        max_tokens = kwargs.get("max_tokens")

        try:
            response = await client.chat.completions.create(
                model=model,
                messages=messages,  # type: ignore (handles List[Dict[str, str]])
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False,
                **{k: v for k, v in kwargs.items() if k not in ["temperature", "max_tokens"]}
            )
            
            text_content = response.choices[0].message.content or ""
            
            # Map Cerebras' usage block metrics to our standardized blueprint format
            usage_data = {
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                "total_tokens": response.usage.total_tokens if response.usage else 0
            }

            return {
                "text": text_content,
                "usage": usage_data
            }

        except cerebras.cloud.sdk.AuthenticationError:
            raise HTTPException(status_code=401, detail="Cerebras Authentication Failed: The provided API key is invalid.")
        except cerebras.cloud.sdk.RateLimitError:
            raise HTTPException(status_code=429, detail="Cerebras Rate Limit Exceeded: Please slow down your requests.")
        except cerebras.cloud.sdk.BadRequestError as e:
            raise HTTPException(status_code=400, detail=f"Cerebras Bad Request: {str(e)}")
        except cerebras.cloud.sdk.APIError as e:
            raise HTTPException(status_code=502, detail=f"Cerebras Gateway API Error: {str(e)}")

    async def generate_stream(self, model: str, messages: List[Dict[str, str]], **kwargs: Any) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Asynchronously executes an ultra-low latency token stream request.
        Pushes out raw text modifications instantly, and yields final token counts at termination.
        """
        client = self._get_client()
        
        temperature = kwargs.get("temperature", 0.7)
        max_tokens = kwargs.get("max_tokens")

        # Cerebras follows OpenAI's syntax blueprint for requesting token usage records inside active streams
        stream_options = {"include_usage": True}

        try:
            response_stream = await client.chat.completions.create(
                model=model,
                messages=messages,  # type: ignore
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
                stream_options=stream_options,
                **{k: v for k, v in kwargs.items() if k not in ["temperature", "max_tokens", "stream_options"]}
            )

            async for chunk in response_stream:
                # 1. Process normal incoming stream text tokens
                if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                    yield {"text": chunk.choices[0].delta.content, "usage": None}
                
                # 2. Intercept final usage metrics frame (sent by Cerebras when text content finishes)
                if hasattr(chunk, 'usage') and chunk.usage is not None:
                    yield {
                        "text": "",
                        "usage": {
                            "prompt_tokens": chunk.usage.prompt_tokens,
                            "completion_tokens": chunk.usage.completion_tokens,
                            "total_tokens": chunk.usage.total_tokens
                        }
                    }

        except cerebras.cloud.sdk.APIError as e:
            yield {"text": f"[ERROR: Cerebras stream interrupted: {str(e)}]", "usage": None}