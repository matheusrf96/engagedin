# Multi-language Post Generation — Design

## 1. End-to-end flow after the change

```
CLI --language ru   /   POST /api/v1/drafts {"language": "ru"}   /   ruleset language: en
        │
        ▼
resolve_language("ru") ──► "ru"          (ValueError on garbage: CLI exit 1, API 400)
        │
        ▼
Engine.generate_draft(topic, language) / Engine.generate_headliner_draft(..., language)
        │  effective = ruleset.model_copy(update={"language": resolved})   (None → ruleset as-is)
        ▼
LLMClient.generate_post(topic, effective_ruleset)      (signature unchanged)
        │  build_system_prompt(effective_ruleset)
        │    "…Write the entire post in Russian…"          ← curated display name
        │    hashtags: case-aware phrasing                 ← zh/ar/ja/… omit style clause
        ▼
GeneratedDraft(content, character_count)               Unicode end to end
        ▼
persist (API: PostRecord.language = resolved | NULL)  /  preview (CLI: panel title shows tag)
        ▼
Engine.publish_draft(draft)                            unchanged
```

Headliner flow keeps `SOURCE: <n>` parsing; the marker regex now tolerates a
full-width colon and the prompt pins the marker to ASCII regardless of the
post language.

## 2. New module — `engagedin/core/languages.py`

Single source of truth for tag handling; no settings, no I/O.

```python
from __future__ import annotations

import re

LANGUAGE_TAG_RE = re.compile(r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{1,8})*$")

# primary tag → English display name (curated; extensible, not exhaustive)
LANGUAGE_NAMES: dict[str, str] = {
    "en": "English", "pt": "Portuguese", "es": "Spanish", "fr": "French",
    "de": "German", "it": "Italian", "nl": "Dutch", "ru": "Russian",
    "uk": "Ukrainian", "pl": "Polish", "tr": "Turkish", "ar": "Arabic",
    "he": "Hebrew", "fa": "Persian", "hi": "Hindi", "bn": "Bengali",
    "zh": "Chinese", "ja": "Japanese", "ko": "Korean", "th": "Thai",
    "vi": "Vietnamese", "id": "Indonesian", "sv": "Swedish", "no": "Norwegian",
    "da": "Danish", "fi": "Finnish", "cs": "Czech", "el": "Greek",
    "ro": "Romanian", "hu": "Hungarian",
}

# full normalized tag → name (overrides the primary-tag lookup)
LANGUAGE_OVERRIDES: dict[str, str] = {
    "zh-Hans": "Simplified Chinese",
    "zh-Hant": "Traditional Chinese",
    "pt-BR": "Brazilian Portuguese",
    "pt-PT": "European Portuguese",
}

CASELESS_LANGUAGES: frozenset[str] = frozenset(
    {"zh", "ja", "ko", "ar", "he", "fa", "hi", "th", "bn"}
)


def resolve_language(value: str) -> str:
    """Normalize and validate a BCP-47-style tag. Raises ValueError."""
    tag = value.strip()
    if not LANGUAGE_TAG_RE.match(tag):
        raise ValueError(f"Invalid language tag: {value!r}")
    parts = tag.split("-")
    primary = parts[0].lower()
    subtags = [
        p.capitalize() if len(p) == 4 and p.isalpha()
        else (p.upper() if p.isalpha() and len(p) in (2, 3) else p.lower())
        for p in parts[1:]
    ]
    return "-".join([primary, *subtags])


def language_display_name(tag: str) -> str:
    normalized = resolve_language(tag)
    if normalized in LANGUAGE_OVERRIDES:
        return LANGUAGE_OVERRIDES[normalized]
    return LANGUAGE_NAMES.get(normalized.split("-")[0], normalized)


def has_case(tag: str) -> bool:
    return tag.split("-")[0].lower() not in CASELESS_LANGUAGES
```

