"""Prospective source-dependent setup/abstention studies, without trade authority.

This measures a frozen policy's contribution, not the causal value of a vendor
or a retrained model. Full model/source-removal ablations remain separate studies.
"""

from datetime import datetime, timezone
from hashlib import sha256
import json
import math


def _json(row):
    return json.dumps(row, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _time(value):
    try:
        value = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return value if value.tzinfo else None
    except ValueError:
        return None


def _insert(connection, identity, kind, component, row, at):
    payload = _json(row)
    previous = connection.execute("SELECT payload_json FROM operating_events WHERE event_id=?", (identity,)).fetchone()
    if previous:
        prior = json.loads(previous[0])
        volatile = {"registered_at"} if kind == "component_study" else {"pair_recorded_at"} if kind == "component_pair" else set()
        if {k: v for k, v in row.items() if k not in volatile} != {k: v for k, v in prior.items() if k not in volatile}:
            raise ValueError("component_study_immutable_identity_conflict")
        return 0
    return connection.execute("INSERT INTO operating_events VALUES (?,?,?,?,?,?,?)",
        (identity, kind, component, kind, payload, sha256(payload.encode()).hexdigest(), at)).rowcount


def register_studies(store, hypotheses, akber_inputs):
    """Register before future decisions; existing decisions cannot receive credit."""
    versions = {row.get("hypothesis_id"): row.get("strategy_version_id") for row in hypotheses}
    at = datetime.now(timezone.utc).isoformat()
    count = 0
    with store.transaction() as connection:
        for packet in akber_inputs:
            version = versions.get(packet.get("hypothesis_id"))
            if not version:
                continue
            for source in sorted(set(packet.get("current_trigger_sources", [])))[:3]:
                component = "source:" + source
                identity = "component-study:" + sha256(f"{component}:{version}:dependent-setup.1".encode()).hexdigest()
                row = {"registration_id": identity, "component_id": component,
                    "frozen_with_version": version, "frozen_without_version": "abstain.1",
                    "scope": "source_dependent_setup_vs_abstention", "registered_at": at,
                    "risk_budget": "equal_unit_notional_ceiling", "cash_return": 0.0,
                    "component_causal_value_proven": False, "paper_order_allowed": False}
                count += _insert(connection, identity, "component_study", component, row, at)
    return count


def record_study_decisions(store, decisions):
    now = datetime.now(timezone.utc)
    count = 0
    with store.transaction() as connection:
        studies = [json.loads(row[0]) for row in connection.execute(
            "SELECT payload_json FROM operating_events WHERE aggregate_type='component_study' ORDER BY created_at DESC LIMIT 300")]
        for decision in decisions:
            start, due = _time(decision.get("decision_at")), _time(decision.get("outcome_due_at"))
            if not start or not due or not start <= now < due or decision.get("simulated_elapsed_time") is not False:
                continue
            frozen = decision.get("frozen_decision_payload") or {}
            # Use the producer's canonical hashing convention, not a boolean claim.
            from orchestrator.qadam_operator_ready_common import sha256_json
            if sha256_json(frozen) != decision.get("frozen_decision_hash"):
                continue
            for study in studies:
                if (study["frozen_with_version"] != decision.get("strategy_version_id")
                        or _time(study["registered_at"]) > start
                        or study["component_id"][7:] not in frozen.get("current_trigger_sources", [])):
                    continue
                identity = "component-pair:" + sha256(f"{study['registration_id']}:{decision['decision_id']}".encode()).hexdigest()
                row = {**study, "pair_id": identity, "decision_id": decision["decision_id"],
                    "decision_hash": decision["frozen_decision_hash"],
                    "event_available_at": decision["decision_at"], "pair_recorded_at": now.isoformat(),
                    "independent_event_id": decision.get("economic_signal_identity_id"),
                    "direction": frozen.get("direction"), "entry_observation": frozen.get("entry_observation"),
                    "outcome_due_at": decision["outcome_due_at"], "evaluation_contract": frozen.get("evaluation_contract")}
                count += _insert(connection, identity, "component_pair", study["component_id"], row, now.isoformat())
    return count


def record_study_outcomes(store, outcomes):
    now = datetime.now(timezone.utc)
    count = 0
    with store.transaction() as connection:
        pairs = [json.loads(row[0]) for row in connection.execute(
            "SELECT payload_json FROM operating_events WHERE aggregate_type='component_pair' ORDER BY created_at DESC LIMIT 3000")]
        by_decision = {row.get("decision_id"): row for row in outcomes}
        for pair in pairs:
            outcome = by_decision.get(pair["decision_id"], {})
            observation = outcome.get("outcome_observation") or {}
            entry = pair.get("entry_observation") or {}
            end = _time(observation.get("available_at"))
            observed = _time(observation.get("observed_at"))
            registered = _time(pair["pair_recorded_at"])
            entry_observed, entry_available = _time(entry.get("observed_at")), _time(entry.get("available_at"))
            if (not end or not observed or not registered or not registered < observed <= end <= now
                    or not entry_observed or not entry_available
                    or not entry_observed <= entry_available <= _time(pair["event_available_at"])
                    or observed < _time(pair["outcome_due_at"])
                    or any(row.get("provider_backed") is not True or row.get("sample") or row.get("fixture")
                           for row in (entry, observation))
                    or entry.get("instrument") != observation.get("instrument")):
                continue
            price, exit_price = entry.get("price"), observation.get("price")
            cost = (pair.get("evaluation_contract") or {}).get("cost_bps")
            if (any(type(x) not in (int, float) or not math.isfinite(x) for x in (price, exit_price, cost))
                    or min(price, exit_price) <= 0 or cost < 0 or pair["direction"] not in {"long", "short"}):
                continue
            net = (exit_price / price - 1) * (1 if pair["direction"] == "long" else -1) - cost / 10000
            row = {**pair, "completed_at": end.isoformat(), "outcome_id": outcome.get("outcome_id"),
                "outcome_observation": observation, "with_component_net_return": net,
                "without_component_net_return": 0.0, "decision_changed": True,
                "registration_receipt_verified": True, "provider_backed_outcome": True,
                "same_event_same_window": True, "same_risk_budget": True,
                "hypotheses_mutated": False, "holdout_reused": False,
                "component_causal_value_proven": False}
            count += _insert(connection, "component-result:" + pair["pair_id"], "component_result",
                             pair["component_id"], row, now.isoformat())
    return count


def verified_results(connection, rows):
    verified = []
    for row in rows:
        registration = connection.execute("SELECT payload_json FROM operating_events WHERE event_id=? AND aggregate_type='component_study'", (row.get("registration_id"),)).fetchone()
        pair = connection.execute("SELECT payload_json FROM operating_events WHERE event_id=? AND aggregate_type='component_pair'", (row.get("pair_id"),)).fetchone()
        if not registration or not pair:
            continue
        registered, frozen = json.loads(registration[0]), json.loads(pair[0])
        if all(row.get(key) == value for key, value in frozen.items()) and all(frozen.get(key) == value for key, value in registered.items()):
            verified.append(row)
    return verified
