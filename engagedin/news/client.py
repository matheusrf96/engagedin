from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime, timedelta

import httpx

from engagedin.core.config import settings
from engagedin.news.models import NewsArticle

HN_BASE = "https://hacker-news.firebaseio.com/v0"
NEWSAPI_BASE = "https://newsapi.org/v2"
HN_MAX_WORKERS = 10


class NewsError(Exception):
    """Base exception for news fetching errors."""


class NewsClient:
    def __init__(
        self,
        source: str | None = None,
        api_key: str | None = None,
    ) -> None:
        self.source = source or settings.news_source
        self.api_key = api_key or settings.news_api_key or None

    def fetch_tech_news(
        self, days: int = 1, topic: str = "technology"
    ) -> list[NewsArticle]:
        if self.source == "hackernews":
            return self._fetch_from_hackernews(days, topic)
        if self.source == "newsapi":
            return self._fetch_from_newsapi(days, topic)
        raise NewsError(f"Unknown news source: {self.source}")

    def _fetch_item(
        self,
        client: httpx.Client,
        sid: int,
        cutoff: float,
        topic: str,
    ) -> NewsArticle | None:
        try:
            item_resp = client.get(f"{HN_BASE}/item/{sid}.json")
            item_resp.raise_for_status()
            item = item_resp.json()
        except httpx.HTTPError:
            return None

        if not item or item.get("type") != "story":
            return None

        published = item.get("time", 0)
        if published < cutoff:
            return None

        title: str = item.get("title", "") or ""
        # HN is tech-focused, so "technology" accepts all stories;
        # other topics require a keyword match in the title.
        topic_lower = topic.lower()
        if topic != "technology" and topic_lower not in title.lower():
            return None

        return NewsArticle(
            title=title,
            source="Hacker News",
            url=item.get("url", f"https://news.ycombinator.com/item?id={sid}"),
            description=item.get("text", "") or "",
            published_at=datetime.fromtimestamp(published, tz=UTC).isoformat(),
        )

    def _fetch_from_hackernews(
        self, days: int, topic: str
    ) -> list[NewsArticle]:
        cutoff = time.time() - days * 86400

        with httpx.Client(timeout=15.0) as client:
            resp = client.get(f"{HN_BASE}/topstories.json")
            resp.raise_for_status()
            story_ids: list[int] = resp.json()[:100]

            articles: list[NewsArticle] = []
            pool = ThreadPoolExecutor(max_workers=HN_MAX_WORKERS)
            try:
                futures = {
                    pool.submit(self._fetch_item, client, sid, cutoff, topic): sid
                    for sid in story_ids
                }
                for future in as_completed(futures):
                    result = future.result()
                    if result is not None:
                        articles.append(result)
                        if len(articles) >= 20:
                            break
            finally:
                pool.shutdown(wait=False, cancel_futures=True)

        return articles

    def _fetch_from_newsapi(
        self, days: int, topic: str
    ) -> list[NewsArticle]:
        if not self.api_key:
            raise NewsError("NEWS_API_KEY is required when source is 'newsapi'")

        from_date = (datetime.now(UTC) - timedelta(days=days)).strftime(
            "%Y-%m-%d"
        )

        with httpx.Client(timeout=15.0) as client:
            resp = client.get(
                f"{NEWSAPI_BASE}/everything",
                params={
                    "q": topic,
                    "from": from_date,
                    "language": "en",
                    "sortBy": "popularity",
                    "apiKey": self.api_key,
                },
            )
            resp.raise_for_status()
            data = resp.json()

            if data.get("status") != "ok":
                raise NewsError(f"NewsAPI error: {data.get('message', 'unknown')}")

            articles: list[NewsArticle] = []
            for item in data.get("articles", [])[:20]:
                articles.append(
                    NewsArticle(
                        title=item.get("title", ""),
                        source=item.get("source", {}).get("name", "NewsAPI"),
                        url=item.get("url", ""),
                        description=item.get("description", "") or "",
                        published_at=item.get("publishedAt", ""),
                    )
                )

        return articles

    @staticmethod
    def format_articles(articles: list[NewsArticle]) -> str:
        lines: list[str] = []
        for i, article in enumerate(articles, 1):
            lines.append(f"{i}. {article.title}")
            lines.append(f"   Source: {article.source}")
            lines.append(f"   URL: {article.url}")
            if article.description:
                lines.append(f"   {article.description}")
            lines.append("")
        return "\n".join(lines).strip()
