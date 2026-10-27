"""Durable, independent creation requests with no production queue dependency."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from .billing import _entitlement_issues, billing_snapshot, insufficient_balance_blocker, quote_argv
from .capabilities import load_create_capabilities
from .generation_contract import _parse_error_payload, extract_credit_cost
from .pixverse import (
    apply_generation_defaults,
    classify_error,
    create_kind,
    ensure_async_json_args,
    ensure_local_asset,
    extract_task_id,
    media_type_for_kind,
    result_urls,
    terminal_from_status,
    validate_create_argv,
)
from .preferences import project_quote_confirmation_state
from .region import effective_pixverse_region
from .shell import run_json
from .state import repo_root, utc_now
from .template import is_canvas_template, output_media, template_detail, template_outputs


@contextmanager
def request_lock(path: Path):
    """Kernel lock releases on process exit; intent is persisted before submission."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.with_suffix(".lock").open("a+b") as handle:
        if os.name == "nt":
            import msvcrt

            handle.write(b"0")
            handle.flush()
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            if os.name == "nt":
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle, fcntl.LOCK_UN)


def save(path: Path, data: dict[str, Any]) -> None:
    data["updated_at"] = utc_now()
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=".request-")
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def receipt_path(request_id: str) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", request_id):
        raise ValueError("Request ID must contain 1–80 letters, digits, hyphens or underscores.")
    return repo_root() / "projects" / "pixverse-requests" / (request_id + ".json")


def identity(snapshot: dict) -> dict:
    account = snapshot.get("account", {})
    if account.get("authenticated") is not True or not account.get("account_fingerprint"):
        raise ValueError(
            "Authenticated account identity is required; sign in and refresh account info."
        )
    return {
        "transport": "cli",
        "region": effective_pixverse_region([]),
        "account": account["account_fingerprint"],
        "workspace": account.get("workspace_id"),
    }


def prepare(
    argv: list[str],
    request_id: str,
    *,
    accept_basic_fallback: bool = False,
    snapshot: dict | None = None,
) -> tuple[list[str], dict]:
    # Inspect all user arguments, including global options before the create mode.
    # These are managed by the durable receipt, never by an untracked caller.
    reserved = {
        "--idempotency-key",
        "--client-request-id",
        "--region",
        "--env",
        "--workspace-id",
        "--no-wait",
        "--wait",
        "--timeout",
        "--json",
        "-p",
    }
    if any(arg.split("=", 1)[0] in reserved for arg in argv):
        raise ValueError(
            "Request identity, region, workspace and output controls are managed by the runtime."
        )
    argv = apply_generation_defaults(["pixverse", "create", *argv])
    if any(arg == "-" for arg in argv[2:]) or any("{{" in arg for arg in argv):
        raise ValueError(
            "Provide stable literal inputs or local files; stdin and dependency placeholders are unsupported."
        )
    kind = validate_create_argv(argv)
    if not load_create_capabilities().get("modes", {}).get(kind):
        raise ValueError(
            "Create capabilities are unavailable; repair the managed CLI before generation."
        )
    # One request owns one independent creation. Explicit image batches use separate IDs.
    for i, value in enumerate(argv):
        if (
            value == "--count"
            and (i + 1 == len(argv) or argv[i + 1] != "1")
            or value.startswith("--count=")
            and value != "--count=1"
        ):
            raise ValueError("Use one request ID per image or clip; --count must be 1.")
    snapshot = (
        snapshot
        if snapshot is not None
        else billing_snapshot(usage_limit=0, include_slots=False, include_model_catalogs=False)
    )
    account = snapshot.get("account", {})
    line = quote_argv(argv, task_id=request_id, snapshot=snapshot)
    confirmation = project_quote_confirmation_state("pixverse-requests")
    quote = {
        "account": account,
        "lines": [line],
        "planned_generation_tasks": 1,
        "membership_choice_required": account.get("membership_tier") == "basic"
        and not accept_basic_fallback,
        "entitlement_issues": _entitlement_issues(
            [line], account.get("membership_tier", "unknown")
        ),
        "requires_confirmation": confirmation["requires_confirmation"],
        "confirmation": confirmation,
        "basic_fallback_accepted": accept_basic_fallback,
    }
    quote["blocker"] = insufficient_balance_blocker(quote)
    quote["identity"] = identity(snapshot)
    return argv, quote


