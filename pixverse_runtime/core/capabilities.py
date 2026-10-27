from __future__ import annotations

import json
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from typing import Any

from .cli_support import CREATE_CAPABILITIES_SCHEMA
from .compatibility import (
    pixverse_cli_capabilities_path,
)


def _normalize_duration_scalar(value: Any, *, zero_is_auto: bool) -> Any:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        if zero_is_auto and value == 0:
            return "auto"
        if float(value).is_integer():
            return str(int(value))
    if isinstance(value, str) and zero_is_auto and (value.strip() == "0"):
        return "auto"
    return value


def _normalize_reference_duration_contract(create: dict[str, Any]) -> dict[str, Any]:
    """Canonicalize equivalent public/internal reference duration encodings.

    PixVerse CLI 1.4.0 accepts ``--duration auto`` for models that expose the
    public schema's numeric ``0`` sentinel.  The internal artifact already
    serializes the same contract as strings with an explicit ``auto`` value.
    Keep one wrapper-facing representation so queue validation is independent
    of the selected distribution channel.
    """
    normalized = deepcopy(create)
    modes = normalized.get("modes")
    reference = modes.get("reference") if isinstance(modes, dict) else None
    if not isinstance(reference, dict):
        return normalized
    parameters = reference.get("parameters")
    duration = parameters.get("duration") if isinstance(parameters, dict) else None
    if isinstance(duration, dict):
        duration["type"] = "string"
        if "default" in duration:
            duration["default"] = _normalize_duration_scalar(
                duration.get("default"), zero_is_auto=True
            )
        if isinstance(duration.get("enum"), list):
            duration["enum"] = [
                _normalize_duration_scalar(value, zero_is_auto=True) for value in duration["enum"]
            ]
        duration["unit"] = "seconds_or_auto"
        duration["description"] = "Output duration in seconds, or auto where supported."
    model_parameters = reference.get("model_parameters")
    by_model = model_parameters.get("duration") if isinstance(model_parameters, dict) else None
    if isinstance(by_model, dict):
        for contract in by_model.values():
            if not isinstance(contract, dict):
                continue
            if "default" in contract:
                contract["default"] = _normalize_duration_scalar(
                    contract.get("default"), zero_is_auto=True
                )
            if isinstance(contract.get("enum"), list):
                contract["enum"] = [
                    _normalize_duration_scalar(value, zero_is_auto=True)
                    for value in contract["enum"]
                ]
    return normalized


def _normalized_create_domain(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict) or payload.get("schema_version") != "1.2.0":
        return {}
    domains = payload.get("capability_domains")
    create = domains.get("create") if isinstance(domains, dict) else None
    if (
        not isinstance(create, dict)
        or create.get("schema_version") != CREATE_CAPABILITIES_SCHEMA
        or create.get("encoding") != "normalized"
        or (not isinstance(create.get("modes"), dict))
    ):
        return {}
    return _normalize_reference_duration_contract(create)


def _capabilities_payload(payload: Any) -> dict[str, Any]:
    return payload if isinstance(payload, dict) else {}


@lru_cache(maxsize=8)
def _read_capabilities_payload_file(path_text: str, _mtime_ns: int, _size: int) -> dict[str, Any]:
    try:
        return _capabilities_payload(json.loads(Path(path_text).read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError):
        return {}


@lru_cache(maxsize=8)
def _read_capabilities_file(path_text: str, _mtime_ns: int, _size: int) -> dict[str, Any]:
    return _normalized_create_domain(_read_capabilities_payload_file(path_text, _mtime_ns, _size))


def load_cli_capabilities() -> dict[str, Any]:
    """Load the complete offline CLI capability manifest for either channel."""
    installed = pixverse_cli_capabilities_path()
    try:
        installed_stat = installed.stat()
    except OSError:
        installed_stat = None
    if installed_stat is not None:
        payload = _read_capabilities_payload_file(
            str(installed.resolve()), installed_stat.st_mtime_ns, installed_stat.st_size
        )
        if payload:
            return payload
    return {}


def load_create_capabilities() -> dict[str, Any]:
    """Load reviewed normalized create capabilities without invoking the CLI or network."""
    installed = pixverse_cli_capabilities_path()
    try:
        installed_stat = installed.stat()
    except OSError:
        installed_stat = None
    if installed_stat is not None:
        create = _read_capabilities_file(
            str(installed.resolve()), installed_stat.st_mtime_ns, installed_stat.st_size
        )
        if create:
            return create
    return {}


def create_mode_capability(mode: str) -> dict[str, Any]:
    modes = load_create_capabilities().get("modes")
    payload = modes.get(mode) if isinstance(modes, dict) else None
    return payload if isinstance(payload, dict) else {}


def create_model_supported(mode: str, model: str) -> bool:
    model_ids = create_mode_capability(mode).get("model_ids")
    return isinstance(model_ids, list) and model in model_ids


def create_model_parameter(mode: str, model: str, parameter: str) -> dict[str, Any]:
    mode_payload = create_mode_capability(mode)
    model_parameters = mode_payload.get("model_parameters")
    parameter_payload = (
        model_parameters.get(parameter) if isinstance(model_parameters, dict) else None
    )
    model_payload = parameter_payload.get(model) if isinstance(parameter_payload, dict) else None
    return model_payload if isinstance(model_payload, dict) else {}
