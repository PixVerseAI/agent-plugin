from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from .state import local_data_home

COMPATIBILITY_PATH = Path(__file__).with_name("cli-compatibility.json")


def load_cli_compatibility() -> dict[str, Any]:
    payload = json.loads(COMPATIBILITY_PATH.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("pixverse_cli"), dict):
        raise RuntimeError(f"invalid PixVerse CLI compatibility contract: {COMPATIBILITY_PATH}")
    return payload


CLI_COMPATIBILITY = load_cli_compatibility()
CLI_CONTRACT = CLI_COMPATIBILITY["pixverse_cli"]
PIXVERSE_CLI_PACKAGE = str(CLI_CONTRACT["package"])
PIXVERSE_CLI_MINIMUM_VERSION = str(CLI_CONTRACT["minimum_version"])
PIXVERSE_CLI_NODE_REQUIREMENT = str(CLI_CONTRACT["node_requirement"])
PIXVERSE_CLI_INSTALL_SPEC = str(CLI_CONTRACT["install_spec"])
PIXVERSE_CLI_CAPABILITIES_SCHEMA = str(CLI_CONTRACT["capabilities_schema_version"])


def pixverse_cli_runtime_root() -> Path:
    configured = os.environ.get("PIXVERSE_AGENT_CLI_RUNTIME", "").strip()
    if configured:
        return Path(configured).expanduser()
    return local_data_home() / "runtime" / "pixverse-cli" / "current"


def pixverse_cli_channel() -> str:
    return "online"


def pixverse_cli_node_requirement() -> str:
    """Return the shared Node floor for both managed CLI channels."""
    return PIXVERSE_CLI_NODE_REQUIREMENT


def pixverse_cli_source() -> str:
    return "npm-latest"


def pixverse_cli_effective_install_spec() -> str:
    return PIXVERSE_CLI_INSTALL_SPEC


def pixverse_cli_artifact_sha256() -> str:
    return ""


def pixverse_cli_active_root() -> Path:
    return pixverse_cli_runtime_root()


def pixverse_cli_executable() -> Path:
    binary = "pixverse.cmd" if os.name == "nt" else "pixverse"
    return pixverse_cli_active_root() / "node_modules" / ".bin" / binary


def pixverse_cli_package_root() -> Path:
    return pixverse_cli_active_root() / "node_modules" / PIXVERSE_CLI_PACKAGE


def pixverse_cli_package_json() -> Path:
    return pixverse_cli_package_root() / "package.json"


def pixverse_cli_capabilities_path() -> Path:
    return pixverse_cli_package_root() / "dist" / "capabilities.json"


def pixverse_cli_installed_version() -> str:
    try:
        payload = json.loads(pixverse_cli_package_json().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""
    return str(payload.get("version") or "") if isinstance(payload, dict) else ""


def pixverse_cli_runtime_is_supported() -> bool:
    executable = pixverse_cli_executable()
    ready = executable.is_file() and (os.name == "nt" or os.access(executable, os.X_OK))
    return ready and pixverse_cli_version_supported(pixverse_cli_installed_version())


def pixverse_cli_install_argv(npm: str = "npm") -> list[str]:
    return [
        npm,
        "install",
        "--prefix",
        str(pixverse_cli_runtime_root()),
        "--save-exact",
        "--ignore-scripts",
        "--no-audit",
        "--no-fund",
        f"{PIXVERSE_CLI_PACKAGE}@{PIXVERSE_CLI_INSTALL_SPEC}",
    ]


def normalize_cli_version(value: str) -> str:
    match = re.search("(?<!\\d)(\\d+\\.\\d+\\.\\d+)(?!\\d)", value)
    return match.group(1) if match else ""


def semver_tuple(value: str) -> tuple[int, int, int] | None:
    normalized = normalize_cli_version(value)
    if not normalized:
        return None
    return tuple((int(part) for part in normalized.split(".")))


def pixverse_cli_version_at_least(value: str, minimum: str) -> bool:
    actual_tuple = semver_tuple(value)
    minimum_tuple = semver_tuple(minimum)
    return bool(
        actual_tuple is not None and minimum_tuple is not None and (actual_tuple >= minimum_tuple)
    )


def pixverse_cli_version_supported(value: str) -> bool:
    return pixverse_cli_version_at_least(value, PIXVERSE_CLI_MINIMUM_VERSION)
