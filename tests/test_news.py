from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from engagedin.news.client import NewsClient, NewsError
from engagedin.news.models import NewsArticle


def _mock_hackernews_responses(
    mock_client: MagicMock,
    story_ids: list[int] | None = None,
    items: list[dict] | None = None,
) -> None:
    mock_client.get.return_value.raise_for_status.return_value = None

    def get_side_effect(url: str, **kwargs):
        resp = MagicMock()
        resp.raise_for_status.return_value = None
        if url.endswith("/topstories.json"):
            resp.json.return_value = story_ids or []
        elif "/item/" in url:
            sid = int(url.split("/item/")[1].split(".json")[0])
            for item in items or []:
                if item["id"] == sid:
                    resp.json.return_value = item
                    break
            else:
                resp.json.return_value = None
        return resp

    mock_client.get.side_effect = get_side_effect


def test_hackernews_success() -> None:
    now = int(datetime.now(UTC).timestamp())
    items = [
        {
            "id": 1,
            "type": "story",
            "title": "AI Breakthrough in 2026",
            "url": "https://example.com/ai-news",
            "time": now - 1000,
        },
        {
            "id": 2,
            "type": "story",
            "title": "New Programming Language Released",
            "url": "https://example.com/new-lang",
            "time": now - 2000,
        },
        {
            "id": 3,
            "type": "story",
            "title": "Some Old Article",
            "url": "https://example.com/old",
            "time": now - 90000,
        },
    ]
    story_ids = [1, 2, 3]

    with patch("httpx.Client") as mock_client_class:
        mock_client = mock_client_class.return_value.__enter__.return_value
        _mock_hackernews_responses(mock_client, story_ids, items)

        client = NewsClient(source="hackernews")
        articles = client.fetch_tech_news(days=1, topic="technology")

    assert len(articles) == 2
    assert articles[0].title == "AI Breakthrough in 2026"
    assert articles[1].title == "New Programming Language Released"


def test_hackernews_filters_by_topic() -> None:
    now = int(datetime.now(UTC).timestamp())
    items = [
        {
            "id": 1,
            "type": "story",
            "title": "AI Breakthrough in 2026",
            "url": "https://example.com/ai",
            "time": now - 1000,
        },
        {
            "id": 2,
            "type": "story",
            "title": "Python 4.0 Released",
            "url": "https://example.com/python",
            "time": now - 2000,
        },
    ]
    story_ids = [1, 2]

    with patch("httpx.Client") as mock_client_class:
        mock_client = mock_client_class.return_value.__enter__.return_value
        _mock_hackernews_responses(mock_client, story_ids, items)

        client = NewsClient(source="hackernews")
        articles = client.fetch_tech_news(days=1, topic="AI")

    assert len(articles) == 1
    assert articles[0].title == "AI Breakthrough in 2026"


def test_hackernews_skips_non_story() -> None:
    now = int(datetime.now(UTC).timestamp())
    items = [
        {
            "id": 1,
            "type": "story",
            "title": "Real Story",
            "url": "https://example.com/story",
            "time": now - 1000,
        },
        {
            "id": 2,
            "type": "comment",
            "text": "Just a comment",
            "time": now - 1000,
        },
        {
            "id": 3,
            "type": "story",
            "title": "Another Story",
            "url": "https://example.com/story2",
            "time": now - 2000,
        },
    ]
    story_ids = [1, 2, 3]

    with patch("httpx.Client") as mock_client_class:
        mock_client = mock_client_class.return_value.__enter__.return_value
        _mock_hackernews_responses(mock_client, story_ids, items)

        client = NewsClient(source="hackernews")
        articles = client.fetch_tech_news(days=1, topic="technology")

    assert len(articles) == 2


def test_hackernews_empty_results() -> None:
    with patch("httpx.Client") as mock_client_class:
        mock_client = mock_client_class.return_value.__enter__.return_value
        _mock_hackernews_responses(mock_client, [], [])

        client = NewsClient(source="hackernews")
        articles = client.fetch_tech_news(days=1, topic="technology")

    assert articles == []