Normalization rules (REQ-ML-001): trim → regex validate → lowercase primary →
script subtags (4 alpha chars) capitalized, region subtags (2–3 alpha chars)
uppercased, anything else lowercased. Unknown conforming tags pass through
untouched (CON-ML-003).

## 3. Core models — `engagedin/core/models.py`

One field added; everything else untouched:

```python
class PostRuleset(BaseModel):
    language: str = "en"
    tone: Tone = Tone.professional
    ...  # unchanged
```

`GeneratedDraft`, `Post`, `ArticleRef` need no changes: content is already
`str` (Unicode), and publishing does not depend on the language.

## 4. Rules loader — `engagedin/rules/loader.py` and `defaults.yaml`

```python
return PostRuleset(
    language=resolve_language(data.get("language", "en")),
    tone=data.get("tone", "professional"),
    ...  # unchanged
)
```

`defaults.yaml` gains `language: en` as its first key. `engagedin rules show`
picks the field up automatically via `model_dump`.

## 5. Prompt changes — `engagedin/llm/prompts.py`

`SYSTEM_PROMPT` gains an output-language rule; the hashtag rule becomes
language-aware. `build_system_prompt` keeps its signature:

```python
SYSTEM_PROMPT = """You are a LinkedIn content strategist.
Your task is to write engaging, professional LinkedIn posts
that drive engagement and build authority.

Follow these rules strictly:
- Write the entire post in {language}
- Write in a {tone} tone
- Posts must be between {min_length} and {max_length} characters
- {hashtag_rule}
- Start with a hook: {hook_types}
- End with an outro: {outro_types}
..."""


def _hashtag_rule(ruleset: PostRuleset) -> str:
    count = ruleset.hashtags.count
    if has_case(ruleset.language):
        return (
            f"Use exactly {count} hashtags at the end, "
            f"formatted in {ruleset.hashtags.style.value} style"
        )
    return f"Use exactly {count} hashtags at the end"


def build_system_prompt(ruleset: PostRuleset) -> str:
    return SYSTEM_PROMPT.format(
        language=language_display_name(ruleset.language),
        hashtag_rule=_hashtag_rule(ruleset),
        tone=ruleset.tone.value,
        ...  # unchanged
    )
```

Hashtags for a non-Latin post are generated in the post's own language; for
caseless scripts (Arabic, Chinese, …) the case instruction is dropped instead
of being a no-op the model has to interpret (ADR-ML-006).

`HEADLINER_USER_PROMPT` hardens the marker instruction (REQ-ML-006):

```python
End your reply with a final line on its own, in exact ASCII format regardless
of the post language:
SOURCE: <number of the article from the list above that your post is about>
```

`engagedin/llm/client.py` is **unchanged**: `generate_post` /
`generate_headliner_post` already receive the ruleset, and the language flows
through `build_system_prompt` (CON-ML-004).

## 6. Engine — `engagedin/core/engine.py`

Override semantics (REQ-ML-007) plus marker-regex tolerance (REQ-ML-006):

```python
SOURCE_LINE_RE = re.compile(r"^\s*SOURCE[：:]\s*(\d+)\s*$", re.IGNORECASE)


def _effective_ruleset(self, language: str | None) -> PostRuleset:
    if language is None:
        return self.ruleset
    return self.ruleset.model_copy(update={"language": resolve_language(language)})


def generate_draft(self, topic: str, language: str | None = None) -> GeneratedDraft:
    ruleset = self._effective_ruleset(language)
    content = self.llm.generate_post(topic, ruleset)
    ...  # unchanged


def generate_headliner_draft(
    self, days: int = 1, topic: str = "technology", language: str | None = None
) -> GeneratedDraft:
    articles = self.news.fetch_tech_news(days=days, topic=topic)   # English-only (CON-ML-001)
    ...
    reply = self.llm.generate_headliner_post(topic, news_context, self._effective_ruleset(language), days=days)
    ...
```

`publish_draft`, `schedule_advisory`, `generate_and_publish`, and
`_split_reference` logic are unchanged (only the regex above is touched).

## 7. CLI — `cli/main.py`

