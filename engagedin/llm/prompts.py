from __future__ import annotations

from engagedin.core.models import PostRuleset

SYSTEM_PROMPT = """You are a LinkedIn content strategist.
Your task is to write engaging, professional LinkedIn posts
that drive engagement and build authority.

Follow these rules strictly:
- Write in a {tone} tone
- Posts must be between {min_length} and {max_length} characters
- Use exactly {hashtag_count} hashtags at the end, formatted in {hashtag_style} style
- Start with a hook: {hook_types}
- End with an outro: {outro_types}
- Do not use emojis unless they add genuine value
- Write in natural, conversational language
- Each paragraph should be 1-3 sentences max
- Use line breaks between paragraphs for readability
- The post should stand alone without additional context"""


def _format_enum_values(values: list[str]) -> str:
    return ", ".join(v.replace("_", " ") for v in values)


def build_system_prompt(ruleset: PostRuleset) -> str:
    return SYSTEM_PROMPT.format(
        tone=ruleset.tone.value,
        min_length=ruleset.min_length,
        max_length=ruleset.max_length,
        hashtag_count=ruleset.hashtags.count,
        hashtag_style=ruleset.hashtags.style.value,
        hook_types=_format_enum_values(
            [h.value for h in ruleset.templates.hooks]
        ),
        outro_types=_format_enum_values(
            [o.value for o in ruleset.templates.outros]
        ),
    )


USER_PROMPT = """Write a LinkedIn post about the following topic:

{topic}"""

HEADLINER_USER_PROMPT = """You are a tech commentator writing an opinion piece for LinkedIn.

Below are the latest tech news headlines and summaries
from the past {days} day(s), filtered by topic "{topic}":

{news}

Write an opinionated LinkedIn post that:
- Takes a clear, defensible stance on the most significant news item above
- Shows original analysis and critical thinking beyond the headline
- Connects the news to broader industry trends
- Challenges the reader to think differently
- Uses the tone and follows the rules specified in the system prompt

Focus your post on the single most important or interesting story from the news above."""
