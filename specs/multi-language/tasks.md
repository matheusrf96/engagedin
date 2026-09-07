# Multi-language Post Generation — Tasks

> Implementation order: `languages.py` → core models → rules loader →
> prompts → engine → migration/data model → API service/schemas/router →
> CLI → tests → verification. The checklist below is grouped by requirement ID.

## Spec

- [x] Write `specs/multi-language/requirements.md`
- [x] Write `specs/multi-language/design.md`
- [x] Link the spec from `specs/README.md`

## REQ-ML-001 — Tag normalization and validation

- [x] Create `engagedin/core/languages.py` with `LANGUAGE_TAG_RE`,
      `resolve_language` (trim, normalize primary/subtag case, validate,
      `ValueError` on invalid)
- [x] Unit tests in `tests/unit/test_languages.py`: `"en"`, `"PT-br"` →
      `pt-BR`, `"zh-hans"` → `zh-Hans`; `""`, `"not a tag!"` raise `ValueError`

## REQ-ML-002 — Display names

- [x] Add `LANGUAGE_NAMES`, `LANGUAGE_OVERRIDES`, and
      `language_display_name` (full tag → primary → raw tag fallback)
- [x] Unit tests: `pt-BR` → "Brazilian Portuguese", `zh-Hans` → "Simplified
      Chinese", `ar` → "Arabic", unknown tag → raw tag

## REQ-ML-003 — Caseless-script detection

- [x] Add `CASELESS_LANGUAGES` and `has_case` (primary-subtag decision)
- [x] Unit tests: `False` for `zh`, `ar`, `ja`, `he`; `True` for `en`, `ru`,
      `pt-BR`

## REQ-ML-004 — Language on the ruleset

- [x] Add `language: str = "en"` to `PostRuleset` in
      `engagedin/core/models.py`
- [x] `engagedin/rules/loader.py` reads `language` via `resolve_language`
- [x] Add `language: en` to `engagedin/rules/defaults.yaml`
- [x] Unit tests in `tests/unit/test_models.py` (default) and
      `tests/unit/test_rules.py` (YAML override, absent key, invalid value
      raises)

## REQ-ML-005 — Output-language instruction

- [x] `engagedin/llm/prompts.py`: add `- Write the entire post in {language}`
      to `SYSTEM_PROMPT`; add `_hashtag_rule` helper (case-aware phrasing);
      `build_system_prompt` formats `language=language_display_name(...)` and
      `hashtag_rule=...`
- [x] Unit tests in `tests/unit/test_llm.py`: prompt contains "Russian" for a
      `ru` ruleset; `zh-Hans`/`ar` rulesets omit the style clause; `en` keeps
      "formatted in lowercase style"

## REQ-ML-006 — Headliner marker robustness

- [x] `HEADLINER_USER_PROMPT`: require the final `SOURCE: <number>` line in
      exact ASCII format regardless of post language
- [x] `SOURCE_LINE_RE` in `engagedin/core/engine.py` accepts `:` and `：`
- [x] Unit tests: regex matches `SOURCE：3`; built user prompt contains the
      ASCII instruction

## REQ-ML-007 — Per-call language override

- [x] `Engine._effective_ruleset(language)` (`model_copy`, no mutation) and
      `language: str | None = None` parameters on `generate_draft` and
      `generate_headliner_draft`
- [x] Unit tests in `tests/unit/test_engine.py`: LLM receives ruleset with
      resolved language; `self.ruleset` unmutated; `None` passes ruleset
      as-is

## REQ-ML-008 — CLI `--language` option

- [x] `cli/main.py`: `--language/-l` on `draft`, `post`, `headliner`; resolve
      up front, `_fail` on `ValueError`; resolved tag in the panel title
- [x] Unit tests in `tests/unit/test_cli.py`: `--language ru` reaches the
      engine; invalid tag exits 1 before generation; omitted → unchanged

## REQ-ML-009 — API request field and validation

- [x] `api/schemas.py`: `DraftCreateRequest.language: str | None = None`
- [x] `api/services/posts.py`: `create_draft` resolves the tag, raises
      `ExternalServiceError(status_code=400)` on `ValueError`, forwards the
      resolved value through `_generate` to the engine
- [x] `api/routers/generation.py`: pass `request.language`
- [x] Unit tests in `tests/unit/api/test_service.py` and
      `test_generation.py`: resolved value reaches the engine; invalid tag →
      400; omitted → unchanged behavior

## REQ-ML-010 — Persistence

- [x] `api/models.py`: `language: Mapped[str | None] = mapped_column(String(35))`
      on `PostRecord`; `create_draft` stores resolved tag or `NULL`
- [x] Create `migrations/versions/0003_post_language.py` (`down_revision`
      `0002`) with symmetric downgrade
- [x] Unit tests: record carries the resolved language / `None`
- [x] Verify `uv run alembic upgrade head` on the dev database and that
      `alembic revision --autogenerate` afterwards yields an empty diff

## REQ-ML-011 — Language in responses

- [x] `api/schemas.py`: `PostOut.language: str | None`
- [x] Unit tests in `tests/unit/api/test_generation.py` / `test_posts.py`
      asserting the field appears in responses
- [x] Update `tests/integration/test_api_flow.py` for the new response field

## REQ-ML-012 — Non-Latin end-to-end

- [x] Audit the changed paths for encoding assumptions (no `.encode()` /
      `.decode()`, no ASCII-only regex on post content); confirm
      `character_count` stays `len(content)`
- [x] Unit tests with non-Latin fixtures: generated content in Arabic /
      Chinese / Russian flows through `create_draft` and `publish_draft`
      verbatim (mocked clients)

## Verification

- [x] `uv run ruff check --fix .` passes
- [x] `uv run mypy .` passes (pre-existing test-file errors unaffected)
- [x] `uv run pytest` passes with the existing coverage gate
- [x] `docker compose up -d` + `uv run alembic upgrade head` + empty
      `alembic revision --autogenerate` diff
- [x] Smoke: `uv run engagedin draft "AI regulation" --language zh-Hans` and
      `--language ar` render non-Latin drafts; `--language "not a tag"` exits
      1 with a clear message
- [ ] Smoke (manual, real token): publish a `zh-Hans` and an `ar` draft and
      confirm correct rendering on LinkedIn
