import cohere
from cohere import AsyncClient
# Import the absolute base API exception exposed by the Cohere SDK engine
from cohere.core.api_error import ApiError
from typing import AsyncGenerator, Any, List, Dict
from .base_provider import BaseProvider
from fastapi import HTTPException

class CohereProvider(BaseProvider):
    """
    Production-Grade asynchronous implementation of the Cohere provider.
    Fully satisfies the BaseProvider blueprint with AsyncClient execution,
    structured chat history conversion, and robust error fallback parsing.
    """

    def _get_client(self) -> AsyncClient:
        """
        Helper method to initialize the official AsyncClient on-the-fly.
        """
        return AsyncClient(
            api_key=self.api_key,
            base_url=self.extra_config.get("base_url")  # Overrides proxy base targets if injected
        )

    async def generate_response(self, model: str, messages: List[Dict[str, str]], **kwargs: Any) -> Dict[str, Any]:
        """
        Asynchronously executes a standard non-streaming chat completion request.
        """
        client = self._get_client()
        
        # Cohere's native chat endpoint expects the latest message as text, 
        # and prior messages passed separately into chat_history.
        current_message = messages[-1]["content"] if messages else ""
        
        chat_history = []
        if len(messages) > 1:
            for msg in messages[:-1]:
                role = "USER" if msg["role"] == "user" else "CHATBOT"
                chat_history.append({"role": role, "message": msg["content"]})

        try:
            response = await client.chat(
                model=model,
                message=current_message,
                chat_history=chat_history,  # type: ignore
                temperature=kwargs.get("temperature", 0.3),
                max_tokens=kwargs.get("max_tokens"),
                **{k: v for k, v in kwargs.items() if k not in ["temperature", "max_tokens"]}
            )
            
            text_content = response.text or ""
            
            # Standardize Cohere's usage telemetry structure
            usage_data = {
                "prompt_tokens": response.meta.tokens.input_tokens if response.meta and response.meta.tokens else 0,
                "completion_tokens": response.meta.tokens.output_tokens if response.meta and response.meta.tokens else 0,
                "total_tokens": response.meta.tokens.get("total_tokens", 0) if response.meta and response.meta.tokens else 0
            }

            return {
                "text": text_content,
                "usage": usage_data
            }

        except ApiError as e:
            status = getattr(e, "status_code", 502) or 502
            detail_msg = f"Cohere Gateway API Error: {str(e)}"
            if status == 401:
                detail_msg = "Cohere Authentication Failed: The provided API key is invalid."
            elif status == 429:
                detail_msg = "Cohere Rate Limit Exceeded: You have hit your billing limit or concurrency ceiling."
            raise HTTPException(status_code=status, detail=detail_msg)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Cohere Internal Client Exception: {str(e)}")

    async def generate_stream(self, model: str, messages: List[Dict[str, str]], **kwargs: Any) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Asynchronously executes a streaming chat completion request.
        """
        client = self._get_client()
        
        current_message = messages[-1]["content"] if messages else ""
        chat_history = []
        if len(messages) > 1:
            for msg in messages[:-1]:
                role = "USER" if msg["role"] == "user" else "CHATBOT"
                chat_history.append({"role": role, "message": msg["content"]})

        try:
            response_stream = await client.chat_stream(
                model=model,
                message=current_message,
                chat_history=chat_history,  # type: ignore
                temperature=kwargs.get("temperature", 0.3),
                max_tokens=kwargs.get("max_tokens"),
                **{k: v for k, v in kwargs.items() if k not in ["temperature", "max_tokens"]}
            )

            async for chunk in response_stream:
                # 1. Capture incoming real-time text fragment alterations
                if chunk.event_type == "text-generation":
                    yield {"text": chunk.text, "usage": None}
                
                # 2. Intercept the final payload frame containing full metric calculations
                if chunk.event_type == "stream-end" and hasattr(chunk, 'response') and chunk.response.meta:
                    tokens = chunk.response.meta.tokens
                    yield {
                        "text": "",
                        "usage": {
                            "prompt_tokens": tokens.input_tokens if tokens else 0,
                            "completion_tokens": tokens.output_tokens if tokens else 0,
                            "total_tokens": (tokens.input_tokens + tokens.output_tokens) if tokens else 0
                        }
                    }

        except ApiError as e:
            yield {"text": f"[ERROR: Cohere stream interrupted: {str(e)}]", "usage": None}
        except Exception as e:
            yield {"text": f"[ERROR: Cohere connection failure: {str(e)}]", "usage": None}