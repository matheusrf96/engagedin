from __future__ import annotations

from unittest.mock import MagicMock, patch

from engagedin.core.models import PostRuleset
from engagedin.llm.client import LLMClient


def test_generate_post() -> None:
    mock_completion = MagicMock()
    mock_completion.choices[0].message.content = "Generated post content"

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
        ruleset = PostRuleset()
        result = client.generate_post("AI in 2025", ruleset)

    assert result == "Generated post content"
    mock_complete.assert_called_once()
    call_args = mock_complete.call_args[1]
    assert call_args["model"] == "deepseek-chat"
    messages = call_args["messages"]
    assert len(messages) == 2
    assert messages[1]["content"] == (
        "Write a LinkedIn post about the following topic:\n\nAI in 2025"
    )


def test_generate_post_empty_response() -> None:
    mock_completion = MagicMock()
    mock_completion.choices[0].message.content = ""

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
        result = client.generate_post("empty topic", ruleset)

    assert result == ""


def test_generate_post_custom_provider() -> None:
    mock_completion = MagicMock()
    mock_completion.choices[0].message.content = "Response"

    with patch(
        "engagedin.llm.client.completion",
        return_value=mock_completion,
    ) as mock_complete:
        client = LLMClient(
            provider="openai",
            model="gpt-4o",
            api_key="sk-test",
        )
        ruleset = PostRuleset()
        result = client.generate_post("custom provider", ruleset)

    assert result == "Response"
    assert mock_complete.call_args[1]["model"] == "gpt-4o"
