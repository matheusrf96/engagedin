# LinkedIn Article Card — Design

## 1. End-to-end flow after the change

```
NewsClient.fetch_tech_news
        │  list[NewsArticle] (title, source, url, description, published_at)
        ▼
Engine.generate_headliner_draft
        │  1. format_articles → news context (unchanged, includes URLs)
        │  2. LLM reply ends with "SOURCE: <n>"
        │  3. strip marker → content; map n → articles[n-1]  (fallback: articles[0])
        │  4. GeneratedDraft(content, character_count, reference_url,
        │                   reference_title, reference_description)
        ▼
persist (API) / preview (CLI)          reference travels with the draft
        ▼
Engine.publish_draft
        │  Post(author, commentary, article=ArticleRef(...))
        ▼
LinkedInClient.create_post
        │  body["content"] = {"article": {"source", "title", "description"}}
        ▼
LinkedIn renders the native article card in the feed
```

Standard drafts skip steps 3–4: `reference_*` stay `None`, `Post.article` is
`None`, and the request body is byte-identical to today's.

## 2. Prompt change — `engagedin/llm/prompts.py`

`HEADLINER_USER_PROMPT` gains two instructions (system prompt and standard
`USER_PROMPT` untouched):

```python
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

Focus your post on the single most important or interesting story from the
news above.

Do not include the article URL inside the post text; the URL will be attached
as a link preview separately.

End your reply with a final line on its own in the exact format:
SOURCE: <number of the article from the list above that your post is about>"""
```

`LLMClient.generate_headliner_post` is unchanged — it keeps returning the raw
reply (marker included); parsing belongs to the engine (CON-LAC-003).

## 3. Core models — `engagedin/core/models.py`

```python
class ArticleRef(BaseModel):
    source: str
    title: str
    description: str


class GeneratedDraft(BaseModel):
    content: str
    character_count: int = 0
    reference_url: str | None = None
    reference_title: str | None = None
    reference_description: str | None = None


class Post(BaseModel):
    author: str
    commentary: str
    article: ArticleRef | None = None
    visibility: Literal["PUBLIC", "CONNECTIONS"] = "PUBLIC"
    lifecycle_state: Literal["PUBLISHED"] = "PUBLISHED"
```

## 4. Engine — `engagedin/core/engine.py`

Marker parsing (REQ-LAC-001/002):

```python
import re

SOURCE_LINE_RE = re.compile(r"^\s*SOURCE:\s*(\d+)\s*$", re.IGNORECASE)


def _split_reference(
    content: str, articles: list[NewsArticle]
) -> tuple[str, NewsArticle]:
    lines = content.splitlines()
    match = SOURCE_LINE_RE.match(lines[-1]) if lines else None
    article: NewsArticle | None = None
    if match is not None:
        index = int(match.group(1))
        if 1 <= index <= len(articles):
            article = articles[index - 1]
        content = "\n".join(lines[:-1]).rstrip("\n")
    if article is None:
        article = articles[0]          # top-ranked fallback (REQ-LAC-002)
    return content, article
```

`generate_headliner_draft`:

```python
def generate_headliner_draft(self, days: int = 1, topic: str = "technology") -> GeneratedDraft:
    articles = self.news.fetch_tech_news(days=days, topic=topic)
    if not articles:
        raise NewsError(...)
    news_context = NewsClient.format_articles(articles)
    reply = self.llm.generate_headliner_post(topic, news_context, self.ruleset, days=days)
    content, article = _split_reference(reply, articles)
    return GeneratedDraft(
        content=content,
        character_count=len(content),
        reference_url=article.url,
        reference_title=article.title,
        reference_description=article.description or None,
    )
```

`publish_draft` (REQ-LAC-007):

```python
article = None
if draft.reference_url:
    article = ArticleRef(
        source=draft.reference_url,
        title=draft.reference_title or draft.reference_url,
        description=(
            draft.reference_description
            or draft.reference_title
            or draft.reference_url
        ),
    )
post = Post(author=author, commentary=draft.content, article=article)
```

`generate_draft`, `schedule_advisory`, `generate_and_publish` are untouched.

## 5. LinkedIn client — `engagedin/linkedin/client.py`

`create_post` builds the body, then conditionally attaches the card
(REQ-LAC-006):

```python
body: dict[str, object] = {
    "author": post.author,
    "commentary": post.commentary,
    "visibility": post.visibility,
    "distribution": {...},          # unchanged
    "lifecycleState": post.lifecycle_state,
    "isReshareDisabledByAuthor": False,
}
if post.article is not None:
    body["content"] = {
        "article": {
            "source": post.article.source,
            "title": post.article.title,
            "description": post.article.description,
        }
    }
```

No `thumbnail` key (CON-LAC-001). LinkedIn accepts any absolute URL in
`article.source` and wraps it in its `lnkd.in` redirect; `title` is required by
LinkedIn — always sent. Rest of the method (headers, retries, URN extraction)
is unchanged.

## 6. Data model — `api/models.py` and migration `0002`

`PostRecord` gains three nullable mapped columns:

```python
reference_url: Mapped[str | None] = mapped_column(String(2048))
reference_title: Mapped[str | None] = mapped_column(String(1024))
reference_description: Mapped[str | None] = mapped_column(Text)
```

`migrations/versions/0002_post_reference.py`:

```python
revision: str = "0002"
down_revision: str | None = "0001"

def upgrade() -> None:
    op.add_column("posts", sa.Column("reference_url", sa.String(length=2048), nullable=True))
    op.add_column("posts", sa.Column("reference_title", sa.String(length=1024), nullable=True))
    op.add_column("posts", sa.Column("reference_description", sa.Text(), nullable=True))

def downgrade() -> None:
    op.drop_column("posts", "reference_description")
    op.drop_column("posts", "reference_title")
    op.drop_column("posts", "reference_url")
```

