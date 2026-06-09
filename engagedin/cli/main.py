from __future__ import annotations

import http.server
import secrets
import threading
import webbrowser

import click
import yaml
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm

from engagedin.core.config import settings
from engagedin.core.engine import Engine
from engagedin.linkedin.auth import (
    OAuthCallbackHandler,
    build_authorization_url,
    exchange_code_for_token,
    get_user_urn,
)
from engagedin.linkedin.client import LinkedInClient
from engagedin.rules.loader import load_ruleset

console = Console()


@click.group()
def cli() -> None:
    """EngagedIn — AI-powered LinkedIn content generator."""


@cli.group()
def auth() -> None:
    """Manage LinkedIn authentication."""


@auth.command(name="login")
def auth_login() -> None:
    """Authenticate with LinkedIn via OAuth 2.0."""
    if not settings.linkedin_client_id or not settings.linkedin_client_secret:
        console.print(
            "[red]LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET must be set in .env[/red]"
        )
        raise SystemExit(1)

    state = secrets.token_urlsafe(32)
    auth_url = build_authorization_url(state)

    OAuthCallbackHandler.authorization_code = None
    OAuthCallbackHandler.expected_state = state

    server = http.server.HTTPServer(("localhost", 18473), OAuthCallbackHandler)
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()

    console.print(
        "[bold]Opening browser for LinkedIn authorization...[/bold]"
    )
    console.print(f"If the browser doesn't open, visit:\n{auth_url}")
    webbrowser.open(auth_url)

    server.handle_request()
    server.server_close()

    code = OAuthCallbackHandler.authorization_code
    if not code:
        console.print("[red]Authorization failed or was cancelled[/red]")
        raise SystemExit(1)

    console.print("[green]Authorization code received, exchanging for token...[/green]")
    token = exchange_code_for_token(code)

    access_token = token.get("access_token", "")
    if not access_token:
        console.print("[red]Failed to obtain access token[/red]")
        raise SystemExit(1)

    console.print("[green]Access token obtained! Fetching your profile...[/green]")
    user_urn = get_user_urn(access_token)
    console.print(f"[green]Authenticated as: {user_urn}[/green]")

    console.print(
        "\n[yellow]Add these to your .env file:[/yellow]"
    )
    console.print(f"LINKEDIN_ACCESS_TOKEN={access_token}")
    console.print(f"LINKEDIN_USER_URN={user_urn}")


@auth.command(name="status")
def auth_status() -> None:
    """Check authentication status."""
    client = LinkedInClient()
    try:
        info = client.get_user_info()
        console.print("[green]Authenticated[/green]")
        console.print(f"Name: {info.get('name', 'Unknown')}")
        console.print(f"Subject: {info.get('sub', 'Unknown')}")
    except Exception as e:
        console.print(f"[red]Not authenticated or token invalid: {e}[/red]")


@cli.command()
@click.argument("topic")
@click.option("--rules", "-r", help="Path to custom ruleset YAML")
@click.option(
    "--yes", "-y", is_flag=True, help="Skip confirmation prompt"
)
def post(topic: str, rules: str | None, yes: bool) -> None:
    """Generate and publish a LinkedIn post about TOPIC."""
    engine = Engine(rules_path=rules)

    with console.status("[bold green]Generating post draft..."):
        draft = engine.generate_draft(topic)

    console.print(
        Panel(
            draft.content,
            title=f"📝 Draft ({draft.character_count} chars)",
            border_style="blue",
        )
    )

    if draft.character_count < 100:
        console.print(
            "[yellow]Warning: Post is very short. Consider a more detailed topic.[/yellow]"
        )
    if draft.character_count > 3000:
        console.print(
            "[yellow]Warning: Post exceeds 3000 characters (LinkedIn limit).[/yellow]"
        )

    if not yes:
        confirm = Confirm.ask("Publish this post to LinkedIn?")
        if not confirm:
            console.print("[yellow]Cancelled[/yellow]")
            raise SystemExit(0)

    with console.status("[bold green]Publishing to LinkedIn..."):
        post_urn = engine.publish_draft(draft)

    console.print(f"[green]Published! Post URN: {post_urn}[/green]")


@cli.command()
@click.argument("topic")
@click.option("--rules", "-r", help="Path to custom ruleset YAML")
def draft(topic: str, rules: str | None) -> None:
    """Generate a draft post without publishing."""
    engine = Engine(rules_path=rules)

    with console.status("[bold green]Generating post draft..."):
        draft = engine.generate_draft(topic)

    console.print(
        Panel(
            draft.content,
            title=f"📝 Draft ({draft.character_count} chars)",
            border_style="blue",
        )
    )


@cli.command()
@click.option(
    "--days",
    "-d",
    type=click.IntRange(1, 7),
    default=1,
    help="Days of news to consider (1-7)",
)
@click.option(
    "--topic",
    "-t",
    default="technology",
    help="News topic (e.g., AI, cybersecurity)",
)
@click.option("--rules", "-r", help="Path to custom ruleset YAML")
@click.option(
    "--yes", "-y", is_flag=True, help="Skip confirmation prompt"
)
def headliner(
    days: int, topic: str, rules: str | None, yes: bool
) -> None:
    """Generate an opinative LinkedIn post based on recent tech news."""
    engine = Engine(rules_path=rules)

    with console.status("[bold green]Fetching latest tech news..."):
        draft = engine.generate_headliner_draft(days=days, topic=topic)

    console.print(
        Panel(
            draft.content,
            title=f"📝 Headliner Draft ({draft.character_count} chars)",
            border_style="blue",
        )
    )

    if draft.character_count < 100:
        console.print(
            "[yellow]Warning: Post is very short. Consider a more detailed topic.[/yellow]"
        )
    if draft.character_count > 3000:
        console.print(
            "[yellow]Warning: Post exceeds 3000 characters (LinkedIn limit).[/yellow]"
        )

    if not yes:
        confirm = Confirm.ask("Publish this post to LinkedIn?")
        if not confirm:
            console.print("[yellow]Cancelled[/yellow]")
            raise SystemExit(0)

    with console.status("[bold green]Publishing to LinkedIn..."):
        post_urn = engine.publish_draft(draft)

    console.print(f"[green]Published! Post URN: {post_urn}[/green]")


@cli.group()
def rules() -> None:
    """Manage post rulesets."""


@rules.command(name="show")
def rules_show() -> None:
    """Display the current ruleset."""
    ruleset = load_ruleset()
    console.print(
        Panel(
            yaml.dump(ruleset.model_dump(mode="json"), default_flow_style=False),
            title="📋 Current Ruleset",
            border_style="green",
        )
    )


@cli.group()
def config() -> None:
    """Manage configuration."""


@config.command(name="show")
def config_show() -> None:
    """Display current configuration (secrets masked)."""
    cfg = settings.model_dump()
    for key in cfg:
        value = cfg[key]
        if isinstance(value, str) and value and any(
            secret in key.lower()
            for secret in ["secret", "token", "key", "password"]
        ):
            cfg[key] = value[:4] + "..." if len(value) > 4 else "***"
    console.print(
        Panel(
            yaml.dump(cfg, default_flow_style=False),
            title="⚙️ Configuration",
            border_style="yellow",
        )
    )
