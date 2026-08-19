#!/usr/bin/env python3
# ruff: noqa: E402
"""Generate and verify strict CATC schemas from executable models."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_decision_transaction import (
    DecisionTransaction,
    ExecutionContext,
    GateDecision,
    LifecycleEventRecord,
    OrderEvent,
    PaperOpsHandoffRecord,
    PrimaryBlocker,
    TradeOutcome,
)
from orchestrator.qadam_operator_ready_common import now_iso, runtime_dir, write_json_atomic


MODELS = {
    "decision-transaction": DecisionTransaction,
    "execution-context": ExecutionContext,
    "gate-decision": GateDecision,
    "primary-blocker": PrimaryBlocker,
    "paperops-handoff": PaperOpsHandoffRecord,
    "order-event": OrderEvent,
    "lifecycle-event": LifecycleEventRecord,
    "trade-outcome": TradeOutcome,
}


def main() -> int:
    schema_dir = ROOT / "schemas"
    schema_dir.mkdir(parents=True, exist_ok=True)
    hashes = {}
    errors = []
    for name, model in MODELS.items():
        schema = model.model_json_schema()
        text = json.dumps(schema, indent=2, sort_keys=True) + "\n"
        path = schema_dir / f"qadam.{name}.v1.schema.json"
        path.write_text(text, encoding="utf-8")
        hashes[name] = sha256(text.encode("utf-8")).hexdigest()
        if schema.get("additionalProperties") is not False:
            errors.append(f"schema_not_strict:{name}")
    payload = {
        "schema_version": "qadam_decision_schema_checks.v1",
        "artifact_type": "qadam_decision_schema_checks",
        "generated_at": now_iso(),
        "status": "passed" if not errors else "blocked",
        "schema_hashes": hashes,
        "validation_errors": errors,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "live_capital_enabled": False,
    }
    write_json_atomic(runtime_dir() / "qadam_decision_schema_checks.json", payload)
    print(f"qadam_decision_schema_status={payload['status']}")
    print(f"schema_count={len(hashes)}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
