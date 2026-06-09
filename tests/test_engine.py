from __future__ import annotations

from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest

from engagedin.core.engine import Engine
from engagedin.core.models import GeneratedDraft, PostRuleset
from engagedin.linkedin.client import LinkedInClient
from engagedin.llm.client import LLMClient
from engagedin.news.client import NewsClient
from engagedin.news.models import NewsArticle


@pytest.fixture
def mock_engine_settings() -> Generator[MagicMock, None, None]:
    with patch("engagedin.core.engine.settings") as m:
        yield m


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
    with pytest.raises(RuntimeError, match="No news articles found"):
        engine.generate_headliner_draft(days=1, topic="obscure")
