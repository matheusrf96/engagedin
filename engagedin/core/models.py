from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class Tone(StrEnum):
    professional = "professional"
    provocative = "provocative"
    educational = "educational"
    storytelling = "storytelling"


class HashtagStyle(StrEnum):
    lowercase = "lowercase"
    camelcase = "camelcase"
    uppercase = "uppercase"


class HookType(StrEnum):
    question = "question"
    statistic = "statistic"
    story = "story"
    bold_statement = "bold_statement"


class OutroType(StrEnum):
    cta_question = "cta_question"
    cta_discuss = "cta_discuss"
    reflection = "reflection"


class ScheduleRule(BaseModel):
    best_times: list[str] = ["7-9", "12-13", "17-18"]
    cooldown_hours: int = 4


class PostRuleset(BaseModel):
    tone: Tone = Tone.professional
    min_length: int = 150
    max_length: int = 3000
    hashtags: HashtagRule = Field(default_factory=lambda: HashtagRule())
    schedule: ScheduleRule = Field(default_factory=lambda: ScheduleRule())
    templates: TemplateRule = Field(default_factory=lambda: TemplateRule())


class HashtagRule(BaseModel):
    count: int = 3
    style: HashtagStyle = HashtagStyle.lowercase


class TemplateRule(BaseModel):
    hooks: list[HookType] = Field(
        default_factory=lambda: list(HookType)
    )
    outros: list[OutroType] = Field(
        default_factory=lambda: list(OutroType)
    )


class GeneratedDraft(BaseModel):
    content: str
    character_count: int = 0


class Post(BaseModel):
    author: str
    commentary: str
    visibility: Literal["PUBLIC", "CONNECTIONS"] = "PUBLIC"
    lifecycle_state: Literal["PUBLISHED"] = "PUBLISHED"
