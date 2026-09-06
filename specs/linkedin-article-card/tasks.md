# LinkedIn Article Card — Tasks

> Implementation order: core models → prompt → engine → LinkedIn client →
> migration/data model → API service/schemas → CLI → tests → verification.
> The checklist below is grouped by requirement ID.

## Spec

- [ ] Write `specs/linkedin-article-card/requirements.md`
- [ ] Write `specs/linkedin-article-card/design.md`
- [ ] Link the spec from `specs/README.md`

## REQ-LAC-001 — SOURCE marker parsing

- [ ] Add `SOURCE_LINE_RE` and `_split_reference` helper in
      `engagedin/core/engine.py` (strip trailing marker, 1-based index mapping)
- [ ] `generate_headliner_draft` populates `reference_url`/`reference_title`/
      `reference_description` from the mapped article
- [ ] Unit tests: valid `SOURCE: 3` maps to `articles[2]`; marker stripped from
      content; `character_count` computed post-strip

## REQ-LAC-002 — Top-ranked fallback

- [ ] `_split_reference` falls back to `articles[0]` on missing, non-numeric,
      or out-of-range marker without raising
- [ ] Unit tests: missing marker (content untouched), out-of-range index,
      malformed marker line

## REQ-LAC-003 — GeneratedDraft reference fields

- [ ] Extend `GeneratedDraft` in `engagedin/core/models.py` with optional
      `reference_url`, `reference_title`, `reference_description` (default
      `None`)
- [ ] Confirm `generate_draft` (standard) leaves them `None`
- [ ] Unit tests in `tests/unit/test_models.py` for defaults

## REQ-LAC-004 — Prompt marker instruction

- [ ] Update `HEADLINER_USER_PROMPT` in `engagedin/llm/prompts.py`: forbid the
      URL in the post body; require the final `SOURCE: <number>` line
- [ ] Unit test in `tests/unit/test_llm.py` asserting the instructions render
      into the built user prompt

## REQ-LAC-005 — ArticleRef and Post content

- [ ] Add `ArticleRef(source, title, description)` to
      `engagedin/core/models.py`
- [ ] Add `article: ArticleRef | None = None` to `Post`
- [ ] Unit tests for `ArticleRef` validation and `Post` default

## REQ-LAC-006 — Article card request body

- [ ] `LinkedInClient.create_post` adds
      `body["content"] = {"article": {...}}` only when `post.article` is set
      (no `thumbnail` key); body otherwise unchanged
- [ ] Unit tests in `tests/unit/test_linkedin.py`: body with card, body
      without `content` key

## REQ-LAC-007 — Publish flow passes the reference

- [ ] `Engine.publish_draft` builds `ArticleRef` from draft reference fields
      with description fallback (`description` → `title` → `url`)
- [ ] No `reference_url` → text-only post as before
- [ ] Unit tests: `Post.article` populated from a referenced draft; `None` for
      a plain draft

## REQ-LAC-008 — Reference columns on `posts`

- [ ] Add `reference_url` (String 2048), `reference_title` (String 1024),
      `reference_description` (Text) to `PostRecord` in `api/models.py`
- [ ] Create `migrations/versions/0002_post_reference.py` (`down_revision`
      `0001`) with symmetric downgrade
- [ ] Verify `uv run alembic upgrade head` on the dev database and that
      `alembic revision --autogenerate` afterwards yields an empty diff

## REQ-LAC-009 — Draft creation persistence

- [ ] `PostService.create_draft` stores the draft's reference fields in the
      record (standard → `NULL`)
- [ ] Unit tests in `tests/unit/api/test_service.py`: headliner persists
      reference; standard leaves `None`

## REQ-LAC-010 — Publish from stored record

- [ ] `PostService._publish_draft` accepts the reference fields and rebuilds
      `GeneratedDraft` with them; `publish` passes the record's stored fields
- [ ] Unit tests: publish forwards stored reference fields; `NULL` fields →
      text-only publish

## REQ-LAC-011 — Reference in API responses

- [ ] Add the three nullable reference fields to `PostOut` in
      `api/schemas.py`
- [ ] Unit tests in `tests/unit/api/test_generation.py` / `test_posts.py`
      asserting the fields appear in responses
- [ ] Update `tests/integration/test_api_flow.py` for the new response fields

## REQ-LAC-012 — Headliner preview shows the reference

- [ ] `cli/main.py` `headliner` renders a reference panel (title + URL) when
      `draft.reference_url` is set, omitted otherwise
- [ ] Unit tests in `tests/unit/test_cli.py` for both branches

## Verification

- [ ] `uv run ruff check --fix .` passes
- [ ] `uv run mypy .` passes
- [ ] `uv run pytest -q` passes with the existing coverage gate
- [ ] `docker compose up -d` + `uv run alembic upgrade head` + empty
      `alembic revision --autogenerate` diff
- [ ] `uv run engagedin headliner` smoke: reference panel renders and the
      published post shows the article card on LinkedIn
