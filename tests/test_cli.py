from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from engagedin.cli.main import cli
from engagedin.core.models import GeneratedDraft
from engagedin.linkedin.client import LinkedInClient, LinkedInError


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def test_cli_help(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "EngagedIn" in result.output


def test_auth_login_missing_creds(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["auth", "login"])
    assert result.exit_code == 1
    assert "LINKEDIN_CLIENT_ID" in result.output


def test_auth_status_unauthenticated(runner: CliRunner) -> None:
    with patch(
        "engagedin.cli.main.LinkedInClient",
        side_effect=LinkedInError(
            "No LinkedIn access token available. "
            "Run `engagedin auth login` or set LINKEDIN_ACCESS_TOKEN in .env"
        ),
    ):
        result = runner.invoke(cli, ["auth", "status"])
    assert result.exit_code == 1
    assert result.exception is not None


def test_auth_status_token_expired(runner: CliRunner) -> None:
    mock_client = MagicMock(spec=LinkedInClient)
    mock_client.get_user_info.side_effect = Exception("Token expired")
    with patch(
        "engagedin.cli.main.LinkedInClient", return_value=mock_client
    ):
        result = runner.invoke(cli, ["auth", "status"])
    assert result.exit_code == 0
    assert "Not authenticated" in result.output


def test_auth_status_authenticated(runner: CliRunner) -> None:
    mock_client = MagicMock(spec=LinkedInClient)
    mock_client.get_user_info.return_value = {
        "name": "John Doe",
        "sub": "abc123",
    }
    with patch(
        "engagedin.cli.main.LinkedInClient", return_value=mock_client
    ):
        result = runner.invoke(cli, ["auth", "status"])
        assert result.exit_code == 0
        assert "Authenticated" in result.output
        assert "John Doe" in result.output


def test_draft(runner: CliRunner) -> None:
    mock_engine = MagicMock()
    mock_engine.generate_draft.return_value = GeneratedDraft(
        content="Test draft content",
        character_count=18,
    )
    with patch("engagedin.cli.main.Engine", return_value=mock_engine):
        result = runner.invoke(cli, ["draft", "AI in business"])
    assert result.exit_code == 0
    assert "Test draft content" in result.output
    assert "18 chars" in result.output


def test_draft_with_rules(runner: CliRunner) -> None:
    mock_engine = MagicMock()
    mock_engine.generate_draft.return_value = GeneratedDraft(
        content="Custom rules draft",
        character_count=19,
    )
    with patch("engagedin.cli.main.Engine", return_value=mock_engine):
        result = runner.invoke(
            cli, ["draft", "tech trends", "--rules", "/tmp/custom.yaml"]
        )
    assert result.exit_code == 0
    assert "Custom rules draft" in result.output


def test_post_yes_flag(runner: CliRunner) -> None:
    mock_engine = MagicMock()
    mock_engine.generate_draft.return_value = GeneratedDraft(
        content="Post content",
        character_count=12,
    )
    mock_engine.publish_draft.return_value = "urn:li:share:12345"
    with patch("engagedin.cli.main.Engine", return_value=mock_engine):
        result = runner.invoke(
            cli, ["post", "my topic", "--yes"]
        )
    assert result.exit_code == 0
    assert "Post content" in result.output
    assert "Published" in result.output
    assert "urn:li:share:12345" in result.output


def test_post_cancelled(runner: CliRunner) -> None:
    mock_engine = MagicMock()
    mock_engine.generate_draft.return_value = GeneratedDraft(
        content="Post content",
        character_count=12,
    )
    with patch("engagedin.cli.main.Engine", return_value=mock_engine):
        result = runner.invoke(
            cli, ["post", "my topic"], input="n\n"
        )
    assert result.exit_code == 0
    assert "Cancelled" in result.output


def test_post_short_warning(runner: CliRunner) -> None:
    mock_engine = MagicMock()
    mock_engine.generate_draft.return_value = GeneratedDraft(
        content="Hi",
        character_count=2,
    )
    with patch("engagedin.cli.main.Engine", return_value=mock_engine):
        result = runner.invoke(
            cli, ["post", "tiny topic", "--yes"]
        )
    assert "very short" in result.output


def test_post_long_warning(runner: CliRunner) -> None:
    mock_engine = MagicMock()
    mock_engine.generate_draft.return_value = GeneratedDraft(
        content="A" * 3001,
        character_count=3001,
    )
    with patch("engagedin.cli.main.Engine", return_value=mock_engine):
        result = runner.invoke(
            cli, ["post", "long topic", "--yes"]
        )
    assert "exceeds 3000" in result.output


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
        "engagedin.cli.main.settings.linkedin_access_token",
        "supersecret123",
    )
    result = runner.invoke(cli, ["config", "show"])
    assert "supe..." in result.output
    assert "supersecret123" not in result.output


