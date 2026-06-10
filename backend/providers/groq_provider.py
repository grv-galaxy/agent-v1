import groq
from groq import AsyncGroq
from typing import AsyncGenerator, Any, List, Dict
from .base_provider import BaseProvider
from fastapi import HTTPException

class GroqProvider(BaseProvider):
    """
    Production-Grade asynchronous implementation of the Groq provider.
    Fully satisfies the BaseProvider blueprint with AsyncGroq execution,
    structured messages, robust error interception, and standardized token tracking metadata.
    """

    def _get_client(self) -> AsyncGroq:
        """
        Helper method to initialize the official AsyncGroq client on-the-fly.
        """
        return AsyncGroq(
            api_key=self.api_key,
            base_url=self.extra_config.get("base_url")  # Overrides host endpoint if utilizing a custom network proxy
        )

    async def generate_response(self, model: str, messages: List[Dict[str, str]], **kwargs: Any) -> Dict[str, Any]:
        """
        Asynchronously executes a standard non-streaming chat completion request.
        Ideal for validating user-submitted API credentials instantly during onboarding.
        """
        client = self._get_client()
        
        temperature = kwargs.get("temperature", 0.7)
        max_tokens = kwargs.get("max_tokens")

        try:
            # Native asynchronous call routed through Groq's chat completions submodule
            response = await client.chat.completions.create(
                model=model,
                messages=messages,  # type: ignore
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False,
                **{k: v for k, v in kwargs.items() if k not in ["temperature", "max_tokens"]}
            )
            
            text_content = response.choices[0].message.content or ""
            
            # Map Groq's usage block metrics onto your standardized blueprint payload
            usage_data = {
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                "total_tokens": response.usage.total_tokens if response.usage else 0
            }

            return {
                "text": text_content,
                "usage": usage_data
            }

        except groq.AuthenticationError:
            raise HTTPException(status_code=401, detail="Groq Authentication Failed: The provided API key is invalid.")
        except groq.RateLimitError:
            raise HTTPException(status_code=429, detail="Groq Rate Limit Exceeded: You have hit a concurrency or token ceiling.")
        except groq.BadRequestError as e:
            raise HTTPException(status_code=400, detail=f"Groq Bad Request: {str(e)}")
        except groq.APIError as e:
            raise HTTPException(status_code=502, detail=f"Groq Gateway API Error: {str(e)}")

    async def generate_stream(self, model: str, messages: List[Dict[str, str]], **kwargs: Any) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Asynchronously executes an ultra-fast streaming request via client.chat.completions.create.
        Delivers text tokens instantly, yielding final token metrics upon stream termination.
        """
        client = self._get_client()
        
        temperature = kwargs.get("temperature", 0.7)
        max_tokens = kwargs.get("max_tokens")

        # Instructs Groq's inference cluster to bundle complete usage analytics into the final frame
        # stream_options = {"include_usage": True}

        try:
            response_stream = await client.chat.completions.create(
                model=model,
                messages=messages,  # type: ignore
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
                # stream_options=stream_options,
                **{k: v for k, v in kwargs.items() if k not in ["temperature", "max_tokens", "stream_options"]}
            )

            async for chunk in response_stream:
                # 1. Process normal incoming stream text tokens
                if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                    yield {"text": chunk.choices[0].delta.content, "usage": None}
                
                # 2. Intercept final usage metrics frame (sent by Groq when choices list is empty)
                if hasattr(chunk, 'usage') and chunk.usage is not None:
                    yield {
                        "text": "",
                        "usage": {
                            "prompt_tokens": chunk.usage.prompt_tokens,
                            "completion_tokens": chunk.usage.completion_tokens,
                            "total_tokens": chunk.usage.total_tokens
                        }
                    }

        except groq.APIError as e:
            yield {"text": f"[ERROR: Groq stream interrupted: {str(e)}]", "usage": None}