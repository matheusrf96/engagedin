from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from engagedin.core.engine import Engine
from engagedin.core.models import GeneratedDraft, PostRuleset
from engagedin.linkedin.client import LinkedInClient, LinkedInError
from engagedin.llm.client import LLMClient
from engagedin.news.client import NewsClient, NewsError
from engagedin.news.models import NewsArticle


def test_generate_draft() -> None:
    mock_llm = MagicMock(spec=LLMClient)
    mock_llm.generate_post.return_value = "Test post content"
    mock_linkedin = MagicMock(spec=LinkedInClient)

    engine = Engine(
        ruleset=PostRuleset(),
        llm_client=mock_llm,
        linkedin_client=mock_linkedin,
    )
    draft = engine.generate_draft("Python tips")

    assert draft.content == "Test post content"
    assert draft.character_count == len("Test post content")


@patch("engagedin.core.engine.settings")
def test_publish_draft_with_urn(
    mock_engine_settings: MagicMock,
) -> None:
    mock_linkedin = MagicMock(spec=LinkedInClient)
    mock_linkedin.create_post.return_value = "urn:li:share:12345"
    mock_llm = MagicMock(spec=LLMClient)
    draft = GeneratedDraft(content="Test content")
    mock_engine_settings.linkedin_user_urn = "urn:li:person:abc123"

    engine = Engine(
        ruleset=PostRuleset(),
        llm_client=mock_llm,
        linkedin_client=mock_linkedin,
    )
    result = engine.publish_draft(draft)

    assert result == "urn:li:share:12345"
    post = mock_linkedin.create_post.call_args[0][0]
    assert post.author == "urn:li:person:abc123"
    assert post.commentary == "Test content"


def test_publish_draft_resolves_urn() -> None:
    mock_linkedin = MagicMock(spec=LinkedInClient)
    mock_linkedin.create_post.return_value = "urn:li:share:12345"
    mock_linkedin.get_user_info.return_value = {"sub": "user456"}
    mock_llm = MagicMock(spec=LLMClient)

    engine = Engine(
        ruleset=PostRuleset(),
        llm_client=mock_llm,
        linkedin_client=mock_linkedin,
    )
    draft = GeneratedDraft(content="Test content")
    result = engine.publish_draft(draft)

    assert result == "urn:li:share:12345"
    post = mock_linkedin.create_post.call_args[0][0]
    assert post.author == "urn:li:person:user456"


def test_generate_and_publish() -> None:
    mock_llm = MagicMock(spec=LLMClient)
    mock_llm.generate_post.return_value = "Full post content with hashtags"
    mock_linkedin = MagicMock(spec=LinkedInClient)
    mock_linkedin.create_post.return_value = "urn:li:share:67890"

    engine = Engine(
        ruleset=PostRuleset(),
        llm_client=mock_llm,
        linkedin_client=mock_linkedin,
    )
    draft, post_urn = engine.generate_and_publish("Remote work trends")

    assert draft.content == "Full post content with hashtags"
    assert post_urn == "urn:li:share:67890"


def test_engine_init_does_not_require_linkedin_token() -> None:
    engine = Engine(ruleset=PostRuleset())
    assert engine.linkedin is None
    with pytest.raises(LinkedInError, match="No LinkedIn access token"):
        engine.publish_draft(GeneratedDraft(content="Test content"))


def test_schedule_advisory_in_best_window() -> None:
    engine = Engine(ruleset=PostRuleset(), llm_client=MagicMock(spec=LLMClient))
    assert engine.schedule_advisory(now=datetime(2026, 6, 9, 8, 30)) is None


def test_schedule_advisory_outside_best_window() -> None:
    engine = Engine(ruleset=PostRuleset(), llm_client=MagicMock(spec=LLMClient))
    message = engine.schedule_advisory(now=datetime(2026, 6, 9, 14, 0))
    assert message is not None
    assert "best posting window" in message
    assert "7-9" in message


def test_generate_headliner_draft() -> None:
    mock_llm = MagicMock(spec=LLMClient)
    mock_llm.generate_headliner_post.return_value = "Opinion about AI news"
    mock_linkedin = MagicMock(spec=LinkedInClient)
    mock_news_client = MagicMock(spec=NewsClient)
    mock_news_client.fetch_tech_news.return_value = [
        NewsArticle(
            title="AI News",
            source="Hacker News",
            url="https://example.com",
            description="AI description",
            published_at="2026-06-09T12:00:00Z",
        ),
    ]

    engine = Engine(
        ruleset=PostRuleset(),
        llm_client=mock_llm,
        linkedin_client=mock_linkedin,
        news_client=mock_news_client,
    )
    draft = engine.generate_headliner_draft(days=3, topic="AI")

    assert draft.content == "Opinion about AI news"
    assert draft.character_count == len("Opinion about AI news")
    mock_llm.generate_headliner_post.assert_called_once()
    call_args = mock_llm.generate_headliner_post.call_args
    assert call_args[0][0] == "AI"
    assert call_args[0][2] == engine.ruleset
    assert call_args[1]["days"] == 3


def test_generate_headliner_draft_no_articles() -> None:
    mock_llm = MagicMock(spec=LLMClient)
    mock_linkedin = MagicMock(spec=LinkedInClient)
    mock_news_client = MagicMock(spec=NewsClient)
    mock_news_client.fetch_tech_news.return_value = []

    engine = Engine(
        ruleset=PostRuleset(),
        llm_client=mock_llm,
        linkedin_client=mock_linkedin,
        news_client=mock_news_client,
    )
    with pytest.raises(NewsError, match="No news articles found"):
        engine.generate_headliner_draft(days=1, topic="obscure")


