from __future__ import annotations

from litellm import completion

from engagedin.core.config import settings
from engagedin.core.models import PostRuleset
from engagedin.llm.prompts import (
    HEADLINER_USER_PROMPT,
    USER_PROMPT,
    build_system_prompt,
)

LOCAL_PROVIDERS = frozenset({"ollama", "lm_studio", "vllm", "local"})


class LLMConfigError(Exception):
    """Raised when the LLM configuration is missing required values."""


class LLMClient:
    def __init__(
        self,
        provider: str | None = None,
        model: str | None = None,
        api_key: str | None = None,
    ) -> None:
        self.provider = provider or settings.llm_provider
        self.model = model or settings.llm_model
        self.api_key = api_key or settings.llm_api_key

    def _ensure_api_key(self) -> None:
        if not self.api_key and self.provider not in LOCAL_PROVIDERS:
            raise LLMConfigError(
                f"LLM_API_KEY is not set for provider '{self.provider}'. "
                "Set LLM_API_KEY in your .env file, or use a local provider "
                "(ollama, lm_studio, vllm) that needs no key."
            )

    def generate_post(self, topic: str, ruleset: PostRuleset) -> str:
        self._ensure_api_key()
        system_prompt = build_system_prompt(ruleset)
        user_prompt = USER_PROMPT.format(topic=topic)

        response = completion(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            api_key=self.api_key,
            temperature=0.7,
            max_tokens=2000,
        )

        return response.choices[0].message.content or ""

    def generate_headliner_post(
        self,
        topic: str,
        news_context: str,
        ruleset: PostRuleset,
        days: int = 1,
    ) -> str:
        self._ensure_api_key()
        system_prompt = build_system_prompt(ruleset)
        user_prompt = HEADLINER_USER_PROMPT.format(
            topic=topic, news=news_context, days=days
        )

        response = completion(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            api_key=self.api_key,
            temperature=0.7,
            max_tokens=2000,
        )

        return response.choices[0].message.content or ""
