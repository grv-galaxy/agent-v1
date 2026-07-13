from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Groq API configuration
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    
    # Allows loading from .env file
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
