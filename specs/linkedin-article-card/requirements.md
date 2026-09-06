# LinkedIn Article Card — Requirements

Feature ID: `LAC`

## Context

Headliner drafts are generated from news articles fetched by `NewsClient`
(Hacker News or NewsAPI). Each `NewsArticle` already carries `title`, `source`,
`url`, and `description`, and all of that metadata is passed to the LLM as
context. However, the generated `GeneratedDraft` only keeps `content` and
`character_count`: the reference to the news story the post is about is lost
before the draft is stored or published. Published posts therefore carry no
link to the source news.

On the LinkedIn side, the versioned Posts API (`POST /rest/posts`, the endpoint
this project already uses with `X-Restli-Protocol-Version: 2.0.0` and
`Linkedin-Version: 202506`) does **not** support URL scraping for article post
creation. A bare URL inside `commentary` renders as plain clickable text with
no preview card. To render the native article card (the format that engages
best for news commentary), the API partner must set the article fields itself:

```json
"content": {
  "article": {
    "source": "<article URL>",
    "title": "<title>",
    "description": "<description>",
    "thumbnail": "<urn:li:image:...>"   (optional; requires Images API)
  }
}
```

The missing piece in the generation flow is knowing **which** article the LLM
wrote about. The prompt already asks the LLM to focus on "the single most
important or interesting story", but the LLM never tells the engine which one
it picked.

Decisions locked during planning:

- **Link style**: native article card via `content.article` — not a plain URL
  appended to the post text.
- **Reference selection**: the LLM ends its reply with a `SOURCE: <number>`
  marker identifying the article (1-based index into the fetched list); the
  engine strips the marker and maps it back to the article.
- **Fallback**: when the marker is missing, unparseable, or out of range, the
  top-ranked article (index 1) is used.
- **Thumbnail**: out of scope — no Images API integration in this feature.
- **Metadata source**: `title`/`description` come from the fetched
  `NewsArticle` only; no page scraping.

## Requirements

### Reference selection

### REQ-LAC-001 — SOURCE marker parsing

WHEN `Engine.generate_headliner_draft` receives an LLM reply whose last line
matches `SOURCE: <n>` (case-insensitive, `n` a 1-based integer)
THE SYSTEM SHALL strip that line from the post content, map `n` to the `n`-th
article of the fetched list, and populate `reference_url`,
`reference_title`, and `reference_description` from that `NewsArticle`
AND `character_count` SHALL be computed from the content after stripping
WHILE the news context and the article list are built from the same list so
indices always agree.

### REQ-LAC-002 — Top-ranked fallback

WHEN the LLM reply has no `SOURCE:` line, or the parsed index is out of range
(`n < 1` or `n > len(articles)`)
THE SYSTEM SHALL use the first (top-ranked) article as the reference
AND SHALL keep the post content unchanged (nothing stripped, no error raised)
WHILE generation still succeeds whenever at least one article was fetched.

### REQ-LAC-003 — GeneratedDraft reference fields

THE SYSTEM SHALL add optional `reference_url`, `reference_title`, and
`reference_description` fields to `GeneratedDraft`, all defaulting to `None`
AND standard drafts produced by `Engine.generate_draft` SHALL have all three
fields `None`
WHILE `character_count` continues to reflect the post content only (the article
card does not count toward the LinkedIn commentary length).

### Headliner prompt

### REQ-LAC-004 — Prompt marker instruction

WHEN the headliner user prompt is built
THE SYSTEM SHALL instruct the LLM to not include the article URL inside the
post text
AND SHALL instruct the LLM to end its reply with a final line
`SOURCE: <number>` identifying the article from the list it wrote about
WHILE the system prompt and the standard `USER_PROMPT` remain unchanged.

### Core models

### REQ-LAC-005 — ArticleRef and Post content

THE SYSTEM SHALL define an `ArticleRef` model with `source`, `title`, and
`description` string fields
AND `Post` SHALL accept an optional `article: ArticleRef | None` field
defaulting to `None`
WHILE text-only posts (no article) produce a request body identical to the
current one.

### LinkedIn publishing

### REQ-LAC-006 — Article card request body

