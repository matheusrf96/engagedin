from __future__ import annotations

from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest

from engagedin.core.models import PostRuleset
from engagedin.llm.client import LLMClient
from engagedin.news.models import NewsArticle


@pytest.fixture
def mock_llm_settings() -> Generator[MagicMock, None, None]:
    with patch("engagedin.llm.client.settings") as m:
        yield m


@pytest.fixture
def mock_completion_fn() -> Generator[MagicMock, None, None]:
    with patch("engagedin.llm.client.completion") as m:
        yield m


def test_generate_post(
    mock_llm_settings: MagicMock,
    mock_completion_fn: MagicMock,
) -> None:
    mock_completion = MagicMock()
    mock_completion.choices[0].message.content = "Generated post content"
    mock_completion_fn.return_value = mock_completion
    mock_llm_settings.llm_api_key = "test-key"
    mock_llm_settings.llm_model = "deepseek-chat"

    client = LLMClient()
    ruleset = PostRuleset()
    result = client.generate_post("AI in 2025", ruleset)

    assert result == "Generated post content"
    mock_completion_fn.assert_called_once()
    call_args = mock_completion_fn.call_args[1]
    assert call_args["model"] == "deepseek-chat"
    messages = call_args["messages"]
    assert len(messages) == 2
    assert messages[1]["content"] == (
        "Write a LinkedIn post about the following topic:\n\nAI in 2025"
    )


def test_generate_post_empty_response(
    mock_llm_settings: MagicMock,
    mock_completion_fn: MagicMock,
) -> None:
    mock_completion = MagicMock()
    mock_completion.choices[0].message.content = ""
    mock_completion_fn.return_value = mock_completion
    mock_llm_settings.llm_api_key = "test-key"
    mock_llm_settings.llm_model = "deepseek-chat"

    client = LLMClient()
    ruleset = PostRuleset()
    result = client.generate_post("empty topic", ruleset)

    assert result == ""


def test_generate_post_custom_provider(
    mock_completion_fn: MagicMock,
) -> None:
    mock_completion = MagicMock()
    mock_completion.choices[0].message.content = "Response"
    mock_completion_fn.return_value = mock_completion

    client = LLMClient(
        provider="openai",
        model="gpt-4o",
        api_key="sk-test",
    )
    ruleset = PostRuleset()
    result = client.generate_post("custom provider", ruleset)

    assert result == "Response"
    assert mock_complete.call_args[1]["model"] == "gpt-4o"


def test_generate_headliner_post() -> None:
    mock_completion = MagicMock()
    mock_completion.choices[0].message.content = "Opinion post about AI news"

    articles = [
        NewsArticle(
            title="AI Breakthrough",
            source="Hacker News",
            url="https://example.com",
            description="New AI model released",
            published_at="2026-06-09T12:00:00Z",
        ),
    ]

    with (
        patch("engagedin.llm.client.settings") as mock_settings,
        patch(
            "engagedin.llm.client.completion",
            return_value=mock_completion,
        ) as mock_complete,
    ):
        mock_settings.llm_api_key = "test-key"
        mock_settings.llm_model = "deepseek-chat"

        client = LLMClient()
        ruleset = PostRuleset(tone="opinative")
        result = client.generate_headliner_post(
            "AI", articles, ruleset, days=1
        )

    assert result == "Opinion post about AI news"
    mock_complete.assert_called_once()
    call_args = mock_complete.call_args[1]
    messages = call_args["messages"]
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert "AI Breakthrough" in messages[1]["content"]
    assert "AI" in messages[1]["content"]


def test_generate_headliner_post_empty() -> None:
    mock_completion = MagicMock()
    mock_completion.choices[0].message.content = ""

    articles = [
        NewsArticle(
            title="Empty response test",
            source="Test",
            url="https://example.com",
            description="",
            published_at="2026-06-09T12:00:00Z",
        ),
    ]

    with (
        patch("engagedin.llm.client.settings") as mock_settings,
        patch(
            "engagedin.llm.client.completion",
            return_value=mock_completion,
        ),
    ):
        mock_settings.llm_api_key = "test-key"
        mock_settings.llm_model = "deepseek-chat"

        client = LLMClient()
        ruleset = PostRuleset()
        result = client.generate_headliner_post(
            "tech", articles, ruleset, days=3
        )

    assert result == ""
