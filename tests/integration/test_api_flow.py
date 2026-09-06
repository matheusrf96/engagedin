from __future__ import annotations

from unittest.mock import patch

from httpx import AsyncClient

from engagedin.core.models import GeneratedDraft
from engagedin.linkedin.client import LinkedInError


async def test_healthz_reports_reachable(async_client: AsyncClient) -> None:
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["database"] == "reachable"


async def test_full_post_lifecycle(async_client: AsyncClient) -> None:
    with patch("api.services.posts.Engine") as mock_engine:
        mock_engine.return_value.generate_draft.return_value = GeneratedDraft(
            content="Integration test draft", character_count=25
        )
        mock_engine.return_value.publish_draft.return_value = "urn:li:share:int123"

        # Create draft
        resp = await async_client.post(
            "/api/v1/drafts", json={"topic": "integration"}
        )
        assert resp.status_code == 201
        post_id = resp.json()["id"]

        # List posts
        resp = await async_client.get("/api/v1/posts")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

        # Get the specific post
        resp = await async_client.get(f"/api/v1/posts/{post_id}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "draft"

        # Update content
        resp = await async_client.patch(
            f"/api/v1/posts/{post_id}",
            json={"content": "Updated integration content"},
        )
        assert resp.status_code == 200
        assert resp.json()["content"] == "Updated integration content"

        # Publish
        resp = await async_client.post(f"/api/v1/posts/{post_id}/publish")
        assert resp.status_code == 200
        assert resp.json()["status"] == "published"
        assert resp.json()["linkedin_post_urn"] == "urn:li:share:int123"

        # Publish again (409)
        resp = await async_client.post(f"/api/v1/posts/{post_id}/publish")
        assert resp.status_code == 409

    # Delete
    resp = await async_client.delete(f"/api/v1/posts/{post_id}")
    assert resp.status_code == 204

    # Get after delete (404)
    resp = await async_client.get(f"/api/v1/posts/{post_id}")
    assert resp.status_code == 404


async def test_headliner_reference_roundtrip(async_client: AsyncClient) -> None:
    with patch("api.services.posts.Engine") as mock_engine:
        mock_engine.return_value.generate_headliner_draft.return_value = (
            GeneratedDraft(
                content="Headliner integration draft",
                character_count=25,
                reference_url="https://example.com/int",
                reference_title="Integration news",
                reference_description="Integration description",
            )
        )
        mock_engine.return_value.publish_draft.return_value = "urn:li:share:int456"

        resp = await async_client.post(
            "/api/v1/drafts",
            json={"topic": "AI", "source": "headliner", "days": 1},
        )
        assert resp.status_code == 201
        data = resp.json()
        post_id = data["id"]
        assert data["reference_url"] == "https://example.com/int"
        assert data["reference_title"] == "Integration news"
        assert data["reference_description"] == "Integration description"

        # Published post carries the stored reference to the engine
        resp = await async_client.post(f"/api/v1/posts/{post_id}/publish")
        assert resp.status_code == 200
        draft = mock_engine.return_value.publish_draft.call_args[0][0]
        assert draft.reference_url == "https://example.com/int"
        assert draft.reference_title == "Integration news"
        assert draft.reference_description == "Integration description"


async def test_publish_linkedin_failure_marks_failed(
    async_client: AsyncClient,
) -> None:
    with patch("api.services.posts.Engine") as mock_engine:
        mock_engine.return_value.generate_draft.return_value = GeneratedDraft(
            content="Will fail on publish", character_count=21
        )

        resp = await async_client.post(
            "/api/v1/drafts", json={"topic": "linkedin-fail"}
        )
        assert resp.status_code == 201
        post_id = resp.json()["id"]

    with patch("api.services.posts.Engine") as mock_engine:
        mock_engine.return_value.publish_draft.side_effect = LinkedInError(
            "LinkedIn API error"
        )

        resp = await async_client.post(f"/api/v1/posts/{post_id}/publish")
        assert resp.status_code == 502

    # Verify the record persisted as failed
    resp = await async_client.get(f"/api/v1/posts/{post_id}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "failed"
    assert "LinkedIn API error" in resp.json()["error"]


async def test_list_pagination_and_filters(
    async_client: AsyncClient,
) -> None:
    with patch("api.services.posts.Engine") as mock_engine:
        mock_engine.return_value.generate_draft.return_value = GeneratedDraft(
            content="x", character_count=1
        )

        for topic in ["py", "py", "rust"]:
            await async_client.post("/api/v1/drafts", json={"topic": topic})

    # Filter by topic
    resp = await async_client.get("/api/v1/posts", params={"topic": "py"})
    assert resp.json()["total"] == 2

    # Filter by status
    resp = await async_client.get(
        "/api/v1/posts", params={"status": "draft"}
    )
    assert resp.json()["total"] >= 3

    # Pagination
    resp = await async_client.get("/api/v1/posts", params={"limit": 1})
    assert len(resp.json()["items"]) == 1

    resp = await async_client.get(
        "/api/v1/posts", params={"limit": 2, "offset": 2}
    )
    assert len(resp.json()["items"]) <= 2
