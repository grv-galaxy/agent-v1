import openai
from openai import AsyncOpenAI
from typing import AsyncGenerator, Any, List, Dict
from app.providers.base import BaseProvider
from fastapi import HTTPException

class DeepSeekProvider(BaseProvider):
    """
    Production-Grade asynchronous implementation of the DeepSeek provider.
    Fully satisfies the BaseProvider blueprint by leveraging the OpenAI client spec
    directed to DeepSeek's platform architecture, complete with error routing and token tracking.
    """

    def _get_client(self) -> AsyncOpenAI:
        """
        Helper method to initialize an AsyncOpenAI client configured for DeepSeek.
        """
        # DeepSeek adheres explicitly to the OpenAI client standard, 
        # requiring only a targeted base_url redirection.
        base_url = self.extra_config.get("base_url") or "https://api.deepseek.com"
        return AsyncOpenAI(
            api_key=self.api_key,
            base_url=base_url
        )

    async def generate_response(self, model: str, messages: List[Dict[str, str]], **kwargs: Any) -> Dict[str, Any]:
        """
        Asynchronously executes a standard non-streaming request. Perfect for key verification.
        Extracts token usage stats directly from the standard response object.
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
            
            # Map DeepSeek's usage metrics to our standardized blueprint format
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
            raise HTTPException(status_code=401, detail="DeepSeek Authentication Failed: The provided API key is invalid.")
        except openai.RateLimitError:
            raise HTTPException(status_code=429, detail="DeepSeek Rate Limit Exceeded: Balance exhausted or rate limit hit.")
        except openai.BadRequestError as e:
            raise HTTPException(status_code=400, detail=f"DeepSeek Bad Request: {str(e)}")
        except openai.OpenAIError as e:
            raise HTTPException(status_code=502, detail=f"DeepSeek Gateway API Error: {str(e)}")

    async def generate_stream(self, model: str, messages: List[Dict[str, str]], **kwargs: Any) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Asynchronously executes a streaming request yielding text chunks in real-time.
        Delivers text instantly, and passes an aggregated usage tracking summary chunk at termination.
        """
        client = self._get_client()
        
        temperature = kwargs.get("temperature", 0.7)
        max_tokens = kwargs.get("max_tokens")

        # Request token usage metrics inside active streams following the OpenAI specifications
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
                
                # 2. Intercept final usage metrics frame passed right after completion
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
            yield {"text": f"[ERROR: DeepSeek stream interrupted: {str(e)}]", "usage": None}
