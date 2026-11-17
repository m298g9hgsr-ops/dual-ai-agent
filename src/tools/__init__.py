"""Tooling package: command execution with safety guardrails."""

from .executor import (
    CommandExecutor,
    CommandResult,
    DockerExecutor,
    LocalExecutor,
    SafetyError,
    WslKaliExecutor,
    build_executor,
    check_command,
    host_of,
)

__all__ = [
    "CommandExecutor",
    "CommandResult",
    "DockerExecutor",
    "LocalExecutor",
    "SafetyError",
    "WslKaliExecutor",
    "build_executor",
    "check_command",
    "host_of",
]