def _headliner_engine_with_articles(
    reply: str,
) -> tuple[Engine, MagicMock, MagicMock]:
    articles = [
        NewsArticle(
            title="First news",
            source="Hacker News",
            url="https://example.com/first",
            description="First description",
            published_at="2026-06-09T12:00:00Z",
        ),
        NewsArticle(
            title="Second news",
            source="Hacker News",
            url="https://example.com/second",
            description="Second description",
            published_at="2026-06-09T13:00:00Z",
        ),
        NewsArticle(
            title="Third news",
            source="Hacker News",
            url="https://example.com/third",
            description="",
            published_at="2026-06-09T14:00:00Z",
        ),
    ]
    mock_llm = MagicMock(spec=LLMClient)
    mock_llm.generate_headliner_post.return_value = reply
    mock_news_client = MagicMock(spec=NewsClient)
    mock_news_client.fetch_tech_news.return_value = articles
    engine = Engine(
        ruleset=PostRuleset(),
        llm_client=mock_llm,
        linkedin_client=MagicMock(spec=LinkedInClient),
        news_client=mock_news_client,
    )
    return engine, mock_llm, mock_news_client


def test_generate_headliner_draft_source_marker_selects_article() -> None:
    engine, _, _ = _headliner_engine_with_articles(
        "Opinion about the second story\n\nSOURCE: 2"
    )
    draft = engine.generate_headliner_draft(days=1, topic="AI")

    assert draft.content == "Opinion about the second story"
    assert draft.character_count == len("Opinion about the second story")
    assert draft.reference_url == "https://example.com/second"
    assert draft.reference_title == "Second news"
    assert draft.reference_description == "Second description"


def test_generate_headliner_draft_source_marker_missing_falls_back() -> None:
    engine, _, _ = _headliner_engine_with_articles("Opinion without marker")
    draft = engine.generate_headliner_draft(days=1, topic="AI")

    assert draft.content == "Opinion without marker"
    assert draft.reference_url == "https://example.com/first"
    assert draft.reference_title == "First news"


def test_generate_headliner_draft_source_marker_out_of_range_falls_back() -> None:
    engine, _, _ = _headliner_engine_with_articles("Opinion\n\nSOURCE: 99")
    draft = engine.generate_headliner_draft(days=1, topic="AI")

    assert draft.content == "Opinion"
    assert draft.reference_url == "https://example.com/first"


def test_generate_headliner_draft_empty_description_is_none() -> None:
    engine, _, _ = _headliner_engine_with_articles("Opinion\n\nSOURCE: 3")
    draft = engine.generate_headliner_draft(days=1, topic="AI")

    assert draft.reference_url == "https://example.com/third"
    assert draft.reference_title == "Third news"
    assert draft.reference_description is None


def test_generate_headliner_draft_marker_case_insensitive() -> None:
    engine, _, _ = _headliner_engine_with_articles("Opinion\n\nsource: 2")
    draft = engine.generate_headliner_draft(days=1, topic="AI")

    assert draft.content == "Opinion"
    assert draft.reference_url == "https://example.com/second"


def test_generate_headliner_draft_marker_with_trailing_blank_lines() -> None:
    engine, _, _ = _headliner_engine_with_articles(
        "Opinion\n\nSOURCE: 2\n\n\n"
    )
    draft = engine.generate_headliner_draft(days=1, topic="AI")

    assert draft.content == "Opinion"
    assert draft.reference_url == "https://example.com/second"
    assert "SOURCE:" not in draft.content


def test_publish_draft_with_reference_builds_article() -> None:
    mock_linkedin = MagicMock(spec=LinkedInClient)
    mock_linkedin.create_post.return_value = "urn:li:share:12345"
    engine = Engine(
        ruleset=PostRuleset(),
        llm_client=MagicMock(spec=LLMClient),
        linkedin_client=mock_linkedin,
    )
    draft = GeneratedDraft(
        content="Test content",
        reference_url="https://example.com/news",
        reference_title="News title",
        reference_description="News description",
    )

    engine.publish_draft(draft)

    post = mock_linkedin.create_post.call_args[0][0]
    assert post.article is not None
    assert post.article.source == "https://example.com/news"
    assert post.article.title == "News title"
    assert post.article.description == "News description"


def test_publish_draft_reference_description_falls_back_to_title() -> None:
    mock_linkedin = MagicMock(spec=LinkedInClient)
    mock_linkedin.create_post.return_value = "urn:li:share:12345"
    engine = Engine(
        ruleset=PostRuleset(),
        llm_client=MagicMock(spec=LLMClient),
        linkedin_client=mock_linkedin,
    )
    draft = GeneratedDraft(
        content="Test content",
        reference_url="https://example.com/news",
        reference_title="News title",
        reference_description=None,
    )

    engine.publish_draft(draft)

    post = mock_linkedin.create_post.call_args[0][0]
    assert post.article is not None
    assert post.article.title == "News title"
    assert post.article.description == "News title"


def test_publish_draft_without_reference_is_text_only() -> None:
    mock_linkedin = MagicMock(spec=LinkedInClient)
    mock_linkedin.create_post.return_value = "urn:li:share:12345"
    engine = Engine(
        ruleset=PostRuleset(),
        llm_client=MagicMock(spec=LLMClient),
        linkedin_client=mock_linkedin,
    )
    draft = GeneratedDraft(content="Test content")

    engine.publish_draft(draft)

    post = mock_linkedin.create_post.call_args[0][0]
    assert post.article is None
