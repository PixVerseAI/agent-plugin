from __future__ import annotations

import subprocess
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from .account import (
    _account_fingerprint as _account_fingerprint,
)
from .account import (
    _account_summary as _account_summary,
)
from .account import (
    _entitlement_issues as _entitlement_issues,
)
from .account import (
    insufficient_balance_blocker as insufficient_balance_blocker,
)
from .account import (
    membership_tier as membership_tier,
)
from .capabilities import load_create_capabilities
from .pixverse import create_kind
from .shell import CommandResult, run_json, which
from .state import utc_now
from .template import is_canvas_template, output_media, template_detail

PROMPT_ENHANCE_SKILL = "skills-shared/prompting.md"

GENERATION_CONFIRMATION_NOTE = "Confirm the planned task count, models/key parameters and account balance under the effective approval policy. Actual credit usage is recorded after generation when reported."
BILLING_QUERY_TIMEOUT_SECONDS = 30
BASIC_MEMBERSHIP_LABELS = {"free", "basic", "starter", "guest"}


def billing_snapshot(
    *, usage_limit: int = 100, include_slots: bool = True, include_model_catalogs: bool = True
) -> dict[str, Any]:
    snapshot: dict[str, Any] = {
        "checked_at": utc_now(),
        "pixverse_found": bool(which("pixverse")),
        "account_info": {},
        "auth": {},
        "slots": {},
        "usage": {},
        "voice_models": {},
        "music_models": {},
        "issues": [],
    }
    if not snapshot["pixverse_found"]:
        snapshot["issues"].append("pixverse_cli_missing")
        return snapshot
    commands = {
        "account_info": ["pixverse", "account", "info", "--json"],
        "auth": ["pixverse", "auth", "status", "--json"],
    }
    if include_slots:
        commands["slots"] = ["pixverse", "account", "slots", "--json"]
    if include_model_catalogs:
        commands["voice_models"] = ["pixverse", "voice", "models", "--json"]
        commands["music_models"] = ["pixverse", "music", "models", "--json"]
    if usage_limit > 0:
        commands["usage"] = [
            "pixverse",
            "account",
            "usage",
            "--type",
            "used",
            "--limit",
            str(usage_limit),
            "--json",
        ]
    with ThreadPoolExecutor(
        max_workers=len(commands), thread_name_prefix="pixverse-runtime-billing"
    ) as executor:
        outcomes = list(executor.map(_billing_query, commands.items()))
    for key, argv, result, payload, issue in outcomes:
        if issue:
            snapshot["issues"].append(issue)
            continue
        assert result is not None
        if result.ok and isinstance(payload, dict):
            snapshot[key] = payload
        else:
            snapshot["issues"].append(
                {
                    "command": " ".join(argv),
                    "stderr": _truncate(result.stderr, 500),
                    "stdout": _truncate(result.stdout, 500),
                }
            )
    account_info = snapshot.get("account_info")
    auth_info = snapshot.get("auth")
    snapshot["account"] = _account_summary(account_info, auth_info)
    snapshot["account_info"] = _redact_account_info(account_info)
    snapshot["auth"] = _redact_auth_info(auth_info)
    snapshot["observed_prices"] = observed_price_index(snapshot.get("usage"))
    return snapshot


def _billing_query(
    item: tuple[str, list[str]],
) -> tuple[str, list[str], CommandResult | None, dict[str, Any], dict[str, Any] | None]:
    (key, argv) = item
    try:
        (result, payload) = run_json(argv, timeout=BILLING_QUERY_TIMEOUT_SECONDS)
        return (key, argv, result, payload, None)
    except subprocess.TimeoutExpired as exc:
        return (
            key,
            argv,
            None,
            {},
            {"command": " ".join(argv), "error": "timeout", "timeout_seconds": exc.timeout},
        )


def quote_argv(
    argv: list[str], *, task_id: str = "", label: str = "", snapshot: dict[str, Any]
) -> dict[str, Any]:
    kind = create_kind(argv)
    model = _option_value(argv, "--model", "-m") or _default_model(kind, snapshot)
    count = _int_option(argv, "--count", default=1)
    params = _generation_params(argv)
    detail = template_detail(argv) if kind == "template" else {}
    if detail:
        model = str(
            detail.get("template_model")
            or ("template-defined" if is_canvas_template(detail) else "v5.5")
        )
        params["template_id"] = detail["template_id"]
    return {
        "id": task_id,
        "label": label or task_id,
        "kind": kind,
        "media_type": ("template-defined" if is_canvas_template(detail) else output_media(detail))
        if detail
        else _media_type(kind),
        **(
            {
                "template": detail,
                "output_count": "template-defined" if is_canvas_template(detail) else count,
            }
            if detail
            else {}
        ),
        "model": model,
        "params": params,
        "count": count,
        "pre_generation_credits": "not_available",
        "note": GENERATION_CONFIRMATION_NOTE,
        "prompt_preview": _prompt_preview(argv),
        **({"prompt_enhance_skill": PROMPT_ENHANCE_SKILL} if model == "seedance-2.5" else {}),
        "command": " ".join(argv),
    }


