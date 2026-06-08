from __future__ import annotations

from unittest.mock import MagicMock, patch

from engagedin.core.engine import Engine
from engagedin.core.models import GeneratedDraft, PostRuleset
from engagedin.linkedin.client import LinkedInClient
from engagedin.llm.client import LLMClient


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


def test_publish_draft_with_urn() -> None:
    mock_linkedin = MagicMock(spec=LinkedInClient)
    mock_linkedin.create_post.return_value = "urn:li:share:12345"
    mock_llm = MagicMock(spec=LLMClient)
    draft = GeneratedDraft(content="Test content")

    with patch("engagedin.core.engine.settings") as mock_settings:
        mock_settings.linkedin_user_urn = "urn:li:person:abc123"
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