`draft`, `post`, and `headliner` gain the same option; validation happens up
front so an invalid tag fails before any LLM call (REQ-ML-008):

```python
@click.option(
    "--language", "-l", default=None,
    help="BCP-47 tag for the post language (e.g. en, pt-BR, zh-Hans, ru, ar)",
)
def draft(topic: str, rules: str | None, language: str | None) -> None:
    resolved: str | None = None
    if language is not None:
        try:
            resolved = resolve_language(language)
        except ValueError as e:
            _fail(f"Invalid language tag: {e}")
    engine = Engine(rules_path=rules)
    draft = engine.generate_draft(topic, language=resolved)
```

The preview panel title includes the resolved tag when one was supplied:

```python
title=f"📝 Draft ({resolved}) ({draft.character_count} chars)"   # when resolved
```

`rules show` and `config show` need no changes.

## 8. API layer — `api/schemas.py`, `api/services/posts.py`, `api/routers/generation.py`

```python
# api/schemas.py
class DraftCreateRequest(BaseModel):
    topic: str = Field(min_length=1, max_length=500)
    source: Literal["standard", "headliner"] = "standard"
    days: int = Field(default=1, ge=1, le=7)
    language: str | None = None          # resolved in the service, not pattern-gated


class PostOut(BaseModel):
    ...
    language: str | None
```

```python
# api/services/posts.py
async def create_draft(
    self, topic: str, source: DraftSource, days: int, language: str | None = None
) -> PostRecord:
    resolved: str | None = None
    if language is not None:
        try:
            resolved = resolve_language(language)
        except ValueError as e:
            raise ExternalServiceError(str(e), status_code=400) from e
    draft = await self._generate(topic, source, days, resolved)
    record = PostRecord(
        ...,
        language=resolved,       # NULL when not supplied (REQ-ML-010)
    )
    return await self.repo.add(record)

def _generate(self, topic, source, days, language=None) -> GeneratedDraft:
    if source == DraftSource.HEADLINER:
        return await asyncio.to_thread(self._generate_headliner, topic, days, language)
    return await asyncio.to_thread(self._generate_standard, topic, language)
```

`api/routers/generation.py` passes `language=request.language`; the existing
`except ExternalServiceError` mapping already turns a 400 into
`HTTPException(status_code=400, detail=...)`. Repositories are generic — no
changes.

## 9. Data model — `api/models.py` and migration `0003`

```python
class PostRecord(Base):
    ...
    language: Mapped[str | None] = mapped_column(String(12))
```

`migrations/versions/0003_post_language.py`:

```python
revision: str = "0003"
down_revision: str | None = "0002"

def upgrade() -> None:
    op.add_column("posts", sa.Column("language", sa.String(length=12), nullable=True))

def downgrade() -> None:
    op.drop_column("posts", "language")
```

`varchar(12)` fits any conforming tag (primary + two subtags ≤ 12 chars, e.g.
`zh-Hans` = 7). Existing rows keep `NULL`; no index or constraint is added.

## 10. Unicode guarantees (REQ-ML-012)

- LiteLLM messages, httpx JSON bodies, SQLAlchemy `Text`/`String` columns, and
  Rich panels already move `str` around as UTF-8 — no encoding code exists
  today and none is added.
- `len(content)` counts code points; LinkedIn counts characters the same way,
  so min/max length rules stay script-agnostic with no per-language overrides
  in this iteration (CON-ML-005).
- Hashtag content is LLM-generated text published verbatim; no `.lower()` /
  `.upper()` coercion exists in code and none is introduced.

## 11. Testing strategy

Existing suites are extended; mocking at boundaries, `@patch` decorators,
`AsyncMock` for async calls (CON-ML-006):

