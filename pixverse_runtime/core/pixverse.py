from __future__ import annotations

import re
import shlex
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from pathlib import Path
from typing import Any

from .capabilities import load_create_capabilities
from .generation_contract import (
    _parse_error_payload as _parse_error_payload,
)
from .generation_contract import (
    classify_error as classify_error,
)
from .generation_contract import (
    extract_credit_cost as extract_credit_cost,
)
from .generation_contract import (
    extract_task_id as extract_task_id,
)
from .generation_contract import (
    media_type_for_kind as media_type_for_kind,
)
from .generation_contract import (
    poll_type_for_kind as poll_type_for_kind,
)
from .generation_contract import (
    result_urls as result_urls,
)
from .generation_contract import (
    stable_key as stable_key,
)
from .generation_contract import (
    terminal_from_status as terminal_from_status,
)
from .model_defaults import IMAGE_DETAIL, IMAGE_MODEL, IMAGE_QUALITY, VIDEO_MODEL, VIDEO_QUALITY
from .region import effective_pixverse_region
from .shell import CommandResult, run_json

CREATE_KINDS = {
    "video",
    "image",
    "transition",
    "voice",
    "music",
    "extend",
    "modify",
    "upscale",
    "reference",
    "motion-control",
    "template",
}
CONCURRENCY_CODES = {429, 500041, 500042, 500044}
INSUFFICIENT_BALANCE_CODES = {500043}
PROMPT_CODES = {400018, 400038}
PARAM_CODES = {400017}
MEMBERSHIP_CODES = {500323, 500342}
DOWNLOAD_INITIAL_FEEDBACK_SECONDS = 2.0
DOWNLOAD_MAX_FEEDBACK_SECONDS = 30.0


def split_command(command: str) -> list[str]:
    argv = shlex.split(command)
    if not argv:
        raise ValueError("empty command")
    if Path(argv[0]).name != "pixverse":
        raise ValueError("PixVerse Agent Plugin queue only runs pixverse commands")
    return argv


def create_kind(argv: list[str]) -> str:
    normalized = _normalize_pixverse_create_globals(argv)
    if len(normalized) >= 3 and normalized[1] == "create":
        kind = normalized[2]
        if kind in CREATE_KINDS:
            return kind
    if argv[1:3] == ["miniapps", "create"]:
        raise ValueError(
            "MiniApps creation is not supported by the pixverse-runtime paid queue yet; pixverse miniapps list/info remain available for read-only inspection"
        )
    raise ValueError("queued command must be `pixverse create <kind> ...`")


def apply_generation_defaults(argv: list[str]) -> list[str]:
    """Materialize defaults when authoring a new queue, preserving explicit choices.

    Do not rewrite saved queues at load/run time: their commands may already have
    paid receipts or approval, and changing them would change idempotency keys.
    """
    args = list(argv)
    try:
        kind = create_kind(args)
    except ValueError:
        return args
    model = _argv_option_value(args, "--model", "-m")
    if not model:
        if kind == "image":
            model = IMAGE_MODEL
        elif kind in {"video", "reference"}:
            model = VIDEO_MODEL
        elif kind == "transition" and len(_argv_list_option_values(args, "--images")) == 2:
            model = VIDEO_MODEL
        if model:
            args.extend(["--model", model])
    if model in {IMAGE_MODEL, VIDEO_MODEL} and (not _argv_option_value(args, "--quality", "-q")):
        args.extend(["--quality", IMAGE_QUALITY if model == IMAGE_MODEL else VIDEO_QUALITY])
    if model == IMAGE_MODEL and (not _argv_option_value(args, "--detail-level")):
        args.extend(["--detail-level", IMAGE_DETAIL])
    return args