Existing rows keep `NULL`; no index or constraint is added.

## 7. API layer

`api/schemas.py` — `PostOut` only (request schemas unchanged, CON-LAC-005):

```python
class PostOut(BaseModel):
    ...
    reference_url: str | None
    reference_title: str | None
    reference_description: str | None
```

`api/services/posts.py`:

```python
# create_draft — persist whatever the engine produced (REQ-LAC-009)
record = PostRecord(
    topic=topic,
    source=source,
    status=PostStatus.DRAFT,
    content=draft.content,
    character_count=draft.character_count,
    reference_url=draft.reference_url,
    reference_title=draft.reference_title,
    reference_description=draft.reference_description,
)

# publish — rebuild the draft with stored reference fields (REQ-LAC-010)
def _publish_draft(
    self,
    content: str,
    character_count: int,
    reference_url: str | None,
    reference_title: str | None,
    reference_description: str | None,
) -> str:
    draft = GeneratedDraft(
        content=content,
        character_count=character_count,
        reference_url=reference_url,
        reference_title=reference_title,
        reference_description=reference_description,
    )
    return Engine().publish_draft(draft)
```

`publish` calls it inside `asyncio.to_thread` with the record's stored fields
(`record.reference_url`, `record.reference_title`,
`record.reference_description`). Repositories and routers need no changes —
`PostRepository.add/update` are generic and `PostOut.model_validate` picks up
the new columns.

## 8. CLI — `cli/main.py`

Only the `headliner` command's preview changes (REQ-LAC-012); `draft` and
`post` are untouched:

```python
if draft.reference_url:
    console.print(
        Panel(
            f"{draft.reference_title}\n{draft.reference_url}",
            title="📰 Reference article",
            border_style="cyan",
        )
    )
```

Publishing stays `engine.publish_draft(draft)` — the engine already carries
the reference, so no CLI signature changes.

## 9. Testing strategy

Existing suites to extend (mock at boundaries, `@patch` decorators,
`AsyncMock` for async calls — CON-LAC-006):

| File | New cases |
|------|-----------|
| `tests/unit/test_engine.py` | marker parsed and stripped (content + `character_count` post-strip); `SOURCE: 3` maps to `articles[2]`; missing marker → `articles[0]` with content untouched; out-of-range / non-numeric index → `articles[0]`; empty description → `reference_description is None`; `publish_draft` builds `Post.article` from reference fields and `None` without them |
| `tests/unit/test_models.py` | `ArticleRef` required fields; `GeneratedDraft` reference defaults to `None` |
| `tests/unit/test_linkedin.py` | body contains `content.article` with the three fields when `article` is set; no `content` key when `article is None` |
| `tests/unit/test_llm.py` | `HEADLINER_USER_PROMPT` contains the `SOURCE:` instruction and the no-URL rule |
| `tests/unit/test_cli.py` | headliner preview shows/hides the reference panel |
| `tests/unit/api/test_service.py` | `create_draft` (headliner) persists reference columns; `create_draft` (standard) leaves them `None`; `publish` forwards the stored reference fields to `GeneratedDraft`/engine |
| `tests/unit/api/test_generation.py` + `test_posts.py` | `PostOut` includes the three nullable fields |
| `tests/integration/test_api_flow.py` | headliner create → 201 with reference fields; publish → engine receives them (mocked) |

LLM-marker nondeterminism is fully covered by unit tests around
`_split_reference`; no live LLM/LinkedIn calls in tests.

## 10. Verification

```bash
uv run ruff check --fix .
uv run mypy .
docker compose up -d
uv run alembic upgrade head
uv run alembic revision --autogenerate        # must yield an empty diff
uv run pytest -q
uv run engagedin headliner --yes              # smoke: reference panel renders,
                                              # published post shows the card
```

Manual check with a real token: publish a headliner draft and confirm the
LinkedIn post renders the article card with the news title/description and the
source URL as the card target.

## 11. ADR references

- **ADR-LAC-001 — Article card over plain-text URL.** The Posts API removed
  URL scraping; a bare URL in `commentary` is plain text with no preview.
  `content.article` renders the native card and reuses metadata the news APIs
  already provide. Rejected: URL in commentary (weaker engagement, no card),
  reshare-based approaches (commentary would be lost).
- **ADR-LAC-002 — `SOURCE:` text marker over structured output / two-pass LLM.**
  Plain-text trailing marker keeps provider portability and adds no latency or
  cost. Rejected: JSON-mode replies (provider-dependent, complicates the
  shared `LLMClient`), two-pass generation (pick article, then write — doubles
  LLM calls). Risk of an ignored marker is mitigated by the top-ranked
  fallback, which matches the prompt's "most significant story" instruction.
- **ADR-LAC-003 — Metadata from the news API, not scraping.** `NewsArticle`
  already carries `title`/`description`/`url`; scraping would add HTTP
  fetches, bot-blocking risk, and HTML parsing for no quality gain.
- **ADR-LAC-004 — No thumbnail in v1.** `article.thumbnail` needs an image
  upload through the Images API (URN), which involves extra requests and
  LinkedIn product/permission considerations for member posts; the card
  renders fine without it. Deferred.
- **ADR-LAC-005 — Reference is derived, not user-editable.** The reference is
  a generation artifact selected by the engine; adding user-editable fields to
  `DraftCreateRequest`/`PostUpdateRequest` would expand the API contract with
  validation concerns (URL safety, length) that this feature does not need.