| File | New cases |
|------|-----------|
| `tests/unit/test_languages.py` (new) | normalization (`"en"`, `"PT-br"` → `pt-BR`, `"zh-hans"` → `zh-Hans`); invalid (`""`, `"toolongtag!"`) raises `ValueError`; display names (override → primary → raw); `has_case` for caseless vs case-bearing primaries |
| `tests/unit/test_models.py` | `PostRuleset` defaults `language` to `"en"` |
| `tests/unit/test_rules.py` | YAML `language` override; absent key → `"en"`; invalid value raises |
| `tests/unit/test_llm.py` | built system prompt contains the display name (e.g. "Russian"); `zh-Hans`/`ar` ruleset omits the style clause, `en` keeps it; headliner user prompt carries the ASCII `SOURCE:` instruction |
| `tests/unit/test_engine.py` | `generate_draft`/`generate_headliner_draft` forward an effective ruleset with the resolved language; `self.ruleset` unmutated; `language=None` passes ruleset as-is; `SOURCE_LINE_RE` matches `SOURCE：3` |
| `tests/unit/test_cli.py` | `--language ru` reaches the engine; invalid tag exits 1 before generation; panel title shows the tag |
| `tests/unit/api/test_service.py` | `create_draft` persists the resolved language; `None` → `NULL`; invalid tag → `ExternalServiceError` with status 400 |
| `tests/unit/api/test_generation.py`, `test_posts.py` | request accepts/omits `language`; invalid tag → 400; `PostOut` includes `language` |
| `tests/integration/test_api_flow.py` | create with `language` → 201 and response carries it; omitted → `null` |

No live LLM/LinkedIn calls in tests; language behavior is fully asserted on
prompt/rule objects and call arguments.

## 12. Verification

```bash
uv run ruff check --fix .
uv run mypy .
docker compose up -d
uv run alembic upgrade head
uv run alembic revision --autogenerate        # must yield an empty diff
uv run pytest -q
uv run engagedin draft "AI regulation" --language zh-Hans   # smoke: Chinese output
uv run engagedin draft "AI regulation" --language ar        # smoke: Arabic output
uv run engagedin rules show                                # shows language: en
```

Manual check with a real token: publish a `zh-Hans` and an `ar` draft and
confirm the LinkedIn feed renders the posts with correct script shaping/RTL.

## 13. ADR references

- **ADR-ML-001 — Free-form BCP-47 tag over a closed enum.** LLMs can write in
  any language; a curated enum would block legitimate tags and require a code
  change per new language. The curated name map is a prompt-quality aid, not a
  gate: unknown tags fall back to the raw tag, which LLMs also understand.
  Rejected: `Literal`/`Enum` of ~40 languages (rigid, breaks users).
- **ADR-ML-002 — Language on the ruleset; per-call override via `model_copy`.**
  `build_system_prompt` already consumes the ruleset, so the prompt picks the
  language up with zero `LLMClient` signature churn, and the ruleset remains
  the single config surface (`rules show` reflects it). Rejected: threading a
  separate `language` parameter through `LLMClient` (duplicates state,
  touches every call site) or a global env var (no per-request control).
- **ADR-ML-003 — News stays English-only.** Hacker News has no language
  filter, and restricting NewsAPI to the post language narrows the source pool;
  mixed-language flows (English news → Arabic post) are legitimate. Locked
  decision from planning.
- **ADR-ML-004 — Prompt-driven control, no output verification.** A one-line
  system-prompt instruction is reliable across providers and adds no latency;
  langdetect-style checks add dependencies, false failures (short posts,
  code-switching), and no recovery path. Deferred.
- **ADR-ML-005 — Persist the requested language.** `posts.language` (nullable
  `varchar(12)`) records explicitly requested languages for auditing and
  analytics; `NULL` cleanly means "ruleset default" and keeps pre-feature rows
  valid without a backfill.
- **ADR-ML-006 — Case-aware hashtag phrasing.** `lowercase`/`uppercase`/
  `camelcase` are meaningless in caseless scripts (Arabic, Chinese, Japanese,
  Korean, Hebrew, Hindi, Thai, Persian, Bengali); the prompt omits the clause
  for them rather than special-casing validation or post-processing.
