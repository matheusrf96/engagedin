# LinkedIn Article Card — Tasks

> Implementation order: core models → prompt → engine → LinkedIn client →
> migration/data model → API service/schemas → CLI → tests → verification.
> The checklist below is grouped by requirement ID.

## Spec

- [x] Write `specs/linkedin-article-card/requirements.md`
- [x] Write `specs/linkedin-article-card/design.md`
- [x] Link the spec from `specs/README.md`

## REQ-LAC-001 — SOURCE marker parsing

- [x] Add `SOURCE_LINE_RE` and `_split_reference` helper in
      `engagedin/core/engine.py` (strip trailing marker, 1-based index mapping)
- [x] `generate_headliner_draft` populates `reference_url`/`reference_title`/
      `reference_description` from the mapped article
- [x] Unit tests: valid `SOURCE: 3` maps to `articles[2]`; marker stripped from
      content; `character_count` computed post-strip

## REQ-LAC-002 — Top-ranked fallback

- [x] `_split_reference` falls back to `articles[0]` on missing, non-numeric,
      or out-of-range marker without raising
- [x] Unit tests: missing marker (content untouched), out-of-range index,
      malformed marker line

## REQ-LAC-003 — GeneratedDraft reference fields

- [x] Extend `GeneratedDraft` in `engagedin/core/models.py` with optional
      `reference_url`, `reference_title`, `reference_description` (default
      `None`)
- [x] Confirm `generate_draft` (standard) leaves them `None`
- [x] Unit tests in `tests/unit/test_models.py` for defaults

## REQ-LAC-004 — Prompt marker instruction

- [x] Update `HEADLINER_USER_PROMPT` in `engagedin/llm/prompts.py`: forbid the
      URL in the post body; require the final `SOURCE: <number>` line
- [x] Unit test in `tests/unit/test_llm.py` asserting the instructions render
      into the built user prompt

## REQ-LAC-005 — ArticleRef and Post content

- [x] Add `ArticleRef(source, title, description)` to
      `engagedin/core/models.py`
- [x] Add `article: ArticleRef | None = None` to `Post`
- [x] Unit tests for `ArticleRef` validation and `Post` default

## REQ-LAC-006 — Article card request body

- [x] `LinkedInClient.create_post` adds
      `body["content"] = {"article": {...}}` only when `post.article` is set
      (no `thumbnail` key); body otherwise unchanged
- [x] Unit tests in `tests/unit/test_linkedin.py`: body with card, body
      without `content` key

## REQ-LAC-007 — Publish flow passes the reference

- [x] `Engine.publish_draft` builds `ArticleRef` from draft reference fields
      with description fallback (`description` → `title` → `url`)
- [x] No `reference_url` → text-only post as before
- [x] Unit tests: `Post.article` populated from a referenced draft; `None` for
      a plain draft

## REQ-LAC-008 — Reference columns on `posts`

- [x] Add `reference_url` (String 2048), `reference_title` (String 1024),
      `reference_description` (Text) to `PostRecord` in `api/models.py`
- [x] Create `migrations/versions/0002_post_reference.py` (`down_revision`
      `0001`) with symmetric downgrade
- [x] Verify `uv run alembic upgrade head` on the dev database and that
      `alembic revision --autogenerate` afterwards yields an empty diff

## REQ-LAC-009 — Draft creation persistence

- [x] `PostService.create_draft` stores the draft's reference fields in the
      record (standard → `NULL`)
- [x] Unit tests in `tests/unit/api/test_service.py`: headliner persists
      reference; standard leaves `None`

## REQ-LAC-010 — Publish from stored record

- [x] `PostService._publish_draft` accepts the reference fields and rebuilds
      `GeneratedDraft` with them; `publish` passes the record's stored fields
- [x] Unit tests: publish forwards stored reference fields; `NULL` fields →
      text-only publish

## REQ-LAC-011 — Reference in API responses

- [x] Add the three nullable reference fields to `PostOut` in
      `api/schemas.py`
- [x] Unit tests in `tests/unit/api/test_generation.py` / `test_posts.py`
      asserting the fields appear in responses
- [x] Update `tests/integration/test_api_flow.py` for the new response fields

## REQ-LAC-012 — Headliner preview shows the reference

- [x] `cli/main.py` `headliner` renders a reference panel (title + URL) when
      `draft.reference_url` is set, omitted otherwise
- [x] Unit tests in `tests/unit/test_cli.py` for both branches

## Verification

- [x] `uv run ruff check --fix .` passes
- [x] `uv run mypy engagedin cli api migrations` passes (pre-existing test-file
      errors unaffected)
- [x] `uv run pytest` passes with the existing coverage gate (100%)
- [x] `docker compose up -d` + `uv run alembic upgrade head` + empty
      `alembic revision --autogenerate` diff
- [ ] `uv run engagedin headliner` smoke: reference panel renders and the
      published post shows the article card on LinkedIn (requires a live
      publish against a real token — pending manual verification)