def validate_create_argv(argv: list[str], *, capabilities: dict[str, Any] | None = None) -> str:
    """Validate release-pinned capability walls that would otherwise spend a failed task."""
    effective_pixverse_region(argv[1:])
    argv = _normalize_pixverse_create_globals(argv)
    kind = create_kind(argv)
    workspace_id = _argv_option_value(argv, "--workspace-id")
    if workspace_id:
        raise ValueError(
            "queued paid generation does not accept --workspace-id; select the intended active workspace before preflight so account, balance, submission, and reconciliation stay aligned"
        )
    if kind == "upscale":
        quality = _argv_option_value(argv, "--quality", "-q")
        if quality and quality != "2160p":
            raise ValueError("PixVerse video upscale supports only --quality 2160p")
    model = _argv_option_value(argv, "--model", "-m")
    if model == "seedance-2.5":
        if kind not in {"video", "reference", "transition"}:
            raise ValueError(
                "Seedance 2.5 is supported only for video, reference, and two-frame transition generation"
            )
        for flag, message in (
            (
                "--audio",
                "Seedance 2.5 does not expose an audio toggle; omit --audio and describe the desired sound in the prompt. This does not mean the model cannot generate audio",
            ),
            (
                "--no-audio",
                "Seedance 2.5 does not expose an audio toggle; omit --no-audio and remove the audio track during local export if a silent deliverable is required",
            ),
            ("--multi-shot", "Seedance 2.5 does not support generated multi-shot mode"),
            ("--off-peak", "Seedance 2.5 does not support off-peak generation"),
        ):
            if _argv_has_option(argv, flag):
                raise ValueError(message)
        quality = _argv_option_value(argv, "--quality", "-q")
        if quality and quality not in {"480p", "720p", "1080p"}:
            raise ValueError("Seedance 2.5 quality must be 480p, 720p, or 1080p")
        aspect_ratio = _argv_option_value(argv, "--aspect-ratio")
        if (
            aspect_ratio
            and kind in {"video", "reference"}
            and (aspect_ratio not in {"auto", "21:9", "16:9", "4:3", "1:1", "3:4", "9:16"})
        ):
            raise ValueError(f"Seedance 2.5 does not support aspect ratio {aspect_ratio}")
        duration = _argv_option_value(argv, "--duration", "-d")
        if duration and (not (kind == "reference" and duration == "auto")):
            try:
                duration_value = float(duration)
            except ValueError as exc:
                raise ValueError("Seedance 2.5 duration must be an integer from 4 to 30") from exc
            if not duration_value.is_integer() or duration_value < 4 or duration_value > 30:
                raise ValueError("Seedance 2.5 duration must be an integer from 4 to 30")
        task_type = _argv_option_value(argv, "--task-type")
        if task_type:
            if kind != "reference":
                raise ValueError(
                    "--task-type is available only for Seedance 2.5 reference generation"
                )
            if task_type not in {"auto", "reference", "edit", "extend"}:
                raise ValueError(
                    "Seedance 2.5 --task-type must be auto, reference, edit, or extend"
                )
        if kind == "transition" and len(_argv_list_option_values(argv, "--images")) != 2:
            raise ValueError("Seedance 2.5 transition requires exactly two keyframe images")
        if kind == "reference":
            reference_limits = {"--images": 30, "--videos": 10, "--audios": 10}
            reference_counts = {
                option: len(_argv_list_option_values(argv, option)) for option in reference_limits
            }
            for option, limit in reference_limits.items():
                if reference_counts[option] > limit:
                    raise ValueError(
                        f"Seedance 2.5 reference accepts at most {limit} values for {option}"
                    )
            if sum(reference_counts.values()) > 50:
                raise ValueError("Seedance 2.5 reference accepts at most 50 total media references")
    if kind == "music" and (
        _argv_has_option(argv, "--no-duration-auto")
        or _argv_option_value(argv, "--duration-seconds")
    ):
        raise ValueError(
            "PixVerse music generation uses automatic duration; drop --duration-seconds / --no-duration-auto and trim, loop or fade the returned audio locally to the picture"
        )
    _validate_create_capability_argv(argv, kind=kind, model=model, capabilities=capabilities)
    return kind


