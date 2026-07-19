from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_runtime_producers import PRODUCERS


def test_every_registered_artifact_has_one_owner() -> None:
    owners: dict[str, list[str]] = {}
    for producer in PRODUCERS:
        for artifact in producer.artifact_names:
            owners.setdefault(artifact, []).append(producer.producer_id)
    assert owners
    assert {artifact: values for artifact, values in owners.items() if len(values) != 1} == {}


def test_safe_refresh_commands_cannot_call_paperops_or_brokers() -> None:
    commands = [part for producer in PRODUCERS if producer.safe_refresh for command in producer.command_sequence for part in command]
    joined = " ".join(commands).lower()
    assert "run_paperops_autonomous_pass" not in joined
    assert "submit" not in joined
    assert "live capital" not in joined


def test_research_evidence_validation_runs_in_dependency_order() -> None:
    producer = next(
        item for item in PRODUCERS if item.producer_id == "research_evidence_validation"
    )
    assert producer.command_sequence == (
        ("scripts/check_qadam_forward_labels.py",),
        ("scripts/check_qadam_statistical_backtest.py",),
        ("scripts/check_qadam_nonlinear_quantum_value.py",),
        ("scripts/check_qadam_edge_registry.py",),
    )
