import openai
from openai import AsyncOpenAI
from typing import AsyncGenerator, Any, List, Dict
from app.providers.base import BaseProvider
from fastapi import HTTPException

class OpenRouterProvider(BaseProvider):
    """
    Production-Grade asynchronous implementation of the OpenRouter provider.
    Fully satisfies the BaseProvider blueprint by leveraging the OpenAI client spec 
    directed to OpenRouter's routing engine, complete with error routing and token tracking.
    """

    def _get_client(self) -> AsyncOpenAI:
        """
        Helper method to initialize an AsyncOpenAI client configured for OpenRouter.
        """
        base_url = self.extra_config.get("base_url") or "https://openrouter.ai/api/v1"
        return AsyncOpenAI(
            api_key=self.api_key,
            base_url=base_url
        )

    async def generate_response(self, model: str, messages: List[Dict[str, str]], **kwargs: Any) -> Dict[str, Any]:
        """
        Asynchronously executes a standard non-streaming chat completion request.
        Perfect for checking credentials or generating analytical insights from small contexts.
        """
        client = self._get_client()
        
        temperature = kwargs.get("temperature", 0.7)
        max_tokens = kwargs.get("max_tokens") or 4096

        try:
            # We pass down extra OpenRouter-specific headers if provided in extra_config
            # (e.g., HTTP-Referer or X-Title for OpenRouter rankings)
            extra_headers = self.extra_config.get("headers", {})

            response = await client.chat.completions.create(
                model=model,
                messages=messages,  # type: ignore
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False,
                extra_headers=extra_headers,
                **{k: v for k, v in kwargs.items() if k not in ["temperature", "max_tokens", "headers"]}
            )
            
            text_content = response.choices[0].message.content or ""
            
            # Map OpenRouter's response token counters over to your standardized layout blueprint
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
            raise HTTPException(status_code=401, detail="OpenRouter Authentication Failed: Invalid API Key provided.")
        except openai.RateLimitError:
            raise HTTPException(status_code=429, detail="OpenRouter Rate Limit Exceeded: You have hit a concurrency limit or ran out of credits.")
        except openai.BadRequestError as e:
            raise HTTPException(status_code=400, detail=f"OpenRouter Bad Request: {str(e)}")
        except openai.OpenAIError as e:
            raise HTTPException(status_code=502, detail=f"OpenRouter Gateway Error: {str(e)}")

    async def generate_stream(self, model: str, messages: List[Dict[str, str]], **kwargs: Any) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Asynchronously executes a real-time text streaming request.
        Yields text chunks instantly, providing final token metadata stats upon stream termination.
        """
        client = self._get_client()
        
        temperature = kwargs.get("temperature", 0.7)
        max_tokens = kwargs.get("max_tokens") or 4096
        extra_headers = self.extra_config.get("headers", {})

        # Instructs OpenRouter to drop an additional chunk with token totals at the end of the stream
        stream_options = {"include_usage": True}

        try:
            response_stream = await client.chat.completions.create(
                model=model,
                messages=messages,  # type: ignore
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
                stream_options=stream_options,
                extra_headers=extra_headers,
                **{k: v for k, v in kwargs.items() if k not in ["temperature", "max_tokens", "stream_options", "headers"]}
            )

            async for chunk in response_stream:
                # 1. Yield real-time content data strings directly to the frontend layout engine
                if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                    yield {"text": chunk.choices[0].delta.content, "usage": None}
                
                # 2. Intercept the final payload frame holding aggregate generation metrics
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
            yield {"text": f"[ERROR: OpenRouter stream interrupted: {str(e)}]", "usage": None}
