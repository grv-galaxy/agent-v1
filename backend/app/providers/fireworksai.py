import fireworks
from fireworks.client import AsyncFireworks
from typing import AsyncGenerator, Any, List, Dict
from app.providers.base import BaseProvider
from fastapi import HTTPException

class FireworksAIProvider(BaseProvider):
    """
    Production-Grade asynchronous implementation of the Fireworks AI provider.
    Fully satisfies the BaseProvider blueprint with AsyncFireworks execution,
    structured messages, robust error interception, and standardized token tracking metadata.
    """

    def _get_client(self) -> AsyncFireworks:
        """
        Helper method to initialize the official AsyncFireworks client on-the-fly.
        """
        # If your setup uses an enterprise network gateway proxy, 
        # passing base_url overrides the default serverless inference path safely.
        base_url = self.extra_config.get("base_url")
        return AsyncFireworks(
            api_key=self.api_key,
            base_url=base_url
        )

    async def generate_response(self, model: str, messages: List[Dict[str, str]], **kwargs: Any) -> Dict[str, Any]:
        """
        Asynchronously executes a standard non-streaming text completion request.
        Extracts token usage metrics directly from the standard response tracking block.
        """
        client = self._get_client()
        
        temperature = kwargs.get("temperature", 0.7)
        max_tokens = kwargs.get("max_tokens")

        try:
            response = await client.chat.completions.acreate(
                model=model,
                messages=messages,  # type: ignore
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False,
                **{k: v for k, v in kwargs.items() if k not in ["temperature", "max_tokens"]}
            )
            
            text_content = response.choices[0].message.content or ""
            
            # Map Fireworks' token usage blocks onto your standardized layout
            usage_data = {
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                "total_tokens": response.usage.total_tokens if response.usage else 0
            }

            return {
                "text": text_content,
                "usage": usage_data
            }

        except Exception as e:
            # Safely capture common API exception conditions and wrap them in clear HTTP statuses
            err_msg = str(e)
            if "unauthorized" in err_msg.lower() or "api key" in err_msg.lower():
                raise HTTPException(status_code=401, detail="Fireworks AI Authentication Failed: The provided API key is invalid.")
            elif "rate limit" in err_msg.lower() or "429" in err_msg:
                raise HTTPException(status_code=429, detail="Fireworks AI Rate Limit Exceeded: Please slow down your requests.")
            raise HTTPException(status_code=502, detail=f"Fireworks AI Gateway Error: {err_msg}")

    async def generate_stream(self, model: str, messages: List[Dict[str, str]], **kwargs: Any) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Asynchronously executes a streaming chat completion request.
        Pushes out raw text content modifications instantly, and yields total token tracking weights at termination.
        """
        client = self._get_client()
        
        temperature = kwargs.get("temperature", 0.7)
        max_tokens = kwargs.get("max_tokens")

        # Instructs Fireworks to bundle the final aggregate usage stats chunk before closing the stream
        stream_options = {"include_usage": True}

        try:
            response_stream = await client.chat.completions.acreate(
                model=model,
                messages=messages,  # type: ignore
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
                stream_options=stream_options,
                **{k: v for k, v in kwargs.items() if k not in ["temperature", "max_tokens", "stream_options"]}
            )

            async for chunk in response_stream:
                # 1. Yield real-time chunk data content modifications straight to the client UI
                if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                    yield {"text": chunk.choices[0].delta.content, "usage": None}
                
                # 2. Intercept the final payload frame containing full usage calculations
                if hasattr(chunk, 'usage') and chunk.usage is not None:
                    yield {
                        "text": "",
                        "usage": {
                            "prompt_tokens": chunk.usage.prompt_tokens,
                            "completion_tokens": chunk.usage.completion_tokens,
                            "total_tokens": chunk.usage.total_tokens
                        }
                    }

        except Exception as e:
            yield {"text": f"[ERROR: Fireworks AI stream interrupted: {str(e)}]", "usage": None}
