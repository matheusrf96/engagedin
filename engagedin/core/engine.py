from __future__ import annotations

from datetime import datetime
from pathlib import Path

from engagedin.core.config import settings
from engagedin.core.models import GeneratedDraft, Post, PostRuleset
from engagedin.core.schedule import is_best_time
from engagedin.linkedin.client import LinkedInClient
from engagedin.llm.client import LLMClient
from engagedin.news.client import NewsClient, NewsError
from engagedin.rules.loader import load_ruleset


class Engine:
    def __init__(
        self,
        ruleset: PostRuleset | None = None,
        rules_path: str | Path | None = None,
        llm_client: LLMClient | None = None,
        linkedin_client: LinkedInClient | None = None,
        news_client: NewsClient | None = None,
    ) -> None:
        self.ruleset = ruleset or load_ruleset(rules_path)
        self.llm = llm_client or LLMClient()
        self.linkedin = linkedin_client
        self.news = news_client or NewsClient()

    def _get_linkedin(self) -> LinkedInClient:
        if self.linkedin is None:
            self.linkedin = LinkedInClient()
        return self.linkedin

    def generate_draft(self, topic: str) -> GeneratedDraft:
        content = self.llm.generate_post(topic, self.ruleset)
        return GeneratedDraft(
            content=content,
            character_count=len(content),
        )

    def generate_headliner_draft(
        self,
        days: int = 1,
        topic: str = "technology",
    ) -> GeneratedDraft:
        articles = self.news.fetch_tech_news(days=days, topic=topic)
        if not articles:
            raise NewsError(
                f"No news articles found for topic '{topic}' in the last {days} day(s)"
            )
        news_context = NewsClient.format_articles(articles)
        content = self.llm.generate_headliner_post(
            topic, news_context, self.ruleset, days=days
        )
        return GeneratedDraft(
            content=content,
            character_count=len(content),
        )

    def publish_draft(self, draft: GeneratedDraft) -> str:
        linkedin = self._get_linkedin()
        if not settings.linkedin_user_urn:
            user_info = linkedin.get_user_info()
            author = f"urn:li:person:{user_info['sub']}"
        else:
            author = settings.linkedin_user_urn

        post = Post(
            author=author,
            commentary=draft.content,
        )
        post_urn = linkedin.create_post(post)
        return post_urn

    def schedule_advisory(self, now: datetime | None = None) -> str | None:
        """Return an advisory message when now is outside the best posting hours."""
        now = now or datetime.now()
        if is_best_time(now, self.ruleset.schedule.best_times):
            return None
        best = ", ".join(self.ruleset.schedule.best_times)
        return (
            f"Not in a best posting window ({best}). "
            "Consider scheduling this post for later."
        )

    def generate_and_publish(self, topic: str) -> tuple[GeneratedDraft, str]:
        draft = self.generate_draft(topic)
        post_urn = self.publish_draft(draft)
        return draft, post_urn
