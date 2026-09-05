# AGENTS.md — Code best practices

## Imports

- **No mid-file imports.** All imports go at the top of the module. If an import causes a circular dependency, restructure the modules — do not defer imports inside functions.

## Control flow

- **Early returns over if/else.** Use guard clauses (`if condition: raise/return`) to handle error/edge cases first, then proceed with the happy path. Avoid nesting happy-path logic inside `else` blocks.

```python
# Good
async def get(self, post_id: int) -> PostRecord:
    record = await self.session.get(PostRecord, post_id)
    if record is None:
        raise NotFoundError(f"Post {post_id} not found")
    return record

# Bad
async def get(self, post_id: int) -> PostRecord:
    record = await self.session.get(PostRecord, post_id)
    if record is not None:
        return record
    else:
        raise NotFoundError(f"Post {post_id} not found")
```

## Exceptions

- **Domain exceptions belong in the service layer.** Services raise typed exceptions (`NotFoundError`, `ConflictError`, `ExternalServiceError`). Routers catch service exceptions and map them to HTTP status codes. Routers never import third-party exception types directly (e.g. `LinkedInError`, `LLMConfigError`).

```python
# Good — service catches and wraps
except LinkedInError as e:
    raise ExternalServiceError(str(e)) from e

# Good — router only knows service exceptions
except ExternalServiceError as e:
    raise HTTPException(status_code=e.status_code, detail=str(e))
```

## Testing

- **`@patch` decorators, not `with patch(...)` blocks.** Use `@patch("target")` as a decorator on the test function. The mock is passed as a positional argument. This keeps test bodies clean and avoids deeply nested `with` blocks.

```python
# Good
@patch("api.routers.posts.PostService")
async def test_get_post(mock_cls: MagicMock, client: AsyncClient) -> None:
    mock_cls.return_value.get = AsyncMock(return_value=record)
    response = await client.get("/api/v1/posts/1")
    assert response.status_code == 200

# Bad
async def test_get_post(client: AsyncClient) -> None:
    with patch("api.routers.posts.PostService") as mock_cls:
        mock_cls.return_value.get = AsyncMock(return_value=record)
        response = await client.get("/api/v1/posts/1")
        assert response.status_code == 200
```

- **Mock at the boundary, not deep inside.** Mock the service class in router tests, the router in integration tests, not internal implementation details.
- **AsyncMock for async calls.** Always use `AsyncMock` for `async def` methods; use `MagicMock` for sync attributes and return values.

## Style

- **Line length**: 100 characters (ruff enforced).
- **Python 3.12+**: use `X | Y` union syntax, `str.removeprefix`, `datetime.UTC`, `from __future__ import annotations`.
- **Ruff rule sets**: E, F, I, N, W, UP. Run `uv run ruff check --fix .` to auto-fix import ordering.
- **Mypy**: `disallow_untyped_defs = true`. All public functions must have full type annotations.
