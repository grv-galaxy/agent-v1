import openai
from openai import AsyncOpenAI
from typing import AsyncGenerator, Any, List, Dict
from .base_provider import BaseProvider
from fastapi import HTTPException

class TogetherAIProvider(BaseProvider):
    """
    Production-Grade asynchronous implementation of the Together AI provider.
    Fully satisfies the BaseProvider blueprint by leveraging the OpenAI client spec 
    directed to Together AI's infrastructure, complete with error routing and token tracking.
    """

    def _get_client(self) -> AsyncOpenAI:
        """
        Helper method to initialize an AsyncOpenAI client configured for Together AI.
        """
        # Targets Together AI's foundational inference hub if a customized gateway override isn't supplied
        base_url = self.extra_config.get("base_url") or "https://api.together.xyz/v1"
        return AsyncOpenAI(
            api_key=self.api_key,
            base_url=base_url
        )

    async def generate_response(self, model: str, messages: List[Dict[str, str]], **kwargs: Any) -> Dict[str, Any]:
        """
        Asynchronously executes a standard non-streaming chat completion request.
        Perfect for testing user-provided API keys and initial model response validation.
        """
        client = self._get_client()
        
        temperature = kwargs.get("temperature", 0.7)
        max_tokens = kwargs.get("max_tokens")

        try:
            response = await client.chat.completions.create(
                model=model,
                messages=messages,  # type: ignore
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False,
                **{k: v for k, v in kwargs.items() if k not in ["temperature", "max_tokens"]}
            )
            
            text_content = response.choices[0].message.content or ""
            
            # Map Together AI's response token counters over to your standardized layout blueprint
            usage_data = {
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                "total_tokens": response.usage.total_tokens if response.usage else 0
            }

            return {
                "text": text_content,
                "usage": usage_data
            }

        except openai.AuthenticationError:
            raise HTTPException(status_code=401, detail="Together AI Authentication Failed: The provided API key is invalid.")
        except openai.RateLimitError:
            raise HTTPException(status_code=429, detail="Together AI Rate Limit Exceeded: Please slow down or top up your credit balance.")
        except openai.BadRequestError as e:
            raise HTTPException(status_code=400, detail=f"Together AI Bad Request: {str(e)}")
        except openai.OpenAIError as e:
            raise HTTPException(status_code=502, detail=f"Together AI Gateway API Error: {str(e)}")

    async def generate_stream(self, model: str, messages: List[Dict[str, str]], **kwargs: Any) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Asynchronously executes a highly optimized token streaming request.
        Yields text chunks instantly, delivering accumulated token consumption at stream termination.
        """
        client = self._get_client()
        
        temperature = kwargs.get("temperature", 0.7)
        max_tokens = kwargs.get("max_tokens")

        # Injects the mandatory flag instructing Together AI's proxy layer to push analytical metrics
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
                # 1. Yield real-time text chunks directly down to the websocket or streaming transport layer
                if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                    yield {"text": chunk.choices[0].delta.content, "usage": None}
                
                # 2. Intercept the closing payload chunk that isolates final stream execution pricing
                if hasattr(chunk, 'usage') and chunk.usage is not None:
                    yield {
                        "text": "",
                        "usage": {
                            "prompt_tokens": chunk.usage.prompt_tokens,
                            "completion_tokens": chunk.usage.completion_tokens,
                            "total_tokens": chunk.usage.total_tokens
                        }
                    }

        except openai.OpenAIError as e:
            yield {"text": f"[ERROR: Together AI stream interrupted: {str(e)}]", "usage": None}