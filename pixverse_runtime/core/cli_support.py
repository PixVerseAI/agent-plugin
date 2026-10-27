from __future__ import annotations

import re

ONLINE_CLI_CHANNEL = "online"
CREATE_CAPABILITIES_SCHEMA = "pixverse_create_capabilities.v1"


def normalize_version(value: str) -> str:
    match = re.search("(?<!\\d)(\\d+\\.\\d+\\.\\d+)(?!\\d)", value)
    return match.group(1) if match else ""


def semver_tuple(value: str) -> tuple[int, int, int] | None:
    normalized = normalize_version(value)
    if not normalized:
        return None
    return tuple((int(part) for part in normalized.split(".")))


def version_at_least(value: str, minimum: str) -> bool:
    actual = semver_tuple(value)
    floor = semver_tuple(minimum)
    return bool(actual is not None and floor is not None and (actual >= floor))


def node_version_satisfies(actual: str, requirement: str) -> bool:
    match = re.fullmatch("\\s*>=\\s*(\\d+\\.\\d+\\.\\d+)\\s*", requirement)
    return bool(match and version_at_least(actual, match.group(1)))
