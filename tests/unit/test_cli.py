from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from cli.main import cli
from engagedin.core.models import GeneratedDraft
from engagedin.linkedin.auth import OAuthError
from engagedin.linkedin.client import LinkedInClient, LinkedInError
from engagedin.llm.client import LLMConfigError
from engagedin.news.client import NewsError


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def _mock_engine(advisory: str | None = None) -> MagicMock:
    mock = MagicMock()
    mock.schedule_advisory.return_value = advisory
    return mock


def test_cli_help(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "EngagedIn" in result.output


def test_auth_login_missing_creds(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["auth", "login"])
    assert result.exit_code == 1
    assert "LINKEDIN_CLIENT_ID" in result.output


@patch("cli.main.LinkedInClient")
def test_auth_status_unauthenticated(
    mock_linkedin_client_cls: MagicMock, runner: CliRunner
) -> None:
    mock_linkedin_client_cls.side_effect = LinkedInError(
        "No LinkedIn access token available. "
        "Run `engagedin auth login` or set LINKEDIN_ACCESS_TOKEN in .env"
    )
    result = runner.invoke(cli, ["auth", "status"])
    assert result.exit_code == 1
    assert result.exception is not None


@patch("cli.main.LinkedInClient")
def test_auth_status_token_expired(
    mock_linkedin_client_cls: MagicMock, runner: CliRunner
) -> None:
    mock_client = MagicMock(spec=LinkedInClient)
    mock_client.get_user_info.side_effect = Exception("Token expired")
    mock_linkedin_client_cls.return_value = mock_client
    result = runner.invoke(cli, ["auth", "status"])
    assert result.exit_code == 0
    assert "Not authenticated" in result.output


@patch("cli.main.LinkedInClient")
def test_auth_status_authenticated(
    mock_linkedin_client_cls: MagicMock, runner: CliRunner
) -> None:
    mock_client = MagicMock(spec=LinkedInClient)
    mock_client.get_user_info.return_value = {
        "name": "John Doe",
        "sub": "abc123",
    }
    mock_linkedin_client_cls.return_value = mock_client
    result = runner.invoke(cli, ["auth", "status"])
    assert result.exit_code == 0
    assert "Authenticated" in result.output
    assert "John Doe" in result.output


@patch("cli.main.Engine")
def test_draft(mock_engine_cls: MagicMock, runner: CliRunner) -> None:
    mock_engine = _mock_engine()
    mock_engine.generate_draft.return_value = GeneratedDraft(
        content="Test draft content",
        character_count=18,
    )
    mock_engine_cls.return_value = mock_engine
    result = runner.invoke(cli, ["draft", "AI in business"])
    assert result.exit_code == 0
    assert "Test draft content" in result.output
    assert "18 chars" in result.output


@patch("cli.main.Engine")
def test_draft_with_rules(mock_engine_cls: MagicMock, runner: CliRunner) -> None:
    mock_engine = _mock_engine()
    mock_engine.generate_draft.return_value = GeneratedDraft(
        content="Custom rules draft",
        character_count=19,
    )
    mock_engine_cls.return_value = mock_engine
    result = runner.invoke(
        cli, ["draft", "tech trends", "--rules", "/tmp/custom.yaml"]
    )
    assert result.exit_code == 0
    assert "Custom rules draft" in result.output


@patch("cli.main.Engine")
def test_draft_generation_error(
    mock_engine_cls: MagicMock, runner: CliRunner
) -> None:
    mock_engine = _mock_engine()
    mock_engine.generate_draft.side_effect = LLMConfigError("LLM_API_KEY is not set")
    mock_engine_cls.return_value = mock_engine
    result = runner.invoke(cli, ["draft", "some topic"])
    assert result.exit_code == 1
    assert "Could not generate the post" in result.output
    assert "LLM_API_KEY is not set" in result.output


def test_draft_missing_llm_key(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["draft", "some topic"])
    assert result.exit_code == 1
    assert "LLM_API_KEY is not set" in result.output


@patch("cli.main.Engine")
def test_post_yes_flag(mock_engine_cls: MagicMock, runner: CliRunner) -> None:
    mock_engine = _mock_engine()
    mock_engine.generate_draft.return_value = GeneratedDraft(
        content="Post content",
        character_count=12,
    )
    mock_engine.publish_draft.return_value = "urn:li:share:12345"
    mock_engine_cls.return_value = mock_engine
    result = runner.invoke(cli, ["post", "my topic", "--yes"])
    assert result.exit_code == 0
    assert "Post content" in result.output
    assert "Published" in result.output
    assert "urn:li:share:12345" in result.output


@patch("cli.main.Engine")
def test_post_cancelled(mock_engine_cls: MagicMock, runner: CliRunner) -> None:
    mock_engine = _mock_engine()
    mock_engine.generate_draft.return_value = GeneratedDraft(
        content="Post content",
        character_count=12,
    )
    mock_engine_cls.return_value = mock_engine
    result = runner.invoke(cli, ["post", "my topic"], input="n\n")
    assert result.exit_code == 0
    assert "Cancelled" in result.output


@patch("cli.main.Engine")
def test_post_short_warning(mock_engine_cls: MagicMock, runner: CliRunner) -> None:
    mock_engine = _mock_engine()
    mock_engine.generate_draft.return_value = GeneratedDraft(
        content="Hi",
        character_count=2,
    )
    mock_engine_cls.return_value = mock_engine
    result = runner.invoke(cli, ["post", "tiny topic", "--yes"])
    assert "very short" in result.output


@patch("cli.main.Engine")
def test_post_long_warning(mock_engine_cls: MagicMock, runner: CliRunner) -> None:
    mock_engine = _mock_engine()
    mock_engine.generate_draft.return_value = GeneratedDraft(
        content="A" * 3001,
        character_count=3001,
    )
    mock_engine_cls.return_value = mock_engine
    result = runner.invoke(cli, ["post", "long topic", "--yes"])
    assert "exceeds 3000" in result.output


@patch("cli.main.Engine")
def test_post_schedule_advisory(
    mock_engine_cls: MagicMock, runner: CliRunner
) -> None:
    mock_engine = _mock_engine(advisory="Not in a best posting window (7-9).")
    mock_engine.generate_draft.return_value = GeneratedDraft(
        content="Post content",
        character_count=12,
    )
    mock_engine.publish_draft.return_value = "urn:li:share:12345"
    mock_engine_cls.return_value = mock_engine
    result = runner.invoke(cli, ["post", "my topic", "--yes"])
    assert "Not in a best posting window (7-9)." in result.output


@patch("cli.main.Engine")
def test_post_generation_error(
    mock_engine_cls: MagicMock, runner: CliRunner
) -> None:
    mock_engine = _mock_engine()
    mock_engine.generate_draft.side_effect = LLMConfigError("LLM_API_KEY is not set")
    mock_engine_cls.return_value = mock_engine
    result = runner.invoke(cli, ["post", "my topic", "--yes"])
    assert result.exit_code == 1
    assert "Could not generate the post" in result.output


@patch("cli.main.Engine")
def test_post_publish_error(
    mock_engine_cls: MagicMock, runner: CliRunner
) -> None:
    mock_engine = _mock_engine()
    mock_engine.generate_draft.return_value = GeneratedDraft(
        content="Post content",
        character_count=12,
    )
    mock_engine.publish_draft.side_effect = LinkedInError("publish boom")
    mock_engine_cls.return_value = mock_engine
    result = runner.invoke(cli, ["post", "my topic", "--yes"])
    assert result.exit_code == 1
    assert "Could not publish the post" in result.output
    assert "publish boom" in result.output


def test_rules_show(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["rules", "show"])
    assert result.exit_code == 0
    assert "Current Ruleset" in result.output
    assert "professional" in result.output


def test_config_show(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["config", "show"])
    assert result.exit_code == 0
    assert "Configuration" in result.output
    assert "deepseek-chat" in result.output


def test_config_show_masks_secrets(runner: CliRunner, monkeypatch) -> None:
    monkeypatch.setattr(
        "cli.main.settings.linkedin_access_token",
        "supersecret123",
    )
    result = runner.invoke(cli, ["config", "show"])
    assert "supe..." in result.output
    assert "supersecret123" not in result.output


def _fake_run_oauth_login(on_url=None, **_):
    if on_url is not None:
        on_url("http://dummy.url/auth")
    return ("tok_abc123", "urn:li:person:user999")


@patch("cli.main.save_env_values")
@patch("cli.main.run_oauth_login")
@patch("cli.main.settings")
def test_auth_login_success(
    mock_settings: MagicMock,
    mock_run_oauth_login: MagicMock,
    mock_save_env: MagicMock,
    runner: CliRunner,
) -> None:
    mock_settings.linkedin_client_id = "test_id"
    mock_settings.linkedin_client_secret = "test_secret"
    mock_run_oauth_login.side_effect = _fake_run_oauth_login

    result = runner.invoke(cli, ["auth", "login"])

    assert result.exit_code == 0
    assert "Opening browser" in result.output
    assert "http://dummy.url/auth" in result.output
    assert "tok_abc123" in result.output
    assert "urn:li:person:user999" in result.output
    mock_save_env.assert_called_once_with(
        ".env",
        {
            "LINKEDIN_ACCESS_TOKEN": "tok_abc123",
            "LINKEDIN_USER_URN": "urn:li:person:user999",
        },
    )


@patch("cli.main.run_oauth_login")
@patch("cli.main.settings")
def test_auth_login_authorization_failed(
    mock_settings: MagicMock,
    mock_run_oauth_login: MagicMock,
    runner: CliRunner,
) -> None:
    mock_settings.linkedin_client_id = "test_id"
    mock_settings.linkedin_client_secret = "test_secret"
    mock_run_oauth_login.side_effect = OAuthError(
        "Authorization failed or was cancelled"
    )
    result = runner.invoke(cli, ["auth", "login"])

    assert result.exit_code == 1
    assert "Authorization failed or was cancelled" in result.output


@patch("cli.main.run_oauth_login")
@patch("cli.main.settings")
def test_auth_login_no_access_token(
    mock_settings: MagicMock,
    mock_run_oauth_login: MagicMock,
    runner: CliRunner,
) -> None:
    mock_settings.linkedin_client_id = "test_id"
    mock_settings.linkedin_client_secret = "test_secret"
    mock_run_oauth_login.side_effect = OAuthError("Failed to obtain access token")
    result = runner.invoke(cli, ["auth", "login"])

    assert result.exit_code == 1
    assert "Failed to obtain access token" in result.output


@patch("cli.main.Engine")
def test_headliner_defaults(
    mock_engine_cls: MagicMock, runner: CliRunner
) -> None:
    mock_engine = _mock_engine()
    mock_engine.generate_headliner_draft.return_value = GeneratedDraft(
        content="Opinative post about tech news",
        character_count=30,
    )
    mock_engine_cls.return_value = mock_engine
    result = runner.invoke(cli, ["headliner", "--yes"])

    assert result.exit_code == 0
    assert "Opinative post about tech news" in result.output
    assert "Headliner Draft" in result.output
    mock_engine.generate_headliner_draft.assert_called_once_with(
        days=1, topic="technology"
    )


@patch("cli.main.Engine")
def test_headliner_with_options(
    mock_engine_cls: MagicMock, runner: CliRunner
) -> None:
    mock_engine = _mock_engine()
    mock_engine.generate_headliner_draft.return_value = GeneratedDraft(
        content="AI opinion piece",
        character_count=16,
    )
    mock_engine_cls.return_value = mock_engine
    result = runner.invoke(
        cli, ["headliner", "--days", "3", "--topic", "AI", "--yes"]
    )

    assert result.exit_code == 0
    assert "AI opinion piece" in result.output
    mock_engine.generate_headliner_draft.assert_called_once_with(
        days=3, topic="AI"
    )


@patch("cli.main.Engine")
def test_headliner_cancelled(
    mock_engine_cls: MagicMock, runner: CliRunner
) -> None:
    mock_engine = _mock_engine()
    mock_engine.generate_headliner_draft.return_value = GeneratedDraft(
        content="Draft that gets cancelled",
        character_count=25,
    )
    mock_engine_cls.return_value = mock_engine
    result = runner.invoke(cli, ["headliner", "-d", "7"], input="n\n")

    assert result.exit_code == 0
    assert "Cancelled" in result.output


@patch("cli.main.Engine")
def test_headliner_short_warning(
    mock_engine_cls: MagicMock, runner: CliRunner
) -> None:
    mock_engine = _mock_engine()
    mock_engine.generate_headliner_draft.return_value = GeneratedDraft(
        content="Hi",
        character_count=2,
    )
    mock_engine_cls.return_value = mock_engine
    result = runner.invoke(cli, ["headliner", "--yes"])

    assert "very short" in result.output


@patch("cli.main.Engine")
def test_headliner_long_warning(
    mock_engine_cls: MagicMock, runner: CliRunner
) -> None:
    mock_engine = _mock_engine()
    mock_engine.generate_headliner_draft.return_value = GeneratedDraft(
        content="A" * 3001,
        character_count=3001,
    )
    mock_engine_cls.return_value = mock_engine
    result = runner.invoke(cli, ["headliner", "--yes"])

    assert "exceeds 3000" in result.output


@patch("cli.main.Engine")
def test_headliner_generation_error(
    mock_engine_cls: MagicMock, runner: CliRunner
) -> None:
    mock_engine = _mock_engine()
    mock_engine.generate_headliner_draft.side_effect = NewsError("No news found")
    mock_engine_cls.return_value = mock_engine
    result = runner.invoke(cli, ["headliner", "--yes"])

    assert result.exit_code == 1
    assert "Could not generate the headliner" in result.output
    assert "No news found" in result.output


@patch("cli.main.Engine")
def test_headliner_schedule_advisory(
    mock_engine_cls: MagicMock, runner: CliRunner
) -> None:
    mock_engine = _mock_engine(advisory="Not in a best posting window (7-9).")
    mock_engine.generate_headliner_draft.return_value = GeneratedDraft(
        content="Opinion piece",
        character_count=13,
    )
    mock_engine.publish_draft.return_value = "urn:li:share:12345"
    mock_engine_cls.return_value = mock_engine
    result = runner.invoke(cli, ["headliner", "--yes"])

    assert "Not in a best posting window (7-9)." in result.output


@patch("cli.main.Engine")
def test_headliner_publish_error(
    mock_engine_cls: MagicMock, runner: CliRunner
) -> None:
    mock_engine = _mock_engine()
    mock_engine.generate_headliner_draft.return_value = GeneratedDraft(
        content="Opinion piece",
        character_count=13,
    )
    mock_engine.publish_draft.side_effect = LinkedInError("publish boom")
    mock_engine_cls.return_value = mock_engine
    result = runner.invoke(cli, ["headliner", "--yes"])

    assert result.exit_code == 1
    assert "Could not publish the post" in result.output
    assert "publish boom" in result.output
