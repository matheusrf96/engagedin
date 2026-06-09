from __future__ import annotations

from engagedin.core.models import (
    GeneratedDraft,
    HashtagRule,
    HashtagStyle,
    HookType,
    OutroType,
    Post,
    PostRuleset,
    ScheduleRule,
    TemplateRule,
    Tone,
)


def test_default_ruleset() -> None:
    ruleset = PostRuleset()
    assert ruleset.tone == Tone.professional
    assert ruleset.min_length == 150
    assert ruleset.max_length == 3000
    assert isinstance(ruleset.hashtags, HashtagRule)
    assert ruleset.hashtags.count == 3
    assert isinstance(ruleset.schedule, ScheduleRule)
    assert ruleset.schedule.cooldown_hours == 4
    assert isinstance(ruleset.templates, TemplateRule)


def test_custom_ruleset() -> None:
    ruleset = PostRuleset(
        tone=Tone.storytelling,
        min_length=300,
        max_length=2000,
        hashtags=HashtagRule(count=5, style="camelcase"),
    )
    assert ruleset.tone == Tone.storytelling
    assert ruleset.min_length == 300
    assert ruleset.max_length == 2000
    assert ruleset.hashtags.count == 5
    assert ruleset.hashtags.style == HashtagStyle.camelcase


def test_tone_values() -> None:
    assert [t.value for t in Tone] == [
        "professional",
        "provocative",
        "educational",
        "storytelling",
        "opinionated",
    ]


def test_hook_type_values() -> None:
    assert [h.value for h in HookType] == [
        "question",
        "statistic",
        "story",
        "bold_statement",
    ]


def test_outro_type_values() -> None:
    assert [o.value for o in OutroType] == [
        "cta_question",
        "cta_discuss",
        "reflection",
    ]


def test_default_post() -> None:
    post = Post(author="urn:li:person:abc123", commentary="Hello World")
    assert post.author == "urn:li:person:abc123"
    assert post.commentary == "Hello World"
    assert post.visibility == "PUBLIC"
    assert post.lifecycle_state == "PUBLISHED"


def test_custom_visibility() -> None:
    post = Post(
        author="urn:li:person:abc123",
        commentary="Hello World",
        visibility="CONNECTIONS",
    )
    assert post.visibility == "CONNECTIONS"


def test_generated_draft() -> None:
    draft = GeneratedDraft(content="test", character_count=4)
    assert draft.content == "test"
    assert draft.character_count == 4


def test_schedule_rule_defaults() -> None:
    schedule = ScheduleRule()
    assert "7-9" in schedule.best_times
    assert schedule.cooldown_hours == 4


def test_hashtag_rule_defaults() -> None:
    rule = HashtagRule()
    assert rule.count == 3
    assert rule.style == HashtagStyle.lowercase


def test_template_rule_defaults() -> None:
    template = TemplateRule()
    assert HookType.question in template.hooks
    assert OutroType.cta_question in template.outros
