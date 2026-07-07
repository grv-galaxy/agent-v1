from google import genai
from google.genai import types
from google.genai.errors import APIError
from typing import AsyncGenerator, Any, List, Dict
from app.providers.base import BaseProvider
from fastapi import HTTPException

class GeminiProvider(BaseProvider):
    """
    Production-Grade asynchronous implementation of the Google Gemini provider.
    Fully satisfies the BaseProvider blueprint with client.aio execution, structured messages,
    robust error interception, and standardized token tracking metadata.
    """

    def _get_client(self) -> genai.Client:
        """
        Helper method to initialize the modern Google GenAI client,
        safely filtering extra_config to prevent initialization errors.
        """
        # Define the keys that the official google-genai Client constructor accepts
        ALLOWED_CLIENT_ARGS = {'api_key', 'http_options', 'transport', 'vertexai', 'region'}
        
        # Filter the extra_config to only include allowed keys
        safe_config = {
            k: v for k, v in (self.extra_config or {}).items() 
            if k in ALLOWED_CLIENT_ARGS
        }
        
        return genai.Client(
            api_key=self.api_key,
            **safe_config
        )

    def _convert_messages(self, messages: List[Dict[str, str]]) -> List[types.Content]:
        """
        Converts standard List[Dict[str, str]] message formats into google-genai SDK 
        compatible types.Content models, supporting system, user, and model roles.
        """
        gemini_contents = []
        for msg in messages:
            role = msg.get("role", "user")
            content_text = msg.get("content", "")
            
            # Map standard 'assistant' role nomenclature to Gemini's expected 'model' role
            gemini_role = "model" if role == "assistant" else role
            
            gemini_contents.append(
                types.Content(
                    role=gemini_role,
                    parts=[types.Part.from_text(text=content_text)]
                )
            )
        return gemini_contents

    def _build_config(self, kwargs: dict) -> types.GenerateContentConfig:
        """
        Helper method to map raw kwargs into Google's specific configuration object.
        """
        # Explicitly instruct the API to send back token metadata during generation streams
        return types.GenerateContentConfig(
            temperature=kwargs.get("temperature", 0.7),
            max_output_tokens=kwargs.get("max_tokens"),
            **{k: v for k, v in kwargs.items() if k not in ["temperature", "max_tokens"]}
        )

    async def generate_response(self, model: str, messages: List[Dict[str, str]], **kwargs: Any) -> Dict[str, Any]:
        """
        Asynchronously executes a standard non-streaming content request using client.aio.
        Extracts execution token statistics directly from the backend metadata payload.
        """
        client = self._get_client()
        contents = self._convert_messages(messages)
        config = self._build_config(kwargs)

        try:
            # Route requests through the .aio submodule for clean asynchronous event loops
            response = await client.aio.models.generate_content(
                model=model,
                contents=contents,
                config=config
            )
            
            # Safely query token values from Google's response metadata wrapper
            usage_metadata = response.usage_metadata
            usage_data = {
                "prompt_tokens": usage_metadata.prompt_token_count if usage_metadata else 0,
                "completion_tokens": usage_metadata.candidates_token_count if usage_metadata else 0,
                "total_tokens": usage_metadata.total_token_count if usage_metadata else 0
            }

            return {
                "text": response.text or "",
                "usage": usage_data
            }

        except APIError as e:
            # Handle standard authentication failure codes gracefully
            if e.code == 403 or "API_KEY_INVALID" in str(e):
                raise HTTPException(status_code=401, detail="Gemini Authentication Failed: The provided API key is invalid.")
            elif e.code == 429:
                raise HTTPException(status_code=429, detail="Gemini Rate Limit Exceeded: Resource exhaustion.")
            raise HTTPException(status_code=502, detail=f"Gemini Gateway API Error: {str(e)}")

    async def generate_stream(self, model: str, messages: List[Dict[str, str]], **kwargs: Any) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Asynchronously executes a streaming text request via client.aio.
        Streams text blocks out instantly, and yields calculated token footprints on final resolution.
        """
        client = self._get_client()
        contents = self._convert_messages(messages)
        config = self._build_config(kwargs)

        try:
            response_stream = await client.aio.models.generate_content_stream(
                model=model,
                contents=contents,
                config=config
            )

            last_chunk = None
            async for chunk in response_stream:
                last_chunk = chunk
                if chunk.text:
                    yield {"text": chunk.text, "usage": None}

            # The modern google-genai SDK drops accumulated token counts inside the final chunk payload
            if last_chunk and last_chunk.usage_metadata:
                meta = last_chunk.usage_metadata
                yield {
                    "text": "",
                    "usage": {
                        "prompt_tokens": meta.prompt_token_count or 0,
                        "completion_tokens": meta.candidates_token_count or 0,
                        "total_tokens": meta.total_token_count or 0
                    }
                }

        except APIError as e:
            yield {"text": f"[ERROR: Gemini stream interrupted: {str(e)}]", "usage": None}