def test_auth_login_success(runner: CliRunner) -> None:
    from engagedin.linkedin.auth import OAuthCallbackHandler

    mock_token = {"access_token": "tok_abc123"}
    with (
        patch("engagedin.cli.main.settings") as mock_settings,
        patch(
            "engagedin.cli.main.build_authorization_url",
            return_value="http://dummy.url/auth",
        ),
        patch("webbrowser.open"),
        patch(
            "http.server.HTTPServer"
        ) as mock_server_class,
        patch(
            "engagedin.cli.main.exchange_code_for_token",
            return_value=mock_token,
        ),
        patch(
            "engagedin.cli.main.get_user_urn",
            return_value="urn:li:person:user999",
        ),
    ):
        mock_settings.linkedin_client_id = "test_id"
        mock_settings.linkedin_client_secret = "test_secret"

        mock_server = MagicMock()
        mock_server_class.return_value = mock_server

        mock_server.handle_request.side_effect = (
            lambda: setattr(
                OAuthCallbackHandler, "authorization_code", "code_xyz"
            )
        )

        result = runner.invoke(cli, ["auth", "login"])

    assert result.exit_code == 0
    assert "Authorization code received" in result.output
    assert "tok_abc123" in result.output
    assert "urn:li:person:user999" in result.output


def test_auth_login_no_code(runner: CliRunner) -> None:
    with (
        patch("engagedin.cli.main.settings") as mock_settings,
        patch(
            "engagedin.cli.main.build_authorization_url",
            return_value="http://dummy.url/auth",
        ),
        patch("webbrowser.open"),
        patch(
            "http.server.HTTPServer"
        ) as mock_server_class,
    ):
        mock_settings.linkedin_client_id = "test_id"
        mock_settings.linkedin_client_secret = "test_secret"

        mock_server = MagicMock()
        mock_server_class.return_value = mock_server

        result = runner.invoke(cli, ["auth", "login"])

    assert result.exit_code == 1
    assert "Authorization failed" in result.output


def test_auth_login_no_access_token(runner: CliRunner) -> None:
    from engagedin.linkedin.auth import OAuthCallbackHandler

    with (
        patch("engagedin.cli.main.settings") as mock_settings,
        patch(
            "engagedin.cli.main.build_authorization_url",
            return_value="http://dummy.url/auth",
        ),
        patch("webbrowser.open"),
        patch(
            "http.server.HTTPServer"
        ) as mock_server_class,
        patch(
            "engagedin.cli.main.exchange_code_for_token",
            return_value={"access_token": ""},
        ),
    ):
        mock_settings.linkedin_client_id = "test_id"
        mock_settings.linkedin_client_secret = "test_secret"

        mock_server = MagicMock()
        mock_server_class.return_value = mock_server
        mock_server.handle_request.side_effect = (
            lambda: setattr(
                OAuthCallbackHandler, "authorization_code", "code_xyz"
            )
        )

        result = runner.invoke(cli, ["auth", "login"])

    assert result.exit_code == 1
    assert "Failed to obtain access token" in result.output
