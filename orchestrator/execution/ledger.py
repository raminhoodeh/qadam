"""Canonical operating ledger for Qadam's guarded paper-trading system.

The SQLite control plane is authoritative. JSON output from this module is a
read-only projection for the dashboard and diagnostics.
"""

from __future__ import annotations

from contextlib import contextmanager
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import secrets
import sqlite3
from typing import Any, Iterator, Mapping

from orchestrator.config import Settings
from orchestrator.paper_account import OPEN_ORDER_STATUSES, PaperAccountMirrorStore
from orchestrator.qadam_control_plane_store import ControlPlaneError, ControlPlaneStore
from orchestrator.qadam_control_plane_identity import canonical_risk_decision_id
from orchestrator.qadam_outcome_attribution import (
    attributed_outcome, cohort_metrics, reconstruct_order_history, learning_lots,
)
from orchestrator.qadam_operator_ready_common import atomic_write_text, read_json, runtime_dir


SCHEMA_VERSION = "qadam_operating_ledger.v1"
PROJECTION_ARTIFACT = "qadam_operating_ledger_summary.json"
LIVENESS_ARTIFACT = "qadam_operational_liveness.json"
EXECUTION_LEASE_NAME = "canonical_alpaca_paper_execution"
EXECUTION_STATE_ID = "canonical_paper_execution"
EXECUTION_OWNER_ID_ENV = "QADAM_EXECUTION_OWNER_ID"
EXECUTION_OWNER_TOKEN_ENV = "QADAM_EXECUTION_OWNER_TOKEN"
ACTIVE_ORDER_STATES = frozenset(
    {"prepared", "submitting", "submitted", "accepted", "partially_filled"}
)
RETRYABLE_PRE_SUBMIT_ORDER_STATES = frozenset(
    {"deferred_market_session", "pre_submit_blocked", "submission_failed"}
)


class ExecutionOwnerError(ControlPlaneError):
    """Raised when a process does not own the canonical broker-write lease."""


@dataclass(frozen=True)
class ExecutionLease:
    owner_id: str
    token: str
    acquired_at: str
    expires_at: str

    def environment(self) -> dict[str, str]:
        return {
            EXECUTION_OWNER_ID_ENV: self.owner_id,
            EXECUTION_OWNER_TOKEN_ENV: self.token,
        }


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime | None = None) -> str:
    return (value or _now()).astimezone(timezone.utc).isoformat()


