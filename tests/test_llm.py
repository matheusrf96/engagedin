from __future__ import annotations

from unittest.mock import MagicMock, patch

from engagedin.core.models import PostRuleset
from engagedin.llm.client import LLMClient


class TestLLMClient:
    def test_generate_post(self) -> None:
        mock_completion = MagicMock()
        mock_completion.choices[0].message.content = "Generated post content"

        with (
            patch(
                "engagedin.llm.client.settings"
            ) as mock_settings,
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
            assert len(call_args["messages"]) == 2
            assert call_args["messages"][1]["content"] == (
                "Write a LinkedIn post about the following topic:\n\nAI in 2025"
            )
