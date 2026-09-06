from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from engagedin.core.models import PostRuleset
from engagedin.llm.client import LLMClient, LLMConfigError


@patch("engagedin.llm.client.settings")
@patch("engagedin.llm.client.completion")
def test_generate_post(
    mock_completion_fn: MagicMock,
    mock_llm_settings: MagicMock,
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


@patch("engagedin.llm.client.settings")
@patch("engagedin.llm.client.completion")
def test_generate_post_empty_response(
    mock_completion_fn: MagicMock,
    mock_llm_settings: MagicMock,
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


@patch("engagedin.llm.client.completion")
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
    assert mock_completion_fn.call_args[1]["model"] == "gpt-4o"


@patch("engagedin.llm.client.completion")
def test_generate_post_missing_api_key(
    mock_completion_fn: MagicMock,
) -> None:
    client = LLMClient(provider="deepseek", model="deepseek-chat", api_key=None)
    with pytest.raises(LLMConfigError, match="LLM_API_KEY is not set"):
        client.generate_post("some topic", PostRuleset())
    mock_completion_fn.assert_not_called()


@patch("engagedin.llm.client.completion")
def test_generate_post_local_provider_no_key(
    mock_completion_fn: MagicMock,
) -> None:
    mock_completion = MagicMock()
    mock_completion.choices[0].message.content = "Local response"
    mock_completion_fn.return_value = mock_completion

    client = LLMClient(provider="ollama", model="llama3", api_key=None)
    result = client.generate_post("local topic", PostRuleset())

    assert result == "Local response"
    mock_completion_fn.assert_called_once()


@patch("engagedin.llm.client.completion")
def test_generate_headliner_missing_api_key(
    mock_completion_fn: MagicMock,
) -> None:
    client = LLMClient(provider="deepseek", model="deepseek-chat", api_key=None)
    with pytest.raises(LLMConfigError, match="LLM_API_KEY is not set"):
        client.generate_headliner_post("AI", "1. News", PostRuleset())
    mock_completion_fn.assert_not_called()


@patch("engagedin.llm.client.settings")
@patch("engagedin.llm.client.completion")
def test_generate_headliner_post(
    mock_completion_fn: MagicMock,
    mock_settings: MagicMock,
) -> None:
    mock_completion = MagicMock()
    mock_completion.choices[0].message.content = "Opinion post about AI news"
    mock_completion_fn.return_value = mock_completion

    mock_settings.llm_api_key = "test-key"
    mock_settings.llm_model = "deepseek-chat"

    news_context = "1. AI Breakthrough\n   Source: Hacker News\n   URL: https://example.com"

    client = LLMClient()
    ruleset = PostRuleset(tone="opinionated")
    result = client.generate_headliner_post(
        "AI", news_context, ruleset, days=1
    )

    assert result == "Opinion post about AI news"
    mock_completion_fn.assert_called_once()
    call_args = mock_completion_fn.call_args[1]
    messages = call_args["messages"]
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert "AI Breakthrough" in messages[1]["content"]
    assert "AI" in messages[1]["content"]
    assert "SOURCE:" in messages[1]["content"]
    assert "Do not include the article URL inside the post text" in messages[1]["content"]


@patch("engagedin.llm.client.settings")
@patch("engagedin.llm.client.completion")
def test_generate_headliner_post_empty(
    mock_completion_fn: MagicMock,
    mock_settings: MagicMock,
) -> None:
    mock_completion = MagicMock()
    mock_completion.choices[0].message.content = ""
    mock_completion_fn.return_value = mock_completion

    mock_settings.llm_api_key = "test-key"
    mock_settings.llm_model = "deepseek-chat"

    client = LLMClient()
    ruleset = PostRuleset()
    result = client.generate_headliner_post(
        "tech", "1. News item", ruleset, days=3
    )

    assert result == ""
