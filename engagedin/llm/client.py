from __future__ import annotations

from litellm import completion

from engagedin.core.config import settings
from engagedin.core.models import PostRuleset
from engagedin.llm.prompts import USER_PROMPT, build_system_prompt


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

    def generate_post(self, topic: str, ruleset: PostRuleset) -> str:
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