def fingerprint(argv: list[str]) -> str:
    files = {}
    for arg in argv[3:]:
        value = arg.split("=", 1)[1] if arg.startswith("-") and "=" in arg else arg
        try:
            candidate = Path(value).expanduser()
            if candidate.is_file():
                digest = hashlib.sha256()
                with candidate.open("rb") as handle:
                    for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                        digest.update(chunk)
                files[str(candidate.resolve())] = digest.hexdigest()
        except (OSError, ValueError):
            pass
    return hashlib.sha256(
        json.dumps([argv, files], sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


def create(
    argv: list[str],
    request_id: str,
    *,
    preflight: bool = False,
    confirmed: bool = False,
    accept_basic_fallback: bool = False,
) -> dict:
    path = receipt_path(request_id)
    with request_lock(path):
        argv, quote = prepare(argv, request_id, accept_basic_fallback=accept_basic_fallback)
        digest = fingerprint(argv)
        if path.exists():
            record = json.loads(path.read_text(encoding="utf-8"))
            if record["fingerprint"] != digest or record["identity"] != quote["identity"]:
                raise ValueError(
                    "Request ID belongs to different arguments, files, account, workspace or region; do not resubmit it."
                )
            return record
        if preflight or quote["blocker"] or quote["requires_confirmation"] and not confirmed:
            return {
                "status": "preflight",
                "request_id": request_id,
                "quote": quote,
                "error": quote["blocker"]
                or (
                    "quote_confirmation_required"
                    if quote["requires_confirmation"] and not confirmed
                    else ""
                ),
            }
        kind = create_kind(argv)
        detail = template_detail(argv) if kind == "template" else {}
        record = {
            "request_id": request_id,
            "fingerprint": digest,
            "identity": quote["identity"],
            "argv": argv,
            "quote": quote,
            "status": "unresolved",
            "outputs": [],
            "created_at": utc_now(),
        }
        # Atomic write before ANY paid call. A crash or timeout must never produce a new attempt.
        save(path, record)
        key = hashlib.sha256(
            json.dumps([quote["identity"], request_id, digest], sort_keys=True).encode()
        ).hexdigest()[:32]
        record["client_request_id"] = key
        args = (
            argv + ["--json", "--no-wait"]
            if is_canvas_template(detail)
            else ensure_async_json_args(argv, key)
        )
        save(path, record)
        try:
            result, payload = run_json(args, timeout=90)
        except (subprocess.TimeoutExpired, OSError) as exc:
            record["error"] = "submission_unknown"
            record["message"] = str(exc)
            save(path, record)
            return record
        if not payload and not result.ok:
            payload = _parse_error_payload(result)
        record["response"] = payload
        outputs, complete = template_outputs(payload) if is_canvas_template(detail) else ([], True)
        outputs = [
            {"task_id": str(item["media_id"]), "media_type": item["media_type"]} for item in outputs
        ]
        if not outputs:
            task_id = extract_task_id(payload, kind)
            ids = [task_id] if task_id else []
            for key in ("image_ids", "video_ids", "audio_ids", "ids"):
                values = payload.get(key)
                if isinstance(values, list):
                    ids.extend(
                        str(value)
                        for value in values
                        if isinstance(value, (str, int)) and not isinstance(value, bool)
                    )
            media_type = output_media(detail) if kind == "template" else media_type_for_kind(kind)
            outputs = [{"task_id": value, "media_type": media_type} for value in dict.fromkeys(ids)]
        record["outputs"] = outputs
        record["status"] = "running" if outputs and result.ok and complete else "unresolved"
        record["incomplete_receipt"] = not complete
        if not result.ok:
            record["error"] = classify_error(result, payload)
            record["message"] = result.stderr or result.stdout
        save(path, record)
        return record


def follow(request_id: str, *, download: bool = False) -> dict:
    path = receipt_path(request_id)
    with request_lock(path):
        record = json.loads(path.read_text(encoding="utf-8"))
        snapshot = billing_snapshot(
            usage_limit=0, include_slots=False, include_model_catalogs=False
        )
        if identity(snapshot) != record["identity"]:
            raise ValueError(
                "Restore the original CLI account, workspace and region before recovery."
            )
        if not record["outputs"]:
            record["recovery"] = (
                "Submission outcome unknown. Retain this receipt and request ID. Inspect the original account receipt or contact support; never create a replacement automatically."
            )
            return record
        for output in record["outputs"]:
            task_id = str(output.get("task_id") or output.get("id") or "")
            media = str(output.get("media_type") or output.get("type") or "")
            if not task_id or media not in {"image", "video", "audio"}:
                raise ValueError(
                    "Incomplete submission receipt; recover the original output IDs before continuing."
                )
            result, payload = run_json(
                ["pixverse", "task", "status", "--ids", task_id, "--type", media, "--json"],
                timeout=30,
            )
            if not result.ok:
                output["status_error"] = result.stderr or result.stdout
                continue
            items = payload.get("tasks", payload.get("results", []))
            info = (
                next(
                    (
                        item
                        for item in items
                        if isinstance(item, dict)
                        and str(item.get("id") or item.get("task_id") or item.get(f"{media}_id"))
                        == task_id
                    ),
                    {},
                )
                if isinstance(items, list)
                else {}
            )
            if not info and isinstance(payload.get(task_id), dict):
                info = payload[task_id]
            if (
                not info
                and str(payload.get("id") or payload.get("task_id") or payload.get(f"{media}_id"))
                == task_id
            ):
                info = payload
            if not info:
                output["status_error"] = (
                    "No matching task in status response; retain the previous receipt."
                )
                continue
            output.pop("status_error", None)
            terminal, error, message = terminal_from_status(info)
            output.update(status=terminal or "running", error=error, message=message)
            if terminal == "success":
                output["url"], output["cover_url"] = result_urls(info)
                credits, source = extract_credit_cost(info)
                if credits is not None:
                    output["cost_credits"] = credits
                    output["cost_source"] = source
                if download:
                    output["delivery"] = ensure_local_asset(
                        task_id=task_id,
                        media_type=media,
                        project_path=path.parent,
                        existing_path=output.get("delivery", {}).get("local_path", ""),
                    )
        statuses = {item.get("status") for item in record["outputs"]}
        record["status"] = (
            "success"
            if statuses == {"success"}
            else "failed"
            if statuses <= {"success", "failed"}
            else "running"
        )
        if record.get("incomplete_receipt"):
            record["status"] = "unresolved"
        elif record["status"] == "success" and record.get("error"):
            record["submission_error"] = record.pop("error")
        save(path, record)
        return record
