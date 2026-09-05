"""Utilities for exporting the FastAPI OpenAPI schema."""

import asyncio
import json
from pathlib import Path

from api.main import app


async def export_openapi_schema(output_path: str = "docs/openapi.json") -> None:
    """Export the FastAPI OpenAPI schema to a JSON file.

    Args:
        output_path: Destination path for the exported OpenAPI JSON document.
    """
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    openapi_schema = app.openapi()
    schema_json = json.dumps(openapi_schema, indent=2, ensure_ascii=False)

    await asyncio.to_thread(output_file.write_text, schema_json, encoding="utf-8")