def _parse(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _json(payload: Mapping[str, Any] | list[Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def _sha(payload: Mapping[str, Any] | list[Any] | str) -> str:
    text = payload if isinstance(payload, str) else _json(payload)
    return sha256(text.encode("utf-8")).hexdigest()


def _stable_id(prefix: str, *parts: Any) -> str:
    material = "|".join(str(part or "") for part in parts)
    return f"{prefix}:{sha256(material.encode('utf-8')).hexdigest()[:24]}"


def _float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value if value not in {None, ""} else default)
    except (TypeError, ValueError):
        return default


def read_operating_health(runtime: Path) -> dict[str, Any]:
    """Observe authority without creating a database, taking a lease or trading."""
    connection = None
    try:
        connection = sqlite3.connect(
            f"file:{runtime / 'qadam-control-plane.sqlite3'}?mode=ro", uri=True, timeout=5
        )
        connection.row_factory = sqlite3.Row
        state = connection.execute("SELECT * FROM execution_state WHERE state_id=?", (EXECUTION_STATE_ID,)).fetchone()
        reconciliation = connection.execute(
            "SELECT status,created_at,payload_json FROM reconciliation_runs ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
        unprotected = [row[0] for row in connection.execute(
            "SELECT p.instrument FROM positions p LEFT JOIN exit_plans e ON e.exit_plan_id=p.exit_plan_id "
            "WHERE p.state='open' AND (e.exit_plan_id IS NULL OR e.stop_price<=0 OR e.take_profit_price<=0 "
            "OR e.maximum_holding_sessions<=0 OR e.state IN ('closed','cancelled') "
            "OR (e.state='close_requested' AND NOT EXISTS (SELECT 1 FROM canonical_orders o "
            "WHERE o.exit_plan_id=e.exit_plan_id AND o.order_key LIKE 'exit-order:%' "
            "AND o.state IN ('prepared','submitting','submitted','new','accepted','pending_new','partially_filled'))))"
        )]
        blockers = []
        if not state or state["frozen"]:
            blockers.append("execution_frozen:" + str(state["reason"] if state else "state_missing"))
        observed = _parse(reconciliation["created_at"]) if reconciliation else None
        age = (_now() - observed).total_seconds() if observed else None
        if not reconciliation or reconciliation["status"] != "passed":
            blockers.append("broker_reconciliation_not_passed")
        # Operational cadence is not permission to submit against an old quote.
        if age is None or not 0 <= age <= 2400:
            blockers.append("broker_reconciliation_cadence_missed")
        if unprotected:
            blockers.append("position_protection_missing")
        return {"status": "healthy" if not blockers else "degraded", "blockers": blockers,
                "execution_state": dict(state) if state else {}, "unprotected_symbols": unprotected,
                "reconciliation_age_seconds": age,
                "pre_submit_reconciliation_fresh": age is not None and 0 <= age <= 180,
                "paper_order_allowed": False, "broker_write_count": 0}
    except sqlite3.Error as exc:
        return {"status": "degraded", "blockers": ["canonical_database_unreadable"],
                "error_class": type(exc).__name__, "paper_order_allowed": False, "broker_write_count": 0}
    finally:
        if connection is not None:
            connection.close()


def _trading_lane(value: Any) -> str:
    text = str(value or "").lower()
    if "validated" in text and "unvalidated" not in text:
        return "validated"
    return "discovery"


def _register_strategy_definition(connection: Any, version: str, definition: dict) -> None:
    expected = "paper-strategy-version:" + _sha(definition)[:24]
    if version != expected:
        raise ControlPlaneError("strategy_definition_version_mismatch")
    _event(connection, aggregate_type="strategy_version", aggregate_id=version,
           event_type="strategy_definition_registered", payload=definition,
           created_at=_iso())


def execution_owner_process_state(owner_id: str) -> str:
    """Return local process truth for canonical PaperOps owner identifiers."""

    parts = str(owner_id or "").split(":")
    if len(parts) != 3 or parts[0] != "paperops-autonomous-pass":
        return "unknown"
    try:
        pid = int(parts[1])
    except ValueError:
        return "unknown"
    if pid <= 0:
        return "unknown"
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return "dead"
    except PermissionError:
        return "alive"
    return "alive"


def _event(
    connection: Any,
    *,
    aggregate_type: str,
    aggregate_id: str,
    event_type: str,
    payload: Mapping[str, Any],
    created_at: str | None = None,
) -> None:
    timestamp = created_at or _iso()
    payload_text = _json(payload)
    payload_sha = _sha(payload_text)
    event_id = _stable_id(
        "operating-event", aggregate_type, aggregate_id, event_type, payload_sha
    )
    connection.execute(
        "INSERT OR IGNORE INTO operating_events ("
        "event_id,aggregate_type,aggregate_id,event_type,payload_json,"
        "payload_sha256,created_at) VALUES (?,?,?,?,?,?,?)",
        (
            event_id,
            aggregate_type,
            aggregate_id,
            event_type,
            payload_text,
            payload_sha,
            timestamp,
        ),
    )


class OperatingLedger:
    """High-level operating contract on the existing control-plane database."""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        store: ControlPlaneStore | None = None,
    ) -> None:
        self.settings = settings or Settings.from_env()
        self.store = store or ControlPlaneStore.from_settings(self.settings)

    def acquire_execution_owner(
        self,
        owner_id: str,
        *,
        ttl_seconds: int = 2_400,
    ) -> ExecutionLease:
        if not owner_id.strip():
            raise ExecutionOwnerError("execution_owner_id_missing")
        if ttl_seconds < 60 or ttl_seconds > 7_200:
            raise ExecutionOwnerError("execution_owner_ttl_out_of_bounds")
        now = _now()
        token = secrets.token_urlsafe(32)
        token_sha = _sha(token)
        acquired_at = _iso(now)
        expires_at = _iso(now + timedelta(seconds=ttl_seconds))
        with self.store.transaction() as connection:
            row = connection.execute(
                "SELECT * FROM execution_owner_leases WHERE lease_name = ?",
                (EXECUTION_LEASE_NAME,),
            ).fetchone()
            if row is not None:
                current_expiry = _parse(str(row["expires_at"]))
                active = str(row["state"]) == "active" and bool(
                    current_expiry and current_expiry > now
                )
                if active:
                    previous_owner = str(row["owner_id"])
                    if execution_owner_process_state(previous_owner) != "dead":
                        raise ExecutionOwnerError(
                            f"execution_owner_busy:{previous_owner}"
                        )
                    connection.execute(
                        "UPDATE execution_owner_leases SET state='orphaned',heartbeat_at=?,"
                        "expires_at=? WHERE lease_name=? AND owner_id=? AND state='active'",
                        (
                            acquired_at,
                            acquired_at,
                            EXECUTION_LEASE_NAME,
                            previous_owner,
                        ),
                    )
                    _event(
                        connection,
                        aggregate_type="execution_owner",
                        aggregate_id=EXECUTION_LEASE_NAME,
                        event_type="orphaned_lease_reclaimed",
                        payload={
                            "previous_owner_id": previous_owner,
                            "replacement_owner_id": owner_id,
                            "reason": "local_owner_process_not_running",
                            "paper_only": True,
                            "live_capital_enabled": False,
                        },
                        created_at=acquired_at,
                    )
            connection.execute(
                "INSERT INTO execution_owner_leases ("
                "lease_name,owner_id,token_sha256,state,acquired_at,heartbeat_at,expires_at"
                ") VALUES (?,?,?,?,?,?,?) ON CONFLICT(lease_name) DO UPDATE SET "
                "owner_id=excluded.owner_id,token_sha256=excluded.token_sha256,"
                "state=excluded.state,acquired_at=excluded.acquired_at,"
                "heartbeat_at=excluded.heartbeat_at,expires_at=excluded.expires_at",
                (
                    EXECUTION_LEASE_NAME,
                    owner_id,
                    token_sha,
                    "active",
                    acquired_at,
                    acquired_at,
                    expires_at,
                ),
            )
            _event(
                connection,
                aggregate_type="execution_owner",
                aggregate_id=EXECUTION_LEASE_NAME,
                event_type="lease_acquired",
                payload={
                    "owner_id": owner_id,
                    "expires_at": expires_at,
                    "paper_only": True,
                    "live_capital_enabled": False,
                },
                created_at=acquired_at,
            )
        return ExecutionLease(owner_id, token, acquired_at, expires_at)

    def assert_execution_owner(
        self,
        *,
        owner_id: str | None = None,
        token: str | None = None,
    ) -> dict[str, Any]:
        owner_id = owner_id or os.getenv(EXECUTION_OWNER_ID_ENV, "")
        token = token or os.getenv(EXECUTION_OWNER_TOKEN_ENV, "")
        if not owner_id or not token:
            raise ExecutionOwnerError("canonical_execution_owner_lease_missing")
        with self.store.connect() as connection:
            row = connection.execute(
                "SELECT * FROM execution_owner_leases WHERE lease_name = ?",
                (EXECUTION_LEASE_NAME,),
            ).fetchone()
        if row is None:
            raise ExecutionOwnerError("canonical_execution_owner_lease_missing")
        expires_at = _parse(str(row["expires_at"]))
        checks = {
            "state_active": str(row["state"]) == "active",
            "owner_matches": secrets.compare_digest(str(row["owner_id"]), owner_id),
            "token_matches": secrets.compare_digest(str(row["token_sha256"]), _sha(token)),
            "lease_fresh": bool(expires_at and expires_at > _now()),
        }
        if not all(checks.values()):
            raise ExecutionOwnerError(
                "canonical_execution_owner_lease_invalid:"
                + ",".join(key for key, passed in checks.items() if not passed)
            )
        return {
            "owner_id": owner_id,
            "expires_at": str(row["expires_at"]),
            "checks": checks,
        }

    def heartbeat_execution_owner(self, lease: ExecutionLease) -> None:
        self.assert_execution_owner(owner_id=lease.owner_id, token=lease.token)
        now = _now()
        expires_at = _iso(now + timedelta(seconds=2_400))
        with self.store.transaction() as connection:
            cursor = connection.execute(
                "UPDATE execution_owner_leases SET heartbeat_at=?, expires_at=? "
                "WHERE lease_name=? AND owner_id=? AND token_sha256=? AND state='active'",
                (
                    _iso(now),
                    expires_at,
                    EXECUTION_LEASE_NAME,
                    lease.owner_id,
                    _sha(lease.token),
                ),
            )
            if cursor.rowcount != 1:
                raise ExecutionOwnerError("execution_owner_heartbeat_failed")

    def release_execution_owner(self, lease: ExecutionLease) -> None:
        with self.store.transaction() as connection:
            cursor = connection.execute(
                "UPDATE execution_owner_leases SET state='released',heartbeat_at=?,"
                "expires_at=? WHERE lease_name=? AND owner_id=? AND token_sha256=? "
                "AND state='active'",
                (
                    _iso(),
                    _iso(),
                    EXECUTION_LEASE_NAME,
                    lease.owner_id,
                    _sha(lease.token),
                ),
            )
            if cursor.rowcount not in {0, 1}:
                raise ExecutionOwnerError("execution_owner_release_rowcount_invalid")
            if cursor.rowcount == 1:
                _event(
                    connection,
                    aggregate_type="execution_owner",
                    aggregate_id=EXECUTION_LEASE_NAME,
                    event_type="lease_released",
                    payload={"owner_id": lease.owner_id, "paper_only": True},
                )

    @contextmanager
    def execution_owner(
        self,
        owner_id: str,
        *,
        ttl_seconds: int = 2_400,
    ) -> Iterator[ExecutionLease]:
        lease = self.acquire_execution_owner(owner_id, ttl_seconds=ttl_seconds)
        try:
            yield lease
        finally:
            self.release_execution_owner(lease)

    def execution_state(self) -> dict[str, Any]:
        with self.store.connect() as connection:
            row = connection.execute(
                "SELECT * FROM execution_state WHERE state_id=?",
                (EXECUTION_STATE_ID,),
            ).fetchone()
        return dict(row) if row is not None else {
            "state_id": EXECUTION_STATE_ID,
            "frozen": 1,
            "reason": "execution_state_missing",
        }

    def require_execution_available(self) -> None:
        state = self.execution_state()
        if int(state.get("frozen") or 0) == 1:
            raise ExecutionOwnerError(
                f"canonical_execution_frozen:{state.get('reason') or 'unknown'}"
            )

    def set_execution_frozen(
        self,
        *,
        reason: str,
        reconciliation_id: str | None = None,
    ) -> None:
        with self.store.transaction() as connection:
            current = connection.execute(
                "SELECT * FROM execution_state WHERE state_id=?", (EXECUTION_STATE_ID,)
            ).fetchone()
            # A transport failure must not replace an operator or safety hold.
            protected = current and current["frozen"] and not self._recoverable_freeze(
                str(current["reason"] or "")
            )
            if not protected:
                connection.execute(
                    "UPDATE execution_state SET frozen=1,reason=?,reconciliation_id=?,"
                    "updated_at=? WHERE state_id=?",
                    (reason, reconciliation_id, _iso(), EXECUTION_STATE_ID),
                )
            _event(
                connection,
                aggregate_type="execution_state",
                aggregate_id=EXECUTION_STATE_ID,
                event_type="execution_frozen",
                payload={"reason": reason, "reconciliation_id": reconciliation_id},
            )

    @staticmethod
    def _recoverable_freeze(reason: str) -> bool:
        return reason.startswith(("broker_reconciliation_", "ambiguous_order_submission:")) or (
            reason.endswith("_paper_mirror_refresh_failed")
        )

    def clear_reconciliation_freeze(
        self,
        *,
        reconciliation_id: str,
    ) -> None:
        self.assert_execution_owner()
        with self.store.transaction() as connection:
            row = connection.execute(
                "SELECT * FROM reconciliation_runs WHERE reconciliation_id=?",
                (reconciliation_id,),
            ).fetchone()
            if row is None or str(row["status"]) != "passed":
                raise ControlPlaneError("execution_unfreeze_requires_passed_reconciliation")
            state = connection.execute(
                "SELECT * FROM execution_state WHERE state_id=?", (EXECUTION_STATE_ID,)
            ).fetchone()
            if not state or not state["frozen"]:
                return
            incident_at = _parse(state["updated_at"])
            checked_at = _parse(row["created_at"])
            if (
                not self._recoverable_freeze(str(state["reason"] or ""))
                or incident_at is None or checked_at is None or checked_at <= incident_at
                or not 0 <= (_now() - checked_at).total_seconds() <= 180
            ):
                raise ControlPlaneError("execution_unfreeze_requires_current_recoverable_incident")
            if str(state["reason"]).endswith("_paper_mirror_refresh_failed"):
                observations = set()
                for check in connection.execute(
                    "SELECT payload_json FROM reconciliation_runs "
                    "WHERE created_at>? AND created_at<=? AND status='passed'",
                    (state["updated_at"], row["created_at"]),
                ):
                    observed_at = _parse(json.loads(check["payload_json"]).get("observed", {}).get(
                        "mirror_observed_at"
                    ))
                    if observed_at and observed_at > incident_at and (
                        0 <= (_now() - observed_at).total_seconds() <= 180
                    ):
                        observations.add(observed_at)
                if len(observations) < 2:
                    return
            connection.execute(
                "UPDATE execution_state SET frozen=0,reason=NULL,reconciliation_id=?,"
                "updated_at=? WHERE state_id=?",
                (reconciliation_id, _iso(), EXECUTION_STATE_ID),
            )
            _event(
                connection,
                aggregate_type="execution_state",
                aggregate_id=EXECUTION_STATE_ID,
                event_type="execution_unfrozen_after_reconciliation",
                payload={"reconciliation_id": reconciliation_id},
            )

    def _decision_exists(self, connection: Any, decision_id: str | None) -> bool:
        if not decision_id:
            return False
        return connection.execute(
            "SELECT 1 FROM decision_transactions WHERE decision_id=?",
            (decision_id,),
        ).fetchone() is not None

    def _handoff_payload(self, connection: Any, handoff_id: str | None) -> dict[str, Any]:
        if not handoff_id:
            return {}
        row = connection.execute(
            "SELECT payload_json FROM handoffs WHERE handoff_id=?",
            (handoff_id,),
        ).fetchone()
        if row is None:
            return {}
        payload = json.loads(str(row["payload_json"]))
        return payload if isinstance(payload, dict) else {}

    def register_strategy_definition(self, hypothesis: Mapping[str, Any]) -> None:
        """Preregister immutable research rules, without execution authority."""
        version = str(hypothesis.get("strategy_version_id") or "")
        definition = hypothesis.get("strategy_definition")
        if not isinstance(definition, dict):
            raise ControlPlaneError("strategy_definition_missing")
        with self.store.transaction() as connection:
            _register_strategy_definition(connection, version, definition)

    def record_hypothesis(
        self,
        payload: Mapping[str, Any],
        *,
        generation_id: str,
        trading_lane: str | None = None,
    ) -> str:
        hypothesis_id = str(
            payload.get("hypothesis_id")
            or payload.get("strategy_hypothesis_id")
            or _stable_id("hypothesis", generation_id, _sha(dict(payload)))
        )
        timestamp = str(payload.get("generated_at") or _iso())
        lane = trading_lane or _trading_lane(
            payload.get("evidence_class") or payload.get("experimental_tier")
        )
        record = dict(payload)
        payload_text = _json(record)
        payload_sha = _sha(payload_text)
        with self.store.transaction() as connection:
            connection.execute(
                "INSERT INTO hypotheses (hypothesis_id,generation_id,research_goal_id,"
                "strategy_id,strategy_version,instrument,direction,trading_lane,state,"
                "payload_json,payload_sha256,created_at,updated_at) VALUES "
                "(?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(hypothesis_id) DO UPDATE SET "
                "state=excluded.state,payload_json=excluded.payload_json,"
                "payload_sha256=excluded.payload_sha256,updated_at=excluded.updated_at,"
                "strategy_version=excluded.strategy_version",
                (
                    hypothesis_id,
                    generation_id,
                    str(payload.get("research_goal_id") or "research-goal-unclassified"),
                    str(payload.get("strategy_id") or payload.get("strategy_family_id") or "strategy-unclassified"),
                    str(payload.get("strategy_version") or payload.get("strategy_version_id") or "unversioned"),
                    str(payload.get("instrument") or payload.get("execution_symbol") or "unknown"),
                    str(payload.get("direction") or "abstain"),
                    lane,
                    str(payload.get("state") or payload.get("status") or "research"),
                    payload_text,
                    payload_sha,
                    timestamp,
                    timestamp,
                ),
            )
            version = str(payload.get("strategy_version") or payload.get("strategy_version_id") or "")
            definition = payload.get("strategy_definition")
            if version.startswith("paper-strategy-version:") and isinstance(definition, dict):
                _register_strategy_definition(connection, version, definition)
            _event(
                connection,
                aggregate_type="hypothesis",
                aggregate_id=hypothesis_id,
                event_type="hypothesis_recorded",
                payload=record,
                created_at=timestamp,
            )
        return hypothesis_id

    def record_risk_decision(
        self,
        *,
        risk_decision_id: str,
        decision_id: str,
        trading_lane: str,
        state: str,
        proposed_notional: float,
        approved_notional: float,
        payload: Mapping[str, Any],
    ) -> bool:
        payload_text = _json(dict(payload))
        payload_sha = _sha(payload_text)
        with self.store.transaction() as connection:
            if not self._decision_exists(connection, decision_id):
                raise ControlPlaneError("risk_decision_requires_canonical_decision")
            existing = connection.execute(
                "SELECT decision_id,payload_sha256 FROM risk_decisions "
                "WHERE risk_decision_id=?",
                (risk_decision_id,),
            ).fetchone()
            if existing is not None:
                if (
                    str(existing["decision_id"]) != decision_id
                    or str(existing["payload_sha256"]) != payload_sha
                ):
                    raise ControlPlaneError(
                        f"immutable_identity_collision:risk_decisions:{risk_decision_id}"
                    )
                return False
            connection.execute(
                "INSERT INTO risk_decisions (risk_decision_id,decision_id,trading_lane,"
                "state,proposed_notional,approved_notional,payload_json,payload_sha256,"
                "created_at) VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    risk_decision_id,
                    decision_id,
                    trading_lane,
                    state,
                    proposed_notional,
                    approved_notional,
                    payload_text,
                    payload_sha,
                    _iso(),
                ),
            )
            _event(
                connection,
                aggregate_type="risk_decision",
                aggregate_id=risk_decision_id,
                event_type="risk_decision_recorded",
                payload=dict(payload),
            )
            return True

    def record_research_generation(
        self,
        router_state: Mapping[str, Any],
    ) -> dict[str, int]:
        """Persist the complete research generation behind the router projection."""

        setups = [
            dict(row)
            for row in router_state.get("setups", [])
            if isinstance(row, Mapping)
        ]
        decisions = [
            dict(row)
            for row in router_state.get("decisions", [])
            if isinstance(row, Mapping)
        ]
        decision_by_setup = {
            str(row.get("setup_id") or ""): row for row in decisions
        }
        hypothesis_count = 0
        risk_count = 0
        for setup in setups:
            decision = decision_by_setup.get(str(setup.get("setup_id") or ""), {})
            lineage = setup.get("lineage")
            lineage = lineage if isinstance(lineage, Mapping) else {}
            generation_id = str(
                decision.get("router_execution_generation_id")
                or setup.get("decision_generation_id")
                or router_state.get("generated_at")
                or _iso()
            )
            hypothesis_payload = {
                **setup,
                "hypothesis_id": lineage.get("hypothesis_id")
                or setup.get("hypothesis_id")
                or _stable_id("hypothesis", generation_id, setup.get("setup_id")),
                "research_goal_id": lineage.get("research_goal_id"),
                "strategy_id": setup.get("strategy_family_id"),
                "strategy_version": lineage.get("strategy_version_id"),
                "strategy_definition": setup.get("strategy_definition"),
                "instrument": setup.get("execution_symbol") or setup.get("instrument"),
                "direction": setup.get("direction"),
                "evidence_class": setup.get("evidence_class"),
                "state": decision.get("final_state") or "research",
                "router_decision_id": decision.get("router_decision_id"),
            }
            self.record_hypothesis(
                hypothesis_payload,
                generation_id=generation_id,
                trading_lane=_trading_lane(setup.get("evidence_class")),
            )
            hypothesis_count += 1

            decision_id = str(decision.get("router_decision_id") or "")
            source_risk_proposal_id = str(lineage.get("risk_proposal_id") or "")
            if not decision_id or not source_risk_proposal_id:
                continue
            risk_id = canonical_risk_decision_id(
                source_risk_proposal_id=source_risk_proposal_id,
                decision_id=decision_id,
            )
            proposed_notional = _float(setup.get("proposed_notional_usd"))
            review_states = {
                "paper-review-candidate",
                "experimental-paper-review-candidate",
                "validated_paper_review_candidate",
                "experimental_paper_review_candidate",
            }
            approved_notional = (
                proposed_notional
                if str(decision.get("final_state") or "") in review_states
                else 0.0
            )
            inserted = self.record_risk_decision(
                risk_decision_id=risk_id,
                decision_id=decision_id,
                trading_lane=_trading_lane(setup.get("evidence_class")),
                state=str(decision.get("final_state") or "hold"),
                proposed_notional=proposed_notional,
                approved_notional=approved_notional,
                payload={
                    "risk_decision_id": risk_id,
                    "risk_proposal_id": source_risk_proposal_id,
                    "source_risk_proposal_id": source_risk_proposal_id,
                    "decision_id": decision_id,
                    "hypothesis_id": hypothesis_payload["hypothesis_id"],
                    "proposed_notional_usd": proposed_notional,
                    "approved_notional_usd": approved_notional,
                    "maximum_loss_at_invalidation": setup.get(
                        "maximum_loss_at_invalidation"
                    ),
                    "portfolio_level_controls": {
                        "duplicate_exposure_conflict": setup.get(
                            "duplicate_exposure_conflict"
                        ),
                        "drawdown_context_complete": setup.get(
                            "drawdown_context_complete"
                        ),
                        "drawdown_breached": setup.get("drawdown_breached"),
                        "hard_ceiling_usd": 5_000.0,
                    },
                    "paper_only": True,
                    "live_capital_enabled": False,
                },
            )
            risk_count += int(inserted)
        return {
            "hypothesis_count": hypothesis_count,
            "risk_decision_inserted_count": risk_count,
        }

    def prepare_order(self, candidate: Mapping[str, Any]) -> dict[str, Any]:
        owner = self.assert_execution_owner()
        self.require_execution_available()
        request = candidate.get("request_preview")
        request = request if isinstance(request, Mapping) else {}
        order_key = str(request.get("client_order_id") or candidate.get("idempotency_key") or "")
        instrument = str(request.get("symbol") or candidate.get("alpaca_symbol") or "").upper()
        side = str(request.get("side") or "").lower()
        quantity = _float(request.get("qty"))
        handoff_id = str(candidate.get("paperops_handoff_id") or "") or None
        decision_id = str(candidate.get("router_decision_id") or "") or None
        lane = _trading_lane(candidate.get("evidence_class"))
        notional = _float(candidate.get("notional_usd"))
        risk = _float(candidate.get("risk_usd"))
        if not notional:
            notional = _float(
                (candidate.get("source_pre_trade_snapshot") or {}).get("notional_usd")
                if isinstance(candidate.get("source_pre_trade_snapshot"), Mapping)
                else 0.0
            )
        with self.store.transaction() as connection:
            handoff_row = (
                connection.execute(
                    "SELECT decision_id,state,payload_json FROM handoffs WHERE handoff_id=?",
                    (handoff_id,),
                ).fetchone()
                if handoff_id
                else None
            )
            handoff = (
                json.loads(str(handoff_row["payload_json"]))
                if handoff_row is not None
                else {}
            )
            invalidation_value = candidate.get("invalidation") or handoff.get("invalidation")
            if isinstance(invalidation_value, list):
                invalidation = "; ".join(str(item) for item in invalidation_value if str(item))
            else:
                invalidation = str(invalidation_value or "").strip()
            notional = notional or _float(handoff.get("proposed_notional_usd"))
            risk = risk or _float(handoff.get("maximum_loss_at_invalidation"))
            hard_errors = []
            if not order_key:
                hard_errors.append("idempotency_key_missing")
            if not instrument:
                hard_errors.append("instrument_missing")
            if side not in {"buy", "sell"}:
                hard_errors.append("direction_missing")
            if quantity <= 0:
                hard_errors.append("quantity_missing")
            if not invalidation:
                hard_errors.append("invalidation_missing")
            if notional <= 0 or risk <= 0:
                hard_errors.append("risk_reference_missing")
            if not decision_id:
                hard_errors.append("canonical_decision_id_missing")
            elif not self._decision_exists(connection, decision_id):
                hard_errors.append("canonical_decision_missing")
            if not handoff_id:
                hard_errors.append("canonical_handoff_id_missing")
            elif handoff_row is None:
                hard_errors.append("canonical_handoff_missing")
            elif str(handoff_row["decision_id"]) != decision_id:
                hard_errors.append("canonical_handoff_decision_mismatch")
            elif str(handoff_row["state"]) != "accepted_for_paperops_review":
                hard_errors.append("canonical_handoff_not_active")
            if hard_errors:
                raise ControlPlaneError("order_hard_evidence_missing:" + ",".join(hard_errors))
            open_position = connection.execute(
                "SELECT position_key FROM positions WHERE instrument=? AND state='open'",
                (instrument,),
            ).fetchone()
            if open_position is not None:
                raise ControlPlaneError(
                    f"duplicate_open_position_in_ledger:{instrument}"
                )
            risk_decision = connection.execute(
                "SELECT state,approved_notional,trading_lane FROM risk_decisions "
                "WHERE decision_id=? ORDER BY created_at DESC LIMIT 1",
                (decision_id,),
            ).fetchone()
            if risk_decision is None:
                raise ControlPlaneError("canonical_risk_decision_missing")
            approved_notional = _float(risk_decision["approved_notional"])
            if approved_notional <= 0:
                raise ControlPlaneError("canonical_risk_decision_not_approved")
            if approved_notional + 0.01 < notional:
                raise ControlPlaneError("canonical_risk_notional_exceeded")
            if str(risk_decision["trading_lane"]) != lane:
                raise ControlPlaneError("canonical_risk_lane_mismatch")
            reference_price = notional / quantity
            loss_per_unit = max(risk / quantity, reference_price * 0.0025)
            if side == "buy":
                stop_price = max(reference_price - loss_per_unit, 0.01)
                take_profit_price = reference_price + (2.0 * loss_per_unit)
            else:
                stop_price = reference_price + loss_per_unit
                take_profit_price = max(reference_price - (2.0 * loss_per_unit), 0.01)
            horizon = str(candidate.get("horizon") or handoff.get("horizon") or "3d_forward")
            maximum_holding_sessions = 1 if horizon.startswith("1d") else 5 if horizon.startswith("5d") else 3
            exit_plan_id = _stable_id("exit-plan", order_key, instrument)
            exit_payload = {
                "exit_plan_id": exit_plan_id,
                "instrument": instrument,
                "side": side,
                "reference_price": round(reference_price, 6),
                "stop_price": round(stop_price, 6),
                "take_profit_price": round(take_profit_price, 6),
                "reward_to_risk": 2.0,
                "maximum_holding_sessions": maximum_holding_sessions,
                "invalidation": invalidation,
                "paper_only": True,
            }
            exit_text = _json(exit_payload)
            timestamp = _iso()
            connection.execute(
                "INSERT OR IGNORE INTO exit_plans (exit_plan_id,decision_id,handoff_id,"
                "instrument,side,stop_price,take_profit_price,maximum_holding_sessions,"
                "invalidation,state,payload_json,payload_sha256,created_at,updated_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    exit_plan_id,
                    decision_id,
                    handoff_id,
                    instrument,
                    side,
                    stop_price,
                    take_profit_price,
                    maximum_holding_sessions,
                    invalidation,
                    "armed_before_entry",
                    exit_text,
                    _sha(exit_text),
                    timestamp,
                    timestamp,
                ),
            )
            immutable_candidate = {
                "paperops_handoff_id": handoff_id,
                "router_decision_id": decision_id,
                "evidence_class": candidate.get("evidence_class"),
                "notional_usd": round(notional, 6),
                "risk_usd": round(risk, 6),
                "invalidation": invalidation,
                "horizon": horizon,
                "request_preview": {
                    "client_order_id": order_key,
                    "symbol": instrument,
                    "side": side,
                    "qty": quantity,
                    **(
                        {"type": request.get("type")}
                        if request.get("type") is not None
                        else {}
                    ),
                    **(
                        {"time_in_force": request.get("time_in_force")}
                        if request.get("time_in_force") is not None
                        else {}
                    ),
                },
            }
            order_payload = {
                "purpose": "canonical_position_entry",
                "candidate": immutable_candidate,
                "exit_plan": exit_payload,
                "paper_only": True,
                "live_capital_enabled": False,
            }
            order_text = _json(order_payload)
            try:
                connection.execute(
                    "INSERT INTO canonical_orders (order_key,handoff_id,decision_id,exit_plan_id,"
                    "instrument,side,quantity,trading_lane,state,broker_order_id_hash,"
                    "payload_json,payload_sha256,created_at,updated_at) VALUES "
                    "(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        order_key,
                        handoff_id,
                        decision_id,
                        exit_plan_id,
                        instrument,
                        side,
                        quantity,
                        lane,
                        "prepared",
                        None,
                        order_text,
                        _sha(order_text),
                        timestamp,
                        timestamp,
                    ),
                )
            except Exception as exc:
                if "UNIQUE constraint failed: canonical_orders.instrument" in str(exc):
                    raise ControlPlaneError(
                        f"duplicate_active_exposure_in_ledger:{instrument}"
                    ) from exc
                existing = connection.execute(
                    "SELECT handoff_id,decision_id,exit_plan_id,instrument,side,quantity,"
                    "trading_lane,payload_sha256,state FROM canonical_orders WHERE order_key=?",
                    (order_key,),
                ).fetchone()
                identity_matches = existing is not None and (
                    str(existing["handoff_id"] or "") == str(handoff_id or "")
                    and str(existing["decision_id"] or "") == str(decision_id or "")
                    and str(existing["exit_plan_id"] or "") == exit_plan_id
                    and str(existing["instrument"] or "").upper() == instrument
                    and str(existing["side"] or "").lower() == side
                    and abs(_float(existing["quantity"]) - quantity) <= 0.000001
                    and str(existing["trading_lane"] or "") == lane
                )
                if not identity_matches:
                    raise ControlPlaneError(f"canonical_order_identity_collision:{order_key}") from exc
                if str(existing["state"]) in RETRYABLE_PRE_SUBMIT_ORDER_STATES:
                    connection.execute(
                        "UPDATE canonical_orders SET state='prepared',broker_order_id_hash=NULL,"
                        "payload_json=?,payload_sha256=?,updated_at=? WHERE order_key=?",
                        (order_text, _sha(order_text), timestamp, order_key),
                    )
                    _event(
                        connection,
                        aggregate_type="order",
                        aggregate_id=order_key,
                        event_type="order_reprepared_after_pre_submit_defer",
                        payload={
                            **order_payload,
                            "prior_state": str(existing["state"]),
                            "execution_owner_id": owner["owner_id"],
                        },
                        created_at=timestamp,
                    )
                    return {
                        "order_key": order_key,
                        "instrument": instrument,
                        "trading_lane": lane,
                        "exit_plan": exit_payload,
                        "already_prepared": True,
                    }
                if str(existing["payload_sha256"]) != _sha(order_text):
                    raise ControlPlaneError(f"canonical_order_identity_collision:{order_key}") from exc
            _event(
                connection,
                aggregate_type="order",
                aggregate_id=order_key,
                event_type="order_prepared_with_exit_plan",
                payload={**order_payload, "execution_owner_id": owner["owner_id"]},
                created_at=timestamp,
            )
        return {
            "order_key": order_key,
            "instrument": instrument,
            "trading_lane": lane,
            "exit_plan": exit_payload,
            "already_prepared": False,
        }

    def record_order_result(
        self,
        *,
        order_key: str,
        succeeded: bool,
        receipt: Mapping[str, Any] | None,
        failure_class: str | None,
        post_attempted: bool = True,
    ) -> None:
        receipt = dict(receipt or {})
        if succeeded and not post_attempted:
            raise ControlPlaneError("successful_order_requires_broker_post_attempt")
        if succeeded:
            state = "submitted"
        elif not post_attempted and failure_class == "market_session_closed":
            state = "deferred_market_session"
        elif not post_attempted:
            state = "pre_submit_blocked"
        else:
            state = "submission_failed"
        with self.store.transaction() as connection:
            row = connection.execute(
                "SELECT payload_json FROM canonical_orders WHERE order_key=?",
                (order_key,),
            ).fetchone()
            if row is None:
                raise ControlPlaneError("order_result_without_prepared_order")
            payload = json.loads(str(row["payload_json"]))
            payload["submission_result"] = {
                "succeeded": succeeded,
                "post_attempted": post_attempted,
                "receipt": receipt,
                "failure_class": failure_class,
            }
            payload_text = _json(payload)
            connection.execute(
                "UPDATE canonical_orders SET state=?,broker_order_id_hash=?,payload_json=?,"
                "payload_sha256=?,updated_at=? WHERE order_key=?",
                (
                    state,
                    receipt.get("broker_order_id_hash"),
                    payload_text,
                    _sha(payload_text),
                    _iso(),
                    order_key,
                ),
            )
            _event(
                connection,
                aggregate_type="order",
                aggregate_id=order_key,
                event_type=state,
                payload=payload["submission_result"],
            )
        if (
            post_attempted
            and not succeeded
            and failure_class not in {"http_400", "http_403", "http_422"}
        ):
            self.set_execution_frozen(reason=f"ambiguous_order_submission:{failure_class or 'unknown'}")

    def record_direct_reconciliation(
        self,
        *,
        phase: str,
        expected: Mapping[str, Any],
        observed: Mapping[str, Any],
        blockers: list[str],
    ) -> dict[str, Any]:
        owner = self.assert_execution_owner()
        timestamp = _iso()
        expected_digest = _sha(dict(expected))
        observed_digest = _sha(dict(observed))
        reconciliation_id = _stable_id(
            "reconciliation", owner["owner_id"], phase, timestamp, observed_digest
        )
        status = "passed" if not blockers else "blocked"
        payload = {
            "reconciliation_id": reconciliation_id,
            "phase": phase,
            "status": status,
            "expected": dict(expected),
            "observed": dict(observed),
            "blockers": sorted(set(blockers)),
            "paper_only": True,
            "live_capital_enabled": False,
        }
        payload_text = _json(payload)
        with self.store.transaction() as connection:
            connection.execute(
                "INSERT INTO reconciliation_runs (reconciliation_id,execution_owner_id,"
                "phase,status,expected_digest,observed_digest,blocker_count,payload_json,"
                "payload_sha256,created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (
                    reconciliation_id,
                    owner["owner_id"],
                    phase,
                    status,
                    expected_digest,
                    observed_digest,
                    len(set(blockers)),
                    payload_text,
                    _sha(payload_text),
                    timestamp,
                ),
            )
            _event(
                connection,
                aggregate_type="reconciliation",
                aggregate_id=reconciliation_id,
                event_type=f"reconciliation_{status}",
                payload=payload,
                created_at=timestamp,
            )
        if blockers:
            self.set_execution_frozen(
                reason="broker_reconciliation_disagreement:" + ",".join(sorted(set(blockers))),
                reconciliation_id=reconciliation_id,
            )
        else:
            state = self.execution_state()
            if int(state.get("frozen") or 0) == 1 and self._recoverable_freeze(
                str(state.get("reason") or "")
            ):
                self.clear_reconciliation_freeze(reconciliation_id=reconciliation_id)
        return payload

    def sync_paper_mirror(
        self,
        *,
        phase: str,
        bootstrap: bool = False,
    ) -> dict[str, Any]:
        owner = self.assert_execution_owner()
        mirror = PaperAccountMirrorStore(settings=self.settings)
        snapshot = mirror.latest_snapshot()
        orders = mirror.read_orders()
        positions = mirror.read_positions()
        closed_trades = mirror.read_closed_trades()
        order_history = reconstruct_order_history(order.to_dict() for order in orders)
        if snapshot is None:
            return self.record_direct_reconciliation(
                phase=phase,
                expected={"mirror": "required"},
                observed={"mirror": "missing"},
                blockers=["paper_account_mirror_missing"],
            )
        observed_at = _parse(snapshot.observed_at)
        blockers: list[str] = []
        if observed_at is None or not 0 <= (_now() - observed_at).total_seconds() <= 180:
            blockers.append("paper_account_mirror_stale")
        mirror_position_symbols = {str(position.instrument).upper() for position in positions}
        with self.store.transaction() as connection:
            existing_open_positions = {
                str(row["instrument"]).upper(): dict(row)
                for row in connection.execute(
                    "SELECT instrument,quantity,decision_id,handoff_id,exit_plan_id,"
                    "trading_lane,opened_at FROM positions WHERE state='open'"
                )
            }
            reconciled_order_keys: set[str] = set()
            recent_broker_order_symbols: set[str] = set()
            expected_active = connection.execute(
                "SELECT order_key,instrument,created_at FROM canonical_orders WHERE state IN "
                "('prepared','submitting','submitted','accepted','partially_filled')"
            ).fetchall()
            for order in orders:
                broker_key = str(order.client_order_id or "") or _stable_id(
                    "mirror-order", order.order_id
                )
                symbol = str(order.instrument).upper()
                order_direction = str(order.direction or "").lower()
                order_side = (
                    "buy" if order_direction in {"buy", "long"} else "sell"
                )
                broker_order_id_hash = str(
                    getattr(order, "broker_order_id_hash", None) or _sha(str(order.order_id))
                )
                existing = connection.execute(
                    "SELECT order_key,exit_plan_id,trading_lane FROM canonical_orders "
                    "WHERE order_key=?",
                    (broker_key,),
                ).fetchone()
                if existing is None:
                    existing = connection.execute(
                        "SELECT order_key,exit_plan_id,trading_lane FROM canonical_orders "
                        "WHERE broker_order_id_hash=? ORDER BY updated_at DESC LIMIT 1",
                        (broker_order_id_hash,),
                    ).fetchone()
                key = str(existing["order_key"]) if existing is not None else broker_key
                if existing is None:
                    if not bootstrap:
                        blockers.append(f"unexplained_broker_order:{broker_key}")
                    exit_plan_id = _stable_id("mirror-exit-plan", key, symbol)
                    exit_payload = {
                        "origin": "broker_mirror_import",
                        "instrument": symbol,
                        "requires_new_entries_to_use_full_exit_contract": True,
                    }
                    exit_text = _json(exit_payload)
                    connection.execute(
                        "INSERT OR IGNORE INTO exit_plans (exit_plan_id,decision_id,handoff_id,"
                        "instrument,side,stop_price,take_profit_price,maximum_holding_sessions,"
                        "invalidation,state,payload_json,payload_sha256,created_at,updated_at) "
                        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (
                            exit_plan_id,
                            None,
                            None,
                            symbol,
                            order_side,
                            0.0,
                            0.0,
                            3,
                            "Imported broker record; canonical exit contract applies to new entries.",
                            "mirror_import",
                            exit_text,
                            _sha(exit_text),
                            order.submitted_at or snapshot.observed_at,
                            snapshot.observed_at,
                        ),
                    )
                    lane = "discovery"
                else:
                    exit_plan_id = str(existing["exit_plan_id"])
                    lane = str(existing["trading_lane"])
                reconciled_order_keys.add(key)
                submitted_at = _parse(str(order.submitted_at or ""))
                if (
                    submitted_at is not None
                    and (_now() - submitted_at).total_seconds() <= 900
                ):
                    recent_broker_order_symbols.add(symbol)
                state = str(order.status or "unknown").lower()
                order_payload = order.to_dict()
                order_text = _json(order_payload)
                connection.execute(
                    "INSERT INTO canonical_orders (order_key,handoff_id,decision_id,exit_plan_id,"
                    "instrument,side,quantity,trading_lane,state,broker_order_id_hash,"
                    "payload_json,payload_sha256,created_at,updated_at) VALUES "
                    "(?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(order_key) DO UPDATE SET "
                    "state=excluded.state,broker_order_id_hash=excluded.broker_order_id_hash,"
                    "payload_json=excluded.payload_json,payload_sha256=excluded.payload_sha256,"
                    "updated_at=excluded.updated_at",
                    (
                        key,
                        None,
                        None,
                        exit_plan_id,
                        symbol,
                        order_side,
                        _float(order.quantity or order.filled_quantity),
                        lane,
                        state,
                        broker_order_id_hash,
                        order_text,
                        _sha(order_text),
                        order.submitted_at or snapshot.observed_at,
                        snapshot.observed_at,
                    ),
                )
                if order.filled_quantity and order.filled_avg_price and order.filled_at:
                    # Mirror orders contain cumulative fills, not incremental executions.
                    # Retain replaced projections in the immutable event journal.
                    fill_id = _stable_id("aggregate-fill", key)
                    for prior in connection.execute("SELECT * FROM fills WHERE order_key=? AND fill_id<>?", (key, fill_id)).fetchall():
                        _event(connection, aggregate_type="order_fill_projection", aggregate_id=str(prior["fill_id"]),
                               event_type="cumulative_fill_projection_superseded", payload=dict(prior))
                    connection.execute("DELETE FROM fills WHERE order_key=? AND fill_id<>?", (key, fill_id))
                    fill_payload = {**order_payload, "measurement_basis": "cumulative_broker_order_fill_not_incremental_execution"}
                    fill_text = _json(fill_payload)
                    prior = connection.execute("SELECT * FROM fills WHERE fill_id=?", (fill_id,)).fetchone()
                    if prior and prior["payload_sha256"] != _sha(fill_text):
                        _event(connection, aggregate_type="order_fill_projection", aggregate_id=fill_id,
                               event_type="cumulative_fill_projection_updated", payload={"prior": dict(prior), "new": fill_payload})
                    connection.execute(
                        "INSERT INTO fills (fill_id,order_key,quantity,price,"
                        "occurred_at,payload_json,payload_sha256,created_at) VALUES (?,?,?,?,?,?,?,?) "
                        "ON CONFLICT(fill_id) DO UPDATE SET quantity=excluded.quantity,price=excluded.price,"
                        "occurred_at=excluded.occurred_at,payload_json=excluded.payload_json,payload_sha256=excluded.payload_sha256",
                        (
                            fill_id,
                            key,
                            _float(order.filled_quantity),
                            _float(order.filled_avg_price),
                            order.filled_at,
                            fill_text,
                            _sha(fill_text),
                            snapshot.observed_at,
                        ),
                    )
            if not bootstrap:
                for row in expected_active:
                    created = _parse(str(row["created_at"]))
                    if (
                        str(row["order_key"]) not in reconciled_order_keys
                        and created is not None
                        and (_now() - created).total_seconds() > 120
                    ):
                        blockers.append(
                            f"canonical_order_missing_at_broker:{row['order_key']}"
                        )
            for position in positions:
                symbol = str(position.instrument).upper()
                position_key = f"{position.paper_epoch_id or 'paper'}:{symbol}"
                lots = [row for row in order_history["open"] if row["instrument"] == symbol
                        and row["paper_epoch_id"] == position.paper_epoch_id
                        and row["broker_account_fingerprint"] == getattr(position, "broker_account_fingerprint", None)
                        and row["complete"] and abs(row["quantity"] - abs(_float(position.quantity))) < 1e-7]
                entries = lots[0]["entry_orders"] if len(lots) == 1 else []
                linked_rows = []
                for entry in entries:
                    matches = connection.execute(
                        "SELECT decision_id,handoff_id,exit_plan_id,trading_lane,side FROM canonical_orders "
                        "WHERE order_key=? OR broker_order_id_hash=?",
                        (entry.get("client_order_id"), entry.get("broker_order_id_hash") or _sha(entry["order_id"])),
                    ).fetchall()
                    if len(matches) == 1:
                        linked_rows.append(matches[0])
                linked = linked_rows[0] if linked_rows and len(linked_rows) == len(entries) and len({
                    (row["decision_id"], row["exit_plan_id"]) for row in linked_rows
                }) == 1 else None
                if linked is not None and not linked["decision_id"]:
                    linked = None
                if linked is None and not bootstrap:
                    blockers.append(f"position_entry_allocation_unresolved:{symbol}")
                existing_position = existing_open_positions.get(symbol)
                if linked is not None and existing_position and existing_position.get("exit_plan_id") != linked["exit_plan_id"]:
                    _event(connection, aggregate_type="position", aggregate_id=position_key,
                           event_type="position_entry_allocation_corrected",
                           payload={"prior": existing_position, "entry_order_ids": [entry["order_id"] for entry in entries],
                                    "exit_plan_id": linked["exit_plan_id"]})
                reference_price = _float(position.current_price or position.entry_price)
                entry_side = (
                    str(linked["side"]).lower()
                    if linked is not None and linked["side"]
                    else "buy"
                    if str(getattr(position, "direction", "long")).lower() == "long"
                    else "sell"
                )
                position_exit_plan_id = (
                    str(linked["exit_plan_id"])
                    if linked is not None and linked["exit_plan_id"]
                    else _stable_id("mirror-position-exit-plan", position_key, symbol)
                )
                exit_plan = connection.execute(
                    "SELECT stop_price,take_profit_price FROM exit_plans "
                    "WHERE exit_plan_id=?",
                    (position_exit_plan_id,),
                ).fetchone()
                imported_exit_missing = exit_plan is None or (
                    _float(exit_plan["stop_price"]) <= 0
                    or _float(exit_plan["take_profit_price"]) <= 0
                )
                if bootstrap and linked is None and reference_price > 0 and imported_exit_missing:
                    stop_price = (
                        reference_price * 0.98
                        if entry_side == "buy"
                        else reference_price * 1.02
                    )
                    take_profit_price = (
                        reference_price * 1.04
                        if entry_side == "buy"
                        else reference_price * 0.96
                    )
                    exit_payload = {
                        "origin": "broker_mirror_bootstrap",
                        "instrument": symbol,
                        "side": entry_side,
                        "reference_price": round(reference_price, 6),
                        "stop_price": round(stop_price, 6),
                        "take_profit_price": round(take_profit_price, 6),
                        "reward_to_risk": 2.0,
                        "maximum_holding_sessions": 3,
                        "invalidation": (
                            "Imported paper position: exit if price breaches the bounded "
                            "2% risk level or after three market sessions."
                        ),
                        "paper_only": True,
                    }
                    exit_text = _json(exit_payload)
                    connection.execute(
                        "INSERT INTO exit_plans (exit_plan_id,decision_id,handoff_id,"
                        "instrument,side,stop_price,take_profit_price,maximum_holding_sessions,"
                        "invalidation,state,payload_json,payload_sha256,created_at,updated_at) "
                        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(exit_plan_id) "
                        "DO UPDATE SET side=excluded.side,stop_price=excluded.stop_price,"
                        "take_profit_price=excluded.take_profit_price,"
                        "maximum_holding_sessions=excluded.maximum_holding_sessions,"
                        "invalidation=excluded.invalidation,state=excluded.state,"
                        "payload_json=excluded.payload_json,payload_sha256=excluded.payload_sha256,"
                        "updated_at=excluded.updated_at",
                        (
                            position_exit_plan_id,
                            None,
                            None,
                            symbol,
                            entry_side,
                            stop_price,
                            take_profit_price,
                            3,
                            exit_payload["invalidation"],
                            "monitoring",
                            exit_text,
                            _sha(exit_text),
                            position.opened_at or snapshot.observed_at,
                            snapshot.observed_at,
                        ),
                    )
                observed_quantity = _float(position.quantity)
                previous_quantity = (
                    _float(existing_position["quantity"])
                    if existing_position is not None
                    else None
                )
                quantity_matches = previous_quantity is not None and abs(
                    previous_quantity - observed_quantity
                ) <= max(0.000001, abs(observed_quantity) * 0.000001)
                if (
                    not bootstrap
                    and not quantity_matches
                    and symbol not in recent_broker_order_symbols
                ):
                    blockers.append(
                        f"unexplained_broker_position:{symbol}"
                        if previous_quantity is None
                        else f"unexplained_broker_position_quantity_change:{symbol}"
                    )
                position_payload = position.to_dict()
                position_text = _json(position_payload)
                if not bootstrap and imported_exit_missing:
                    position_exit_plan_id = None
                connection.execute(
                    "INSERT INTO positions (position_key,instrument,decision_id,handoff_id,"
                    "exit_plan_id,trading_lane,quantity,average_entry_price,current_price,"
                    "unrealized_pnl,state,payload_json,payload_sha256,opened_at,updated_at) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(position_key) DO UPDATE SET "
                    "decision_id=excluded.decision_id,handoff_id=excluded.handoff_id,"
                    "exit_plan_id=excluded.exit_plan_id,trading_lane=excluded.trading_lane,"
                    "quantity=excluded.quantity,average_entry_price=excluded.average_entry_price,"
                    "current_price=excluded.current_price,"
                    "unrealized_pnl=excluded.unrealized_pnl,state=excluded.state,"
                    "payload_json=excluded.payload_json,payload_sha256=excluded.payload_sha256,"
                    "opened_at=CASE WHEN positions.decision_id IS excluded.decision_id "
                    "THEN COALESCE(positions.opened_at,excluded.opened_at) ELSE excluded.opened_at END,"
                    "updated_at=excluded.updated_at",
                    (
                        position_key,
                        symbol,
                        linked["decision_id"] if linked else None,
                        linked["handoff_id"] if linked else None,
                        position_exit_plan_id,
                        str(linked["trading_lane"]) if linked else "discovery",
                        observed_quantity,
                        position.entry_price,
                        position.current_price,
                        _float(position.unrealized_pnl),
                        "open",
                        position_text,
                        _sha(position_text),
                        (min(entry["filled_at"] for entry in entries) if entries else position.opened_at) or snapshot.observed_at,
                        snapshot.observed_at,
                    ),
                )
                pending_plan = connection.execute("SELECT state FROM exit_plans WHERE exit_plan_id=?", (position_exit_plan_id,)).fetchone()
                if linked is not None and pending_plan and pending_plan["state"] == "close_requested":
                    exits = connection.execute(
                        "SELECT order_key,state FROM canonical_orders WHERE exit_plan_id=? AND order_key LIKE 'exit-order:%'",
                        (position_exit_plan_id,),
                    ).fetchall()
                    if exits and all(row["state"] in {"filled", "canceled", "cancelled", "expired", "rejected"} for row in exits):
                        connection.execute("UPDATE exit_plans SET state='monitoring',updated_at=? WHERE exit_plan_id=?",
                                           (snapshot.observed_at, position_exit_plan_id))
                        _event(connection, aggregate_type="exit_plan", aggregate_id=position_exit_plan_id,
                               event_type="exit_monitoring_resumed_after_terminal_readback",
                               payload={"remaining_quantity": observed_quantity, "terminal_orders": [dict(row) for row in exits]})
            for row in connection.execute("SELECT position_key,instrument FROM positions WHERE state='open'"):
                if str(row["instrument"]).upper() not in mirror_position_symbols:
                    connection.execute(
                        "UPDATE positions SET state='closed',updated_at=? WHERE position_key=?",
                        (snapshot.observed_at, str(row["position_key"])),
                    )
            accounting = order_history["closed"]
            for trade in closed_trades:
                outcome_id = str(trade.trade_id)
                payload = attributed_outcome(connection, trade.to_dict(), accounting.get(outcome_id))
                payload_text = _json(payload)
                prior = connection.execute(
                    "SELECT * FROM outcomes WHERE outcome_id=?", (outcome_id,)
                ).fetchone()
                if prior and prior["payload_sha256"] != _sha(payload_text):
                    _event(connection, aggregate_type="outcome", aggregate_id=outcome_id,
                           event_type="outcome_projection_corrected",
                           payload={"prior": dict(prior), "replacement": payload})
                connection.execute(
                    "INSERT INTO outcomes (outcome_id,position_key,decision_id,"
                    "strategy_id,strategy_version,trading_lane,state,realized_pnl,no_trade_return,"
                    "benchmark_return,payload_json,payload_sha256,observed_at) VALUES "
                    "(?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(outcome_id) DO UPDATE SET "
                    "decision_id=excluded.decision_id,strategy_id=excluded.strategy_id,"
                    "strategy_version=excluded.strategy_version,trading_lane=excluded.trading_lane,"
                    "realized_pnl=excluded.realized_pnl,payload_json=excluded.payload_json,"
                    "payload_sha256=excluded.payload_sha256",
                    (
                        outcome_id,
                        None,
                        payload["decision_id"],
                        payload["strategy_id"],
                        payload["strategy_version"],
                        payload["trading_lane"],
                        "closed",
                        payload["realized_pnl"],
                        0.0,
                        None,
                        payload_text,
                        _sha(payload_text),
                        trade.closed_at or snapshot.observed_at,
                    ),
                )
        expected = {
            "active_order_count": len(expected_active),
            "active_order_keys": sorted(str(row["order_key"]) for row in expected_active),
        }
        observed = {
            "mirror_observed_at": snapshot.observed_at,
            "order_count": len(orders),
            "open_order_count": sum(
                str(order.status or "").lower() in OPEN_ORDER_STATUSES for order in orders
            ),
            "position_count": len(positions),
            "closed_trade_count": len(closed_trades),
            "equity": snapshot.equity,
            "cash": snapshot.cash,
        }
        result = self.record_direct_reconciliation(
            phase=phase,
            expected=expected,
            observed=observed,
            blockers=blockers,
        )
        result["execution_owner_id"] = owner["owner_id"]
        return result

    def due_exit_candidates(self, *, current_time: datetime | None = None) -> list[dict[str, Any]]:
        from orchestrator.qadam_exchange_calendar import elapsed_sessions

        now = (current_time or _now()).astimezone(timezone.utc)
        calendar = read_json(runtime_dir(self.settings) / "alpaca_paper_mirror.json").get("market_calendar") or {}
        with self.store.connect() as connection:
            rows = connection.execute(
                "SELECT p.position_key,p.instrument,p.quantity,p.average_entry_price,"
                "p.current_price,p.trading_lane,p.opened_at,e.exit_plan_id,e.side,"
                "e.stop_price,e.take_profit_price,e.maximum_holding_sessions,e.invalidation,"
                "e.state AS exit_state,e.created_at AS exit_created_at "
                "FROM positions p JOIN exit_plans e ON e.exit_plan_id=p.exit_plan_id "
                "WHERE p.state='open' AND e.state IN "
                "('armed_before_entry','monitoring','exit_prepared','exit_submission_failed')"
            ).fetchall()
        candidates: list[dict[str, Any]] = []
        for row in rows:
            stop_price = _float(row["stop_price"])
            take_profit_price = _float(row["take_profit_price"])
            current_price = _float(row["current_price"])
            if stop_price <= 0 or take_profit_price <= 0 or current_price <= 0:
                continue
            entry_side = str(row["side"] or "buy").lower()
            stop_hit = (
                current_price <= stop_price
                if entry_side == "buy"
                else current_price >= stop_price
            )
            take_profit_hit = (
                current_price >= take_profit_price
                if entry_side == "buy"
                else current_price <= take_profit_price
            )
            opened_at = _parse(str(row["opened_at"] or row["exit_created_at"] or ""))
            sessions_elapsed = elapsed_sessions(opened_at, now, calendar)
            maximum_sessions = int(row["maximum_holding_sessions"] or 0)
            maximum_holding_reached = sessions_elapsed is not None and maximum_sessions > 0 and sessions_elapsed >= maximum_sessions
            trigger = (
                "stop_loss"
                if stop_hit
                else "take_profit"
                if take_profit_hit
                else "maximum_holding_period"
                if maximum_holding_reached
                else None
            )
            if trigger:
                candidates.append(
                    {
                        "position_key": str(row["position_key"]),
                        "exit_plan_id": str(row["exit_plan_id"]),
                        "symbol": str(row["instrument"]).upper(),
                        "quantity": abs(_float(row["quantity"])),
                        "entry_side": entry_side,
                        "exit_side": "sell" if entry_side == "buy" else "buy",
                        "trading_lane": str(row["trading_lane"]),
                        "current_price": current_price,
                        "stop_price": stop_price,
                        "take_profit_price": take_profit_price,
                        "sessions_elapsed": sessions_elapsed,
                        "maximum_holding_sessions": maximum_sessions,
                        "invalidation": str(row["invalidation"]),
                        "trigger": trigger,
                        "paper_only": True,
                    }
                )
        return candidates

    def prepare_exit_order(self, candidate: Mapping[str, Any]) -> dict[str, Any]:
        """Commit one deterministic exit intent before any broker mutation."""

        owner = self.assert_execution_owner()
        self.require_execution_available()
        exit_plan_id = str(candidate.get("exit_plan_id") or "")
        position_key = str(candidate.get("position_key") or "")
        instrument = str(candidate.get("symbol") or "").upper()
        side = str(candidate.get("exit_side") or "").lower()
        quantity = abs(_float(candidate.get("quantity")))
        trigger = str(candidate.get("trigger") or "unspecified")
        immutable_candidate = {
            "position_key": position_key,
            "exit_plan_id": exit_plan_id,
            "symbol": instrument,
            "exit_side": side,
            "quantity": quantity,
            "trading_lane": _trading_lane(candidate.get("trading_lane")),
            "trigger": trigger,
            "paper_only": True,
        }
        payload = {
            "purpose": "canonical_position_exit",
            "candidate": immutable_candidate,
            "paper_only": True,
            "live_capital_enabled": False,
        }
        payload_text = _json(payload)
        payload_sha = _sha(payload_text)
        timestamp = _iso()
        with self.store.transaction() as connection:
            prior_exits = connection.execute(
                "SELECT order_key,state FROM canonical_orders WHERE exit_plan_id=? AND order_key LIKE 'exit-order:%' ORDER BY order_key",
                (exit_plan_id,),
            ).fetchall()
            if any(row["state"] not in {"prepared", "submission_failed", "filled", "canceled", "cancelled", "expired", "rejected"} for row in prior_exits):
                raise ControlPlaneError("exit_submission_unresolved_at_broker")
            terminal = [row["order_key"] for row in prior_exits if row["state"] in {"filled", "canceled", "cancelled", "expired", "rejected"}]
            order_key = (_stable_id("exit-order", position_key, exit_plan_id, trigger, _sha(terminal))
                         if terminal else _stable_id("exit-order", position_key, exit_plan_id, trigger))
            row = connection.execute(
                "SELECT p.decision_id,p.handoff_id,p.exit_plan_id,p.instrument,p.quantity,"
                "p.state AS position_state,e.state AS exit_state FROM positions p "
                "JOIN exit_plans e ON e.exit_plan_id=p.exit_plan_id "
                "WHERE p.position_key=?",
                (position_key,),
            ).fetchone()
            hard_errors: list[str] = []
            if row is None:
                hard_errors.append("canonical_position_missing")
            else:
                if str(row["position_state"]) != "open":
                    hard_errors.append("canonical_position_not_open")
                if str(row["exit_plan_id"]) != exit_plan_id:
                    hard_errors.append("canonical_exit_plan_mismatch")
                if str(row["instrument"]).upper() != instrument:
                    hard_errors.append("canonical_exit_instrument_mismatch")
                if abs(abs(_float(row["quantity"])) - quantity) > max(
                    0.000001, quantity * 0.000001
                ):
                    hard_errors.append("canonical_exit_quantity_mismatch")
            if not exit_plan_id:
                hard_errors.append("canonical_exit_plan_missing")
            if side not in {"buy", "sell"}:
                hard_errors.append("canonical_exit_direction_missing")
            if quantity <= 0:
                hard_errors.append("canonical_exit_quantity_missing")
            if hard_errors:
                raise ControlPlaneError(
                    "exit_hard_evidence_missing:" + ",".join(hard_errors)
                )
            existing = connection.execute(
                "SELECT exit_plan_id,instrument,side,quantity,payload_sha256,state "
                "FROM canonical_orders WHERE order_key=?",
                (order_key,),
            ).fetchone()
            if existing is not None:
                if (
                    str(existing["exit_plan_id"]) != exit_plan_id
                    or str(existing["instrument"]).upper() != instrument
                    or str(existing["side"]).lower() != side
                    or abs(_float(existing["quantity"]) - quantity) > 0.000001
                    or str(existing["payload_sha256"]) != payload_sha
                ):
                    raise ControlPlaneError(
                        f"canonical_exit_order_identity_collision:{order_key}"
                    )
                if str(existing["state"]) == "submission_failed":
                    connection.execute(
                        "UPDATE canonical_orders SET state='prepared',updated_at=? "
                        "WHERE order_key=?",
                        (timestamp, order_key),
                    )
                return {
                    "order_key": order_key,
                    "exit_plan_id": exit_plan_id,
                    "instrument": instrument,
                    "already_prepared": True,
                }
            connection.execute(
                "INSERT INTO canonical_orders (order_key,handoff_id,decision_id,exit_plan_id,"
                "instrument,side,quantity,trading_lane,state,broker_order_id_hash,payload_json,"
                "payload_sha256,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    order_key,
                    row["handoff_id"],
                    row["decision_id"],
                    exit_plan_id,
                    instrument,
                    side,
                    quantity,
                    immutable_candidate["trading_lane"],
                    "prepared",
                    None,
                    payload_text,
                    payload_sha,
                    timestamp,
                    timestamp,
                ),
            )
            connection.execute(
                "UPDATE exit_plans SET state='exit_prepared',updated_at=? "
                "WHERE exit_plan_id=?",
                (timestamp, exit_plan_id),
            )
            _event(
                connection,
                aggregate_type="order",
                aggregate_id=order_key,
                event_type="exit_order_prepared",
                payload={**payload, "execution_owner_id": owner["owner_id"]},
                created_at=timestamp,
            )
        return {
            "order_key": order_key,
            "exit_plan_id": exit_plan_id,
            "instrument": instrument,
            "already_prepared": False,
        }

    def mark_order_submitting(self, order_key: str) -> None:
        self.assert_execution_owner()
        self.require_execution_available()
        with self.store.transaction() as connection:
            row = connection.execute(
                "SELECT state FROM canonical_orders WHERE order_key=?", (order_key,)
            ).fetchone()
            if row is None:
                raise ControlPlaneError("canonical_order_missing_before_submission")
            if str(row["state"]) != "prepared":
                raise ControlPlaneError(
                    f"canonical_order_not_submittable:{row['state']}"
                )
            connection.execute(
                "UPDATE canonical_orders SET state='submitting',updated_at=? "
                "WHERE order_key=?",
                (_iso(), order_key),
            )

    def assert_canonical_exit_submission(
        self,
        *,
        order_key: str,
        candidate: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Require a durable, exact exit prewrite before the broker close call."""

        owner = self.assert_execution_owner()
        self.require_execution_available()
        with self.store.connect() as connection:
            row = connection.execute(
                "SELECT order_key,exit_plan_id,instrument,side,quantity,state,payload_json "
                "FROM canonical_orders WHERE order_key=?",
                (order_key,),
            ).fetchone()
        if row is None:
            raise ControlPlaneError("canonical_exit_prewrite_missing")
        payload = json.loads(str(row["payload_json"]))
        errors: list[str] = []
        if str(row["state"]) != "submitting":
            errors.append("state_not_submitting")
        if payload.get("purpose") != "canonical_position_exit":
            errors.append("purpose_not_canonical_exit")
        if str(row["exit_plan_id"]) != str(candidate.get("exit_plan_id") or ""):
            errors.append("exit_plan_mismatch")
        if str(row["instrument"]).upper() != str(candidate.get("symbol") or "").upper():
            errors.append("instrument_mismatch")
        if str(row["side"]).lower() != str(candidate.get("exit_side") or "").lower():
            errors.append("side_mismatch")
        if abs(_float(row["quantity"]) - abs(_float(candidate.get("quantity")))) > 0.000001:
            errors.append("quantity_mismatch")
        if errors:
            raise ControlPlaneError(
                "canonical_exit_prewrite_invalid:" + ",".join(errors)
            )
        return {
            "order_key": str(row["order_key"]),
            "exit_plan_id": str(row["exit_plan_id"]),
            "execution_owner_id": str(owner["owner_id"]),
            "paper_only": True,
        }

    def record_exit_result(
        self,
        *,
        order_key: str,
        candidate: Mapping[str, Any],
        succeeded: bool,
        receipt: Mapping[str, Any] | None,
        failure_class: str | None,
    ) -> str:
        owner = self.assert_execution_owner()
        self.require_execution_available()
        timestamp = _iso()
        exit_plan_id = str(candidate.get("exit_plan_id") or "")
        payload = {
            "candidate": dict(candidate),
            "submission_result": {
                "succeeded": succeeded,
                "receipt": dict(receipt or {}),
                "failure_class": failure_class,
            },
            "execution_owner_id": owner["owner_id"],
            "paper_only": True,
        }
        payload_text = _json(payload)
        with self.store.transaction() as connection:
            prepared = connection.execute(
                "SELECT exit_plan_id,payload_json FROM canonical_orders WHERE order_key=?",
                (order_key,),
            ).fetchone()
            if prepared is None or str(prepared["exit_plan_id"]) != exit_plan_id:
                raise ControlPlaneError("exit_result_without_prepared_order")
            original = json.loads(str(prepared["payload_json"]))
            original["submission_result"] = payload["submission_result"]
            original["execution_owner_id"] = owner["owner_id"]
            result_text = _json(original)
            connection.execute(
                "UPDATE canonical_orders SET state=?,broker_order_id_hash=?,payload_json=?,"
                "payload_sha256=?,updated_at=? WHERE order_key=?",
                (
                    "submitted" if succeeded else "submission_failed",
                    (receipt or {}).get("broker_order_id_hash"),
                    result_text,
                    _sha(result_text),
                    timestamp,
                    order_key,
                ),
            )
            connection.execute(
                "UPDATE exit_plans SET state=?,payload_json=?,payload_sha256=?,updated_at=? "
                "WHERE exit_plan_id=?",
                (
                    "close_requested" if succeeded else "exit_submission_failed",
                    payload_text,
                    _sha(payload_text),
                    timestamp,
                    exit_plan_id,
                ),
            )
            _event(
                connection,
                aggregate_type="exit_plan",
                aggregate_id=exit_plan_id,
                event_type="exit_close_requested" if succeeded else "exit_close_failed",
                payload=payload,
                created_at=timestamp,
            )
        if not succeeded and failure_class not in {"http_400", "http_403", "http_404", "http_422"}:
            self.set_execution_frozen(
                reason=f"ambiguous_exit_submission:{failure_class or 'unknown'}"
            )
        return order_key

    def record_liveness_cycle(
        self,
        *,
        generation_id: str,
        decisions: list[Mapping[str, Any]],
        submitted_order_count: int,
        market_session_date: str | None = None,
    ) -> dict[str, Any]:
        rows: list[dict[str, Any]] = []
        for decision in decisions:
            final_state = str(decision.get("final_state") or "")
            reason = str(
                decision.get("primary_root_cause")
                or decision.get("final_reason")
                or final_state
                or ""
            )
            rows.append(
                {
                    "setup_id": decision.get("setup_id"),
                    "instrument": decision.get("execution_symbol") or decision.get("instrument"),
                    "trading_lane": _trading_lane(decision.get("evidence_class")),
                    "final_state": final_state or "unexplained",
                    "stopped_at": decision.get("primary_root_cause") or final_state or "unexplained",
                    "reason": reason or "No terminal explanation was recorded.",
                }
            )
        advanced_states = {
            "paper-review-candidate",
            "experimental-paper-review-candidate",
            "validated_paper_review_candidate",
            "experimental_paper_review_candidate",
        }
        advanced_count = sum(row["final_state"] in advanced_states for row in rows)
        unexplained = [row for row in rows if row["final_state"] == "unexplained"]
        if unexplained:
            status = "degraded_unexplained_stoppage"
        elif submitted_order_count > 0:
            status = "advanced_to_paper_order"
        elif advanced_count > 0:
            status = "advanced_to_paper_review"
        elif rows:
            status = "idle_explained"
        else:
            status = "idle_no_setups"
        timestamp = _iso()
        session_date = market_session_date or timestamp[:10]
        cycle_id = _stable_id("liveness", session_date, generation_id, _sha(rows))
        payload = {
            "schema_version": SCHEMA_VERSION,
            "cycle_id": cycle_id,
            "generated_at": timestamp,
            "market_session_date": session_date,
            "generation_id": generation_id,
            "status": status,
            "setup_count": len(rows),
            "advanced_count": advanced_count,
            "submitted_order_count": submitted_order_count,
            "setup_outcomes": rows,
            "silence_can_indicate_health": False,
            "paper_only": True,
            "live_capital_enabled": False,
        }
        payload_text = _json(payload)
        with self.store.transaction() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO liveness_cycles (cycle_id,market_session_date,"
                "generation_id,status,setup_count,advanced_count,payload_json,payload_sha256,"
                "created_at) VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    cycle_id,
                    session_date,
                    generation_id,
                    status,
                    len(rows),
                    advanced_count,
                    payload_text,
                    _sha(payload_text),
                    timestamp,
                ),
            )
            _event(
                connection,
                aggregate_type="liveness_cycle",
                aggregate_id=cycle_id,
                event_type=status,
                payload=payload,
                created_at=timestamp,
            )
        atomic_write_text(
            runtime_dir(self.settings) / LIVENESS_ARTIFACT,
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
        )
        return payload

    def rebuild_cohorts(self) -> list[dict[str, Any]]:
        with self.store.transaction() as connection:
            grouped = defaultdict(list)
            for record in connection.execute("SELECT payload_json FROM outcomes WHERE state='closed'"):
                for lot in learning_lots([json.loads(record[0])]):
                    key = (lot.get("strategy_id") or "strategy-unclassified",
                           lot.get("strategy_version") or "unversioned", lot.get("trading_lane") or "discovery")
                    grouped[key].append(lot)
            # Cohorts are disposable projections; old group membership must not survive a repair.
            connection.execute("DELETE FROM strategy_cohorts")
            cohorts: list[dict[str, Any]] = []
            for (strategy, version, lane), outcomes in sorted(grouped.items()):
                row = {"strategy_id": strategy, "strategy_version": version, "trading_lane": lane}
                metrics = cohort_metrics(outcomes)
                n = metrics["independent_outcome_count"]
                lane = str(row["trading_lane"])
                minimum = 20 if lane == "validated" else 10
                eligible = n >= minimum and metrics["benchmark_comparison_available"]
                state = "eligible_for_review" if eligible else "evidence_accumulating"
                cohort_id = _stable_id(
                    "cohort", row["strategy_id"], row["strategy_version"], lane, "all-regimes"
                )
                payload = {
                    "cohort_id": cohort_id,
                    "strategy_id": row["strategy_id"],
                    "strategy_version": row["strategy_version"],
                    "trading_lane": lane,
                    "regime": "all-regimes",
                    "state": state,
                    "independent_outcome_count": n,
                    "minimum_outcomes_for_review": minimum,
                    **metrics,
                    "benchmark_state": "measured"
                    if metrics["benchmark_comparison_available"]
                    else "pending_provider_matched_outcome",
                    "automatic_authority_mutation_allowed": False,
                    "next_action": "review promotion, modification or retirement proposal"
                    if eligible
                    else "collect independent paper outcomes",
                }
                payload_text = _json(payload)
                timestamp = _iso()
                connection.execute(
                    "INSERT INTO strategy_cohorts (cohort_id,strategy_id,strategy_version,"
                    "trading_lane,regime,state,independent_outcome_count,net_expectancy,"
                    "no_trade_delta,benchmark_delta,payload_json,payload_sha256,created_at,"
                    "updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(cohort_id) "
                    "DO UPDATE SET state=excluded.state,independent_outcome_count=excluded.independent_outcome_count,"
                    "net_expectancy=excluded.net_expectancy,no_trade_delta=excluded.no_trade_delta,"
                    "benchmark_delta=excluded.benchmark_delta,payload_json=excluded.payload_json,"
                    "payload_sha256=excluded.payload_sha256,updated_at=excluded.updated_at",
                    (
                        cohort_id,
                        row["strategy_id"],
                        row["strategy_version"],
                        lane,
                        "all-regimes",
                        state,
                        n,
                        metrics["net_expectancy"],
                        metrics["no_trade_delta"],
                        metrics["benchmark_delta"],
                        payload_text,
                        _sha(payload_text),
                        timestamp,
                        timestamp,
                    ),
                )
                cohorts.append(payload)
            return cohorts

    def summary(self) -> dict[str, Any]:
        with self.store.connect() as connection:
            tables = (
                "hypotheses",
                "decision_transactions",
                "risk_decisions",
                "canonical_orders",
                "fills",
                "positions",
                "exit_plans",
                "outcomes",
                "strategy_cohorts",
                "reconciliation_runs",
                "liveness_cycles",
                "operating_events",
            )
            counts = {
                table: int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
                for table in tables
            }
            lane_counts = {
                str(row["trading_lane"]): int(row["count"])
                for row in connection.execute(
                    "SELECT trading_lane,COUNT(*) AS count FROM canonical_orders GROUP BY trading_lane"
                )
            }
            latest_reconciliation = connection.execute(
                "SELECT payload_json FROM reconciliation_runs ORDER BY created_at DESC LIMIT 1"
            ).fetchone()
            latest_liveness = connection.execute(
                "SELECT payload_json FROM liveness_cycles ORDER BY created_at DESC LIMIT 1"
            ).fetchone()
            lease = connection.execute(
                "SELECT owner_id,state,heartbeat_at,expires_at FROM execution_owner_leases "
                "WHERE lease_name=?",
                (EXECUTION_LEASE_NAME,),
            ).fetchone()
            outcome_rows = [json.loads(row[0]) for row in connection.execute("SELECT payload_json FROM outcomes")]
        execution_state = self.execution_state()
        health = read_operating_health(runtime_dir(self.settings))
        projection = {
            "schema_version": SCHEMA_VERSION,
            "artifact_type": "qadam_operating_ledger_summary",
            "generated_at": _iso(),
            "status": "degraded_execution_frozen"
            if int(execution_state.get("frozen") or 0) == 1
            else "operational" if health["status"] == "healthy" else "degraded_canonical_health",
            "health_dimensions": health,
            "outcome_accounting": {
                "closed_record_count": len(outcome_rows),
                "exact_entry_attribution_count": sum(row.get("attribution_status") == "exact_entry_decision" for row in outcome_rows),
                "exact_multi_entry_allocation_count": sum(row.get("attribution_status") == "exact_entry_allocations" for row in outcome_rows),
                "unresolved_attribution_count": sum(row.get("attribution_status") not in {"exact_entry_decision", "exact_entry_allocations"} for row in outcome_rows),
                "modelled_cost_lot_count": sum(row.get("cost_basis") == "modelled" for row in learning_lots(outcome_rows)),
                "gross_reconstructed_count": sum(row.get("accounting_status") == "gross_reconstructed" for row in outcome_rows),
                "cost_measured_count": sum(row.get("costs_measured") is True for row in outcome_rows),
                "placeholder_zero_is_measurement": False,
                "gross_estimates_are_not_net_edge_evidence": True,
            },
            "database": {
                "name": self.store.path.name,
                "authoritative": True,
                "json_is_projection_only": True,
                "integrity": self.store.integrity_report(),
            },
            "execution_owner": dict(lease) if lease else {"state": "idle"},
            "execution_state": execution_state,
            "counts": counts,
            "trading_lanes": {
                "validated": lane_counts.get("validated", 0),
                "discovery": lane_counts.get("discovery", 0),
            },
            "latest_reconciliation": json.loads(str(latest_reconciliation["payload_json"]))
            if latest_reconciliation
            else None,
            "latest_liveness": json.loads(str(latest_liveness["payload_json"]))
            if latest_liveness
            else None,
            "authority": {
                "single_execution_owner": True,
                "paper_only": True,
                "live_capital_enabled": False,
                "direct_auxiliary_broker_writes_allowed": False,
                "proof_credit_allowed": False,
            },
        }
        return projection

    def build_and_write_summary(self) -> dict[str, Any]:
        # Publish the same checked snapshot that the caller reports. Rebuilding
        # here repeats a full SQLite integrity scan under the execution lease.
        projection = self.summary()
        destination = runtime_dir(self.settings) / PROJECTION_ARTIFACT
        atomic_write_text(
            destination,
            json.dumps(projection, indent=2, sort_keys=True) + "\n",
        )
        return projection

    def write_summary(self) -> Path:
        self.build_and_write_summary()
        return runtime_dir(self.settings) / PROJECTION_ARTIFACT


__all__ = [
    "ACTIVE_ORDER_STATES",
    "EXECUTION_LEASE_NAME",
    "EXECUTION_OWNER_ID_ENV",
    "EXECUTION_OWNER_TOKEN_ENV",
    "ExecutionLease",
    "ExecutionOwnerError",
    "LIVENESS_ARTIFACT",
    "OperatingLedger",
    "execution_owner_process_state",
    "PROJECTION_ARTIFACT",
    "SCHEMA_VERSION",
]