def _normalize_pixverse_create_globals(argv: list[str]) -> list[str]:
    if not argv:
        return []
    command_args = [argv[0]]
    deferred: list[str] = []
    index = 1
    while index < len(argv):
        argument = argv[index]
        if argument == "--":
            command_args.extend(argv[index:])
            break
        if argument in {"--json", "-p"}:
            deferred.append(argument)
            index += 1
            continue
        if argument in {"--workspace-id", "--trace-id", "--region"}:
            deferred.append(argument)
            if index + 1 < len(argv):
                deferred.append(argv[index + 1])
            index += 2
            continue
        if any(
            (
                argument.startswith(f"{name}=")
                for name in ("--workspace-id", "--trace-id", "--region")
            )
        ):
            deferred.append(argument)
            index += 1
            continue
        command_args.append(argument)
        index += 1
    return [*command_args, *deferred]


def _parameter_flags(parameter: dict[str, Any]) -> list[str]:
    declaration = str(parameter.get("flag") or "")
    flags: list[str] = []
    for part in declaration.replace(",", "/").split("/"):
        token = part.strip().split(maxsplit=1)[0] if part.strip() else ""
        if token.startswith("-"):
            flags.append(token)
    return flags


def _parameter_is_present(argv: list[str], parameter: dict[str, Any]) -> bool:
    return any((_argv_has_option(argv, flag) for flag in _parameter_flags(parameter)))


def _parameter_value(argv: list[str], parameter: dict[str, Any]) -> str:
    flags = _parameter_flags(parameter)
    return _argv_option_value(argv, *flags) if flags else ""


def _parameter_list_values(argv: list[str], parameter: dict[str, Any]) -> list[str]:
    flags = _parameter_flags(parameter)
    return _argv_list_option_values(argv, flags[0]) if flags else []


def _positive_boolean_requested(argv: list[str], parameter: dict[str, Any]) -> bool:
    flags = _parameter_flags(parameter)
    positive = next((flag for flag in flags if not flag.startswith("--no-")), "")
    return bool(positive and _argv_has_option(argv, positive))


def _validate_integer_parameter(name: str, value: str, contract: dict[str, Any]) -> None:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"--{name.replace('_', '-')} must be an integer") from exc
    minimum = contract.get("min")
    maximum = contract.get("max")
    if isinstance(minimum, int) and parsed < minimum:
        raise ValueError(f"--{name.replace('_', '-')} must be at least {minimum}")
    if isinstance(maximum, int) and parsed > maximum:
        raise ValueError(f"--{name.replace('_', '-')} must be at most {maximum}")


