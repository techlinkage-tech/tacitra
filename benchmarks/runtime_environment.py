#!/usr/bin/env python3
"""Validated, credential-safe command runtime for benchmark replications."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import signal
import subprocess
import tempfile
import tomllib
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SECRET_NAMES = {"AUTHORIZATION", "OPENAI_API_KEY"}


class EnvironmentFailure(Exception):
    """A failure that must occur before any provider call."""

    def __init__(self, classification: str, tool: str | None, reason: str):
        super().__init__(reason)
        self.classification = classification
        self.tool = tool
        self.reason = reason

    def to_json(self) -> dict:
        return {
            "classification": self.classification,
            "tool": self.tool,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class ResolvedTool:
    name: str
    executable: Path
    version: str

    def public_record(self) -> dict:
        return {
            "name": self.name,
            "resolved_executable": self.executable.name,
            "executable_sha256": "sha256:" + hashlib.sha256(self.executable.read_bytes()).hexdigest(),
            "version": self.version,
            "ok": True,
            "failure_reason": None,
        }


@dataclass(frozen=True)
class RuntimeEnvironment:
    tools: dict[str, ResolvedTool]
    child_environment: dict[str, str]
    platform_name: str

    def executable(self, name: str) -> str:
        return str(self.tools[name].executable)

    def public_record(self) -> dict:
        return {
            "schema_version": 1,
            "classification": "environment_preflight_success",
            "platform": self.platform_name,
            "tools": [self.tools[name].public_record() for name in sorted(self.tools)],
            "credentials_forwarded_to_children": False,
        }


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool
    classification: str | None


def _is_secret(name: str) -> bool:
    upper = name.upper()
    return upper in SECRET_NAMES or upper.endswith("_API_KEY") or upper.endswith("_AUTH_TOKEN")


def safe_child_environment(parent: dict[str, str]) -> dict[str, str]:
    """Preserve PATH and ordinary tool settings while removing credentials."""
    return {name: value for name, value in parent.items() if not _is_secret(name)}


def _candidate_names(name: str) -> tuple[str, ...]:
    return (name, f"{name}.exe") if platform.system() == "Windows" else (name,)


def _valid_executable(path: Path) -> bool:
    return path.is_absolute() and path.is_file() and (os.access(path, os.X_OK) or platform.system() == "Windows")


def _which(names: tuple[str, ...], environment: dict[str, str]) -> Path | None:
    for name in names:
        found = shutil.which(name, path=environment.get("PATH", ""))
        if found:
            path = Path(found).resolve()
            if _valid_executable(path):
                return path
    return None


def _run_version(path: Path, arguments: tuple[str, ...], environment: dict[str, str]) -> str:
    try:
        result = subprocess.run(
            [str(path), *arguments],
            env=safe_child_environment(environment),
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise EnvironmentFailure("environment_preflight_failure", path.name, str(error)) from error
    output = (result.stdout or result.stderr).strip()
    if result.returncode != 0 or not output:
        raise EnvironmentFailure(
            "environment_preflight_failure", path.name,
            f"version command exited {result.returncode}: {output[:300]}",
        )
    return output.splitlines()[0]


def _rustup_which(tool: str, environment: dict[str, str]) -> Path | None:
    rustup = _which(_candidate_names("rustup"), environment)
    if rustup is None:
        return None
    try:
        result = subprocess.run(
            [str(rustup), "which", tool], env=safe_child_environment(environment),
            capture_output=True, text=True, timeout=10, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    candidate = Path(result.stdout.strip()).resolve()
    return candidate if _valid_executable(candidate) else None


def resolve_tool(
    name: str,
    environment: dict[str, str],
    *,
    override: str | None = None,
    version_arguments: tuple[str, ...] = ("--version",),
    expected_version: str | None = None,
    rustup_fallback: bool = False,
    related_directory: Path | None = None,
) -> ResolvedTool:
    path = None
    if override and environment.get(override):
        candidate = Path(environment[override])
        if not candidate.is_absolute():
            raise EnvironmentFailure("tool_not_found", name, f"{override} must be an absolute path")
        candidate = candidate.resolve()
        if _valid_executable(candidate):
            path = candidate
    if path is None:
        path = _which(_candidate_names(name), environment)
    if path is None and rustup_fallback:
        path = _rustup_which(name, environment)
    if path is None and related_directory is not None:
        for candidate_name in _candidate_names(name):
            candidate = (related_directory / candidate_name).resolve()
            if _valid_executable(candidate):
                path = candidate
                break
    if path is None:
        raise EnvironmentFailure("tool_not_found", name, f"{name} was not found in the subprocess environment")
    version = _run_version(path, version_arguments, environment)
    if expected_version and expected_version not in version:
        raise EnvironmentFailure(
            "tool_version_mismatch", name,
            f"expected {expected_version}, got {version}",
        )
    return ResolvedTool(name, path, version)


def pinned_rust_version(root: Path = ROOT) -> str:
    document = tomllib.loads((root / "rust-toolchain.toml").read_text(encoding="utf-8"))
    channel = document.get("toolchain", {}).get("channel")
    if not isinstance(channel, str) or not channel:
        raise EnvironmentFailure("environment_preflight_failure", "rustc", "invalid rust-toolchain.toml")
    return channel


def preflight(
    *,
    environment: dict[str, str] | None = None,
    root: Path = ROOT,
    required_files: tuple[Path, ...] = (),
    unused_outputs: tuple[Path, ...] = (),
) -> RuntimeEnvironment:
    parent = dict(os.environ if environment is None else environment)
    expected_rust = pinned_rust_version(root)
    tools: dict[str, ResolvedTool] = {}
    tools["python3"] = resolve_tool("python3", parent)
    tools["go"] = resolve_tool("go", parent, version_arguments=("version",))
    tools["rustc"] = resolve_tool(
        "rustc", parent, override="RUSTC", expected_version=expected_rust, rustup_fallback=True,
    )
    tools["cargo"] = resolve_tool(
        "cargo", parent, override="CARGO", expected_version=expected_rust,
        rustup_fallback=True, related_directory=tools["rustc"].executable.parent,
    )
    tools["patch"] = resolve_tool("patch", parent)
    tacitra = (root / "target/debug" / ("tacitra.exe" if platform.system() == "Windows" else "tacitra")).resolve()
    if not _valid_executable(tacitra):
        raise EnvironmentFailure("tool_not_found", "tacitra", "built Tacitra CLI was not found")
    tools["tacitra"] = ResolvedTool("tacitra", tacitra, _run_version(tacitra, ("--version",), parent))
    for path in required_files:
        if not path.is_file():
            raise EnvironmentFailure("environment_preflight_failure", None, f"required file is missing: {path.name}")
    for path in unused_outputs:
        if path.exists():
            raise EnvironmentFailure("environment_preflight_failure", None, f"output is already in use: {path.name}")
    try:
        with tempfile.TemporaryDirectory(prefix="tacitra-preflight-") as directory:
            probe = Path(directory) / "write-probe"
            probe.write_text("ok", encoding="utf-8")
            if probe.read_text(encoding="utf-8") != "ok":
                raise OSError("temporary write verification failed")
            _run_version(tools["rustc"].executable, ("--version",), parent)
    except OSError as error:
        raise EnvironmentFailure("environment_preflight_failure", None, f"temporary directory is not writable: {error}") from error
    return RuntimeEnvironment(tools, safe_child_environment(parent), platform.platform())


def _expanded_command(command: list[str], case_dir: Path, artifact: Path, work: Path,
                      runtime: RuntimeEnvironment) -> list[str]:
    values = {
        "repo": str(ROOT), "case": str(case_dir), "artifact": str(artifact),
        "work": str(work), "rustc": runtime.executable("rustc"),
    }
    expanded = [part.format(**values) for part in command]
    aliases = {name: runtime.executable(name) for name in ("python3", "go", "patch")}
    if expanded and expanded[0] in aliases:
        expanded[0] = aliases[expanded[0]]
    return expanded


def execute_commands(commands: list[list[str]], case_dir: Path, artifact: Path, work: Path,
                     timeout: int, runtime: RuntimeEnvironment) -> tuple[bool, CommandResult | None]:
    last = None
    environment = dict(runtime.child_environment)
    environment["PYTHONPYCACHEPREFIX"] = str(work / "pycache")
    environment["GOCACHE"] = str(work / "go-cache")
    for command in commands:
        argv = _expanded_command(command, case_dir, artifact, work, runtime)
        try:
            process = subprocess.Popen(
                argv, cwd=work, env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, start_new_session=platform.system() != "Windows",
            )
            try:
                stdout, stderr = process.communicate(timeout=timeout)
                last = CommandResult(process.returncode, stdout, stderr, False, None)
            except subprocess.TimeoutExpired:
                if platform.system() == "Windows":
                    process.kill()
                else:
                    os.killpg(process.pid, signal.SIGKILL)
                stdout, stderr = process.communicate()
                last = CommandResult(124, stdout, stderr, True, "timeout")
        except FileNotFoundError as error:
            last = CommandResult(127, "", str(error), False, "tool_not_found")
        except OSError as error:
            last = CommandResult(126, "", str(error), False, "environment_preflight_failure")
        if last.returncode != 0:
            return False, last
    return True, last


def public_error(error: EnvironmentFailure) -> str:
    return json.dumps(error.to_json(), sort_keys=True, separators=(",", ":"))
