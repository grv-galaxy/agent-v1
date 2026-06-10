import huggingface_hub
from huggingface_hub import AsyncInferenceClient
from huggingface_hub.utils import HfHubHTTPError
from typing import AsyncGenerator, Any, List, Dict
from .base_provider import BaseProvider
from fastapi import HTTPException

class HuggingFaceProvider(BaseProvider):
    """
    Production-Grade asynchronous implementation of the Hugging Face Inference API provider.
    Fully satisfies the BaseProvider blueprint with AsyncInferenceClient execution,
    structured messages, robust error interception, and standardized token tracking metadata.
    """

    def _get_client(self) -> AsyncInferenceClient:
        """
        Helper method to initialize the official AsyncInferenceClient on-the-fly.
        """
        # Extra_config can accept a 'base_url' if routing to a Hugging Face Dedicated Inference Endpoint,
        # otherwise it defaults to the standard Hugging Face Serverless Inference API architecture.
        base_url = self.extra_config.get("base_url")
        return AsyncInferenceClient(
            token=self.api_key,
            base_url=base_url
        )

    async def generate_response(self, model: str, messages: List[Dict[str, str]], **kwargs: Any) -> Dict[str, Any]:
        """
        Asynchronously executes a standard non-streaming text completion request.
        Perfect for verifying API tokens and confirming endpoint availability during onboarding.
        """
        client = self._get_client()
        
        temperature = kwargs.get("temperature", 0.7)
        max_tokens = kwargs.get("max_tokens")

        try:
            # Async completion routing via Hugging Face's OpenAI-compatible chat API
            response = await client.chat.completions.create(
                model=model,
                messages=messages,  # type: ignore
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False,
                **{k: v for k, v in kwargs.items() if k not in ["temperature", "max_tokens"]}
            )
            
            text_content = response.choices[0].message.content or ""
            
            # Standardize Hugging Face's response tracking metrics into your blueprint schema
            usage_data = {
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                "total_tokens": response.usage.total_tokens if response.usage else 0
            }

            return {
                "text": text_content,
                "usage": usage_data
            }

        except HfHubHTTPError as e:
            # Distinguish common HTTP error codes returned by Hugging Face gateways
            status_code = e.response.status_code if e.response else 502
            if status_code == 401:
                raise HTTPException(status_code=401, detail="Hugging Face Authentication Failed: Invalid or expired User Access Token.")
            elif status_code == 429:
                raise HTTPException(status_code=429, detail="Hugging Face Rate Limit Exceeded: Rate limit reached or subscription cap hit.")
            elif status_code == 503:
                raise HTTPException(status_code=503, detail="Hugging Face Service Unavailable: Model is currently loading or down.")
            raise HTTPException(status_code=status_code, detail=f"Hugging Face API Error: {str(e)}")

    async def generate_stream(self, model: str, messages: List[Dict[str, str]], **kwargs: Any) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Asynchronously executes a streaming chat completion request.
        Streams text tokens out immediately to ensure fluid UI response animations.
        """
        client = self._get_client()
        
        temperature = kwargs.get("temperature", 0.7)
        max_tokens = kwargs.get("max_tokens")

        # Tells Hugging Face's TGI/VLLM backend clusters to emit a final usage metadata token block
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
                # 1. Yield real-time chunk data content deltas straight to the user layout interface
                if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                    yield {"text": chunk.choices[0].delta.content, "usage": None}
                
                # 2. Intercept the final stream block payload holding aggregate token tracking counts
                if hasattr(chunk, 'usage') and chunk.usage is not None:
                    yield {
                        "text": "",
                        "usage": {
                            "prompt_tokens": chunk.usage.prompt_tokens,
                            "completion_tokens": chunk.usage.completion_tokens,
                            "total_tokens": chunk.usage.total_tokens
                        }
                    }

        except HfHubHTTPError as e:
            yield {"text": f"[ERROR: Hugging Face stream interrupted: {str(e)}]", "usage": None}