def _validate_create_capability_argv(
    argv: list[str], *, kind: str, model: str, capabilities: dict[str, Any] | None = None
) -> None:
    create = load_create_capabilities() if capabilities is None else capabilities
    modes = create.get("modes") if isinstance(create.get("modes"), dict) else {}
    mode = modes.get(kind) if isinstance(modes, dict) else None
    if not isinstance(mode, dict):
        return
    parameters = mode.get("parameters") if isinstance(mode.get("parameters"), dict) else {}
    shared = (
        create.get("shared_parameters") if isinstance(create.get("shared_parameters"), dict) else {}
    )
    selected_model = model or str(mode.get("default_model") or "")
    model_ids = mode.get("model_ids")
    if model and isinstance(model_ids, list) and (model not in model_ids):
        raise ValueError(f"model {model!r} is not supported by pixverse create {kind}")
    if selected_model in {"minimax-h3", "minimax-h3-max"} and kind == "video":
        aspect = _argv_option_value(argv, "--aspect-ratio")
        image = _argv_option_value(argv, "--image")
        if not image and aspect == "auto":
            raise ValueError(f"{selected_model} text-to-video does not support --aspect-ratio auto")
        if image and aspect and (aspect != "auto"):
            raise ValueError(
                f"{selected_model} image-to-video forces automatic framing; omit --aspect-ratio or use auto, or choose reference mode for a fixed ratio"
            )
    for name, parameter in parameters.items():
        if not isinstance(parameter, dict):
            continue
        parameter_type = str(parameter.get("type") or "")
        present = _parameter_is_present(argv, parameter)
        values = _parameter_list_values(argv, parameter) if parameter_type == "media_list" else []
        value = (
            _parameter_value(argv, parameter)
            if parameter_type not in {"boolean", "media_list"}
            else ""
        )
        if parameter.get("required") is True and (
            not (present and (values or value or parameter_type == "boolean"))
        ):
            flag = _parameter_flags(parameter)[0] if _parameter_flags(parameter) else name
            raise ValueError(f"pixverse create {kind} requires {flag}")
        minimum_count = parameter.get("min_count")
        if isinstance(minimum_count, int) and present and (len(values) < minimum_count):
            flag = _parameter_flags(parameter)[0] if _parameter_flags(parameter) else name
            raise ValueError(f"{flag} requires at least {minimum_count} values")
        if present and parameter_type == "integer":
            _validate_integer_parameter(name, value, parameter)
    model_parameters = mode.get("model_parameters")
    for name, by_model in model_parameters.items() if isinstance(model_parameters, dict) else []:
        contract = by_model.get(selected_model) if isinstance(by_model, dict) else None
        parameter = (
            parameters.get(name) if isinstance(parameters.get(name), dict) else shared.get(name)
        )
        if not isinstance(contract, dict) or not isinstance(parameter, dict):
            continue
        present = _parameter_is_present(argv, parameter)
        parameter_type = str(parameter.get("type") or "")
        if contract.get("supported") is False and (
            _positive_boolean_requested(argv, parameter) if parameter_type == "boolean" else present
        ):
            flag = _parameter_flags(parameter)[0] if _parameter_flags(parameter) else name
            raise ValueError(f"{selected_model} does not support {flag} for pixverse create {kind}")
        if not present:
            continue
        values = _parameter_list_values(argv, parameter) if parameter_type == "media_list" else []
        value = (
            _parameter_value(argv, parameter)
            if parameter_type not in {"boolean", "media_list"}
            else ""
        )
        if parameter_type == "integer":
            _validate_integer_parameter(name, value, contract)
        allowed = contract.get("enum")
        if (
            isinstance(allowed, list)
            and value
            and (str(value) not in {str(item) for item in allowed})
        ):
            flag = _parameter_flags(parameter)[0] if _parameter_flags(parameter) else name
            raise ValueError(f"{flag}={value!r} is not supported by {selected_model}")
        maximum_count = contract.get("max_count")
        if isinstance(maximum_count, int) and len(values) > maximum_count:
            flag = _parameter_flags(parameter)[0] if _parameter_flags(parameter) else name
            raise ValueError(f"{selected_model} accepts at most {maximum_count} values for {flag}")
    for name, parameter in shared.items():
        if not isinstance(parameter, dict) or not _parameter_is_present(argv, parameter):
            continue
        if parameter.get("type") == "integer":
            _validate_integer_parameter(name, _parameter_value(argv, parameter), parameter)
    if kind == "reference":
        reference_counts = {
            name: len(_parameter_list_values(argv, parameters[name]))
            for name in ("images", "videos", "audios")
            if isinstance(parameters.get(name), dict)
        }
        if sum(reference_counts.values()) == 0:
            raise ValueError(
                "pixverse create reference requires at least one image, video, or audio reference"
            )
        if (
            reference_counts.get("audios", 0)
            and (not (reference_counts.get("images", 0) or reference_counts.get("videos", 0)))
            and (selected_model != "wan-3.0")
        ):
            raise ValueError("audio references require an image or video reference for this model")
        metadata = mode.get("model_metadata")
        model_metadata = metadata.get(selected_model) if isinstance(metadata, dict) else None
        total_limit = (
            model_metadata.get("max_reference_items") if isinstance(model_metadata, dict) else None
        )
        if isinstance(total_limit, int) and sum(reference_counts.values()) > total_limit:
            raise ValueError(
                f"{selected_model} accepts at most {total_limit} total media references"
            )
    if kind == "transition":
        image_parameter = (
            parameters.get("images") if isinstance(parameters.get("images"), dict) else {}
        )
        image_count = len(_parameter_list_values(argv, image_parameter))
        variants = mode.get("variants") if isinstance(mode.get("variants"), dict) else {}
        variant_name = (
            "two_frames" if image_count == 2 else "multi_frame" if image_count >= 3 else ""
        )
        variant = variants.get(variant_name) if isinstance(variants, dict) else None
        allowed_models = variant.get("allowed_models") if isinstance(variant, dict) else None
        if (
            selected_model
            and isinstance(allowed_models, list)
            and (selected_model not in allowed_models)
        ):
            raise ValueError(
                f"{selected_model} is not supported for a {image_count}-frame transition"
            )
        rules = mode.get("rules")
        for rule in rules if isinstance(rules, list) else []:
            if not isinstance(rule, dict) or rule.get("id") != "transition-prompt-required":
                continue
            required_models = rule.get("when", {}).get("model", {}).get("in", [])
            if selected_model in required_models:
                prompt = (
                    parameters.get("prompt") if isinstance(parameters.get("prompt"), dict) else {}
                )
                if not _parameter_value(argv, prompt):
                    raise ValueError(f"{selected_model} transition requires --prompt")


