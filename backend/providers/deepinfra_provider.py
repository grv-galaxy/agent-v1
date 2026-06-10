import openai
from openai import AsyncOpenAI
from typing import AsyncGenerator, Any, List, Dict
from .base_provider import BaseProvider
from fastapi import HTTPException

class DeepInfraProvider(BaseProvider):
    """
    Production-Grade asynchronous implementation of the DeepInfra provider.
    Fully satisfies the BaseProvider blueprint by leveraging the OpenAI client spec
    directed to DeepInfra's architecture, complete with error routing and token tracking.
    """

    def _get_client(self) -> AsyncOpenAI:
        """
        Helper method to initialize an AsyncOpenAI client configured for DeepInfra.
        """
        # DeepInfra adheres explicitly to the OpenAI client standard, 
        # requiring only a targeted base_url redirection.
        base_url = self.extra_config.get("base_url") or "https://api.deepinfra.com/v1/openai"
        return AsyncOpenAI(
            api_key=self.api_key,
            base_url=base_url,
            organization=self.extra_config.get("organization")
        )

    async def generate_response(self, model: str, messages: List[Dict[str, str]], **kwargs: Any) -> Dict[str, Any]:
        """
        Asynchronously executes a standard non-streaming request. Perfect for key verification.
        Extracts token usage stats directly from the returned response object.
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
            
            # Map DeepInfra's usage metadata to our standardized blueprint format
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
            raise HTTPException(status_code=401, detail="DeepInfra Authentication Failed: The provided API key is invalid.")
        except openai.RateLimitError:
            raise HTTPException(status_code=429, detail="DeepInfra Rate Limit Exceeded: Please slow down your requests.")
        except openai.BadRequestError as e:
            raise HTTPException(status_code=400, detail=f"DeepInfra Bad Request: {str(e)}")
        except openai.OpenAIError as e:
            raise HTTPException(status_code=502, detail=f"DeepInfra Gateway API Error: {str(e)}")

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
                if chunk.usage is not None:
                    yield {
                        "text": "",
                        "usage": {
                            "prompt_tokens": chunk.usage.prompt_tokens,
                            "completion_tokens": chunk.usage.completion_tokens,
                            "total_tokens": chunk.usage.total_tokens
                        }
                    }

        except openai.OpenAIError as e:
            yield {"text": f"[ERROR: DeepInfra stream interrupted: {str(e)}]", "usage": None}