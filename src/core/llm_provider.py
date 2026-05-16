"""LangChain LLM provider factory.

Default path uses local Ollama via langchain-ollama. The same interface can be
switched to Qwen/OpenAI-compatible APIs by changing .env values.
"""

from __future__ import annotations

from typing import Optional

from src.core.config import settings


def get_chat_model(temperature: float = 0.0):
    """Return a LangChain chat model based on environment configuration.

    Supported providers:
    - LLM_PROVIDER=ollama: local Ollama with langchain_ollama.ChatOllama
    - LLM_PROVIDER=qwen: DashScope/Qwen OpenAI-compatible endpoint
    - LLM_PROVIDER=openai_compatible: any OpenAI-compatible endpoint
    """

    provider = settings.llm_provider.lower().strip()

    if provider == "ollama":
        try:
            from langchain_ollama import ChatOllama
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(
                "langchain-ollama is not installed. Run: pip install langchain-ollama"
            ) from exc
        return ChatOllama(
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
            temperature=temperature,
            timeout=settings.llm_timeout_seconds,
        )

    if provider == "qwen":
        if not settings.qwen_api_key:
            raise RuntimeError("QWEN_API_KEY is not set. Put it in .env on the server, not in GitHub.")
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=settings.qwen_model,
            api_key=settings.qwen_api_key,
            base_url=settings.qwen_base_url,
            temperature=temperature,
            timeout=settings.llm_timeout_seconds,
        )

    if provider == "openai_compatible":
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not set.")
        from langchain_openai import ChatOpenAI

        kwargs = {
            "model": settings.openai_model,
            "api_key": settings.openai_api_key,
            "temperature": temperature,
            "timeout": settings.llm_timeout_seconds,
        }
        if settings.openai_base_url:
            kwargs["base_url"] = settings.openai_base_url
        return ChatOpenAI(**kwargs)

    raise ValueError(f"Unsupported LLM_PROVIDER: {settings.llm_provider}")


async def safe_llm_invoke(prompt: str, temperature: float = 0.0) -> Optional[str]:
    """Call the configured LangChain chat model.

    Returns None if the model is unavailable so the app can fall back to rules.
    """

    try:
        model = get_chat_model(temperature=temperature)
        response = await model.ainvoke(prompt)
        return getattr(response, "content", str(response))
    except Exception:
        return None
