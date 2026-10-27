"""Read-only template discovery and template-specific submission constraints."""

from __future__ import annotations

import subprocess
from typing import Any

from .shell import run_json

CANVAS_TEMPLATE_SOURCES = {21, 22}


def option(argv: list[str], *names: str) -> str:
    for index, value in enumerate(argv):
        for name in names:
            if value == name:
                return argv[index + 1] if index + 1 < len(argv) else ""
            if value.startswith(name + "="):
                return value.split("=", 1)[1]
    return ""


def is_canvas_template(detail: dict[str, Any]) -> bool:
    return detail.get("template_source") in CANVAS_TEMPLATE_SOURCES


def template_detail(argv: list[str]) -> dict[str, Any]:
    raw_id = option(argv, "--template-id")
    if not raw_id.isdigit() or int(raw_id) <= 0:
        raise ValueError("Template creation requires a positive --template-id")
    region = option(argv, "--region")
    command = ["pixverse", "template", "info", raw_id, "--json"]
    if region:
        command.extend(["--region", region])
    try:
        (result, detail) = run_json(command, timeout=30)
    except subprocess.TimeoutExpired as exc:
        raise ValueError(
            "Template detail query timed out; refresh the catalog before generation"
        ) from exc
    if (
        not result.ok
        or not isinstance(detail, dict)
        or str(detail.get("template_id")) != str(int(raw_id))
    ):
        error = result.stderr or (
            str(detail.get("error") or "") if isinstance(detail, dict) else ""
        )
        raise ValueError(
            "Could not read the selected template detail; refresh login/catalog before generation. "
            + error[:500]
        )
    validate_template_options(argv, detail)
    return detail


def validate_template_options(argv: list[str], detail: dict[str, Any]) -> None:
    if is_canvas_template(detail):
        forbidden = {
            "--quality",
            "-q",
            "--duration",
            "-d",
            "--aspect-ratio",
            "--seed",
            "--count",
            "--off-peak",
            "--idempotency-key",
        }
        if any((arg.split("=", 1)[0] in forbidden for arg in argv)):
            raise ValueError(
                "This template has fixed output settings; omit quality/duration/aspect/seed/count/off-peak/idempotency overrides"
            )
        fields = detail.get("input_fields")
        if (
            not isinstance(fields, list)
            or not fields
            or any(
                (
                    not isinstance(item, dict)
                    or item.get("content_type") not in {"text", "image", "video"}
                    for item in fields
                )
            )
        ):
            raise ValueError("Template has no supported input_fields schema")
        for kind in ("text", "video"):
            if sum((item.get("content_type") == kind for item in fields)) > 1:
                raise ValueError(
                    "This template has more video/text slots than the installed CLI supports"
                )


def output_media(detail: dict[str, Any]) -> str:
    return "image" if detail.get("template_type") == 2 else "video"


def template_outputs(payload: dict[str, Any]) -> tuple[list[dict[str, Any]], bool]:
    """Preserve every recoverable receipt, even in an invalid partial response."""
    raw = payload.get("outputs", payload.get("valid_outputs"))
    if not isinstance(raw, list):
        return ([], False)
    valid: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        media_id = item.get("media_id")
        if (
            item.get("media_type") in {"image", "video"}
            and isinstance(media_id, int)
            and (not isinstance(media_id, bool))
            and (media_id > 0)
        ):
            receipt = {"media_id": media_id, "media_type": item["media_type"]}
            if receipt not in valid:
                valid.append(receipt)
    return (valid, bool(raw) and len(valid) == len(raw))
