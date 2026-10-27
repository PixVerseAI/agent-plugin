from __future__ import annotations

import hashlib
from typing import Any

from .model_defaults import FALLBACK_IMAGE_MODEL

BASIC_MEMBERSHIP_LABELS = {"free", "basic", "starter", "guest"}


def _account_summary(payload: Any, auth_payload: Any = None) -> dict[str, Any]:
    payload = payload if isinstance(payload, dict) else {}
    auth_payload = auth_payload if isinstance(auth_payload, dict) else {}
    credits = payload.get("credits")
    credit_total = None
    if isinstance(credits, dict) and isinstance(credits.get("total"), int):
        credit_total = credits["total"]
    elif isinstance(payload.get("credits"), int):
        credit_total = payload["credits"]
    workspace = payload.get("workspace") if isinstance(payload.get("workspace"), dict) else {}
    member_label = (
        workspace.get("memberLabel")
        or payload.get("memberLabel")
        or auth_payload.get("memberType")
        or ""
    )
    member_type = (
        workspace.get("memberType")
        if workspace.get("memberType") is not None
        else payload.get("memberType")
    )
    authenticated: bool | None
    if "authenticated" in auth_payload:
        authenticated = bool(auth_payload.get("authenticated"))
    elif payload:
        authenticated = True
    else:
        authenticated = None
    return {
        "authenticated": authenticated,
        "account_fingerprint": _account_fingerprint(payload),
        "member_type": member_type,
        "member_label": member_label,
        "membership_tier": membership_tier(member_label, member_type),
        "credits_total": credit_total,
        "workspace_id": workspace.get("workspaceId"),
        "workspace_name": workspace.get("name"),
    }


def membership_tier(member_label: object, member_type: object = None) -> str:
    label = str(member_label or "").strip().lower()
    normalized_label = label.replace("-", " ").replace("_", " ")
    first_label_token = normalized_label.split(maxsplit=1)[0] if normalized_label else ""
    if label in {"0", "10"} or first_label_token in BASIC_MEMBERSHIP_LABELS:
        return "basic"
    if label:
        return "premium"
    if member_type in {0, 10, "0", "10"}:
        return "basic"
    return "unknown"


def _account_fingerprint(payload: dict[str, Any]) -> str:
    stable_value = payload.get("accountId") or payload.get("userId") or payload.get("email")
    if stable_value in (None, ""):
        return ""
    return hashlib.sha256(f"pixverse-account:{stable_value}".encode("utf-8")).hexdigest()[:20]


def _entitlement_issues(lines: list[dict[str, Any]], membership: str) -> list[dict[str, str]]:
    if membership != "basic":
        return []
    issues: list[dict[str, str]] = []
    for item in lines:
        kind = str(item.get("kind") or "")
        model = str(item.get("model") or "")
        if kind == "template":
            issues.append(
                {
                    "task": str(item.get("id") or ""),
                    "kind": kind,
                    "model": model,
                    "required_model": "template-defined",
                    "message": "Template settings cannot be replaced by the Basic fallback. Upgrade or explicitly choose a separate fallback creation route.",
                }
            )
        elif kind == "image" and model != FALLBACK_IMAGE_MODEL:
            issues.append(
                {
                    "task": str(item.get("id") or ""),
                    "kind": kind,
                    "model": model,
                    "required_model": FALLBACK_IMAGE_MODEL,
                    "message": "Basic/Free image fallback uses Nano Banana 2 Lite at 1080p after explicit consent.",
                }
            )
        elif (
            kind in {"video", "reference", "transition", "extend", "modify", "motion-control"}
            and model != "v6"
        ):
            issues.append(
                {
                    "task": str(item.get("id") or ""),
                    "kind": kind,
                    "model": model,
                    "required_model": "v6",
                    "message": "Basic/Free video generation should use PixVerse v6.",
                }
            )
    return issues


def insufficient_balance_blocker(quote: dict[str, Any]) -> str:
    account = quote.get("account") if isinstance(quote.get("account"), dict) else {}
    if "authenticated" in account and account.get("authenticated") is False:
        return "authentication_required"
    if quote.get("entitlement_issues") or quote.get("membership_choice_required"):
        return "membership_route_required"
    if account.get("authenticated") is True and account.get("membership_tier") == "unknown":
        return "membership_unknown"
    balance = account.get("credits_total")
    if isinstance(balance, int) and balance <= 0:
        return "insufficient_balance"
    if balance is None:
        return "balance_unknown"
    return ""
