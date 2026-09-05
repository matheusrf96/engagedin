# OpenAPI MCP Server

The OpenAPI MCP server exposes the EngagedIn FastAPI schema to MCP-compatible
clients so they can discover endpoints, validate payloads, and call the API
using the generated OpenAPI document in `docs/openapi.json`.

## What the OpenAPI MCP Server Does

- Reads the generated FastAPI OpenAPI schema from `docs/openapi.json`
- Exposes API operations and schemas to MCP-compatible assistants and tools
- Helps clients validate request and response payloads against documented models
- Makes it easier to explore draft generation, post management, and auth status
  flows safely

## Generating the OpenAPI Schema

Regenerate the schema whenever routes, schemas, or validation rules change:

```bash
make openapi
```

This regenerates `docs/openapi.json` from the live FastAPI app
(`api.main:app`). Equivalent one-liner:

```bash
uv run python -c "import asyncio; from api.openapi_export import export_openapi_schema; asyncio.run(export_openapi_schema())"
```

## Project-Specific Use Cases

- Test draft generation by exploring the `POST /api/v1/drafts` operation and
  its documented request and response models
- Verify Pydantic request and response models used by the post CRUD endpoints
  (list, get, update, publish, delete) before writing client code
- Exercise the health (`/healthz`) and LinkedIn auth status endpoints using
  the documented response payloads
- Let AI assistants inspect available routes before generating test payloads
  or API client examples for the EngagedIn service

## Running the MCP Server Locally

After generating `docs/openapi.json`, start the MCP server locally with:

```bash
npx -y openapi-mcp-server docs/openapi.json
```

The project root also includes `.mcp.json` with the same command
configuration, so MCP-compatible tools can pick it up automatically.

## Keeping the Schema in Sync

CI runs `make openapi-check` and fails when `docs/openapi.json` is stale
relative to the current routes and models. Regenerate and commit the file as
part of any change that touches `api/` routes or Pydantic schemas.