def _argv_option_value(argv: list[str], *names: str) -> str:
    for index, value in enumerate(argv):
        if value in names:
            return argv[index + 1] if index + 1 < len(argv) else ""
        for name in names:
            if value.startswith(f"{name}="):
                return value.split("=", 1)[1]
    return ""


def _argv_has_option(argv: list[str], name: str) -> bool:
    return any((value == name or value.startswith(f"{name}=") for value in argv))


def _argv_list_option_values(argv: list[str], name: str) -> list[str]:
    try:
        index = argv.index(name) + 1
    except ValueError:
        return []
    values: list[str] = []
    while index < len(argv) and (not argv[index].startswith("-")):
        values.append(argv[index])
        index += 1
    return values


def ensure_async_json_args(argv: list[str], key: str) -> list[str]:
    out = list(argv)
    if "--json" not in out and "-p" not in out:
        out.append("--json")
    if "--no-wait" not in out:
        out.append("--no-wait")
    try:
        kind = create_kind(out)
    except ValueError:
        kind = ""
    if kind in {"voice", "music"}:
        if "--client-request-id" not in out:
            out.extend(["--client-request-id", key])
    elif "--idempotency-key" not in out:
        out.extend(["--idempotency-key", key])
    return out


def asset_info(task_id: str, kind: str) -> dict[str, Any]:
    try:
        (result, payload) = run_json(
            ["pixverse", "asset", "info", task_id, "--type", poll_type_for_kind(kind), "--json"],
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        return {}
    if not result.ok or not isinstance(payload, dict):
        return {}
    return payload


def ensure_local_asset(
    *,
    task_id: str,
    media_type: str,
    project_path: Path,
    existing_path: str = "",
    progress: bool = False,
    label: str = "",
    expected_bytes: int | None = None,
) -> dict[str, str]:
    """Download a generated asset to a stable project-local preview path.

    PixVerse status and asset-info payloads expose public URLs and provider media
    paths, neither of which Codex can reliably render inline. Keep those provider
    values for audit and queue dependencies, but always give user-facing preview
    and project QA a real local file. A task-specific directory also makes this
    operation idempotent when a queue is resumed or reconciled.
    """
    if existing_path:
        existing = Path(existing_path).expanduser()
        if _usable_local_file(existing):
            return {"local_path": str(existing.resolve()), "status": "ready", "error": ""}
    normalized_type = media_type if media_type in {"image", "video", "audio"} else ""
    directory_name = {"image": "images", "video": "videos", "audio": "audio"}.get(
        normalized_type, "media"
    )
    safe_task_id = re.sub("[^A-Za-z0-9._-]+", "-", task_id).strip("-.") or "unknown-task"
    destination = (project_path / "assets" / directory_name / safe_task_id).resolve()
    cached = _latest_local_asset(destination, normalized_type)
    if cached is not None:
        return {"local_path": str(cached), "status": "ready", "error": ""}
    if not task_id:
        return {
            "local_path": "",
            "status": "task_id_missing",
            "error": "Cannot download a generated asset without its PixVerse task id.",
        }
    destination.mkdir(parents=True, exist_ok=True)
    argv = ["pixverse", "asset", "download", task_id]
    if normalized_type:
        argv.extend(["--type", normalized_type])
    argv.extend(["--dest", str(destination), "--json"])
    try:
        (result, payload) = _run_json_with_download_feedback(
            argv,
            timeout=5 * 60,
            progress=progress,
            destination=destination,
            label=label or task_id,
            expected_bytes=expected_bytes,
        )
    except subprocess.TimeoutExpired:
        return {
            "local_path": "",
            "status": "download_timeout",
            "error": "Local preview download timed out; the generated provider asset is unchanged.",
        }
    raw_file = str(payload.get("file") or "") if isinstance(payload, dict) else ""
    candidates: list[Path] = []
    if raw_file:
        reported = Path(raw_file).expanduser()
        candidates.append(reported)
        if not reported.is_absolute():
            candidates.append(destination / reported)
    candidates.extend(
        (path for path in [_latest_local_asset(destination, normalized_type)] if path is not None)
    )
    downloaded = next((path.resolve() for path in candidates if _usable_local_file(path)), None)
    if result.ok and downloaded is not None:
        return {"local_path": str(downloaded), "status": "ready", "error": ""}
    return {
        "local_path": "",
        "status": "download_failed",
        "error": result.stderr
        or result.stdout
        or "PixVerse asset download returned no local file.",
    }


def _latest_local_asset(destination: Path, media_type: str = "") -> Path | None:
    if not destination.is_dir():
        return None
    suffixes = {
        "image": {".gif", ".jpeg", ".jpg", ".png", ".webp"},
        "video": {".m4v", ".mov", ".mp4", ".webm"},
        "audio": {".aac", ".flac", ".m4a", ".mp3", ".ogg", ".wav"},
    }.get(media_type, set())
    candidates = sorted(
        (
            path
            for path in destination.rglob("*")
            if not path.name.startswith(".")
            and (not suffixes or path.suffix.lower() in suffixes)
            and _usable_local_file(path)
        ),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    return candidates[0].resolve() if candidates else None


def _usable_local_file(path: Path) -> bool:
    try:
        return path.is_file() and path.stat().st_size > 0
    except OSError:
        return False


def _emit_progress(enabled: bool, message: str) -> None:
    if enabled:
        print(f"[pixverse-agent] {message}", file=sys.stderr, flush=True)


def _run_json_with_download_feedback(
    argv: list[str],
    *,
    timeout: float,
    progress: bool,
    destination: Path,
    label: str,
    expected_bytes: int | None = None,
) -> tuple[CommandResult, dict[str, Any]]:
    """Keep local delivery responsive without spamming long downloads.

    Fast downloads return immediately. For slower ones, sample byte growth in
    the task-specific destination, estimate recent throughput, and adapt the
    next heartbeat from a quick initial response to a 30-second large-file cap.
    """
    started = time.monotonic()
    last_sample_at = started
    last_bytes = _downloaded_bytes(destination)
    smoothed_rate = 0.0
    feedback_interval = DOWNLOAD_INITIAL_FEEDBACK_SECONDS
    with ThreadPoolExecutor(
        max_workers=1, thread_name_prefix="pixverse-runtime-download"
    ) as executor:
        future = executor.submit(run_json, argv, timeout)
        while True:
            try:
                return future.result(timeout=feedback_interval)
            except FutureTimeoutError:
                now = time.monotonic()
                downloaded = _downloaded_bytes(destination)
                sample_seconds = max(0.001, now - last_sample_at)
                instant_rate = max(0, downloaded - last_bytes) / sample_seconds
                if instant_rate > 0:
                    smoothed_rate = (
                        instant_rate
                        if smoothed_rate <= 0
                        else smoothed_rate * 0.4 + instant_rate * 0.6
                    )
                elif smoothed_rate > 0:
                    smoothed_rate *= 0.5
                elapsed = now - started
                _emit_progress(
                    progress,
                    _download_feedback_message(
                        label=label,
                        downloaded_bytes=downloaded,
                        bytes_per_second=smoothed_rate,
                        expected_bytes=expected_bytes,
                        elapsed_seconds=elapsed,
                    ),
                )
                feedback_interval = _next_download_feedback_interval(
                    elapsed_seconds=elapsed,
                    downloaded_bytes=downloaded,
                    bytes_per_second=smoothed_rate,
                )
                last_sample_at = now
                last_bytes = downloaded


def _downloaded_bytes(destination: Path) -> int:
    if not destination.is_dir():
        return 0
    total = 0
    for path in destination.rglob("*"):
        try:
            if path.is_file():
                total += path.stat().st_size
        except OSError:
            continue
    return total


def _next_download_feedback_interval(
    *, elapsed_seconds: float, downloaded_bytes: int, bytes_per_second: float
) -> float:
    mib = 1024 * 1024
    if downloaded_bytes >= 256 * mib:
        return DOWNLOAD_MAX_FEEDBACK_SECONDS
    if downloaded_bytes >= 64 * mib:
        return 20.0
    if bytes_per_second >= 8 * mib:
        return 15.0
    if bytes_per_second >= 1 * mib:
        return 10.0
    if bytes_per_second > 0:
        return 5.0
    if elapsed_seconds < 5:
        return 3.0
    if elapsed_seconds < 15:
        return 5.0
    if elapsed_seconds < 35:
        return 10.0
    return DOWNLOAD_MAX_FEEDBACK_SECONDS


def _download_feedback_message(
    *,
    label: str,
    downloaded_bytes: int,
    bytes_per_second: float,
    expected_bytes: int | None,
    elapsed_seconds: float,
) -> str:
    details: list[str] = []
    if downloaded_bytes > 0:
        details.append(f"downloaded {_format_bytes(downloaded_bytes)}")
    if expected_bytes and expected_bytes > 0:
        percent = min(100.0, downloaded_bytes / expected_bytes * 100)
        details.append(f"{percent:.0f}%")
    if bytes_per_second > 0:
        details.append(f"recent speed {_format_bytes(bytes_per_second)}/s")
    if expected_bytes and expected_bytes > downloaded_bytes and (bytes_per_second > 0):
        eta = (expected_bytes - downloaded_bytes) / bytes_per_second
        details.append(f"ETA {_format_elapsed(eta)}")
    progress_text = ", ".join(details) if details else "waiting for local file data"
    return f"Still downloading the local preview for {label}: {progress_text}; elapsed {_format_elapsed(elapsed_seconds)}. Generation is complete and no regeneration was submitted."


def _format_bytes(value: float | int) -> str:
    amount = float(max(0, value))
    for unit in ("B", "KiB", "MiB", "GiB"):
        if amount < 1024 or unit == "GiB":
            return f"{amount:.1f} {unit}" if unit != "B" else f"{amount:.0f} {unit}"
        amount /= 1024
    return f"{amount:.1f} GiB"


def _format_elapsed(seconds: float) -> str:
    seconds = max(0, int(seconds))
    (minutes, remainder) = divmod(seconds, 60)
    (hours, minutes) = divmod(minutes, 60)
    if hours:
        return f"{hours}h{minutes:02d}m{remainder:02d}s"
    if minutes:
        return f"{minutes}m{remainder:02d}s"
    return f"{remainder}s"
