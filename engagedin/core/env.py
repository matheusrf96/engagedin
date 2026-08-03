from __future__ import annotations

from pathlib import Path


def save_env_values(path: str | Path, values: dict[str, str]) -> Path:
    """Update or append KEY=VALUE lines in a .env-style file.

    Existing keys are replaced in place; comments and unrelated lines are
    preserved; missing keys are appended. Creates the file (and parent
    directories) if needed. The file is restricted to the current user
    (0600) because it may contain credentials. Returns the resolved path.
    """
    path = Path(path)
    lines = path.read_text().splitlines() if path.exists() else []
    keys = set(values)
    written: set[str] = set()
    out: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key = stripped.split("=", 1)[0].strip()
            if key in keys:
                out.append(f"{key}={values[key]}")
                written.add(key)
                continue
        out.append(line)
    for key in sorted(keys - written):
        out.append(f"{key}={values[key]}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(out) + "\n")
    path.chmod(0o600)
    return path
