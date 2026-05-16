"""Configuration management for local/Ollama-first deployment."""

from __future__ import annotations

import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class Settings(BaseSettings):
    """Application settings loaded from .env or environment variables."""

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    # Application
    app_env: str = os.getenv("APP_ENV", "development")
    debug: bool = os.getenv("DEBUG", "true").lower() == "true"
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    # Server
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8000"))
    streamlit_port: int = int(os.getenv("STREAMLIT_PORT", "8501"))

    # Database
    session_db_path: str = os.getenv("SESSION_DB_PATH", "./app.db")
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./app.db")

    # Frontend -> backend
    api_base_url: str = os.getenv("API_BASE_URL", "http://localhost:8000/api")

    # LLM routing
    # Default is Ollama for local deployment. Set LLM_PROVIDER=qwen or openai_compatible later.
    llm_provider: str = os.getenv("LLM_PROVIDER", "ollama")
    use_llm_classification: bool = os.getenv("USE_LLM_CLASSIFICATION", "true").lower() == "true"
    llm_timeout_seconds: int = int(os.getenv("LLM_TIMEOUT_SECONDS", "20"))

    # Ollama
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b")

    # Qwen / OpenAI-compatible API. Do not commit real keys.
    qwen_api_key: str = os.getenv("QWEN_API_KEY", "")
    qwen_model: str = os.getenv("QWEN_MODEL", "qwen-plus")
    qwen_base_url: str = os.getenv("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")

    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    openai_base_url: str = os.getenv("OPENAI_BASE_URL", "")

    # Demo safety
    app_password: str = os.getenv("APP_PASSWORD", "")


settings = Settings()
