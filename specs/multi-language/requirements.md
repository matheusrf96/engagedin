# Multi-language Post Generation — Requirements

Feature ID: `ML`

## Context

EngagedIn has no language configuration anywhere: the ruleset
(`engagedin/rules/defaults.yaml`), the prompt templates
(`engagedin/llm/prompts.py`), the CLI, and the API carry no language field.
Generated posts come out in whatever language the LLM produces from the topic —
in practice English. The only explicit language in the codebase is a hardcoded
`"language": "en"` in the NewsAPI request (`engagedin/news/client.py`), which
stays as-is: news fetching is English-only by decision. The goal is to let
users generate posts in any language — with explicit support for non-Latin
scripts such as Arabic, Chinese, and Russian — via a ruleset default plus
per-request overrides in the CLI and the API.

Three surfaces are affected: the core engine/ruleset/prompts, the CLI
(`draft`, `post`, `headliner`), and the FastAPI module (`POST /api/v1/drafts`
plus persistence).

Decisions locked during planning:

- **Validation**: free-form BCP-47 tag (`en`, `pt-BR`, `zh-Hans`, `ru`, `ar`…).
  No closed language list — unknown but conforming tags pass through; a curated
  map supplies human-readable names for prompt phrasing.
- **Default**: `en` on the ruleset — existing rulesets and requests behave
  exactly as today unless a language is specified.
- **News**: stays English-only; `NewsClient` is untouched.
- **Persistence**: the API stores the requested language on each post record
  (new Alembic revision `0003`), exposed in `PostOut`.
- **Control mechanism**: prompt-driven — the system prompt instructs the output
  language. No output-language verification in this feature.
- **Out of scope**: output verification (langdetect), per-language length
  limits, news translation, `POST_LANGUAGE` env var.

## Requirements

### Language resolution (core)

### REQ-ML-001 — Tag normalization and validation

WHEN `resolve_language` receives a language tag
THE SYSTEM SHALL trim surrounding whitespace and normalize the tag: lowercase
the primary subtag, uppercase 2–3 letter alphabetic subtags, capitalize
4-letter script subtags (`"PT-br"` → `pt-BR`, `"zh-hans"` → `zh-Hans`)
AND SHALL accept any tag matching `^[A-Za-z]{2,3}(-[A-Za-z0-9]{1,8})*$`
AND SHALL raise `ValueError` for empty, whitespace-only, or non-conforming
values
AND SHALL reject tags longer than the BCP-47 maximum of 35 characters
WHILE the normalized tag is the single value consumed by all other layers.

### REQ-ML-002 — Display names

WHEN `language_display_name` is called with a normalized tag
THE SYSTEM SHALL return a curated English name for known tags
(`pt-BR` → "Brazilian Portuguese", `zh-Hans` → "Simplified Chinese",
`ar` → "Arabic", `ru` → "Russian")
AND SHALL return the tag itself unchanged for unknown tags
WHILE the lookup tries the full normalized tag first, then the primary subtag.

### REQ-ML-003 — Caseless-script detection

WHEN `has_case` is called with a normalized tag
THE SYSTEM SHALL return `False` for languages written in caseless scripts (at
minimum `zh`, `ja`, `ko`, `ar`, `he`, `fa`, `hi`, `th`, `bn`)
AND `True` for any other primary subtag
WHILE the decision uses the primary subtag only.

### Ruleset

### REQ-ML-004 — Language on the ruleset

THE SYSTEM SHALL add `language: str = "en"` to `PostRuleset`
AND the rules loader SHALL read the `language` key through `resolve_language`,
defaulting to `en` when the key is absent
AND `defaults.yaml` SHALL declare `language: en`
WHILE an invalid value in a custom ruleset raises `ValueError` from the loader.

### Prompts

### REQ-ML-005 — Output-language instruction

WHEN the system prompt is built
THE SYSTEM SHALL instruct the LLM to write the entire post in the language
named by `language_display_name(ruleset.language)`
AND WHEN the language has no letter case THE SYSTEM SHALL phrase the hashtag
rule as "Use exactly {count} hashtags at the end" (no case-style clause)
WHILE case-bearing languages keep the existing "formatted in {style} style"
instruction
AND no other prompt rules change.