WHEN `LinkedInClient.create_post` is called with a `Post` whose `article` is
set
THE SYSTEM SHALL add `"content": {"article": {"source": ..., "title": ...,
"description": ...}}` to the request body
AND SHALL not send a `thumbnail` field
AND WHEN `article` is `None` THE SYSTEM SHALL omit the `content` key entirely
WHILE the rest of the body (`author`, `commentary`, `visibility`,
`distribution`, `lifecycleState`, `isReshareDisabledByAuthor`) is unchanged.

### REQ-LAC-007 — Publish flow passes the reference

WHEN `Engine.publish_draft` is called with a draft that has `reference_url`
THE SYSTEM SHALL build `Post.article` from the draft's reference fields
AND the article `description` SHALL fall back to `reference_title`, then to
`reference_url`, when `reference_description` is empty or `None`
AND WHEN the draft has no `reference_url` THE SYSTEM SHALL publish a
text-only post as before
WHILE `publish_draft` returns the post URN in both cases.

### Data model and migrations

### REQ-LAC-008 — Reference columns on `posts`

THE SYSTEM SHALL add nullable columns to the `posts` table:
`reference_url` (`varchar(2048)`), `reference_title` (`varchar(1024)`), and
`reference_description` (`text`)
AND SHALL add them through a new Alembic revision (`0002`) with `down_revision`
`0001` and a symmetric downgrade that drops the columns
WHILE existing rows keep `NULL` in all three columns.

### API layer

### REQ-LAC-009 — Draft creation persistence

WHEN `POST /api/v1/drafts` persists a headliner draft
THE SYSTEM SHALL store the draft's `reference_url`, `reference_title`, and
`reference_description` in the new columns
AND WHEN the source is `standard` THE SYSTEM SHALL store `NULL` in all three
WHILE no change is made to `DraftCreateRequest` (the reference is derived, not
user-supplied).

### REQ-LAC-010 — Publish from stored record

WHEN `POST /api/v1/posts/{id}/publish` publishes a record with reference
columns populated
THE SYSTEM SHALL rebuild `GeneratedDraft` with the stored reference fields so
the article card is sent to LinkedIn
AND WHEN the columns are `NULL` THE SYSTEM SHALL publish a text-only post
WHILE success/failure status transitions and error handling are unchanged.

### REQ-LAC-011 — Reference in API responses

WHEN any endpoint returns a `PostOut` record
THE SYSTEM SHALL include `reference_url`, `reference_title`, and
`reference_description` (nullable) in the response
WHILE `PostListResponse` items carry the same fields.

### CLI

### REQ-LAC-012 — Headliner preview shows the reference

WHEN `engagedin headliner` renders the generated draft for confirmation
THE SYSTEM SHALL display the reference article title and URL alongside the
post content before the publish prompt
AND WHEN no reference is available (all fields `None`) THE SYSTEM SHALL omit
the reference display
WHILE the `draft` and `post` commands remain unchanged.

## Constraints

### CON-LAC-001 — No thumbnail

The article card SHALL NOT include a `thumbnail`. Uploading images via the
Images API (and any LinkedIn product permission it requires) is deferred to a
future feature.

### CON-LAC-002 — No page scraping

`title`, `description`, and `source` SHALL come exclusively from the fetched
`NewsArticle` metadata. No HTTP fetches of the article page are added.

### CON-LAC-003 — Business logic placement

Marker parsing and reference mapping SHALL live in `engagedin/core/engine.py`.
`cli/` SHALL only present; `api/` SHALL only persist and orchestrate.

### CON-LAC-004 — Plain-text marker, no structured output

The LLM contract SHALL remain plain text (a trailing `SOURCE:` line). No
JSON-mode / structured-output features of LiteLLM are introduced, keeping
provider portability (DeepSeek, OpenAI, Anthropic, local models).

### CON-LAC-005 — API request schemas unchanged

`DraftCreateRequest` and `PostUpdateRequest` SHALL NOT gain reference fields in
this feature; users cannot edit the reference before publishing.

### CON-LAC-006 — Type, style, and test gates

All new code SHALL pass the ruff configuration (line length 100; rule sets E,
F, I, N, W, UP) and mypy (`disallow_untyped_defs`). Tests SHALL use `@patch`
decorators mocking at boundaries (service/engine/client), `AsyncMock` for
async calls, and the suite SHALL keep the existing coverage gate.
