"""Basic creation CLI. Production orchestration is a separate distribution."""

from __future__ import annotations

import argparse
import json
import subprocess
from typing import Any

from . import __version__, requests
from .cli_support import node_version_satisfies
from .compatibility import (
    PIXVERSE_CLI_MINIMUM_VERSION,
    PIXVERSE_CLI_NODE_REQUIREMENT,
    pixverse_cli_install_argv,
    pixverse_cli_runtime_is_supported,
    pixverse_cli_runtime_root,
)
from .preferences import (
    preferences_snapshot,
    set_project_quote_confirmation_mode,
    set_quote_confirmation_mode,
)
from .shell import run, run_passthrough, which
from .skills import list_skills, validate_skills


def emit(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def setup(install: bool = False) -> int:
    node = run(["node", "--version"], timeout=20) if which("node") else None
    node_ready = bool(
        node and node.ok and node_version_satisfies(node.stdout, PIXVERSE_CLI_NODE_REQUIREMENT)
    )
    if install:
        if not node_ready or not which("npm"):
            raise ValueError(
                f"Install Node.js {PIXVERSE_CLI_NODE_REQUIREMENT} and npm before setup."
            )
        pixverse_cli_runtime_root().mkdir(parents=True, exist_ok=True)
        result = run(pixverse_cli_install_argv(), timeout=600)
        if not result.ok:
            emit({"error": "setup_failed", "message": result.stderr})
            return result.returncode
    ready = node_ready and pixverse_cli_runtime_is_supported()
    emit(
        {
            "ready": ready,
            "node_requirement": PIXVERSE_CLI_NODE_REQUIREMENT,
            "pixverse_cli_minimum": PIXVERSE_CLI_MINIMUM_VERSION,
            "managed_cli_ready": pixverse_cli_runtime_is_supported(),
            "next_step": "pixverse auth status --json" if ready else "setup --install",
        }
    )
    return 0 if ready else 1


def passthrough(args: list[str]) -> int:
    # Inspecting capabilities and an existing receipt must not open a paid bypass.
    allowed = {
        ("account", "info"),
        ("account", "slots"),
        ("account", "usage"),
        ("auth", "status"),
        ("auth", "login"),
        ("auth", "logout"),
        ("capabilities", "create"),
        ("template", "list"),
        ("template", "info"),
        ("template", "categories"),
        ("voice", "models"),
        ("voice", "list"),
        ("music", "models"),
        ("asset", "info"),
        ("task", "status"),
    }
    if args == ["subscribe"]:
        emit({"url": "https://app.pixverse.ai/subscribe", "action": "open_in_supported_browser"})
        return 0
    if tuple(args[:2]) not in allowed:
        raise ValueError(
            "Unsupported direct command. Use create for paid work and status/download for saved requests."
        )
    if any(
        arg.split("=")[0] in {"--env", "--workspace-id", "--region", "--open-system"}
        for arg in args
    ):
        raise ValueError("Use the same active account and PIXVERSE_REGION for the whole request.")
    if "--json" not in args:
        args = [*args, "--json"]
    return run_passthrough(["pixverse", *args])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="PixVerse basic creation and recovery")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)
    install = sub.add_parser("setup")
    install.add_argument("--install", action="store_true")
    sub.add_parser("doctor")
    skills = sub.add_parser("skills")
    skills.add_argument("action", choices=["list", "validate"], default="list", nargs="?")
    direct = sub.add_parser("pixverse")
    direct.add_argument("args", nargs=argparse.REMAINDER)
    create = sub.add_parser("create")
    create.add_argument("--request-id", required=True)
    create.add_argument("--preflight", action="store_true")
    create.add_argument("--confirmed", action="store_true")
    create.add_argument("--accept-basic-fallback", action="store_true")
    create.add_argument("args", nargs=argparse.REMAINDER)
    for action in ["status", "download", "recover"]:
        follow = sub.add_parser(action)
        follow.add_argument("request_id")
    prefs = sub.add_parser("preferences")
    prefs.add_argument("mode", nargs="?", choices=["show", "require", "skip"], default="show")
    prefs.add_argument("--global", dest="global_scope", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.command in {"setup", "doctor"}:
            return setup(getattr(args, "install", False))
        if args.command == "pixverse":
            return passthrough(args.args)
        if args.command == "skills":
            if args.action == "validate":
                issues = validate_skills()
                emit({"issues": issues})
                return int(bool(issues))
            emit([{"name": s.name, "description": s.description} for s in list_skills()])
            return 0
        if args.command == "preferences":
            if args.mode == "show":
                emit(preferences_snapshot())
            elif args.global_scope:
                emit(set_quote_confirmation_mode(args.mode))
            else:
                emit(set_project_quote_confirmation_mode("pixverse-requests", args.mode))
            return 0
        if args.command == "create":
            result = requests.create(
                args.args[1:] if args.args[:1] == ["--"] else args.args,
                args.request_id,
                preflight=args.preflight,
                confirmed=args.confirmed,
                accept_basic_fallback=args.accept_basic_fallback,
            )
        else:
            result = requests.follow(args.request_id, download=args.command == "download")
        emit(result)
        return 1 if result.get("error") or result.get("status") in {"failed", "unresolved"} else 0
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        emit({"error": "request_blocked", "message": str(exc)})
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
