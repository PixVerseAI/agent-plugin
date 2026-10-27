from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from typing import Any

from .compatibility import pixverse_cli_executable, pixverse_cli_runtime_is_supported


@dataclass
class CommandResult:
    argv: list[str]
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool = False

    @property
    def ok(self) -> bool:
        return self.returncode == 0

    def json(self) -> dict[str, Any]:
        if not self.stdout.strip():
            return {}
        return json.loads(self.stdout)


def runtime_environment() -> dict[str, str]:
    env = {key: value for key, value in os.environ.items() if not key.startswith("PIXVERSE_")}
    env["PIXVERSE_ENV"] = "production"
    for key in ("PIXVERSE_REGION", "PIXVERSE_CLI_SOURCE"):
        if key in os.environ:
            env[key] = os.environ[key]
    return env


def which(binary: str) -> str | None:
    if binary == "pixverse":
        managed = pixverse_cli_executable()
        return str(managed) if pixverse_cli_runtime_is_supported() else None
    return shutil.which(binary)


def run(argv: list[str], timeout: int | float = 60) -> CommandResult:
    argv = resolve_argv(argv)
    try:
        proc = subprocess.run(
            argv,
            env=runtime_environment(),
            check=False,
            text=True,
            capture_output=True,
            timeout=timeout,
        )
    except FileNotFoundError as exc:
        return CommandResult(
            argv=argv,
            returncode=127,
            stdout="",
            stderr=f"Executable not found while running {(argv[0] if argv else '<empty>')}: {exc}",
        )
    return CommandResult(
        argv=argv,
        returncode=proc.returncode,
        stdout=proc.stdout.strip(),
        stderr=proc.stderr.strip(),
    )


def run_passthrough(argv: list[str]) -> int:
    return subprocess.call(resolve_argv(argv), env=runtime_environment())


def run_captured(
    argv: list[str], *, input_text: str | None = None, timeout: int | float | None = None
) -> CommandResult:
    """Run a command while retaining byte-for-byte text output.

    Unlike ``run()``, this helper deliberately does not strip stdout/stderr. It
    is used when the wrapper must inspect a result before deciding what to do,
    then replay the managed CLI's output without changing its public contract.
    Callers that guard remote mutation or polling must pass a finite timeout.
    """
    argv = resolve_argv(argv)
    try:
        proc = subprocess.run(
            argv,
            env=runtime_environment(),
            check=False,
            text=True,
            capture_output=True,
            input=input_text,
            timeout=timeout,
        )
    except FileNotFoundError as exc:
        return CommandResult(
            argv=argv,
            returncode=127,
            stdout="",
            stderr=f"Executable not found while running {(argv[0] if argv else '<empty>')}: {exc}\n",
        )
    except subprocess.TimeoutExpired as exc:
        stdout = _timeout_text(exc.stdout)
        stderr = _timeout_text(exc.stderr)
        timeout_message = (
            f"Command timed out after {exc.timeout:g} seconds; remote outcome may be unknown.\n"
        )
        if stderr and (not stderr.endswith("\n")):
            stderr += "\n"
        return CommandResult(
            argv=argv,
            returncode=124,
            stdout=stdout,
            stderr=f"{stderr}{timeout_message}",
            timed_out=True,
        )
    return CommandResult(
        argv=argv, returncode=proc.returncode, stdout=proc.stdout, stderr=proc.stderr
    )


def _timeout_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def run_json(argv: list[str], timeout: int | float = 60) -> tuple[CommandResult, dict[str, Any]]:
    result = run(argv, timeout=timeout)
    try:
        payload = result.json()
    except json.JSONDecodeError:
        payload = {}
    return (result, payload)


def resolve_argv(argv: list[str]) -> list[str]:
    if not argv:
        return argv
    if argv[0] != "pixverse":
        return argv
    binary = which("pixverse")
    if not binary:
        return [str(pixverse_cli_executable()), *argv[1:]]
    real = os.path.realpath(binary)
    return [real, *argv[1:]]
