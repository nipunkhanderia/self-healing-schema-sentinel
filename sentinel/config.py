"""
Configuration — loaded from environment / .env file.
Import `settings` anywhere you need config.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # LLM
    llm_backend: str = Field(default="groq", description="groq or ollama")
    groq_api_key: str = Field(default="", description="Groq API key")
    groq_model: str = Field(default="llama-3.3-70b-versatile")
    ollama_base_url: str = Field(default="http://localhost:11434")
    ollama_model: str = Field(default="llama3.2")

    # GitHub
    github_token: str = Field(default="")
    github_repo: str = Field(default="")
    github_base_branch: str = Field(default="main")

    # Output
    output_mode: str = Field(default="local", description="local or pr")
    schema_store_dir: str = Field(default=".sentinel/schemas")
    generated_tests_dir: str = Field(default="generated_tests")


settings = Settings()
