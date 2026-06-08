from __future__ import annotations

from engagedin.core.models import (
    HashtagRule,
    HookType,
    OutroType,
    Post,
    PostRuleset,
    ScheduleRule,
    TemplateRule,
    Tone,
)


class TestPostRuleset:
    def test_default_ruleset(self) -> None:
        ruleset = PostRuleset()
        assert ruleset.tone == Tone.professional
        assert ruleset.min_length == 150
        assert ruleset.max_length == 3000
        assert isinstance(ruleset.hashtags, HashtagRule)
        assert ruleset.hashtags.count == 3
        assert isinstance(ruleset.schedule, ScheduleRule)
        assert ruleset.schedule.cooldown_hours == 4
        assert isinstance(ruleset.templates, TemplateRule)

    def test_custom_ruleset(self) -> None:
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
        assert ruleset.hashtags.style.value == "camelcase"

    def test_tone_values(self) -> None:
        assert [t.value for t in Tone] == [
            "professional",
            "provocative",
            "educational",
            "storytelling",
        ]

    def test_hook_type_values(self) -> None:
        assert [h.value for h in HookType] == [
            "question",
            "statistic",
            "story",
            "bold_statement",
        ]

    def test_outro_type_values(self) -> None:
        assert [o.value for o in OutroType] == [
            "cta_question",
            "cta_discuss",
            "reflection",
        ]


class TestPost:
    def test_default_post(self) -> None:
        post = Post(author="urn:li:person:abc123", commentary="Hello World")
        assert post.author == "urn:li:person:abc123"
        assert post.commentary == "Hello World"
        assert post.visibility == "PUBLIC"
        assert post.lifecycle_state == "PUBLISHED"

    def test_custom_visibility(self) -> None:
        post = Post(
            author="urn:li:person:abc123",
            commentary="Hello World",
            visibility="CONNECTIONS",
        )
        assert post.visibility == "CONNECTIONS"