### REQ-ML-006 — Headliner marker robustness

WHEN the headliner user prompt is built
THE SYSTEM SHALL state that the final `SOURCE: <number>` line must be emitted
in exact ASCII format regardless of the post language
AND `SOURCE_LINE_RE` SHALL accept both `:` and the full-width `：` before the
number
WHILE a missing or unparseable marker keeps the existing top-ranked fallback
behavior.

### Engine

### REQ-ML-007 — Per-call language override

WHEN `Engine.generate_draft` or `Engine.generate_headliner_draft` receives a
`language` argument (default `None`)
THE SYSTEM SHALL resolve a non-`None` value with `resolve_language` and build
the effective ruleset via `ruleset.model_copy(update={"language": resolved})`
AND SHALL pass the effective ruleset to the LLM
AND `self.ruleset` SHALL remain unmutated
WHILE `language=None` uses the ruleset's own language unchanged.

### CLI

### REQ-ML-008 — `--language` option

WHEN `engagedin draft`, `engagedin post`, or `engagedin headliner` is invoked
with `--language/-l <tag>`
THE SYSTEM SHALL resolve the tag before generation and exit with code 1 and a
clear message on an invalid tag
AND the draft preview panel title SHALL include the resolved tag
WHILE omitting the option leaves behavior unchanged.

### API

### REQ-ML-009 — Request field and validation

WHEN `POST /api/v1/drafts` receives a `language` field (optional, default
`None`)
THE SYSTEM SHALL resolve a non-`None` value with `resolve_language` and forward
it to the engine through `PostService.create_draft`
AND WHEN the tag is invalid THE SYSTEM SHALL respond `400` with the resolver's
message
WHILE omitting `language` behaves exactly as today.

### REQ-ML-010 — Persistence

THE SYSTEM SHALL add a nullable `language` column (`varchar(35)`) to the
`posts` table through Alembic revision `0003` (`down_revision` `0002`) with a
symmetric downgrade
AND `PostService.create_draft` SHALL store the resolved tag when one was
supplied and `NULL` otherwise (the ruleset default was used)
WHILE existing rows keep `NULL`.

### REQ-ML-011 — Language in responses

WHEN any endpoint returns a `PostOut` record
THE SYSTEM SHALL include `language` (nullable) in the response
WHILE `PostListResponse` items carry the same field.

### Unicode handling

### REQ-ML-012 — Non-Latin end-to-end

THE SYSTEM SHALL carry post content as Unicode text end to end (LLM messages,
generated draft, persistence, LinkedIn request body) with no encoding
transformations introduced
AND `character_count` SHALL keep counting Unicode code points
AND hashtags generated in non-Latin scripts SHALL be published verbatim (no
case coercion applied in code)
WHILE news fetching remains English-only (CON-ML-001).

## Constraints

### CON-ML-001 — News stays English-only

`engagedin/news/client.py` is untouched: NewsAPI keeps `language: "en"` and
Hacker News has no language filter. Generating a post in Arabic from English
news is a supported flow.

### CON-ML-002 — No output-language verification

No langdetect-style post-checks, no second-pass translation calls, no LLM
judge on the output language. The system prompt instruction is the only
control.

### CON-ML-003 — No closed language list

Any conforming BCP-47 tag is accepted; unknown tags still work (the raw tag is
used in the prompt). Adding a new language never requires a code change.

### CON-ML-004 — Placement

Language resolution lives in `engagedin/core/languages.py`. The `LLMClient`
signature is unchanged — language flows through the ruleset.
`cli/` only presents; `api/` only persists and orchestrates.

### CON-ML-005 — Scope guards

No per-language length limits, no `POST_LANGUAGE` environment variable, no
translation of user topics, no script-variant inference beyond the tag the
user provides.

### CON-ML-006 — Type, style, and test gates

All new code SHALL pass the ruff configuration (line length 100; rule sets E,
F, I, N, W, UP) and mypy (`disallow_untyped_defs`). Tests SHALL use `@patch`
decorators mocking at boundaries (service/engine/client), `AsyncMock` for
async calls, and the suite SHALL keep the existing coverage gate.
