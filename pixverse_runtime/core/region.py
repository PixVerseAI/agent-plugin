from __future__ import annotations

import os
from pathlib import Path

PIXVERSE_REGION_ENV = "PIXVERSE_REGION"
PIXVERSE_DEFAULT_REGION = "global"
PIXVERSE_REGIONS = frozenset({"global", "cn"})


class PixVerseRegionError(ValueError):
    pass


def explicit_pixverse_region(argv: list[str]) -> str:
    """Return one validated ``--region`` value from a PixVerse argv tail."""
    values: list[str] = []
    index = 0
    while index < len(argv):
        argument = argv[index]
        if argument == "--":
            break
        if argument == "--region":
            if index + 1 >= len(argv) or argv[index + 1] == "--" or argv[index + 1].startswith("-"):
                raise PixVerseRegionError("--region requires global or cn")
            values.append(argv[index + 1])
            index += 2
            continue
        if argument.startswith("--region="):
            values.append(argument.split("=", 1)[1])
        index += 1
    normalized = [value.strip().lower() for value in values]
    invalid = [value for value in normalized if value not in PIXVERSE_REGIONS]
    if invalid:
        raise PixVerseRegionError(f"invalid PixVerse region {invalid[0]!r}; expected global or cn")
    if len(set(normalized)) > 1:
        raise PixVerseRegionError("conflicting --region values were supplied")
    return normalized[0] if normalized else ""


def _dotenv_region(path: Path) -> str | None:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise PixVerseRegionError(f"could not read PixVerse region from {path}: {exc}") from exc
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        (key, value) = stripped.split("=", 1)
        if key.strip() != PIXVERSE_REGION_ENV:
            continue
        normalized = value.strip()
        if (
            len(normalized) >= 2
            and normalized[0] == normalized[-1]
            and (normalized[0] in {'"', "'"})
        ):
            normalized = normalized[1:-1]
        return normalized
    return None


def effective_pixverse_region(argv: list[str] | None = None, *, cwd: Path | None = None) -> str:
    """Resolve the CLI's environment > flag > default region precedence."""
    explicit = explicit_pixverse_region(argv or [])
    environment = os.environ.get(PIXVERSE_REGION_ENV)
    if environment is None:
        environment = _dotenv_region((cwd or Path.cwd()) / ".env")
    selected = environment if environment is not None else explicit or PIXVERSE_DEFAULT_REGION
    normalized = str(selected).strip().lower()
    if normalized not in PIXVERSE_REGIONS:
        raise PixVerseRegionError(
            f"invalid {PIXVERSE_REGION_ENV}={selected!r}; expected global or cn"
        )
    return normalized
