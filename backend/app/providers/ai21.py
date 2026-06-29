import ai21
from ai21 import AsyncAI21Client
from ai21.models.chat import ChatMessage
# Use the absolute, standard base exception class that exists across all version variations
from ai21.errors import AI21Error, AI21APIError
from typing import AsyncGenerator, Any, List, Dict
from app.providers.base import BaseProvider
from fastapi import HTTPException

class AI21Provider(BaseProvider):
    """
    Production-Grade asynchronous implementation of the AI21 Labs provider.
    Fully satisfies the BaseProvider blueprint with AsyncAI21Client execution, 
    structured messages, robust error handling, and standardized token tracking metadata.
    """

    def _get_client(self) -> AsyncAI21Client:
        """
        Helper method to initialize the official AsyncAI21Client on-the-fly.
        """
        return AsyncAI21Client(
            api_key=self.api_key,
            api_host=self.extra_config.get("base_url")  # Overrides host endpoint if utilizing a custom network proxy
        )

    def _convert_messages(self, messages: List[Dict[str, str]]) -> List[ChatMessage]:
        """
        Converts standard List[Dict[str, str]] messages into AI21 SDK-required 
        ChatMessage model instances.
        """
        try:
            return [
                ChatMessage(
                    role=msg.get("role", "user"),
                    text=msg.get("content", "")
                )
                for msg in messages
            ]
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"AI21 Message Formatting Error: {str(e)}")

    async def generate_response(self, model: str, messages: List[Dict[str, str]], **kwargs: Any) -> Dict[str, Any]:
        """
        Asynchronously executes a standard non-streaming request. Perfect for credential verification.
        Extracts token usage parameters directly from the returned response payload.
        """
        client = self._get_client()
        ai21_messages = self._convert_messages(messages)
        
        temperature = kwargs.get("temperature", 0.4)
        max_tokens = kwargs.get("max_tokens", 1024)

        try:
            response = await client.chat.completions.create(
                model=model,
                messages=ai21_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False,
                **{k: v for k, v in kwargs.items() if k not in ["temperature", "max_tokens"]}
            )
            
            text_content = response.choices[0].message.content or ""
            
            usage_data = {
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                "total_tokens": response.usage.total_tokens if response.usage else 0
            }

            return {
                "text": text_content,
                "usage": usage_data
            }

        except AI21APIError as e:
            # Safely capture specific remote engine status codes (e.g., 401 or 429)
            status = getattr(e, "status_code", 502) or 502
            detail_msg = f"AI21 Gateway API Error: {str(e)}"
            if status == 401:
                detail_msg = "AI21 Authentication Failed: The provided API key is invalid."
            elif status == 429:
                detail_msg = "AI21 Rate Limit Exceeded: Balance exhausted or threshold met."
            raise HTTPException(status_code=status, detail=detail_msg)
            
        except AI21Error as e:
            # Fallback wrapper for general SDK internal anomalies
            raise HTTPException(status_code=500, detail=f"AI21 Client Internal Execution Defect: {str(e)}")

    async def generate_stream(self, model: str, messages: List[Dict[str, str]], **kwargs: Any) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Asynchronously executes a streaming text request.
        Pushes out raw text content modifications instantly, and yields total token usage updates at the end.
        """
        client = self._get_client()
        ai21_messages = self._convert_messages(messages)
        
        temperature = kwargs.get("temperature", 0.4)
        max_tokens = kwargs.get("max_tokens", 1024)

        try:
            response_stream = await client.chat.completions.create(
                model=model,
                messages=ai21_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
                **{k: v for k, v in kwargs.items() if k not in ["temperature", "max_tokens"]}
            )

            async for chunk in response_stream:
                if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                    yield {"text": chunk.choices[0].delta.content, "usage": None}
                
                if hasattr(chunk, 'usage') and chunk.usage is not None:
                    yield {
                        "text": "",
                        "usage": {
                            "prompt_tokens": chunk.usage.prompt_tokens,
                            "completion_tokens": chunk.usage.completion_tokens,
                            "total_tokens": chunk.usage.total_tokens
                        }
                    }

        except AI21Error as e:
            yield {"text": f"[ERROR: AI21 stream interrupted: {str(e)}]", "usage": None}
