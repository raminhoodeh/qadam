"""Canonical identities for replay-safe Qadam decision and handoff records."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from orchestrator.qadam_operator_ready_common import sha256_json
from orchestrator.qadam_wave_b_common import stable_id

IDENTITY_VERSION = "qadam_control_plane_identity.v3"


def _without_runtime_metadata(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Return the immutable economic content, excluding observation timestamps."""

    semantic = deepcopy(dict(payload))
    for key in ("decision_id", "created_at", "updated_at", "generated_at"):
        semantic.pop(key, None)
    gates = semantic.get("gate_decisions")
    if isinstance(gates, list):
        for gate in gates:
            if isinstance(gate, dict):
                gate.pop("gate_decision_id", None)
    return semantic


def decision_semantic_sha256(payload: Mapping[str, Any]) -> str:
    """Hash the decision facts that must remain fixed inside one generation."""

    return sha256_json(_without_runtime_metadata(payload))


def handoff_semantic_sha256(payload: Mapping[str, Any]) -> str:
    """Hash a handoff without refresh-only timestamps."""

    return sha256_json(_without_runtime_metadata(payload))


def receipt_semantic_sha256(payload: Mapping[str, Any]) -> str:
    """Hash a receipt without the time at which a replay observed it."""

    return sha256_json(_without_runtime_metadata(payload))


def router_decision_id(
    *,
    setup_id: str,
    candidate_identity: str,
    generation_id: str,
    final_state: str,
    instrument: str,
    direction: str,
    strategy_version: str,
) -> str:
    """Identify one coherent decision generation, not a mutable candidate."""

    return stable_id(
        "router-decision-v5",
        IDENTITY_VERSION,
        setup_id,
        candidate_identity,
        generation_id,
        final_state,
        instrument,
        direction,
        strategy_version,
    )


def paperops_handoff_id(
    *,
    decision_id: str,
    idempotency_key: str,
    paper_epoch_id: str,
) -> str:
    """Identify one guarded paper handoff within one paper-account epoch."""

    return stable_id(
        "paperops-handoff-v5",
        IDENTITY_VERSION,
        decision_id,
        idempotency_key,
        paper_epoch_id,
    )


def handoff_receipt_id(
    *,
    handoff_id: str,
    source_handoff_sha256: str,
    receipt_type: str,
    duplicate_ordinal: int = 0,
) -> str:
    """Identify a receipt independently of list position or process restart."""

    return stable_id(
        "paperops-handoff-v5-receipt",
        IDENTITY_VERSION,
        handoff_id,
        source_handoff_sha256,
        receipt_type,
        duplicate_ordinal,
    )


__all__ = [
    "IDENTITY_VERSION",
    "decision_semantic_sha256",
    "handoff_receipt_id",
    "handoff_semantic_sha256",
    "paperops_handoff_id",
    "receipt_semantic_sha256",
    "router_decision_id",
]