def test_hackernews_limits_to_twenty_articles() -> None:
    now = int(datetime.now(UTC).timestamp())
    items = [
        {
            "id": i,
            "type": "story",
            "title": f"Story {i}",
            "url": f"https://example.com/{i}",
            "time": now - 1000,
        }
        for i in range(25)
    ]
    story_ids = list(range(25))

    with patch("httpx.Client") as mock_client_class:
        mock_client = mock_client_class.return_value.__enter__.return_value
        _mock_hackernews_responses(mock_client, story_ids, items)

        client = NewsClient(source="hackernews")
        articles = client.fetch_tech_news(days=1, topic="technology")

    assert len(articles) == 20


def test_hackernews_uses_default_url_when_missing() -> None:
    now = int(datetime.now(UTC).timestamp())
    items = [
        {
            "id": 42,
            "type": "story",
            "title": "No URL Story",
            "time": now - 1000,
        },
    ]
    story_ids = [42]

    with patch("httpx.Client") as mock_client_class:
        mock_client = mock_client_class.return_value.__enter__.return_value
        _mock_hackernews_responses(mock_client, story_ids, items)

        client = NewsClient(source="hackernews")
        articles = client.fetch_tech_news(days=1, topic="technology")

    assert len(articles) == 1
    assert articles[0].url == "https://news.ycombinator.com/item?id=42"


def test_newsapi_success() -> None:
    with patch("httpx.Client") as mock_client_class:
        mock_client = mock_client_class.return_value.__enter__.return_value
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "status": "ok",
            "articles": [
                {
                    "title": "Tech News 1",
                    "source": {"name": "TechCrunch"},
                    "url": "https://techcrunch.com/1",
                    "description": "Description 1",
                    "publishedAt": "2026-06-08T12:00:00Z",
                },
                {
                    "title": "Tech News 2",
                    "source": {"name": "The Verge"},
                    "url": "https://theverge.com/2",
                    "description": "",
                    "publishedAt": "2026-06-07T12:00:00Z",
                },
            ],
        }
        mock_client.get.return_value = mock_response

        client = NewsClient(source="newsapi", api_key="test-key")
        articles = client.fetch_tech_news(days=1, topic="AI")

    assert len(articles) == 2
    assert articles[0].title == "Tech News 1"
    assert articles[0].source == "TechCrunch"
    assert articles[1].description == ""


def test_newsapi_missing_key() -> None:
    client = NewsClient(source="newsapi", api_key=None)
    with pytest.raises(NewsError, match="NEWS_API_KEY is required"):
        client.fetch_tech_news(days=1, topic="tech")


def test_newsapi_error_status() -> None:
    with patch("httpx.Client") as mock_client_class:
        mock_client = mock_client_class.return_value.__enter__.return_value
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "status": "error",
            "message": "API rate limit exceeded",
        }
        mock_client.get.return_value = mock_response

        client = NewsClient(source="newsapi", api_key="test-key")
        with pytest.raises(NewsError, match="API rate limit exceeded"):
            client.fetch_tech_news(days=1, topic="tech")


def test_unknown_source() -> None:
    client = NewsClient(source="invalid")
    with pytest.raises(NewsError, match="Unknown news source: invalid"):
        client.fetch_tech_news(days=1)


def test_format_articles() -> None:
    articles = [
        NewsArticle(
            title="AI News",
            source="Hacker News",
            url="https://example.com/ai",
            description="Great article about AI",
            published_at="2026-06-09T12:00:00Z",
        ),
        NewsArticle(
            title="No Description",
            source="TechCrunch",
            url="https://example.com/no-desc",
            description="",
            published_at="2026-06-08T12:00:00Z",
        ),
    ]

    result = NewsClient.format_articles(articles)

    assert "1. AI News" in result
    assert "2. No Description" in result
    assert "Source: Hacker News" in result
    assert "URL: https://example.com/ai" in result
    assert "Great article about AI" in result
    assert "URL: https://example.com/no-desc" in result


def test_format_articles_empty() -> None:
    result = NewsClient.format_articles([])
    assert result == ""
