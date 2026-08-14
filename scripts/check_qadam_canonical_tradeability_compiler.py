#!/usr/bin/env python3
"""Run the canonical compiler implementation checks and write certification."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_tradeability_audits import build_and_write_certification


CHECKS = (
    "check_qadam_ctc0_baseline.py",
    "check_qadam_contract_hierarchy.py",
    "check_qadam_tradeability_envelope.py",
    "check_qadam_tradeability_capability_matrix.py",
    "check_qadam_agent_prompt_compiler.py",
    "check_qadam_agent_critic_gauntlet.py",
    "check_qadam_accepted_research_packets.py",
    "check_qadam_tradeability_migration.py",
    "check_qadam_decision_generation.py",
    "check_qadam_tradeability_consumers.py",
    "check_qadam_tradeability_golden_journeys.py",
    "check_qadam_tradeability_reachability.py",
    "check_qadam_contract_self_healing.py",
    "check_qadam_tradeability_public_safety.py",
)


def main() -> int:
    command_failures = []
    for name in CHECKS:
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / name)],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode:
            command_failures.append(name)
            print(result.stdout, end="")
            print(result.stderr, end="", file=sys.stderr)
    certification, status, errors = build_and_write_certification()
    errors = [*command_failures, *errors]
    print(f"status={certification.get('status')}")
    print(f"implementation_complete={status.get('implementation_complete')}")
    print(f"production_release_certified={certification.get('production_release_certified')}")
    print(f"tradeability_reachability={certification.get('tradeability_reachability')}")
    print(f"current_setup_state={certification.get('current_setup_state')}")
    print(f"release_blockers={certification.get('release_blockers')}")
    for error in errors:
        print(f"error={error}")
    # An empirical five-session soak is reported as pending, not fabricated as a code failure.
    return 0 if status.get("implementation_complete") is True and not command_failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
