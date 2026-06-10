from typing import Dict, Type, Any, Optional
from fastapi import HTTPException

# Core Blueprint Abstract Base
from .base_provider import BaseProvider

# Import Concrete Adapter Implementations
from .openai_provider import OpenAIProvider
from .gemini_provider import GeminiProvider
from .anthropic_provider import AnthropicProvider
from .mistral_provider import MistralProvider
from .ai21_provider import AI21Provider
from .cerebras_provider import CerebrasProvider
from .cohere_provider import CohereProvider
from .deepinfra_provider import DeepInfraProvider
from .deepseek_provider import DeepSeekProvider
from .fireworkai_provider import FireworksAIProvider
from .groq_provider import GroqProvider
from .huggingface_provider import HuggingFaceProvider
from .nvidianim_provider import NvidiaNimProvider
from .openrouter_provider import OpenRouterProvider
from .togetherai_provider import TogetherAIProvider


class ProviderFactory:
    """
    Production traffic controller responsible for mapping string identifiers 
    to concrete LLM client adapter instances with automated error handling.
    """

    # Centralized Registry mapping provider keys directly to their explicit Adapter Class
    _registry: Dict[str, Type[BaseProvider]] = {
        "openai": OpenAIProvider,
        "gemini": GeminiProvider,
        "anthropic": AnthropicProvider,
        "mistral": MistralProvider,
        "ai21": AI21Provider,
        "cerebras": CerebrasProvider,
        "cohere": CohereProvider,
        "deepinfra": DeepInfraProvider,
        "deepseek": DeepSeekProvider,
        "fireworksai": FireworksAIProvider,
        "groq": GroqProvider,
        "huggingface": HuggingFaceProvider,
        "nvidianim": NvidiaNimProvider,
        "openrouter": OpenRouterProvider,
        "togetherai": TogetherAIProvider
    }

    @classmethod
    def get_supported_providers(cls) -> list[str]:
        """
        Returns an immutable snapshot of all registered, active vendor adapters.
        """
        return list(cls._registry.keys())

    @classmethod
    def register_custom_provider(cls, name: str, provider_class: Type[BaseProvider]) -> None:
        """
        Extension hook allowing runtime registration of custom internal models
        or custom local mock providers for sandbox testing environments.
        """
        if not issubclass(provider_class, BaseProvider):
            raise TypeError("Custom providers must explicitly subclass the base BaseProvider type.")
        cls._registry[name.lower()] = provider_class

    @classmethod
    def create(
        cls, 
        provider_name: str, 
        api_key: str, 
        extra_config: Optional[Dict[str, Any]] = None
    ) -> BaseProvider:
        """
        Creational factory method that resolves the requested provider identifier,
        validates parameters, and yields an instantiated standalone asynchronous client wrapper.

        Args:
            provider_name: Case-insensitive label for target LLM core infrastructure.
            api_key: Explicit bearer authentication credential string.
            extra_config: Key/Value configuration mutations (e.g., base_url modifications).
        """
        normalized_name = provider_name.strip().lower()

        # 1. Enforce validation guardrail against structural routing anomalies
        if not normalized_name:
            raise HTTPException(
                status_code=400, 
                detail="Routing Malformation: Provider designation argument cannot be left blank."
            )

        if not api_key or not api_key.strip():
            raise HTTPException(
                status_code=401, 
                detail=f"Authentication Denied: Missing or unpopulated API token for provider allocation: '{provider_name}'."
            )

        # 2. Extract and resolve target provider mapping reference from registry map
        provider_class = cls._registry.get(normalized_name)

        if not provider_class:
            supported = ", ".join(cls.get_supported_providers())
            raise HTTPException(
                status_code=422,
                detail=f"Unsupported Provider Mapping: '{provider_name}' matches no active adapters. "
                       f"Available integrations are: [{supported}]."
            )

        # 3. Secure instance instantiation isolation boundary passing configurations safely
        try:
            config_payload = extra_config or {}
            return provider_class(
                api_key=api_key.strip(), 
                extra_config=config_payload
            )
        except Exception as instantiation_error:
            # Shield core thread runners from structural init exceptions
            raise HTTPException(
                status_code=500,
                detail=f"Fatal Initialization Defect inside custom adapter setup context for '{provider_name}': {str(instantiation_error)}"
            )