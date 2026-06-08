from __future__ import annotations

from pathlib import Path

import yaml

from engagedin.core.config import settings
from engagedin.core.models import (
    HashtagRule,
    PostRuleset,
    ScheduleRule,
    TemplateRule,
)


def _get_defaults_path() -> Path:
    return Path(__file__).parent / "defaults.yaml"


def load_ruleset(path: str | Path | None = None) -> PostRuleset:
    if path is None:
        path = settings.rules_path or _get_defaults_path()

    path = Path(path)

    if not path.exists():
        path = _get_defaults_path()

    with open(path) as f:
        data = yaml.safe_load(f)

    hashtags_data = data.get("hashtags", {})
    schedule_data = data.get("schedule", {})
    templates_data = data.get("templates", {})

    return PostRuleset(
        tone=data.get("tone", "professional"),
        min_length=data.get("min_length", 150),
        max_length=data.get("max_length", 3000),
        hashtags=HashtagRule(
            count=hashtags_data.get("count", 3),
            style=hashtags_data.get("style", "lowercase"),
        ),
        schedule=ScheduleRule(
            best_times=schedule_data.get("best_times", ["7-9", "12-13", "17-18"]),
            cooldown_hours=schedule_data.get("cooldown_hours", 4),
        ),
        templates=TemplateRule(
            hooks=templates_data.get("hooks", []),
            outros=templates_data.get("outros", []),
        ),
    )
