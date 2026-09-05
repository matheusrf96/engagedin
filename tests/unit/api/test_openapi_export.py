"""Unit tests for the OpenAPI export utility."""

from unittest.mock import MagicMock, patch

from api.openapi_export import export_openapi_schema


@patch("api.openapi_export.app")
@patch("pathlib.Path.write_text")
@patch("pathlib.Path.mkdir")
async def test_export_openapi_schema_writes_json(
    mock_mkdir: MagicMock, mock_write: MagicMock, mock_app: MagicMock
) -> None:
    mock_app.openapi.return_value = {"openapi": "3.1.0", "paths": {}}

    await export_openapi_schema("/tmp/test_openapi.json")

    mock_app.openapi.assert_called_once()
    mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
    mock_write.assert_called_once()
