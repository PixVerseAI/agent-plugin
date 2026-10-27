from __future__ import annotations

import json
import os
import shlex
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT_MARKERS = (".git", "pyproject.toml", "README.md")


def plugin_root() -> Path:
    """Return the installed plugin root independently from the user's workspace."""
    configured = os.environ.get("PIXVERSE_AGENT_PLUGIN_ROOT", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    for candidate in Path(__file__).resolve().parents:
        if (
            (candidate / "skills").is_dir()
            or (candidate / "packages/skills/catalog.json").is_file()
        ) and (candidate / "scripts/pixverse-runtime").is_file():
            return candidate
    return Path(__file__).resolve().parents[1]


def runtime_command() -> str:
    """Return a shell-ready command prefix for user-facing next-step messages."""
    executable = os.environ.get("PIXVERSE_AGENT_RUNTIME_EXECUTABLE", "").strip()
    return shlex.quote(executable) if executable else "python -m pixverse_runtime.cli"


def repo_root(start: Path | None = None) -> Path:
    """Return the user's current project root, not the installed plugin root."""
    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if any(((candidate / marker).exists() for marker in ROOT_MARKERS)):
            return candidate
    return current


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def slugify(value: str, fallback: str = "untitled") -> str:
    value = unicodedata.normalize("NFKC", value).strip().lower()
    parts: list[str] = []
    previous_separator = False
    for char in value:
        if char.isalnum():
            parts.append(char)
            previous_separator = False
            continue
        if parts and (not previous_separator):
            parts.append("-")
            previous_separator = True
    slug = "".join(parts).strip("-")
    return slug or fallback


class InvalidProjectSlug(ValueError):
    """A caller passed a filesystem path where a project slug was required."""


_PATH_SEPARATORS = tuple((sep for sep in ("/", "\\", os.sep, os.altsep) if sep))


def normalize_project_slug(value: str) -> str:
    """Reject paths before Unicode titles are normalized to workspace identifiers."""
    raw = str(value).strip()
    if not raw:
        raise InvalidProjectSlug("--project requires a non-empty project slug")
    if any((separator in raw for separator in _PATH_SEPARATORS)):
        suggestion = raw.replace("\\", "/").strip("/").rsplit("/", 1)[-1]
        raise InvalidProjectSlug(
            f"--project takes a slug, not a path (got '{raw}'; did you mean '{suggestion}'?)"
        )
    return raw


def project_dir(slug: str, root: Path | None = None) -> Path:
    return repo_root(root) / "projects" / slugify(normalize_project_slug(slug))


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                rows.append(
                    {
                        "kind": "invalid_jsonl",
                        "line": line_number,
                        "error": str(exc),
                        "raw": _compact_text(line),
                    }
                )
    return rows


def _compact_text(value: str, max_length: int = 280) -> str:
    value = " ".join(value.split())
    if len(value) <= max_length:
        return value
    return value[: max_length - 3].rstrip() + "..."


def local_data_home() -> Path:
    base = os.environ.get("PIXVERSE_AGENT_HOME")
    if base:
        return Path(base).expanduser()
    legacy_base = os.environ.get("PVX_HOME")
    if legacy_base:
        return Path(legacy_base).expanduser()
    return Path.home() / ".pixverse-agent-plugin"


def ensure_project(slug: str) -> Path:
    path = project_dir(slug)
    path.mkdir(parents=True, exist_ok=True)
    return path
