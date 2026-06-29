import openai
from openai import AsyncOpenAI
from typing import AsyncGenerator, Any, List, Dict
from app.providers.base import BaseProvider
from fastapi import HTTPException

class NvidiaNimProvider(BaseProvider):
    """
    Production-Grade asynchronous implementation of the NVIDIA NIM / API Catalog provider.
    Fully satisfies the BaseProvider blueprint by leveraging the OpenAI client spec 
    directed to NVIDIA's high-throughput architecture, complete with error routing and token tracking.
    """

    def _get_client(self) -> AsyncOpenAI:
        """
        Helper method to initialize an AsyncOpenAI client configured for NVIDIA NIM.
        Supports both the cloud-hosted NVIDIA API Catalog and localized self-hosted NIM instances.
        """
        # Falls back to the global multi-cloud integration gateway if a local base_url isn't injected.
        base_url = self.extra_config.get("base_url") or "https://integrate.api.nvidia.com/v1"
        return AsyncOpenAI(
            api_key=self.api_key,
            base_url=base_url
        )

    async def generate_response(self, model: str, messages: List[Dict[str, str]], **kwargs: Any) -> Dict[str, Any]:
        """
        Asynchronously executes a standard non-streaming chat completion request.
        Perfect for verifying API tokens and testing NIM container availability during onboarding.
        """
        client = self._get_client()
        
        temperature = kwargs.get("temperature", 0.5)  # NVIDIA NIM models optimize well at 0.5 default
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
            
            # Map NVIDIA's response token counters over to your standardized layout blueprint
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
            raise HTTPException(status_code=401, detail="NVIDIA NIM Authentication Failed: Invalid API Token provided.")
        except openai.RateLimitError:
            raise HTTPException(status_code=429, detail="NVIDIA NIM Rate Limit Exceeded: Concurrency block or credit exhaustion.")
        except openai.BadRequestError as e:
            raise HTTPException(status_code=400, detail=f"NVIDIA NIM Bad Request: {str(e)}")
        except openai.OpenAIError as e:
            raise HTTPException(status_code=502, detail=f"NVIDIA NIM Inference Engine Error: {str(e)}")

    async def generate_stream(self, model: str, messages: List[Dict[str, str]], **kwargs: Any) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Asynchronously executes an accelerated text streaming request.
        Yields text chunks immediately, providing total token performance stats upon connection completion.
        """
        client = self._get_client()
        
        temperature = kwargs.get("temperature", 0.5)
        max_tokens = kwargs.get("max_tokens")

        # Tells NVIDIA's TensorRT-LLM / vLLM underlying backend server to append an analytical token count frame
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
            yield {"text": f"[ERROR: NVIDIA NIM stream interrupted: {str(e)}]", "usage": None}
