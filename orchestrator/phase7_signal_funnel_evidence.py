"""Q7-13 Phase 7 Demo Proof source and signal funnel evidence.

This stage links each Phase 7 proof trade back to the Qadam decision chain:
source quorum, source trust, Akber filter, Signal Integrity, Risk Agent,
Execution Policy, kill-switch state, paper sizing, and broker readiness. It is
an evidence-only layer. It cannot certify Phase 7, infer proof from private
priors, grant proof credit, call broker routes, or enable live capital.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.event_log import EventLog, EventLogEntry
from orchestrator.phase7_artifacts import (
    PHASE7_ARTIFACT_SCHEMA_VERSION,
    PHASE7_EVENT_TYPES,
    phase7_proof_contract,
    phase7_provenance,
    phase7_source_posture,
)
from orchestrator.phase7_guarded_alpaca_paper_submit import (
    PHASE7_GUARDED_ALPACA_SUBMIT_RUNTIME_ARTIFACT,
    build_phase7_guarded_alpaca_paper_submit_path,
    phase7_guarded_alpaca_submit_paths,
    validate_phase7_guarded_alpaca_paper_submit_path,
)
from orchestrator.phase7_override_detector import (
    PHASE7_OVERRIDE_DETECTOR_RUNTIME_ARTIFACT,
    build_phase7_override_detector,
    phase7_override_detector_paths,
    validate_phase7_override_detector,
    write_phase7_override_detector,
)
from orchestrator.phase7_proof_lifecycle_monitor import (
    PHASE7_PROOF_LIFECYCLE_RUNTIME_ARTIFACT,
    build_phase7_proof_lifecycle_monitor,
    phase7_proof_lifecycle_monitor_paths,
    validate_phase7_proof_lifecycle_monitor,
)
from orchestrator.phase7_proof_order_staging import (
    PHASE7_PROOF_ORDER_STAGING_RUNTIME_ARTIFACT,
    build_phase7_proof_order_staging,
    phase7_proof_order_staging_paths,
    validate_phase7_proof_order_staging,
)
from orchestrator.phase7_qualified_setup_ledger import (
    PHASE7_QUALIFIED_SETUP_LEDGER_RUNTIME_ARTIFACT,
    build_phase7_qualified_setup_ledger,
    phase7_qualified_setup_ledger_paths,
    validate_phase7_qualified_setup_ledger,
)
from orchestrator.phase7_readiness import (
    PHASE7_AUTHORITY_FLAGS,
    PHASE7_HARNESS_DAY_COUNT,
    PHASE7_MATURE_CLOSED_TRADE_BENCHMARK,
    PHASE7_MAX_DRAWDOWN_FRACTION,
    PHASE7_PAPER_ACCOUNT_STARTING_GBP,
    PHASE7_UNSAFE_COUNT_FIELDS,
    phase7_authority_defaults,
    phase7_unsafe_counter_defaults,
)
from orchestrator.phase7_test_mode_auto_approval import (
    PHASE7_TEST_MODE_AUTO_APPROVAL_RUNTIME_ARTIFACT,
    build_phase7_test_mode_auto_approval_router,
    phase7_test_mode_auto_approval_paths,
    validate_phase7_test_mode_auto_approval_router,
)


PHASE7_SIGNAL_FUNNEL_EVIDENCE_SCHEMA_VERSION = 1
PHASE7_SIGNAL_FUNNEL_EVIDENCE_RUNTIME_ARTIFACT = (
    "phase7_signal_funnel_evidence.json"
)
PHASE7_SIGNAL_FUNNEL_EVIDENCE_HISTORY = "phase7_signal_funnel_evidence_history.jsonl"
PHASE7_SIGNAL_FUNNEL_EVIDENCE_EVENT_LOG = "phase7_signal_funnel_evidence_events.jsonl"
PHASE7_SIGNAL_FUNNEL_EVIDENCE_EVENT_TYPE = PHASE7_EVENT_TYPES["signal_evidence"]
PHASE7_SIGNAL_FUNNEL_EVIDENCE_COMPONENT = "phase7_signal_funnel_evidence"

PHASE7_SIGNAL_FUNNEL_BOUNDARY = (
    "Q7-13 records Phase 7 source and signal funnel evidence only from Q7 "
    "qualified setup, auto-approval, staged order, paper-submit receipt, proof "
    "lifecycle, and clean-sample override artifacts. It can link proof trades "
    "to source quorum, source trust, Akber filter, Signal Integrity, Risk "
    "Agent, Execution Policy, kill-switch state, paper sizing, broker "
    "readiness, challenge-only Preference/PREF context, Yahoo supplemental "
    "context, and quantum shadow annotations, but it cannot certify Phase 7, "
    "cannot infer proof from private priors alone, cannot grant Phase 7 proof "
    "credit, cannot create proof trades, cannot call broker POST routes, "
    "cannot call Alpaca POST routes, cannot write prediction-market or "
    "crypto-perps orders, cannot mutate policy or strategies, cannot enable "
    "live capital, and cannot permit manual trade-level overrides."
)

PHASE7_REQUIRED_SIGNAL_CHAIN_KEYS: tuple[str, ...] = (
    "source_quorum",
    "source_trust",
    "akber_filter",
    "signal_integrity",
    "risk_agent",
    "execution_policy",
    "kill_switch_state",
    "paper_sizing",
    "broker_readiness",
)

PHASE7_SIGNAL_FUNNEL_REQUIRED_CHECKS: tuple[str, ...] = (
    "q7_12_override_detector_valid",
    "q7_13_signal_evidence_stage_allowed",
    "source_qualified_setup_ledger_valid",
    "source_auto_approval_valid",
    "source_staged_order_gate_valid",
    "source_guarded_submit_valid",
    "source_lifecycle_valid",
    "source_quorum_ref_present_or_no_sample",
    "source_trust_ref_present_or_no_sample",
    "akber_filter_ref_present_or_no_sample",
    "signal_integrity_ref_present_or_no_sample",
    "risk_agent_ref_present_or_no_sample",
    "execution_policy_ref_present_or_no_sample",
    "kill_switch_ref_present_or_no_sample",
    "paper_sizing_ref_present_or_no_sample",
    "broker_readiness_ref_present_or_no_sample",
    "private_priors_not_counted_as_proof",
    "preference_context_challenge_only",
    "yahoo_context_supplemental_only",
    "quantum_context_shadow_only",
    "certification_blocks_incomplete_chain",
    "no_certification_authority",
    "no_proof_credit",
    "no_broker_post",
    "no_alpaca_post",
    "no_live_endpoint",
    "no_live_capital",
    "manual_override_disabled",
    "market_writes_disabled",
    "public_safe",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runtime_dir(settings: Settings | None = None) -> Path:
    return Path((settings or Settings.from_env()).runtime_dir)


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def phase7_signal_funnel_evidence_paths(
    settings: Settings | None = None,
) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / PHASE7_SIGNAL_FUNNEL_EVIDENCE_RUNTIME_ARTIFACT,
        runtime / PHASE7_SIGNAL_FUNNEL_EVIDENCE_HISTORY,
        runtime / PHASE7_SIGNAL_FUNNEL_EVIDENCE_EVENT_LOG,
    )


def _qualified_setup_ledger(settings: Settings) -> dict[str, Any]:
    output_path, _, _ = phase7_qualified_setup_ledger_paths(settings)
    if output_path.exists():
        return _read_json(output_path)
    return build_phase7_qualified_setup_ledger(settings=settings)


def _auto_approval(settings: Settings) -> dict[str, Any]:
    output_path, _, _ = phase7_test_mode_auto_approval_paths(settings)
    if output_path.exists():
        return _read_json(output_path)
    return build_phase7_test_mode_auto_approval_router(settings=settings)


def _staged_orders(settings: Settings) -> dict[str, Any]:
    output_path, _, _ = phase7_proof_order_staging_paths(settings)
    if output_path.exists():
        return _read_json(output_path)
    return build_phase7_proof_order_staging(settings=settings)


def _guarded_submit(settings: Settings) -> dict[str, Any]:
    output_path, _, _ = phase7_guarded_alpaca_submit_paths(settings)
    if output_path.exists():
        return _read_json(output_path)
    return build_phase7_guarded_alpaca_paper_submit_path(settings=settings)


def _lifecycle(settings: Settings) -> dict[str, Any]:
    output_path, _, _ = phase7_proof_lifecycle_monitor_paths(settings)
    if output_path.exists():
        return _read_json(output_path)
    return build_phase7_proof_lifecycle_monitor(settings=settings)


def _override_detector(settings: Settings) -> dict[str, Any]:
    output_path, _, _ = phase7_override_detector_paths(settings)
    if output_path.exists():
        return _read_json(output_path)
    override = build_phase7_override_detector(settings=settings)
    _, _, _, written = write_phase7_override_detector(
        override,
        settings=settings,
        record_event=True,
    )
    return written


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_key(value: str) -> str:
    allowed = []
    for char in value.lower():
        if char.isalnum() or char in {"_", "-"}:
            allowed.append(char)
        else:
            allowed.append("_")
    return "".join(allowed).strip("_") or "unknown"


def _check(name: str, passed: bool, *, detail: Any = None) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def _refs_by_key(records: list[dict[str, Any]], *keys: str) -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    for record in records:
        if not isinstance(record, dict):
            continue
        for key in keys:
            value = str(record.get(key) or "").strip()
            if value:
                output[value] = record
    return output


def _list(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, list):
        return []
    return [record for record in payload if isinstance(record, dict)]


def _gate_passed(record: dict[str, Any], gate_key: str) -> bool:
    for gate in record.get("gate_results", []) or []:
        if isinstance(gate, dict) and gate.get("gate_key") == gate_key:
            return gate.get("status") == "pass"
    return False


def _proof_trade_records(lifecycle: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        record
        for record in _list(lifecycle.get("lifecycle_records"))
        if record.get("proof_trade_created") is True
    ]


def _signal_evidence_policy() -> dict[str, Any]:
    return {
        "policy_schema_version": PHASE7_SIGNAL_FUNNEL_EVIDENCE_SCHEMA_VERSION,
        "required_decision_chain_keys": list(PHASE7_REQUIRED_SIGNAL_CHAIN_KEYS),
        "required_decision_chain_key_count": len(PHASE7_REQUIRED_SIGNAL_CHAIN_KEYS),
        "complete_decision_chain_required_for_certification": True,
        "private_priors_only_certification_allowed": False,
        "private_prior_counts_as_proof": False,
        "canonical_source_quorum_required": True,
        "source_quorum_bypass_allowed": False,
        "source_trust_required": True,
        "akber_filter_required": True,
        "signal_integrity_required": True,
        "risk_agent_required": True,
        "execution_policy_required": True,
        "kill_switch_state_required": True,
        "paper_sizing_required": True,
        "broker_readiness_required": True,
        "preference_mcp_role": "challenge_only_context",
        "preference_mcp_counts_as_source_quorum": False,
        "preference_mcp_counts_as_proof": False,
        "yahoo_finance_role": "supplemental_market_context_only",
        "yahoo_finance_counts_as_source_quorum": False,
        "yahoo_finance_counts_as_proof": False,
        "qctrl_role": "quantum_shadow_annotation_only",
        "qctrl_counts_as_execution_truth": False,
        "qctrl_counts_as_proof": False,
        "certification_authority_allowed": False,
        "proof_credit_allowed": False,
        "broker_post_allowed": False,
        "alpaca_post_allowed": False,
        "live_endpoint_allowed": False,
        "prediction_market_write_allowed": False,
        "crypto_perps_write_allowed": False,
        "policy_mutation_allowed": False,
        "strategy_mutation_allowed": False,
        "manual_trade_level_override_allowed": False,
        "live_capital_enabled": False,
    }


def _authority_ledger(
    *,
    stage_recorded: bool,
    new_proof_trades_frozen: bool,
) -> dict[str, Any]:
    defaults = phase7_authority_defaults()
    if stage_recorded:
        defaults["phase7_proof_lifecycle_write_allowed"] = True
        defaults["phase7_postmortem_write_allowed"] = True
        defaults["phase7_performance_evaluation_write_allowed"] = True
        if not new_proof_trades_frozen:
            defaults["phase7_test_mode_auto_approval_allowed"] = True
            defaults["phase7_proof_order_staging_allowed"] = True
            defaults["phase7_proof_trade_submission_allowed"] = True
    grants = [field for field in PHASE7_AUTHORITY_FLAGS if defaults[field]]
    return {
        "authority_schema_version": PHASE7_SIGNAL_FUNNEL_EVIDENCE_SCHEMA_VERSION,
        "stage": "Q7-13",
        "authority_field_count": len(PHASE7_AUTHORITY_FLAGS),
        "explicit_authority_grant_count": len(grants),
        "explicit_authority_grants": grants,
        "q7_14_maturity_tracker_stage_allowed": stage_recorded,
        "signal_funnel_evidence_write_allowed": stage_recorded,
        "new_proof_trades_frozen": new_proof_trades_frozen,
        **defaults,
        "boundary": PHASE7_SIGNAL_FUNNEL_BOUNDARY,
    }


def _provenance() -> dict[str, Any]:
    provenance = phase7_provenance(
        (
            f"data/runtime/{PHASE7_OVERRIDE_DETECTOR_RUNTIME_ARTIFACT}",
            f"data/runtime/{PHASE7_QUALIFIED_SETUP_LEDGER_RUNTIME_ARTIFACT}",
            f"data/runtime/{PHASE7_TEST_MODE_AUTO_APPROVAL_RUNTIME_ARTIFACT}",
            f"data/runtime/{PHASE7_PROOF_ORDER_STAGING_RUNTIME_ARTIFACT}",
            f"data/runtime/{PHASE7_GUARDED_ALPACA_SUBMIT_RUNTIME_ARTIFACT}",
            f"data/runtime/{PHASE7_PROOF_LIFECYCLE_RUNTIME_ARTIFACT}",
            "orchestrator/phase7_artifacts.py",
            "orchestrator/phase7_override_detector.py",
            "orchestrator/phase7_qualified_setup_ledger.py",
            "orchestrator/phase7_test_mode_auto_approval.py",
            "orchestrator/phase7_proof_order_staging.py",
            "orchestrator/phase7_guarded_alpaca_paper_submit.py",
            "orchestrator/phase7_proof_lifecycle_monitor.py",
            "docs/qadam-phase-7-demo-proof-implementation-plan.md",
            "docs/qadam-phase-7-q7-12-override-detector-audit-2026-05-25.md",
        )
    )
    provenance["decision_chain_refs"] = [
        f"data/runtime/{PHASE7_QUALIFIED_SETUP_LEDGER_RUNTIME_ARTIFACT}",
        f"data/runtime/{PHASE7_TEST_MODE_AUTO_APPROVAL_RUNTIME_ARTIFACT}",
        f"data/runtime/{PHASE7_PROOF_ORDER_STAGING_RUNTIME_ARTIFACT}",
    ]
    provenance["execution_evidence_refs"] = [
        f"data/runtime/{PHASE7_GUARDED_ALPACA_SUBMIT_RUNTIME_ARTIFACT}",
        f"data/runtime/{PHASE7_PROOF_LIFECYCLE_RUNTIME_ARTIFACT}",
    ]
    provenance["market_context_refs"] = [
        "Preference/PREF MCP challenge-only context when present",
        "Yahoo Finance supplemental-only context when present",
        "Q-CTRL quantum shadow annotation when present",
    ]
    provenance["governance_refs"] = [
        f"data/runtime/{PHASE7_OVERRIDE_DETECTOR_RUNTIME_ARTIFACT}",
        "docs/qadam-phase-7-demo-proof-implementation-plan.md",
    ]
    provenance["proof_lifecycle_refs"] = [
        f"data/runtime/{PHASE7_PROOF_LIFECYCLE_RUNTIME_ARTIFACT}"
    ]
    return provenance


def _preflight_blockers(
    override: dict[str, Any],
    setup_ledger: dict[str, Any],
    auto_approval: dict[str, Any],
    staging: dict[str, Any],
    guarded_submit: dict[str, Any],
    lifecycle: dict[str, Any],
) -> list[str]:
    blockers: list[str] = []
    if validate_phase7_override_detector(override):
        blockers.append("phase7_override_detector_validation_errors")
    if override.get("override_detector_recorded") is not True:
        blockers.append("phase7_override_detector_not_recorded")
    if override.get("q7_13_signal_funnel_evidence_stage_allowed") is not True:
        blockers.append("q7_13_signal_funnel_evidence_stage_not_allowed")
    if validate_phase7_qualified_setup_ledger(setup_ledger):
        blockers.append("phase7_qualified_setup_ledger_validation_errors")
    if validate_phase7_test_mode_auto_approval_router(auto_approval):
        blockers.append("phase7_auto_approval_validation_errors")
    if validate_phase7_proof_order_staging(staging):
        blockers.append("phase7_proof_order_staging_validation_errors")
    if validate_phase7_guarded_alpaca_paper_submit_path(guarded_submit):
        blockers.append("phase7_guarded_submit_validation_errors")
    if validate_phase7_proof_lifecycle_monitor(lifecycle):
        blockers.append("phase7_lifecycle_validation_errors")
    for field in (
        "phase7_proof_trade_execution_allowed",
        "phase7_proof_credit_allowed",
        "broker_post_allowed",
        "alpaca_post_allowed",
        "live_endpoint_allowed",
        "live_capital_enabled",
        "manual_trade_level_override_allowed",
    ):
        if override.get(field) is not False:
            blockers.append(f"upstream_forbidden_authority_enabled:{field}")
    return sorted(set(blockers))


def _source_contexts() -> dict[str, dict[str, Any]]:
    try:
        from orchestrator.paperops_qctrl_consultation import (
            paperops_qctrl_shadow_annotation_context,
        )

        qctrl_context = paperops_qctrl_shadow_annotation_context()
    except Exception:  # noqa: BLE001 - optional context should never break Q7 evidence.
        qctrl_context = {
            "present": False,
            "role": "quantum_shadow_annotation_only",
            "counts_as_execution_truth": False,
            "counts_as_proof": False,
            "status": "unavailable",
        }
    qctrl_context = {
        "present": False,
        **qctrl_context,
        "role": "quantum_shadow_annotation_only",
        "counts_as_execution_truth": False,
        "counts_as_proof": False,
    }
    return {
        "preference_mcp": {
            "present": False,
            "role": "challenge_only_context",
            "counts_as_source_quorum": False,
            "counts_as_proof": False,
        },
        "yahoo_finance": {
            "present": False,
            "role": "supplemental_market_context_only",
            "counts_as_source_quorum": False,
            "counts_as_proof": False,
        },
        "qctrl_quantum": qctrl_context,
    }


def _optional_source_ref(
    *,
    prefix: str,
    source_id: str,
    passed: bool,
) -> str | None:
    if not passed or not source_id.strip():
        return None
    return f"{prefix}:{source_id}"


def _record_status(missing: list[str], private_priors_only: bool) -> tuple[str, str]:
    if private_priors_only:
        return "blocked", "blocked_private_priors_only"
    if missing:
        return "blocked", "blocked_missing_decision_chain"
    return "read_only", "complete_decision_chain"


def _signal_evidence_record(
    lifecycle_record: dict[str, Any],
    *,
    setup_record: dict[str, Any] | None = None,
    decision_record: dict[str, Any] | None = None,
    staged_order_record: dict[str, Any] | None = None,
    broker_receipt_record: dict[str, Any] | None = None,
    generated_at: str | None = None,
    source_contexts: dict[str, dict[str, Any]] | None = None,
    private_priors_only: bool = False,
) -> dict[str, Any]:
    setup = setup_record or {}
    decision = decision_record or {}
    staged = staged_order_record or {}
    receipt = broker_receipt_record or {}
    generated_at = generated_at or _now()
    setup_id = str(
        lifecycle_record.get("source_setup_record_id")
        or decision.get("setup_record_id")
        or setup.get("setup_record_id")
        or ""
    ).strip()
    decision_id = str(
        lifecycle_record.get("source_auto_approval_decision_id")
        or decision.get("decision_id")
        or ""
    ).strip()
    staged_order_id = str(
        lifecycle_record.get("source_staged_order_artifact_id")
        or staged.get("artifact_id")
        or ""
    ).strip()
    submitted_order_ref = str(
        lifecycle_record.get("submitted_order_ref")
        or receipt.get("submitted_order_ref")
        or ""
    ).strip()
    broker_receipt_ref = str(
        lifecycle_record.get("broker_receipt_ref")
        or receipt.get("broker_receipt_ref")
        or ""
    ).strip()
    source_key = _safe_key(
        str(
            lifecycle_record.get("artifact_id")
            or submitted_order_ref
            or staged_order_id
            or decision_id
            or setup_id
        )
    )
    gate_source = decision or setup
    source_quorum_passed = (
        decision.get("source_quorum_passed") is True
        or setup.get("source_quorum_passed") is True
        or setup.get("canonical_source_quorum_passed") is True
    )
    source_trust_passed = (
        bool(setup_id)
        and (decision.get("source_phase") == "Q7" or setup.get("source_phase") == "Q7")
        and setup.get("supplemental_only") is not True
    )
    akber_filter_passed = _gate_passed(gate_source, "akber_filter")
    signal_integrity_passed = _gate_passed(gate_source, "signal_integrity")
    risk_agent_passed = (
        decision.get("risk_gate_passed") is True
        or _gate_passed(gate_source, "risk_agent_paper_sizing")
    )
    execution_policy_passed = (
        decision.get("execution_policy_gate_passed") is True
        or _gate_passed(gate_source, "execution_policy")
    )
    kill_switch_state_passed = (
        decision.get("kill_switches_clear") is True
        or _gate_passed(gate_source, "kill_switches")
    )
    paper_sizing_passed = (
        staged.get("status") == "staged"
        and _float(staged.get("quantity")) > 0
        and str(staged.get("idempotency_namespace") or "") == "phase7_demo_proof"
    )
    broker_readiness_passed = (
        decision.get("broker_paper_ready") is True
        or receipt.get("status") == "submitted"
    ) and bool(broker_receipt_ref)

    refs = {
        "source_quorum": _optional_source_ref(
            prefix="q7-3-source-quorum",
            source_id=setup_id or decision_id,
            passed=source_quorum_passed,
        ),
        "source_trust": _optional_source_ref(
            prefix="q7-3-source-trust",
            source_id=setup_id or decision_id,
            passed=source_trust_passed,
        ),
        "akber_filter": _optional_source_ref(
            prefix="q7-3-akber-filter",
            source_id=setup_id or decision_id,
            passed=akber_filter_passed,
        ),
        "signal_integrity": _optional_source_ref(
            prefix="q7-3-signal-integrity",
            source_id=setup_id or decision_id,
            passed=signal_integrity_passed,
        ),
        "risk_agent": _optional_source_ref(
            prefix="q7-5-risk-agent",
            source_id=decision_id or setup_id,
            passed=risk_agent_passed,
        ),
        "execution_policy": _optional_source_ref(
            prefix="q7-6-execution-policy",
            source_id=staged_order_id or decision_id,
            passed=execution_policy_passed,
        ),
        "kill_switch_state": _optional_source_ref(
            prefix="q7-5-kill-switch-state",
            source_id=decision_id or setup_id,
            passed=kill_switch_state_passed,
        ),
        "paper_sizing": _optional_source_ref(
            prefix="q7-6-paper-sizing",
            source_id=staged_order_id,
            passed=paper_sizing_passed,
        ),
        "broker_readiness": _optional_source_ref(
            prefix="q7-7-broker-readiness",
            source_id=broker_receipt_ref,
            passed=broker_readiness_passed,
        ),
    }
    missing = [key for key in PHASE7_REQUIRED_SIGNAL_CHAIN_KEYS if not refs.get(key)]
    status, evidence_state = _record_status(missing, private_priors_only)
    complete = not missing and not private_priors_only
    checks = [
        _check("source_quorum_ref_present_or_no_sample", bool(refs["source_quorum"])),
        _check("source_trust_ref_present_or_no_sample", bool(refs["source_trust"])),
        _check("akber_filter_ref_present_or_no_sample", bool(refs["akber_filter"])),
        _check(
            "signal_integrity_ref_present_or_no_sample",
            bool(refs["signal_integrity"]),
        ),
        _check("risk_agent_ref_present_or_no_sample", bool(refs["risk_agent"])),
        _check(
            "execution_policy_ref_present_or_no_sample",
            bool(refs["execution_policy"]),
        ),
        _check(
            "kill_switch_ref_present_or_no_sample",
            bool(refs["kill_switch_state"]),
        ),
        _check("paper_sizing_ref_present_or_no_sample", bool(refs["paper_sizing"])),
        _check(
            "broker_readiness_ref_present_or_no_sample",
            bool(refs["broker_readiness"]),
        ),
        _check("private_priors_not_counted_as_proof", not private_priors_only),
    ]
    failed_checks = [check["name"] for check in checks if check["passed"] is not True]
    return {
        "schema_version": PHASE7_ARTIFACT_SCHEMA_VERSION,
        "signal_funnel_evidence_schema_version": PHASE7_SIGNAL_FUNNEL_EVIDENCE_SCHEMA_VERSION,
        "artifact_type": "source_signal_funnel_evidence_record",
        "artifact_id": f"phase7:q7-13:signal-evidence:{source_key}",
        "phase": "Q7",
        "stage": "Q7-13",
        "status": status,
        "evidence_state": evidence_state,
        "generated_at": generated_at,
        "public_safe": True,
        "source_lifecycle_artifact_id": lifecycle_record.get("artifact_id"),
        "source_lifecycle_state": lifecycle_record.get("lifecycle_state"),
        "source_setup_record_id": setup_id or None,
        "source_auto_approval_decision_id": decision_id or None,
        "source_staged_order_artifact_id": staged_order_id or None,
        "submitted_order_ref": submitted_order_ref or None,
        "broker_receipt_ref": broker_receipt_ref or None,
        "closed_trade_ref": lifecycle_record.get("closed_trade_ref"),
        "required_decision_chain_keys": list(PHASE7_REQUIRED_SIGNAL_CHAIN_KEYS),
        "required_decision_chain_key_count": len(PHASE7_REQUIRED_SIGNAL_CHAIN_KEYS),
        "decision_chain_refs": refs,
        "decision_chain_ref_count": sum(1 for value in refs.values() if value),
        "missing_decision_chain_refs": missing,
        "missing_decision_chain_ref_count": len(missing),
        "complete_decision_chain": complete,
        "decision_chain_required": True,
        "private_priors_only": private_priors_only,
        "private_prior_counts_as_proof": False,
        "private_priors_only_certification_allowed": False,
        "source_quorum_bypass_allowed": False,
        "source_quorum_credit_from_supplemental_only": False,
        "preference_context": deepcopy(
            (source_contexts or _source_contexts())["preference_mcp"]
        ),
        "yahoo_context": deepcopy(
            (source_contexts or _source_contexts())["yahoo_finance"]
        ),
        "quantum_shadow_annotation": deepcopy(
            (source_contexts or _source_contexts())["qctrl_quantum"]
        ),
        "phase7_certification_blocked_by_signal_evidence": not complete,
        "phase7_proof_credit_allowed": False,
        "broker_post_called": False,
        "broker_post_called_count": 0,
        "alpaca_post_called": False,
        "alpaca_post_called_count": 0,
        "external_broker_post_performed": False,
        "broker_write_allowed": False,
        "live_endpoint_allowed": False,
        "live_capital_enabled": False,
        "prediction_market_write_allowed": False,
        "crypto_perps_write_allowed": False,
        "manual_trade_level_override_allowed": False,
        "secret_value_exposed": False,
        "raw_payload_exposed": False,
        "local_path_exposed": False,
        "authorization_header_exposed": False,
        "broker_order_identifier_exposed": False,
        "checks": checks,
        "failed_checks": failed_checks,
        "failed_check_count": len(failed_checks),
    }


def _signal_evidence_records(
    *,
    lifecycle: dict[str, Any],
    setup_ledger: dict[str, Any],
    auto_approval: dict[str, Any],
    staging: dict[str, Any],
    guarded_submit: dict[str, Any],
    stage_recorded: bool,
) -> list[dict[str, Any]]:
    if not stage_recorded:
        return []
    setup_records = [
        *_list(setup_ledger.get("candidate_setup_records")),
        *_list(setup_ledger.get("qualified_setup_records")),
    ]
    setup_by_id = _refs_by_key(setup_records, "setup_record_id")
    decision_by_id = _refs_by_key(
        _list(auto_approval.get("approval_decision_records")),
        "decision_id",
    )
    staged_by_id = _refs_by_key(
        _list(staging.get("staged_order_records")),
        "artifact_id",
        "proof_order_id",
    )
    receipt_by_id = _refs_by_key(
        _list(guarded_submit.get("broker_receipt_records")),
        "artifact_id",
        "submitted_order_ref",
        "broker_receipt_ref",
    )
    generated_at = _now()
    records: list[dict[str, Any]] = []
    for lifecycle_record in _proof_trade_records(lifecycle):
        setup_id = str(lifecycle_record.get("source_setup_record_id") or "")
        decision_id = str(lifecycle_record.get("source_auto_approval_decision_id") or "")
        staged_order_id = str(lifecycle_record.get("source_staged_order_artifact_id") or "")
        broker_receipt_ref = str(lifecycle_record.get("broker_receipt_ref") or "")
        submitted_order_ref = str(lifecycle_record.get("submitted_order_ref") or "")
        records.append(
            _signal_evidence_record(
                lifecycle_record,
                setup_record=setup_by_id.get(setup_id),
                decision_record=decision_by_id.get(decision_id),
                staged_order_record=staged_by_id.get(staged_order_id),
                broker_receipt_record=(
                    receipt_by_id.get(broker_receipt_ref)
                    or receipt_by_id.get(submitted_order_ref)
                ),
                generated_at=generated_at,
            )
        )
    return records


def _signal_evidence_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    complete_count = sum(
        1 for record in records if record.get("complete_decision_chain") is True
    )
    missing_count = sum(
        1 for record in records if _int(record.get("missing_decision_chain_ref_count")) > 0
    )
    private_count = sum(1 for record in records if record.get("private_priors_only") is True)
    preference_count = sum(
        1
        for record in records
        if isinstance(record.get("preference_context"), dict)
        and record["preference_context"].get("present") is True
    )
    yahoo_count = sum(
        1
        for record in records
        if isinstance(record.get("yahoo_context"), dict)
        and record["yahoo_context"].get("present") is True
    )
    quantum_count = sum(
        1
        for record in records
        if isinstance(record.get("quantum_shadow_annotation"), dict)
        and record["quantum_shadow_annotation"].get("present") is True
    )
    return {
        "proof_trade_evidence_record_count": len(records),
        "complete_decision_chain_count": complete_count,
        "missing_decision_chain_count": missing_count,
        "incomplete_decision_chain_count": len(records) - complete_count,
        "private_priors_only_proof_trade_count": private_count,
        "challenge_only_preference_context_count": preference_count,
        "yahoo_supplemental_context_count": yahoo_count,
        "quantum_shadow_annotation_count": quantum_count,
        "phase7_certification_blocked_by_signal_evidence": (
            missing_count > 0 or private_count > 0
        ),
        "private_priors_only_certification_allowed": False,
        "private_prior_counts_as_proof": False,
    }


def build_phase7_signal_funnel_evidence(
    settings: Settings | None = None,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    override = _override_detector(settings)
    setup_ledger = _qualified_setup_ledger(settings)
    auto_approval = _auto_approval(settings)
    staging = _staged_orders(settings)
    guarded_submit = _guarded_submit(settings)
    lifecycle = _lifecycle(settings)
    blockers = _preflight_blockers(
        override,
        setup_ledger,
        auto_approval,
        staging,
        guarded_submit,
        lifecycle,
    )
    stage_recorded = not blockers
    new_proof_trades_frozen = override.get("new_proof_trades_frozen") is True
    evidence_records = _signal_evidence_records(
        lifecycle=lifecycle,
        setup_ledger=setup_ledger,
        auto_approval=auto_approval,
        staging=staging,
        guarded_submit=guarded_submit,
        stage_recorded=stage_recorded,
    )
    summary = _signal_evidence_summary(evidence_records)
    unsafe_counts = phase7_unsafe_counter_defaults()
    unsafe_counts["paper_order_submitted_count"] = _int(
        override.get("paper_order_submitted_count")
    )
    unsafe_counts["proof_trade_created_count"] = _int(
        override.get("source_proof_trade_count")
    )
    unsafe_counts["manual_trade_level_override_count"] = _int(
        override.get("manual_trade_level_override_count")
    )
    authority_defaults = phase7_authority_defaults()
    if stage_recorded:
        authority_defaults["phase7_proof_lifecycle_write_allowed"] = True
        authority_defaults["phase7_postmortem_write_allowed"] = True
        authority_defaults["phase7_performance_evaluation_write_allowed"] = True
        if not new_proof_trades_frozen:
            authority_defaults["phase7_test_mode_auto_approval_allowed"] = True
            authority_defaults["phase7_proof_order_staging_allowed"] = True
            authority_defaults["phase7_proof_trade_submission_allowed"] = True
    status = "ready_no_proof_trades"
    stage_status = "signal_funnel_evidence_ready_no_proof_trades"
    if evidence_records:
        status = "signal_funnel_evidence_recorded"
        stage_status = "signal_funnel_evidence_recorded"
    if summary["phase7_certification_blocked_by_signal_evidence"]:
        status = "blocked_missing_signal_evidence"
        stage_status = "signal_funnel_evidence_certification_blocked"
    if not stage_recorded:
        status = "blocked"
        stage_status = "signal_funnel_evidence_blocked"
    checks = [
        _check("q7_12_override_detector_valid", not validate_phase7_override_detector(override)),
        _check("q7_13_signal_evidence_stage_allowed", stage_recorded),
        _check(
            "source_qualified_setup_ledger_valid",
            not validate_phase7_qualified_setup_ledger(setup_ledger),
        ),
        _check(
            "source_auto_approval_valid",
            not validate_phase7_test_mode_auto_approval_router(auto_approval),
        ),
        _check(
            "source_staged_order_gate_valid",
            not validate_phase7_proof_order_staging(staging),
        ),
        _check(
            "source_guarded_submit_valid",
            not validate_phase7_guarded_alpaca_paper_submit_path(guarded_submit),
        ),
        _check(
            "source_lifecycle_valid",
            not validate_phase7_proof_lifecycle_monitor(lifecycle),
        ),
        _check(
            "source_quorum_ref_present_or_no_sample",
            not evidence_records
            or all(record.get("decision_chain_refs", {}).get("source_quorum") for record in evidence_records),
        ),
        _check(
            "source_trust_ref_present_or_no_sample",
            not evidence_records
            or all(record.get("decision_chain_refs", {}).get("source_trust") for record in evidence_records),
        ),
        _check(
            "akber_filter_ref_present_or_no_sample",
            not evidence_records
            or all(record.get("decision_chain_refs", {}).get("akber_filter") for record in evidence_records),
        ),
        _check(
            "signal_integrity_ref_present_or_no_sample",
            not evidence_records
            or all(record.get("decision_chain_refs", {}).get("signal_integrity") for record in evidence_records),
        ),
        _check(
            "risk_agent_ref_present_or_no_sample",
            not evidence_records
            or all(record.get("decision_chain_refs", {}).get("risk_agent") for record in evidence_records),
        ),
        _check(
            "execution_policy_ref_present_or_no_sample",
            not evidence_records
            or all(record.get("decision_chain_refs", {}).get("execution_policy") for record in evidence_records),
        ),
        _check(
            "kill_switch_ref_present_or_no_sample",
            not evidence_records
            or all(record.get("decision_chain_refs", {}).get("kill_switch_state") for record in evidence_records),
        ),
        _check(
            "paper_sizing_ref_present_or_no_sample",
            not evidence_records
            or all(record.get("decision_chain_refs", {}).get("paper_sizing") for record in evidence_records),
        ),
        _check(
            "broker_readiness_ref_present_or_no_sample",
            not evidence_records
            or all(record.get("decision_chain_refs", {}).get("broker_readiness") for record in evidence_records),
        ),
        _check("private_priors_not_counted_as_proof", summary["private_priors_only_proof_trade_count"] == 0),
        _check("preference_context_challenge_only", True),
        _check("yahoo_context_supplemental_only", True),
        _check("quantum_context_shadow_only", True),
        _check("certification_blocks_incomplete_chain", True),
        _check("no_certification_authority", True),
        _check("no_proof_credit", True),
        _check("no_broker_post", True),
        _check("no_alpaca_post", True),
        _check("no_live_endpoint", True),
        _check("no_live_capital", True),
        _check("manual_override_disabled", True),
        _check("market_writes_disabled", True),
        _check("public_safe", True),
    ]
    failed_checks = [check["name"] for check in checks if check["passed"] is not True]
    if failed_checks and stage_recorded and evidence_records:
        blockers = sorted(set([*blockers, *failed_checks]))
        stage_recorded = False
        status = "blocked"
        stage_status = "signal_funnel_evidence_blocked"
    artifact = {
        "schema_version": PHASE7_SIGNAL_FUNNEL_EVIDENCE_SCHEMA_VERSION,
        "phase7_artifact_schema_version": PHASE7_ARTIFACT_SCHEMA_VERSION,
        "artifact_type": "phase7_signal_funnel_evidence",
        "artifact_id": "phase7:q7-13:signal-funnel-evidence",
        "phase": "Q7",
        "stage": "Q7-13",
        "status": status,
        "stage_status": stage_status,
        "generated_at": _now(),
        "public_safe": True,
        "recorded": False,
        "event_log_required": True,
        "event_log_written": False,
        "event_log_path": None,
        "event_log_event_count": 0,
        "event_log_correlation_id": None,
        "event_log_created_at": None,
        "runtime_artifact_path": None,
        "history_log_path": None,
        "authority_ledger": _authority_ledger(
            stage_recorded=stage_recorded,
            new_proof_trades_frozen=new_proof_trades_frozen,
        ),
        "proof_contract": phase7_proof_contract(),
        "source_posture": phase7_source_posture(),
        "provenance": _provenance(),
        "signal_evidence_policy": _signal_evidence_policy(),
        "signal_evidence_records": evidence_records,
        "boundary": PHASE7_SIGNAL_FUNNEL_BOUNDARY,
        **authority_defaults,
        **unsafe_counts,
        "source_override_artifact_id": override.get("artifact_id"),
        "source_override_status": override.get("status"),
        "source_override_stage_status": override.get("stage_status"),
        "source_override_sample_contaminated": (
            override.get("sample_contaminated") is True
        ),
        "source_override_clean_sample": override.get("clean_sample") is True,
        "source_override_new_proof_trades_frozen": new_proof_trades_frozen,
        "source_override_manual_trade_level_override_count": _int(
            override.get("manual_trade_level_override_count")
        ),
        "source_setup_ledger_artifact_id": setup_ledger.get("artifact_id"),
        "source_setup_ledger_status": setup_ledger.get("status"),
        "source_auto_approval_artifact_id": auto_approval.get("artifact_id"),
        "source_auto_approval_status": auto_approval.get("status"),
        "source_staged_order_artifact_id": staging.get("artifact_id"),
        "source_staged_order_status": staging.get("status"),
        "source_guarded_submit_artifact_id": guarded_submit.get("artifact_id"),
        "source_guarded_submit_status": guarded_submit.get("status"),
        "source_lifecycle_artifact_id": lifecycle.get("artifact_id"),
        "source_lifecycle_status": lifecycle.get("status"),
        "source_lifecycle_stage_status": lifecycle.get("stage_status"),
        "source_lifecycle_event_count": _int(lifecycle.get("lifecycle_event_count")),
        "source_proof_trade_count": _int(override.get("source_proof_trade_count")),
        "q7_13_signal_funnel_evidence_stage_allowed": (
            override.get("q7_13_signal_funnel_evidence_stage_allowed") is True
        ),
        "q7_14_maturity_tracker_stage_allowed": stage_recorded,
        "signal_funnel_evidence_recorded": stage_recorded,
        "signal_funnel_evidence_write_allowed": stage_recorded,
        "evidence_state": status,
        "decision_chain_required": True,
        "private_prior_counts_as_proof": False,
        "required_decision_chain_keys": list(PHASE7_REQUIRED_SIGNAL_CHAIN_KEYS),
        "required_decision_chain_key_count": len(PHASE7_REQUIRED_SIGNAL_CHAIN_KEYS),
        "source_quorum_bypass_allowed": False,
        "supplemental_source_bypass_allowed": False,
        "preference_mcp_source_quorum_credit_allowed": False,
        "phase7_certification_blocked_by_override": (
            override.get("phase7_certification_blocked_by_override") is True
        ),
        "phase7_certification_blocked_by_contaminated_sample": (
            override.get("phase7_certification_blocked_by_contaminated_sample") is True
        ),
        "new_proof_trades_frozen": stage_recorded and new_proof_trades_frozen,
        "new_proof_order_staging_allowed": stage_recorded
        and override.get("new_proof_order_staging_allowed") is True,
        "new_proof_trade_submission_allowed": stage_recorded
        and override.get("new_proof_trade_submission_allowed") is True,
        "existing_lifecycle_closeout_allowed": stage_recorded,
        **summary,
        "phase5_test_trades_count_for_phase7": False,
        "q6_deferred_learning_counts_as_proof": False,
        "paper_account_starting_gbp": PHASE7_PAPER_ACCOUNT_STARTING_GBP,
        "max_drawdown_fraction": PHASE7_MAX_DRAWDOWN_FRACTION,
        "mature_closed_trade_benchmark": PHASE7_MATURE_CLOSED_TRADE_BENCHMARK,
        "statistical_immaturity_allowed": True,
        "broker_post_called_count": 0,
        "alpaca_post_called_count": 0,
        "external_broker_post_performed_count": 0,
        "proof_trade_credit_count": 0,
        "phase7_proof_credit_allowed_count": 0,
        "live_capital_enabled_count": 0,
        "unsafe_write_counter_total": _int(unsafe_counts["manual_trade_level_override_count"]),
        "checks": checks,
        "failed_checks": failed_checks,
        "failed_check_count": len(failed_checks),
        "blockers": blockers,
        "blocker_count": len(blockers),
        "recommended_next_stage": "Q7-14 100-Trade Maturity Tracker",
    }
    artifact["validation_errors"] = validate_phase7_signal_funnel_evidence(artifact)
    if artifact["validation_errors"]:
        artifact["status"] = "error"
        artifact["stage_status"] = "signal_funnel_evidence_validation_error"
    return artifact


def _authority_errors(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    stage_recorded = artifact.get("signal_funnel_evidence_recorded") is True
    frozen = artifact.get("new_proof_trades_frozen") is True
    ledger = artifact.get("authority_ledger", {})
    if not isinstance(ledger, dict):
        return ["phase7_signal_evidence_authority_ledger_missing"]
    if ledger.get("stage") != "Q7-13":
        errors.append("phase7_signal_evidence_authority_stage_mismatch")
    if ledger.get("authority_field_count") != len(PHASE7_AUTHORITY_FLAGS):
        errors.append("phase7_signal_evidence_authority_count_mismatch")
    expected_true = {
        "phase7_proof_lifecycle_write_allowed",
        "phase7_postmortem_write_allowed",
        "phase7_performance_evaluation_write_allowed",
    }
    if stage_recorded and not frozen:
        expected_true.update(
            {
                "phase7_test_mode_auto_approval_allowed",
                "phase7_proof_order_staging_allowed",
                "phase7_proof_trade_submission_allowed",
            }
        )
    expected_grants = len(expected_true) if stage_recorded else 0
    if ledger.get("explicit_authority_grant_count") != expected_grants:
        errors.append("phase7_signal_evidence_explicit_authority_grant_count_invalid")
    for field in PHASE7_AUTHORITY_FLAGS:
        expected = stage_recorded and field in expected_true
        if artifact.get(field) is not expected:
            errors.append(f"phase7_signal_evidence_authority_invalid:{field}")
        if ledger.get(field) is not expected:
            errors.append(f"phase7_signal_evidence_ledger_authority_invalid:{field}")
    if ledger.get("signal_funnel_evidence_write_allowed") is not stage_recorded:
        errors.append("phase7_signal_evidence_write_ledger_mismatch")
    if ledger.get("q7_14_maturity_tracker_stage_allowed") is not stage_recorded:
        errors.append("phase7_signal_evidence_q7_14_ledger_mismatch")
    if ledger.get("new_proof_trades_frozen") is not frozen:
        errors.append("phase7_signal_evidence_freeze_ledger_mismatch")
    for field in PHASE7_UNSAFE_COUNT_FIELDS:
        value = _int(artifact.get(field))
        if field == "paper_order_submitted_count":
            if value != _int(artifact.get("paper_order_submitted_count")):
                errors.append(f"phase7_signal_evidence_allowed_count_mismatch:{field}")
            continue
        if field == "proof_trade_created_count":
            if value != _int(artifact.get("source_proof_trade_count")):
                errors.append(f"phase7_signal_evidence_allowed_count_mismatch:{field}")
            continue
        if field == "manual_trade_level_override_count":
            if value != _int(artifact.get("source_override_manual_trade_level_override_count")):
                errors.append(f"phase7_signal_evidence_allowed_count_mismatch:{field}")
            continue
        if value != 0:
            errors.append(f"phase7_signal_evidence_unsafe_count_nonzero:{field}")
    if artifact.get("unsafe_write_counter_total") != _int(
        artifact.get("manual_trade_level_override_count")
    ):
        errors.append("phase7_signal_evidence_unsafe_total_mismatch")
    return errors


def _policy_errors(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    policy = artifact.get("signal_evidence_policy", {})
    if not isinstance(policy, dict):
        return ["phase7_signal_evidence_policy_missing"]
    for field in (
        "complete_decision_chain_required_for_certification",
        "canonical_source_quorum_required",
        "source_trust_required",
        "akber_filter_required",
        "signal_integrity_required",
        "risk_agent_required",
        "execution_policy_required",
        "kill_switch_state_required",
        "paper_sizing_required",
        "broker_readiness_required",
    ):
        if policy.get(field) is not True:
            errors.append(f"phase7_signal_evidence_policy_missing_true:{field}")
    for field in (
        "private_priors_only_certification_allowed",
        "private_prior_counts_as_proof",
        "source_quorum_bypass_allowed",
        "preference_mcp_counts_as_source_quorum",
        "preference_mcp_counts_as_proof",
        "yahoo_finance_counts_as_source_quorum",
        "yahoo_finance_counts_as_proof",
        "qctrl_counts_as_execution_truth",
        "qctrl_counts_as_proof",
        "certification_authority_allowed",
        "proof_credit_allowed",
        "broker_post_allowed",
        "alpaca_post_allowed",
        "live_endpoint_allowed",
        "prediction_market_write_allowed",
        "crypto_perps_write_allowed",
        "policy_mutation_allowed",
        "strategy_mutation_allowed",
        "manual_trade_level_override_allowed",
        "live_capital_enabled",
    ):
        if policy.get(field) is not False:
            errors.append(f"phase7_signal_evidence_policy_forbidden:{field}")
    if tuple(policy.get("required_decision_chain_keys", ())) != (
        PHASE7_REQUIRED_SIGNAL_CHAIN_KEYS
    ):
        errors.append("phase7_signal_evidence_policy_required_chain_invalid")
    if policy.get("preference_mcp_role") != "challenge_only_context":
        errors.append("phase7_signal_evidence_policy_preference_role_invalid")
    if policy.get("yahoo_finance_role") != "supplemental_market_context_only":
        errors.append("phase7_signal_evidence_policy_yahoo_role_invalid")
    if policy.get("qctrl_role") != "quantum_shadow_annotation_only":
        errors.append("phase7_signal_evidence_policy_qctrl_role_invalid")
    return errors


def _context_errors(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    preference = record.get("preference_context", {})
    yahoo = record.get("yahoo_context", {})
    quantum = record.get("quantum_shadow_annotation", {})
    if not isinstance(preference, dict):
        errors.append("phase7_signal_evidence_preference_context_missing")
        preference = {}
    if not isinstance(yahoo, dict):
        errors.append("phase7_signal_evidence_yahoo_context_missing")
        yahoo = {}
    if not isinstance(quantum, dict):
        errors.append("phase7_signal_evidence_quantum_context_missing")
        quantum = {}
    if preference.get("role") != "challenge_only_context":
        errors.append("phase7_signal_evidence_preference_role_invalid")
    if preference.get("counts_as_source_quorum") is not False:
        errors.append("phase7_signal_evidence_preference_quorum_credit_allowed")
    if preference.get("counts_as_proof") is not False:
        errors.append("phase7_signal_evidence_preference_counts_as_proof")
    if yahoo.get("role") != "supplemental_market_context_only":
        errors.append("phase7_signal_evidence_yahoo_role_invalid")
    if yahoo.get("counts_as_source_quorum") is not False:
        errors.append("phase7_signal_evidence_yahoo_quorum_credit_allowed")
    if yahoo.get("counts_as_proof") is not False:
        errors.append("phase7_signal_evidence_yahoo_counts_as_proof")
    if quantum.get("role") != "quantum_shadow_annotation_only":
        errors.append("phase7_signal_evidence_quantum_role_invalid")
    if quantum.get("counts_as_execution_truth") is not False:
        errors.append("phase7_signal_evidence_quantum_execution_truth_allowed")
    if quantum.get("counts_as_proof") is not False:
        errors.append("phase7_signal_evidence_quantum_counts_as_proof")
    return errors


def _evidence_record_errors(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if record.get("artifact_type") != "source_signal_funnel_evidence_record":
        errors.append("phase7_signal_evidence_record_type_invalid")
    if record.get("phase") != "Q7" or record.get("stage") != "Q7-13":
        errors.append("phase7_signal_evidence_record_phase_stage_invalid")
    if tuple(record.get("required_decision_chain_keys", ())) != (
        PHASE7_REQUIRED_SIGNAL_CHAIN_KEYS
    ):
        errors.append("phase7_signal_evidence_record_required_chain_invalid")
    refs = record.get("decision_chain_refs", {})
    if not isinstance(refs, dict):
        errors.append("phase7_signal_evidence_record_refs_not_dict")
        refs = {}
    missing = [key for key in PHASE7_REQUIRED_SIGNAL_CHAIN_KEYS if not refs.get(key)]
    if record.get("missing_decision_chain_refs") != missing:
        errors.append("phase7_signal_evidence_record_missing_refs_mismatch")
    if record.get("missing_decision_chain_ref_count") != len(missing):
        errors.append("phase7_signal_evidence_record_missing_ref_count_mismatch")
    if record.get("decision_chain_ref_count") != sum(1 for value in refs.values() if value):
        errors.append("phase7_signal_evidence_record_ref_count_mismatch")
    complete = not missing and record.get("private_priors_only") is not True
    if record.get("complete_decision_chain") is not complete:
        errors.append("phase7_signal_evidence_record_complete_chain_mismatch")
    if record.get("complete_decision_chain") is True:
        if record.get("status") != "read_only":
            errors.append("phase7_signal_evidence_record_status_invalid")
        if record.get("evidence_state") != "complete_decision_chain":
            errors.append("phase7_signal_evidence_record_state_invalid")
        for field in (
            "source_lifecycle_artifact_id",
            "source_setup_record_id",
            "source_auto_approval_decision_id",
            "source_staged_order_artifact_id",
            "submitted_order_ref",
            "broker_receipt_ref",
        ):
            if not str(record.get(field) or "").strip():
                errors.append(f"phase7_signal_evidence_record_missing:{field}")
    else:
        if record.get("status") != "blocked":
            errors.append("phase7_signal_evidence_incomplete_record_status_invalid")
        if record.get("phase7_certification_blocked_by_signal_evidence") is not True:
            errors.append("phase7_signal_evidence_incomplete_not_blocking")
    if record.get("private_priors_only") is True:
        if record.get("evidence_state") != "blocked_private_priors_only":
            errors.append("phase7_signal_evidence_private_prior_state_invalid")
        if record.get("private_priors_only_certification_allowed") is not False:
            errors.append("phase7_signal_evidence_private_prior_cert_allowed")
    if record.get("decision_chain_required") is not True:
        errors.append("phase7_signal_evidence_record_chain_not_required")
    for field in (
        "private_prior_counts_as_proof",
        "private_priors_only_certification_allowed",
        "source_quorum_bypass_allowed",
        "source_quorum_credit_from_supplemental_only",
        "phase7_proof_credit_allowed",
        "broker_post_called",
        "alpaca_post_called",
        "external_broker_post_performed",
        "broker_write_allowed",
        "live_endpoint_allowed",
        "live_capital_enabled",
        "prediction_market_write_allowed",
        "crypto_perps_write_allowed",
        "manual_trade_level_override_allowed",
        "secret_value_exposed",
        "raw_payload_exposed",
        "local_path_exposed",
        "authorization_header_exposed",
        "broker_order_identifier_exposed",
    ):
        if record.get(field) is not False:
            errors.append(f"phase7_signal_evidence_record_forbidden:{field}")
    for count_field in ("broker_post_called_count", "alpaca_post_called_count"):
        if _int(record.get(count_field)) != 0:
            errors.append(f"phase7_signal_evidence_record_count_nonzero:{count_field}")
    checks = record.get("checks", [])
    if not isinstance(checks, list):
        errors.append("phase7_signal_evidence_record_checks_not_list")
        checks = []
    failed_checks = [
        str(check.get("name"))
        for check in checks
        if isinstance(check, dict) and check.get("passed") is not True
    ]
    if record.get("failed_checks") != failed_checks:
        errors.append("phase7_signal_evidence_record_failed_checks_mismatch")
    if record.get("failed_check_count") != len(failed_checks):
        errors.append("phase7_signal_evidence_record_failed_count_mismatch")
    if record.get("complete_decision_chain") is True and failed_checks:
        errors.append("phase7_signal_evidence_complete_record_failed_checks")
    errors.extend(_context_errors(record))
    return errors


def validate_phase7_signal_funnel_evidence(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required_fields = {
        "schema_version",
        "phase7_artifact_schema_version",
        "artifact_type",
        "artifact_id",
        "phase",
        "stage",
        "status",
        "stage_status",
        "generated_at",
        "public_safe",
        "event_log_required",
        "event_log_written",
        "authority_ledger",
        "proof_contract",
        "source_posture",
        "provenance",
        "signal_evidence_policy",
        "signal_evidence_records",
        "boundary",
        "source_override_status",
        "source_override_sample_contaminated",
        "source_override_clean_sample",
        "source_override_new_proof_trades_frozen",
        "source_override_manual_trade_level_override_count",
        "source_setup_ledger_status",
        "source_auto_approval_status",
        "source_staged_order_status",
        "source_guarded_submit_status",
        "source_lifecycle_status",
        "source_lifecycle_stage_status",
        "source_lifecycle_event_count",
        "source_proof_trade_count",
        "q7_13_signal_funnel_evidence_stage_allowed",
        "q7_14_maturity_tracker_stage_allowed",
        "signal_funnel_evidence_recorded",
        "signal_funnel_evidence_write_allowed",
        "evidence_state",
        "decision_chain_required",
        "private_prior_counts_as_proof",
        "required_decision_chain_keys",
        "required_decision_chain_key_count",
        "source_quorum_bypass_allowed",
        "supplemental_source_bypass_allowed",
        "preference_mcp_source_quorum_credit_allowed",
        "proof_trade_evidence_record_count",
        "complete_decision_chain_count",
        "missing_decision_chain_count",
        "incomplete_decision_chain_count",
        "private_priors_only_proof_trade_count",
        "challenge_only_preference_context_count",
        "yahoo_supplemental_context_count",
        "quantum_shadow_annotation_count",
        "phase7_certification_blocked_by_signal_evidence",
        "private_priors_only_certification_allowed",
        "phase7_certification_blocked_by_override",
        "phase7_certification_blocked_by_contaminated_sample",
        "new_proof_trades_frozen",
        "new_proof_order_staging_allowed",
        "new_proof_trade_submission_allowed",
        "existing_lifecycle_closeout_allowed",
        "phase5_test_trades_count_for_phase7",
        "q6_deferred_learning_counts_as_proof",
        "paper_account_starting_gbp",
        "max_drawdown_fraction",
        "mature_closed_trade_benchmark",
        "statistical_immaturity_allowed",
        "paper_order_submitted_count",
        "proof_trade_created_count",
        "broker_post_called_count",
        "alpaca_post_called_count",
        "external_broker_post_performed_count",
        "proof_trade_credit_count",
        "phase7_proof_credit_allowed_count",
        "live_capital_enabled_count",
        "manual_trade_level_override_count",
        "unsafe_write_counter_total",
        "checks",
        "failed_checks",
        "failed_check_count",
        "blockers",
        "blocker_count",
        "recommended_next_stage",
    }
    missing = sorted(required_fields - set(artifact))
    if missing:
        errors.append("phase7_signal_evidence_missing_fields:" + ",".join(missing))
    if artifact.get("schema_version") != PHASE7_SIGNAL_FUNNEL_EVIDENCE_SCHEMA_VERSION:
        errors.append("phase7_signal_evidence_schema_version_mismatch")
    if artifact.get("phase7_artifact_schema_version") != PHASE7_ARTIFACT_SCHEMA_VERSION:
        errors.append("phase7_signal_evidence_artifact_schema_version_mismatch")
    if artifact.get("artifact_type") != "phase7_signal_funnel_evidence":
        errors.append("phase7_signal_evidence_artifact_type_mismatch")
    if artifact.get("phase") != "Q7" or artifact.get("stage") != "Q7-13":
        errors.append("phase7_signal_evidence_phase_stage_mismatch")
    if artifact.get("public_safe") is not True:
        errors.append("phase7_signal_evidence_not_public_safe")
    if artifact.get("event_log_required") is not True:
        errors.append("phase7_signal_evidence_event_log_not_required")
    blockers = artifact.get("blockers", [])
    if not isinstance(blockers, list):
        errors.append("phase7_signal_evidence_blockers_not_list")
        blockers = []
    if artifact.get("blocker_count") != len(blockers):
        errors.append("phase7_signal_evidence_blocker_count_mismatch")
    checks = artifact.get("checks", [])
    if not isinstance(checks, list):
        errors.append("phase7_signal_evidence_checks_not_list")
        checks = []
    failed_checks = [
        str(check.get("name"))
        for check in checks
        if isinstance(check, dict) and check.get("passed") is not True
    ]
    if artifact.get("failed_checks") != failed_checks:
        errors.append("phase7_signal_evidence_failed_checks_mismatch")
    if artifact.get("failed_check_count") != len(failed_checks):
        errors.append("phase7_signal_evidence_failed_check_count_mismatch")
    if tuple(check.get("name") for check in checks if isinstance(check, dict)) != (
        PHASE7_SIGNAL_FUNNEL_REQUIRED_CHECKS
    ):
        errors.append("phase7_signal_evidence_required_checks_invalid")

    stage_recorded = artifact.get("signal_funnel_evidence_recorded") is True
    if stage_recorded:
        if artifact.get("status") not in {
            "ready_no_proof_trades",
            "signal_funnel_evidence_recorded",
            "blocked_missing_signal_evidence",
        }:
            errors.append("phase7_signal_evidence_status_invalid")
        if artifact.get("stage_status") not in {
            "signal_funnel_evidence_ready_no_proof_trades",
            "signal_funnel_evidence_recorded",
            "signal_funnel_evidence_certification_blocked",
        }:
            errors.append("phase7_signal_evidence_stage_status_invalid")
        if blockers:
            errors.append("phase7_signal_evidence_recorded_with_blockers")
        if artifact.get("q7_14_maturity_tracker_stage_allowed") is not True:
            errors.append("q7_14_maturity_tracker_not_allowed")
        if artifact.get("signal_funnel_evidence_write_allowed") is not True:
            errors.append("phase7_signal_evidence_write_not_allowed")
    else:
        if artifact.get("status") not in {"blocked", "error"}:
            errors.append("phase7_signal_evidence_blocked_status_invalid")
        if not blockers and artifact.get("status") != "error":
            errors.append("phase7_signal_evidence_blocked_without_blockers")
        if artifact.get("q7_14_maturity_tracker_stage_allowed") is not False:
            errors.append("q7_14_stage_allowed_while_blocked")
        if artifact.get("signal_funnel_evidence_write_allowed") is not False:
            errors.append("phase7_signal_evidence_write_allowed_while_blocked")
    if artifact.get("q7_13_signal_funnel_evidence_stage_allowed") is not True:
        errors.append("q7_13_signal_funnel_evidence_not_allowed")
    if tuple(artifact.get("required_decision_chain_keys", ())) != (
        PHASE7_REQUIRED_SIGNAL_CHAIN_KEYS
    ):
        errors.append("phase7_signal_evidence_required_chain_invalid")
    if artifact.get("required_decision_chain_key_count") != len(
        PHASE7_REQUIRED_SIGNAL_CHAIN_KEYS
    ):
        errors.append("phase7_signal_evidence_required_chain_count_invalid")

    errors.extend(_authority_errors(artifact))
    errors.extend(_policy_errors(artifact))
    records = artifact.get("signal_evidence_records", [])
    if not isinstance(records, list):
        errors.append("phase7_signal_evidence_records_not_list")
        records = []
    dict_records = [record for record in records if isinstance(record, dict)]
    for record in records:
        if isinstance(record, dict):
            errors.extend(_evidence_record_errors(record))
        else:
            errors.append("phase7_signal_evidence_record_invalid")
    summary = _signal_evidence_summary(dict_records)
    for key, value in summary.items():
        if artifact.get(key) != value:
            errors.append(f"phase7_signal_evidence_summary_mismatch:{key}")
    if artifact.get("source_proof_trade_count") != len(dict_records):
        errors.append("phase7_signal_evidence_source_trade_count_mismatch")
    if artifact.get("source_lifecycle_event_count") < len(dict_records):
        errors.append("phase7_signal_evidence_lifecycle_count_less_than_records")
    if artifact.get("complete_decision_chain_count") > artifact.get(
        "proof_trade_evidence_record_count",
        0,
    ):
        errors.append("phase7_signal_evidence_complete_count_invalid")
    if artifact.get("phase7_certification_blocked_by_signal_evidence") is True:
        if (
            artifact.get("missing_decision_chain_count") == 0
            and artifact.get("private_priors_only_proof_trade_count") == 0
        ):
            errors.append("phase7_signal_evidence_blocked_without_signal_reason")
    if artifact.get("private_priors_only_proof_trade_count") and (
        artifact.get("private_priors_only_certification_allowed") is not False
    ):
        errors.append("phase7_signal_evidence_private_prior_certification_allowed")
    for field in (
        "decision_chain_required",
        "statistical_immaturity_allowed",
    ):
        if artifact.get(field) is not True:
            errors.append(f"phase7_signal_evidence_missing_true:{field}")
    for field in (
        "private_prior_counts_as_proof",
        "private_priors_only_certification_allowed",
        "source_quorum_bypass_allowed",
        "supplemental_source_bypass_allowed",
        "preference_mcp_source_quorum_credit_allowed",
        "phase5_test_trades_count_for_phase7",
        "q6_deferred_learning_counts_as_proof",
        "phase7_proof_trade_execution_allowed",
        "phase7_proof_credit_allowed",
        "broker_post_allowed",
        "alpaca_post_allowed",
        "broker_write_allowed",
        "prediction_market_write_allowed",
        "crypto_perps_write_allowed",
        "live_endpoint_allowed",
        "live_capital_enabled",
        "manual_trade_level_override_allowed",
    ):
        if artifact.get(field) is not False:
            errors.append(f"phase7_signal_evidence_forbidden:{field}")
    for count_field in (
        "broker_post_called_count",
        "alpaca_post_called_count",
        "external_broker_post_performed_count",
        "proof_trade_credit_count",
        "phase7_proof_credit_allowed_count",
        "live_capital_enabled_count",
        "broker_write_allowed_count",
        "prediction_market_write_allowed_count",
        "crypto_perps_write_allowed_count",
        "live_endpoint_allowed_count",
        "phase5_test_trade_reuse_count",
        "ui_inferred_readiness_count",
    ):
        if _int(artifact.get(count_field)) != 0:
            errors.append(f"phase7_signal_evidence_count_nonzero:{count_field}")
    if float(artifact.get("paper_account_starting_gbp", 0.0) or 0.0) != (
        PHASE7_PAPER_ACCOUNT_STARTING_GBP
    ):
        errors.append("phase7_signal_evidence_starting_equity_mismatch")
    if float(artifact.get("max_drawdown_fraction", 0.0) or 0.0) != (
        PHASE7_MAX_DRAWDOWN_FRACTION
    ):
        errors.append("phase7_signal_evidence_drawdown_cap_mismatch")
    if artifact.get("mature_closed_trade_benchmark") != (
        PHASE7_MATURE_CLOSED_TRADE_BENCHMARK
    ):
        errors.append("phase7_signal_evidence_mature_benchmark_mismatch")
    proof_contract = artifact.get("proof_contract", {})
    if not isinstance(proof_contract, dict):
        errors.append("phase7_signal_evidence_proof_contract_missing")
        proof_contract = {}
    if proof_contract.get("harness_day_count") != PHASE7_HARNESS_DAY_COUNT:
        errors.append("phase7_signal_evidence_proof_contract_day_count_mismatch")
    if proof_contract.get("phase5_test_trade_reuse_allowed") is not False:
        errors.append("phase7_signal_evidence_proof_contract_phase5_reuse_allowed")
    source_posture = artifact.get("source_posture", {})
    if not isinstance(source_posture, dict):
        errors.append("phase7_signal_evidence_source_posture_missing")
        source_posture = {}
    if source_posture.get("preference_mcp_source_quorum_credit_allowed") is not False:
        errors.append("phase7_signal_evidence_preference_quorum_credit_allowed")
    if source_posture.get("qctrl_role") != "shadow_annotation_only":
        errors.append("phase7_signal_evidence_qctrl_role_invalid")
    provenance = artifact.get("provenance", {})
    if not isinstance(provenance, dict):
        errors.append("phase7_signal_evidence_provenance_missing")
        provenance = {}
    for ref in provenance.get("source_refs", []) or []:
        ref_text = str(ref)
        lowered = ref_text.lower()
        if ref_text.startswith("/") or ref_text.startswith("~"):
            errors.append("phase7_signal_evidence_provenance_local_path_leak")
        if "api_key" in lowered or "secret" in lowered or "token" in lowered:
            errors.append("phase7_signal_evidence_provenance_secret_ref_leak")
    for field in (
        "raw_secret_exposed",
        "raw_payload_exposed",
        "local_path_exposed",
        "broker_identifier_exposed",
    ):
        if provenance.get(field) is not False:
            errors.append(f"phase7_signal_evidence_provenance_exposure_enabled:{field}")
    boundary = str(artifact.get("boundary") or "")
    for phrase in (
        "records Phase 7 source and signal funnel evidence only",
        "Akber filter",
        "Signal Integrity",
        "challenge-only Preference/PREF context",
        "Yahoo supplemental",
        "quantum shadow annotations",
        "cannot infer proof from private priors alone",
        "cannot grant Phase 7 proof credit",
        "cannot enable live capital",
    ):
        if phrase not in boundary:
            errors.append("phase7_signal_evidence_boundary_weak")
            break
    if artifact.get("event_log_written") is True:
        if not str(artifact.get("event_log_path") or "").strip():
            errors.append("phase7_signal_evidence_event_log_path_missing")
        if artifact.get("event_log_event_count") < 1:
            errors.append("phase7_signal_evidence_event_log_count_invalid")
    return sorted(set(errors))


def attach_phase7_signal_funnel_evidence_event_log(
    artifact: dict[str, Any],
    *,
    event_log: EventLog | None = None,
    event_log_path: str | Path | None = None,
    settings: Settings | None = None,
) -> tuple[dict[str, Any], list[EventLogEntry]]:
    output = deepcopy(artifact)
    log_path = Path(
        event_log_path or (_runtime_dir(settings) / PHASE7_SIGNAL_FUNNEL_EVIDENCE_EVENT_LOG)
    )
    log = event_log or EventLog(log_path, echo=False)
    entry = log.write(
        PHASE7_SIGNAL_FUNNEL_EVIDENCE_EVENT_TYPE,
        PHASE7_SIGNAL_FUNNEL_EVIDENCE_COMPONENT,
        {
            "artifact_id": output.get("artifact_id"),
            "status": output.get("status"),
            "stage_status": output.get("stage_status"),
            "proof_trade_evidence_record_count": output.get(
                "proof_trade_evidence_record_count"
            ),
            "complete_decision_chain_count": output.get(
                "complete_decision_chain_count"
            ),
            "missing_decision_chain_count": output.get(
                "missing_decision_chain_count"
            ),
            "private_priors_only_proof_trade_count": output.get(
                "private_priors_only_proof_trade_count"
            ),
            "phase7_certification_blocked_by_signal_evidence": output.get(
                "phase7_certification_blocked_by_signal_evidence"
            ),
            "phase7_proof_credit_allowed": output.get("phase7_proof_credit_allowed"),
            "live_capital_enabled": output.get("live_capital_enabled"),
            "unsafe_write_counter_total": output.get("unsafe_write_counter_total"),
            "recommended_next_stage": output.get("recommended_next_stage"),
            "boundary": output.get("boundary"),
        },
    )
    output["recorded"] = True
    output["event_log_written"] = True
    output["event_log_path"] = str(log.path)
    output["event_log_event_count"] = 1
    output["event_log_correlation_id"] = entry.correlation_id
    output["event_log_created_at"] = entry.created_at
    output["validation_errors"] = validate_phase7_signal_funnel_evidence(output)
    if output["validation_errors"]:
        output["status"] = "error"
        output["stage_status"] = "signal_funnel_evidence_validation_error"
    return output, [entry]


def write_phase7_signal_funnel_evidence(
    artifact: dict[str, Any],
    *,
    settings: Settings | None = None,
    record_event: bool = True,
    event_log_path: str | Path | None = None,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    output = deepcopy(artifact)
    output_path, history_path, default_event_path = phase7_signal_funnel_evidence_paths(
        settings
    )
    event_path = Path(event_log_path or default_event_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if record_event:
        output, _ = attach_phase7_signal_funnel_evidence_event_log(
            output,
            event_log_path=event_path,
            settings=settings,
        )
    else:
        output["validation_errors"] = validate_phase7_signal_funnel_evidence(output)
        if output["validation_errors"]:
            output["status"] = "error"
            output["stage_status"] = "signal_funnel_evidence_validation_error"
    output["runtime_artifact_path"] = str(output_path)
    output["history_log_path"] = str(history_path)
    output["validation_errors"] = validate_phase7_signal_funnel_evidence(output)
    if output["validation_errors"]:
        output["status"] = "error"
        output["stage_status"] = "signal_funnel_evidence_validation_error"
    output_path.write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    history_record = {
        "schema_version": PHASE7_SIGNAL_FUNNEL_EVIDENCE_SCHEMA_VERSION,
        "artifact_id": output.get("artifact_id"),
        "status": output.get("status"),
        "stage_status": output.get("stage_status"),
        "generated_at": output.get("generated_at"),
        "recorded_at": _now(),
        "proof_trade_evidence_record_count": output.get(
            "proof_trade_evidence_record_count"
        ),
        "complete_decision_chain_count": output.get("complete_decision_chain_count"),
        "missing_decision_chain_count": output.get("missing_decision_chain_count"),
        "private_priors_only_proof_trade_count": output.get(
            "private_priors_only_proof_trade_count"
        ),
        "phase7_certification_blocked_by_signal_evidence": output.get(
            "phase7_certification_blocked_by_signal_evidence"
        ),
        "q7_14_maturity_tracker_stage_allowed": output.get(
            "q7_14_maturity_tracker_stage_allowed"
        ),
        "phase7_proof_credit_allowed": output.get("phase7_proof_credit_allowed"),
        "live_capital_enabled": output.get("live_capital_enabled"),
        "unsafe_write_counter_total": output.get("unsafe_write_counter_total"),
        "blocker_count": output.get("blocker_count"),
        "event_log_written": output.get("event_log_written"),
        "event_log_event_count": output.get("event_log_event_count"),
        "validation_error_count": len(output.get("validation_errors", [])),
    }
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(history_record, sort_keys=True) + "\n")
    return output_path, history_path, event_path, output