def observed_price_index(usage_payload: Any) -> dict[str, Any]:
    items = usage_payload.get("items") if isinstance(usage_payload, dict) else []
    buckets: dict[str, list[int]] = defaultdict(list)
    if isinstance(items, list):
        for item in items:
            if not isinstance(item, dict):
                continue
            model = _normalize_model(str(item.get("video_source") or ""))
            credits = item.get("credits")
            if not model or not isinstance(credits, int) or credits < 0:
                continue
            buckets[model].append(credits)
    return {
        model: {
            "max_observed_credits": max(values),
            "latest_observed_credits": values[0],
            "sample_count": len(values),
        }
        for (model, values) in buckets.items()
        if values
    }


def _default_model(kind: str, snapshot: dict[str, Any]) -> str:
    if kind == "image":
        return str(
            load_create_capabilities().get("modes", {}).get("image", {}).get("default_model")
            or "unknown"
        )
    if kind == "voice":
        voice_models = snapshot.get("voice_models")
        if isinstance(voice_models, dict) and voice_models.get("default_model"):
            return str(voice_models["default_model"])
        return "speech-2.8-hd"
    if kind == "music":
        music_models = snapshot.get("music_models")
        if isinstance(music_models, dict) and music_models.get("default_model"):
            return str(music_models["default_model"])
        return "music-2.6"
    return "v6"


def _redact_account_info(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    redacted = dict(payload)
    for key in ("email", "nickname", "username", "accountId"):
        if key in redacted:
            redacted[key] = "<redacted>"
    return redacted


def _redact_auth_info(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    redacted = dict(payload)
    for key in (
        "email",
        "nickname",
        "username",
        "accountId",
        "userId",
        "accessToken",
        "refreshToken",
    ):
        if key in redacted:
            redacted[key] = "<redacted>"
    return redacted


def _option_value(argv: list[str], *names: str) -> str | None:
    for idx, value in enumerate(argv):
        if value in names and idx + 1 < len(argv):
            return argv[idx + 1]
        for name in names:
            prefix = f"{name}="
            if value.startswith(prefix):
                return value[len(prefix) :]
    return None


def _has_flag(argv: list[str], name: str) -> bool:
    return name in argv


def _generation_params(argv: list[str]) -> dict[str, Any]:
    names = (
        "--quality",
        "--detail-level",
        "--duration",
        "--aspect-ratio",
        "--seed",
        "--image",
        "--voice-id",
        "--provider-voice-id",
        "--language",
        "--speed",
        "--stability",
        "--similarity-boost",
        "--style",
        "--volume",
        "--pitch",
        "--emotion",
        "--duration-seconds",
    )
    params: dict[str, Any] = {}
    for name in names:
        value = _option_value(argv, name)
        if value is not None:
            params[name.lstrip("-").replace("-", "_")] = value
    for flag in (
        "--audio",
        "--no-audio",
        "--multi-shot",
        "--no-multi-shot",
        "--instrumental",
        "--off-peak",
    ):
        if _has_flag(argv, flag):
            params[flag.lstrip("-").replace("-", "_")] = True
    return params


def _prompt_text(argv: list[str]) -> str:
    raw = _option_value(argv, "--prompt", "--text") or ""
    if not raw:
        return ""
    path = Path(raw)
    try:
        if len(raw) < 240 and path.exists() and path.is_file():
            raw = path.read_text(encoding="utf-8").strip()
    except OSError:
        raw = str(raw)
    return raw


def _prompt_preview(argv: list[str], *, limit: int = 180) -> str:
    raw = _prompt_text(argv)
    if not raw:
        return ""
    return _truncate(raw.replace("\n", " "), limit)


def _int_option(argv: list[str], name: str, *, default: int) -> int:
    raw = _option_value(argv, name)
    try:
        value = int(raw) if raw is not None else default
    except ValueError:
        return default
    return max(1, value)


def _normalize_model(value: str) -> str:
    return value.strip().lower().replace("standar", "standard")


def _media_type(kind: str) -> str:
    if kind == "image":
        return "image"
    if kind in {"voice", "music"}:
        return "audio"
    return "video"


def _truncate(value: str, limit: int) -> str:
    return value if len(value) <= limit else value[: limit - 3] + "..."
