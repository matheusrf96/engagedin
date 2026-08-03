from __future__ import annotations

from pathlib import Path

from engagedin.core.env import save_env_values


def test_creates_missing_file(tmp_path: Path) -> None:
    path = tmp_path / "nested" / ".env"
    result = save_env_values(path, {"FOO": "bar"})
    assert result == path
    assert path.read_text() == "FOO=bar\n"


def test_updates_existing_key_in_place(tmp_path: Path) -> None:
    path = tmp_path / ".env"
    path.write_text("# comment\nFOO=old\nBAR=baz\n")
    save_env_values(path, {"FOO": "new"})
    assert path.read_text() == "# comment\nFOO=new\nBAR=baz\n"


def test_appends_new_keys(tmp_path: Path) -> None:
    path = tmp_path / ".env"
    path.write_text("FOO=bar\n")
    save_env_values(path, {"BAR": "baz", "FOO": "bar"})
    assert path.read_text() == "FOO=bar\nBAR=baz\n"


def test_preserves_blank_lines_and_comments(tmp_path: Path) -> None:
    path = tmp_path / ".env"
    path.write_text("A=1\n\n# keep me\nB=2\n")
    save_env_values(path, {"B": "updated"})
    assert path.read_text() == "A=1\n\n# keep me\nB=updated\n"


def test_ignores_commented_keys(tmp_path: Path) -> None:
    path = tmp_path / ".env"
    path.write_text("# TOKEN=secret\n")
    save_env_values(path, {"TOKEN": "new"})
    assert path.read_text() == "# TOKEN=secret\nTOKEN=new\n"


def test_restricts_file_permissions(tmp_path: Path) -> None:
    path = tmp_path / ".env"
    save_env_values(path, {"TOKEN": "secret"})
    assert path.stat().st_mode & 0o777 == 0o600


def test_restricts_permissions_on_existing_file(tmp_path: Path) -> None:
    path = tmp_path / ".env"
    path.write_text("FOO=bar\n")
    path.chmod(0o644)
    save_env_values(path, {"FOO": "updated"})
    assert path.stat().st_mode & 0o777 == 0o600
