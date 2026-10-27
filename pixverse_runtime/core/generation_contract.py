from __future__ import annotations

import hashlib
import json
from typing import Any

from .shell import CommandResult

CONCURRENCY_CODES = {429, 500041, 500042, 500044}
INSUFFICIENT_BALANCE_CODES = {500043}
PROMPT_CODES = {400018, 400038}
PARAM_CODES = {400017}
MEMBERSHIP_CODES = {500323, 500342}


def media_type_for_kind(kind: str) -> str:
    if kind == "image":
        return "image"
    if kind in {"voice", "music"}:
        return "audio"
    return "video"


def poll_type_for_kind(kind: str) -> str:
    return media_type_for_kind(kind)


def stable_key(project: str, task_id: str, command: str) -> str:
    raw = f"{project}:{task_id}:{command}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:32]


def classify_error(result: CommandResult, payload: dict[str, Any] | None = None) -> str:
    if result.returncode == 7:
        return "concurrency"
    payload = payload or {}
    if not payload:
        payload = _parse_error_payload(result)
    text = f"{result.stderr}\n{result.stdout}\n{json.dumps(payload, ensure_ascii=False)}".lower()
    if (
        "width and height between 300 and 6000" in text
        or "no larger than 30mb" in text
        or ("image dimensions" in text and "6000" in text)
    ):
        return "reference_input_invalid"
    if "file too large" in text or "payload too large" in text or "max: 10mb" in text:
        return "input_too_large"
    code = payload.get("code")
    if isinstance(code, str) and code.isdigit():
        code = int(code)
    if code in CONCURRENCY_CODES:
        return "concurrency"
    if code in INSUFFICIENT_BALANCE_CODES:
        return "insufficient_balance"
    if code in PROMPT_CODES:
        return "prompt_invalid"
    if code in PARAM_CODES:
        return "param_invalid"
    if code in MEMBERSHIP_CODES:
        return "membership_required"
    if any(
        (
            phrase in text
            for phrase in (
                "membership required",
                "subscription required",
                "upgrade your plan",
                "upgrade plan",
                "not available for current plan",
                "not available on your plan",
                "insufficient entitlement",
                "user rights insufficient",
                "\u6743\u76ca\u4e0d\u8db3",
                "\u4f1a\u5458\u6743\u76ca",
                "\u9700\u8981\u4f1a\u5458",
            )
        )
    ):
        return "membership_required"
    if "auth" in text or "login" in text:
        return "auth"
    if "quota" in text or "concurrent" in text or "over limit" in text:
        return "concurrency"
    if "credit" in text or "balance" in text:
        return "insufficient_balance"
    if "voice is required" in text or "duration_seconds is reserved" in text:
        return "param_invalid"
    if "timeout" in text:
        return "timeout"
    return "unknown"


def _parse_error_payload(result: CommandResult) -> dict[str, Any]:
    for raw in (result.stdout, result.stderr):
        text = raw.strip()
        if not text.startswith("{"):
            continue
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
    return {}


def terminal_from_status(info: dict[str, Any]) -> tuple[str | None, str, str]:
    status = str(info.get("status") or "").lower()
    status_code = info.get("status_code")
    if status in {"completed", "success", "succeeded"}:
        return ("success", "", "")
    if status_code in {7, 8} or status in {"failed", "error", "rejected", "not approved"}:
        blob = " ".join(
            (
                str(info.get(key) or "")
                for key in ("error", "error_message", "message", "code", "status")
            )
        )
        if status_code == 7:
            return ("failed", "audit_reject", blob.strip())
        code = info.get("code")
        if isinstance(code, str) and code.isdigit():
            code = int(code)
        lowered = blob.lower()
        if code in MEMBERSHIP_CODES or any(
            (
                phrase in lowered
                for phrase in (
                    "membership required",
                    "subscription required",
                    "upgrade your plan",
                    "upgrade plan",
                    "not available for current plan",
                    "not available on your plan",
                    "insufficient entitlement",
                    "\u6743\u76ca\u4e0d\u8db3",
                    "\u4f1a\u5458\u6743\u76ca",
                    "\u9700\u8981\u4f1a\u5458",
                )
            )
        ):
            return ("failed", "membership_required", blob.strip())
        if "not approved" in lowered:
            return ("failed", "audit_reject", blob.strip())
        if (
            code in INSUFFICIENT_BALANCE_CODES
            or "insufficient balance" in lowered
            or "insufficient credit" in lowered
        ):
            return ("failed", "insufficient_balance", blob.strip())
        if "auth" in lowered or "login" in lowered or "\u767b\u5f55" in lowered:
            return ("failed", "auth", blob.strip())
        return ("failed", "generation_failed", blob.strip())
    return (None, "", "")


def result_urls(info: dict[str, Any]) -> tuple[str, str]:
    url = str(
        info.get("video_url")
        or info.get("image_url")
        or info.get("audio_url")
        or info.get("url")
        or ""
    )
    cover = str(info.get("cover_url") or info.get("thumbnail_url") or "")
    return (url, cover)


def extract_task_id(payload: dict[str, Any], kind: str) -> str | None:
    media = media_type_for_kind(kind)
    candidates = [f"{media}_id", "video_id", "image_id", "audio_id", "voice_id", "music_id", "id"]
    for key in candidates:
        value = payload.get(key)
        if value:
            return str(value)
    for key in ("video_ids", "image_ids", "audio_ids", "ids"):
        value = payload.get(key)
        if isinstance(value, list) and value:
            return str(value[0])
    return None


def extract_credit_cost(payload: dict[str, Any]) -> tuple[int | None, str]:
    candidates = (
        ("cost_credits", "cost_credits"),
        ("credits", "credits"),
        ("credit", "credit"),
        ("consume_credits", "consume_credits"),
        ("used_credits", "used_credits"),
    )
    for key, source in candidates:
        value = payload.get(key)
        if isinstance(value, bool):
            continue
        if isinstance(value, int) and value >= 0:
            return (value, source)
        if isinstance(value, float) and value >= 0 and value.is_integer():
            return (int(value), source)
        if isinstance(value, str) and value.isdigit():
            return (int(value), source)
    return (None, "")
