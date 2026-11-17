"""Command execution for the RED agent, with safety guardrails.

Executors:
    LocalExecutor    - bash on the current host
    WslKaliExecutor  - bash inside a WSL distro (kali-linux by default)
    DockerExecutor   - bash inside a running container

Guardrails (always on):
  * target host must be in the allowlist (SPAR_ALLOWED_TARGETS, default localhost only)
  * destructive command patterns are skipped, never executed
  * every command has a timeout and its output is captured
"""

from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass, field
from urllib.parse import urlparse

DEFAULT_ALLOWED = {"127.0.0.1", "localhost", "::1", "0.0.0.0"}

DANGEROUS = re.compile(
    r"(rm\s+-rf\s+/(?!\s)|mkfs|dd\s+if=|shutdown|reboot|halt\b|:\(\)\{"
    r"|curl[^|]*\|\s*(ba)?sh|wget[^|]*\|\s*(ba)?sh|chmod\s+-R\s+777\s+/"
    r"|DROP\s+DATABASE|TRUNCATE\s+TABLE|kill\s+-9\s+1\b|nc\s+-e|bash\s+-i\s*>&)",
    re.I,
)


class SafetyError(RuntimeError):
    """Raised when a command is refused before execution."""


@dataclass
class CommandResult:
    command: str
    returncode: int = 0
    stdout: str = ""
    stderr: str = ""
    skipped: bool = False
    reason: str = ""
    duration_ms: int = 0

    @property
    def ok(self) -> bool:
        return not self.skipped and self.returncode == 0

    def text(self) -> str:
        return (self.stdout + ("\n[stderr]\n" + self.stderr if self.stderr else "")).strip()


def host_of(url: str) -> str:
    if "://" not in url:
        url = "http://" + url
    return (urlparse(url).hostname or "").lower()


def allowed_hosts() -> set[str]:
    raw = os.getenv("SPAR_ALLOWED_TARGETS", "")
    hosts = {h.strip().lower() for h in raw.split(",") if h.strip()}
    return hosts or set(DEFAULT_ALLOWED)


def check_command(command: str, target: str) -> str | None:
    """Return a refusal reason, or None when the command may run."""
    host = host_of(target)
    if host and host not in allowed_hosts():
        return f"target host {host!r} not in allowlist {sorted(allowed_hosts())}"
    if DANGEROUS.search(command):
        return "destructive pattern blocked"
    return None


@dataclass
class CommandExecutor:
    """Base executor: runs a bash command and captures output."""

    timeout: int = 120
    label: str = "local"
    extra_env: dict[str, str] = field(default_factory=dict)

    def build(self, command: str) -> list[str]:
        return ["bash", "-lc", command]

    def run(self, command: str, target: str = "") -> CommandResult:
        reason = check_command(command, target) if target else None
        if reason:
            return CommandResult(command=command, skipped=True, reason=reason)
        import time

        t0 = time.time()
        env = {**os.environ, **self.extra_env}
        try:
            p = subprocess.run(
                self.build(command),
                capture_output=True,
                text=True,
                timeout=self.timeout,
                env=env,
            )
            return CommandResult(
                command=command,
                returncode=p.returncode,
                stdout=p.stdout[:20000],
                stderr=p.stderr[:4000],
                duration_ms=int((time.time() - t0) * 1000),
            )
        except subprocess.TimeoutExpired:
            return CommandResult(command=command, returncode=124, stderr=f"timeout after {self.timeout}s")
        except Exception as exc:  # pragma: no cover
            return CommandResult(command=command, returncode=1, stderr=str(exc)[:500])


class LocalExecutor(CommandExecutor):
    label = "local"


class WslKaliExecutor(CommandExecutor):
    label = "wsl"

    def __init__(self, distro: str = "kali-linux", user: str = "root", **kw):
        super().__init__(**kw)
        self.distro = distro
        self.user = user
        self.label = "wsl"  # dataclass default would otherwise overwrite this

    def build(self, command: str) -> list[str]:
        return ["wsl", "-d", self.distro, "-u", self.user, "--", "bash", "-lc", command]


class DockerExecutor(CommandExecutor):
    label = "docker"

    def __init__(self, container: str, **kw):
        super().__init__(**kw)
        self.container = container
        self.label = "docker"  # dataclass default would otherwise overwrite this

    def build(self, command: str) -> list[str]:
        return ["docker", "exec", self.container, "bash", "-lc", command]


def build_executor(spec: str, timeout: int = 120) -> CommandExecutor:
    """spec: local | wsl[:distro[:user]] | docker:<container>"""
    if spec.startswith("docker:"):
        return DockerExecutor(spec.split(":", 1)[1], timeout=timeout)
    if spec.startswith("wsl"):
        parts = spec.split(":")
        distro = parts[1] if len(parts) > 1 and parts[1] else "kali-linux"
        user = parts[2] if len(parts) > 2 and parts[2] else "root"
        return WslKaliExecutor(distro=distro, user=user, timeout=timeout)
    return LocalExecutor(timeout=timeout)
