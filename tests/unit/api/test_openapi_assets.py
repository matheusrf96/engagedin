"""Asset checks for the OpenAPI export integration."""

from pathlib import Path


def test_openapi_export_module_exists() -> None:
    module_path = Path("api/openapi_export.py")
    assert module_path.exists()


def test_openapi_docs_file_exists_and_non_empty() -> None:
    docs_path = Path("docs/mcp/openapi.md")
    assert docs_path.exists()
    assert docs_path.read_text(encoding="utf-8").strip()


def test_openapi_docs_contains_required_sections() -> None:
    content = Path("docs/mcp/openapi.md").read_text(encoding="utf-8")

    assert "## What the OpenAPI MCP Server Does" in content
    assert "## Generating the OpenAPI Schema" in content
    assert "## Project-Specific Use Cases" in content
    assert "## Running the MCP Server Locally" in content
