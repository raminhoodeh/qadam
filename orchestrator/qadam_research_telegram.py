"""Evidence-grounded research notifications; never a trading authority.

The existing five-minute learning scheduler owns this bounded delivery pass.
Refresh timestamps and source availability alone are not research discoveries.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import fcntl
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import urllib.error
from zoneinfo import ZoneInfo

from orchestrator.config import Settings
from orchestrator.daily_telegram_learning_brief import _safe_text, _telegram_send
from orchestrator.secrets import secret_value


STATE = "qadam_research_telegram_state.json"
STATUS = "qadam_research_telegram_status.json"
MAX_SENDS = 3
RETENTION_DAYS = 30
BOUNDARY = {
    "read_only_research": True,
    "paper_order_created": False,
    "broker_write_allowed": False,
    "strategy_mutation_allowed": False,
    "risk_approval_allowed": False,
    "telegram_command_path_enabled": False,
    "live_capital_enabled": False,
}


def _stamp(value):
    try:
        result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return result.astimezone(timezone.utc) if result.tzinfo else None
    except (ValueError, TypeError):
        return None


def _fresh(value, now, seconds=3600):
    stamp = _stamp(value)
    return stamp is not None and 0 <= (now - stamp).total_seconds() <= seconds


def _digest(value):
    return sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def _text(value, limit=240):
    return " ".join(str(value or "").split())[:limit]


def _number(value):
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError):
        return None


def _read(path, *, lines=False):
    if not path.exists():
        return [] if lines else {}
    # Reject partial generations instead of silently skipping corrupt evidence.
    raw = path.read_text(encoding="utf-8")
    result = (
        [json.loads(line) for line in raw.splitlines() if line.strip()]
        if lines
        else json.loads(raw)
    )
    if not isinstance(result, list if lines else dict):
        raise ValueError("research_notification_input_shape")
    return result


def _atomic(path, payload):
    temporary = path.with_suffix(".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, sort_keys=True, allow_nan=False)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def _events(runtime, now):
    rows = _read(runtime / "qadam_current_event_triggers.jsonl", lines=True)
    return [
        row
        for row in rows
        if isinstance(row, dict)
        and row.get("sample_or_fixture") is False
        and row.get("trigger_state") == "active"
        and row.get("source_event_refs")
        and row.get("source_keys")
        and _stamp(row.get("publication_at")) is not None
        and _stamp(row.get("publication_at")) <= now
        and _fresh(row.get("generated_at"), now)
        and (_stamp(row.get("expires_at")) or now) > now
    ]


def _event_material(row):
    causal = row.get("causal_classification") or {}
    return {
        "summary": _text(row.get("event_summary")),
        "published_at": row.get("publication_at"),
        "sources": sorted(row.get("source_keys") or []),
        "refs": sorted(row.get("source_event_refs") or []),
        "mechanism": _text(causal.get("mechanism")),
        "direction": _text(row.get("direction_clue")),
    }


def _source_names(values):
    names = {"rss": "news feeds", "sec_edgar": "SEC filings", "earnings": "earnings reports"}
    return ", ".join(names.get(str(value), _text(value).replace("_", " ")) for value in values)


def pattern_observations(runtime, now):
    dashboard = _read(runtime / "qadam_pattern_discovery_dashboard.json")
    if dashboard.get("public_safe") is not True or not _fresh(dashboard.get("generated_at"), now):
        return {}, "pattern_evidence_unavailable_or_stale"
    events = _events(runtime, now)
    observations = {}
    for row in dashboard.get("relationships", []):
        fresh = row.get("freshness") or {}
        if not row.get("pattern_id") or not _fresh(fresh.get("observed_at"), now, 1800):
            continue
        if fresh.get("is_current") is not True:
            continue
        symbols = sorted(row.get("instrument_symbols") or [])
        history = row.get("historical_evidence") or {}
        material = {
            "question": _text(row.get("detected_signal")),
            "direction": _text(row.get("direction")),
            "symbols": symbols,
            "stage": _text(row.get("current_stage")),
            "validated": history.get("validated_edge") is True,
            "net_expectancy": _number(history.get("net_expectancy_after_costs")),
            "holdout": _text(history.get("holdout_state")),
            "quantum_summary": _text((row.get("quantum_review") or {}).get("summary")),
        }
        linked = [
            _event_material(event)
            for event in events
            if event.get("strategy_family_id") == row.get("strategy_family_id")
            and set(symbols).intersection(event.get("affected_instruments") or [])
            and event.get("direction_clue")
            in {
                "long",
                "short",
                "bullish",
                "bearish",
                "up",
                "down",
                "positive_for_strategy_expression",
                "negative_for_strategy_expression",
            }
            and (event.get("causal_classification") or {}).get("mechanism")
            not in {None, "", "causal_mechanism_unresolved"}
        ]
        observations[row["pattern_id"]] = {
            "material": material,
            "events": {_digest(event): event for event in linked},
            "title": _text(row.get("title")),
            "score": _number(row.get("raw_pattern_score")),
            "observed_at": fresh["observed_at"],
            "fresh_sources": row.get("fresh_source_count", 0),
            "total_sources": row.get("contributing_source_count", 0),
            "limitation": _text(history.get("summary")),
        }
    return observations, None if observations else "no_fresh_pattern_observations"


def pattern_message(observation, new_events, *, new_pattern=False):
    material = observation["material"]
    label = "New research candidate" if new_pattern else "Pattern evidence update"
    paragraphs = [
        f"{label}: {observation['title']}. Instruments: {', '.join(material['symbols'])}."
    ]
    if material["question"]:
        paragraphs.append(f"Relationship under review: {material['question']}")
    if new_events:
        event_copy = [
            f"{_source_names(event['sources'])} ({event['published_at'][:10]}): {event['summary']}"
            for event in list(new_events.values())[:2]
        ]
        paragraphs.append("New linked evidence: " + "; ".join(event_copy) + ".")
        paragraphs.append(
            "This is a catalyst to test against market outcomes, not confirmation that prices will follow it."
        )
    else:
        paragraphs.append(
            f"Recorded research state: {material['stage']}. {observation['limitation']}"
        )
    score = observation["score"]
    if score is not None:
        paragraphs.append(
            f"Research score {score:.3f} (not a probability of profit); "
            f"{observation['fresh_sources']}/{observation['total_sources']} sources fresh."
        )
    if not material["validated"]:
        paragraphs.append(
            "A repeatable after-cost edge remains unproven. Any paper entry is decided separately by the trading pipeline."
        )
    return "\n\n".join(paragraphs)


def strategy_snapshot(runtime, now):
    hypotheses = _read(runtime / "qadam_strategy_hypotheses_v3.jsonl", lines=True)
    events = {row.get("trigger_id"): row for row in _events(runtime, now)}
    decisions = _read(runtime / "qadam_router_v3_decisions.jsonl", lines=True)
    rows = []
    for hypothesis in hypotheses:
        freshness = hypothesis.get("freshness") or {}
        if not _fresh(hypothesis.get("generated_at"), now):
            continue
        if (_stamp(freshness.get("expires_at")) or now) <= now:
            continue
        direction = hypothesis.get("direction_horizon") or {}
        identity = hypothesis.get("candidate_identity_material") or {}
        proxy = (hypothesis.get("instrument_proxy_mapping") or {}).get("execution_proxy")
        if not proxy or direction.get("direction") not in {"long", "short"}:
            continue
        basis = [
            events[key]
            for key in direction.get("direction_resolution_evidence_ids", [])
            if key in events
        ]
        invalidation = hypothesis.get("invalidation_exit") or {}
        judgment = hypothesis.get("market_judgment") or {}
        matched_decisions = [
            row
            for row in decisions
            if isinstance(row, dict)
            and row.get("hypothesis_id") == hypothesis.get("hypothesis_id")
            and row.get("hypothesis_id")
            and (row.get("lineage") or {}).get("strategy_version_id")
            == hypothesis.get("strategy_version_id")
            and _fresh(row.get("generated_at"), now)
        ]
        decision = max(matched_decisions, key=lambda row: row["generated_at"], default={})
        rows.append(
            {
                "symbol": proxy,
                "direction": direction["direction"],
                "horizon": _text(direction.get("horizon")).replace("_", " "),
                "family": _text(identity.get("strategy_family_id")),
                "version": hypothesis.get("strategy_version_id"),
                "state": _text(hypothesis.get("hypothesis_state")).replace("_", " "),
                "experimental": hypothesis.get("evidence_class") == "experimental_unvalidated",
                "basis": [_event_material(event) for event in basis[:2]],
                "entry_authorized": (hypothesis.get("entry_concept") or {}).get("entry_authorized")
                is True,
                "invalidation": [
                    _text(item, 130) for item in invalidation.get("invalidation_conditions", [])[:2]
                ],
                "exit": [_text(item, 100) for item in invalidation.get("exit_conditions", [])[:2]],
                "consequence": _text(judgment.get("primary_consequence")).replace("_", " "),
                "vetoes": sorted(decision.get("hard_vetoes") or []),
                "return_class": judgment.get("expected_return_class"),
            }
        )
    rows.sort(key=lambda row: (row["symbol"], row["family"]))
    router = _read(runtime / "qadam_router_v3_why_not_trading_now.json")
    router_fresh = _fresh(router.get("generated_at"), now)
    return {
        "strategies": rows,
        "router_reason": _text(router.get("primary_reason")) if router_fresh else None,
        "router_state": router.get("current_router_state") if router_fresh else None,
    }


def strategy_message(snapshot, previous, local_date):
    # Compare economic content, not periodically regenerated hypothesis IDs/timestamps.
    semantic = {
        "strategies": snapshot["strategies"],
        "router_state": snapshot["router_state"],
    }
    fingerprint = _digest(semantic)
    unchanged = previous is not None and fingerprint == previous.get("fingerprint")
    paragraphs = [
        f"Qadam daily strategy update | {local_date}. "
        + (
            "The recorded stance and evidence are unchanged since the previous strategy update."
            if unchanged
            else "Current evidence-based paper-trading stance:"
        )
    ]
    included = 0
    for row in snapshot["strategies"][:3]:
        stage = (
            "unvalidated paper hypothesis"
            if row["experimental"]
            else "recorded strategy hypothesis"
        )
        sentence = (
            f"{row['symbol']}: {row['direction']} over {row['horizon']}; {stage}, {row['state']}."
        )
        if row["basis"]:
            event = row["basis"][0]
            sentence += f" Evidence from {_source_names(event['sources'])} ({event['published_at'][:10]}): {event['summary']}."
        else:
            sentence += " No fresh, linked directional catalyst is available in the current evidence snapshot."
        if not row["entry_authorized"]:
            sentence += " This hypothesis does not authorize an entry; current liquidity, exposure and execution checks still decide it."
        if row["consequence"]:
            sentence += f" Latest assessment: {row['consequence']}."
        if "duplicate_exposure_conflict" in row["vetoes"]:
            sentence += " Qadam already has conflicting exposure, so this setup cannot add another position."
        elif row["vetoes"]:
            sentence += (
                " Entry is blocked by "
                + ", ".join(_text(value).replace("_", " ") for value in row["vetoes"][:2])
                + "."
            )
        if row["return_class"] == "unestimated_discovery_experiment":
            sentence += " After-cost profitability is still unestimated; this remains a small paper experiment."
        if row["invalidation"]:
            sentence += " Reconsider if " + " or ".join(row["invalidation"]) + "."
        if row["exit"]:
            sentence += " Exit policy: " + "; ".join(row["exit"]) + "."
        if sum(len(part) for part in paragraphs) + len(sentence) > 3200:
            break
        paragraphs.append(sentence)
        included += 1
    if len(snapshot["strategies"]) > included:
        paragraphs.append(
            f"{len(snapshot['strategies']) - included} additional hypotheses remain in the dashboard."
        )
    if not snapshot["strategies"]:
        paragraphs.append(
            "No fresh directional strategy hypothesis is available to explain. This does not mean existing holdings should be closed; their recorded exit policies remain separate."
        )
    paragraphs.append(
        "Current routing: "
        + (
            snapshot["router_reason"]
            or "status unavailable or stale; no execution claim can be confirmed."
        )
    )
    paragraphs.append(
        "This note reports the strategy state; it does not change a strategy, approve a trade or claim a proven return."
    )
    return "\n\n".join(paragraphs), fingerprint


def _enqueue(state, key, kind, body, now, expires, **extra):
    if key not in state["outbox"]:
        safe = len(body) <= 3900 and _safe_text("", body)
        state["outbox"][key] = {
            "kind": kind,
            "body": body,
            "created_at": now.isoformat(),
            "expires_at": expires.isoformat(),
            "status": "pending" if safe else "unsafe",
            "attempts": 0,
            **extra,
        }


def notification_health(runtime, now=None):
    """Independent reporting health for the existing three-hour Telegram check."""
    now = now or datetime.now(timezone.utc)
    try:
        status = _read(Path(runtime) / STATUS)
        if not _fresh(status.get("generated_at"), now, 900):
            return "stale", "Research messaging: its five-minute check is missing or stale."
        if status.get("status") != "healthy":
            return (
                "needs_attention",
                "Research messaging: needs attention; delivery or evidence freshness has not been confirmed.",
            )
        return (
            "healthy",
            "Research messaging: current; new-pattern alerts and the daily strategy note are enabled.",
        )
    except (OSError, ValueError):
        return "unavailable", "Research messaging: status unavailable."


def run_research_notifications(settings=None, *, live=False, now=None, sender=None):
    settings = settings or Settings.from_env()
    now = now or datetime.now(timezone.utc)
    runtime = Path(settings.runtime_dir)
    runtime.mkdir(parents=True, exist_ok=True)
    with (runtime / ".research_telegram.lock").open("a+") as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return {"status": "already_running", **BOUNDARY}
        return _run_locked(settings, runtime, now, live, sender or _telegram_send)


def _run_locked(settings, runtime, now, live, sender):
    status = {
        "generated_at": now.isoformat(),
        "status": "healthy",
        "sent_this_pass": 0,
        "blockers": [],
        **BOUNDARY,
    }
    try:
        state = _read(runtime / STATE)
        if not state:
            state = {
                "schema_version": 1,
                "patterns": {},
                "outbox": {},
                "baseline_at": None,
                "last_strategy": None,
            }
        if state.get("schema_version") != 1 or not isinstance(state.get("outbox"), dict):
            raise ValueError("notification_state_invalid")
        for delivery in state["outbox"].values():
            if delivery["status"] == "sending":
                delivery["status"] = "delivery_uncertain"
        try:
            observations, evidence_error = pattern_observations(runtime, now)
        except (OSError, ValueError, TypeError):
            observations, evidence_error = {}, "pattern_evidence_invalid"
        if evidence_error:
            status["blockers"].append(evidence_error)
        for pattern_id, observation in observations.items():
            prior = state["patterns"].get(pattern_id)
            seen = (prior or {}).get("seen_events", {})
            new_events = {
                key: event for key, event in observation["events"].items() if key not in seen
            }
            changed = prior is not None and prior["material"] != observation["material"]
            if state["baseline_at"] and (prior is None or changed or new_events):
                key = "pattern:" + _digest(
                    [
                        pattern_id,
                        observation["material"],
                        sorted(new_events),
                        observation["observed_at"],
                    ]
                )
                _enqueue(
                    state,
                    key,
                    "pattern",
                    pattern_message(observation, new_events, new_pattern=prior is None),
                    now,
                    now + timedelta(hours=1),
                    pattern_id=pattern_id,
                    material_digest=_digest(observation["material"]),
                )
            seen.update({key: now.isoformat() for key in new_events})
            state["patterns"][pattern_id] = {
                "material": observation["material"],
                "seen_at": now.isoformat(),
                "seen_events": {
                    key: value
                    for key, value in seen.items()
                    if _fresh(value, now, RETENTION_DAYS * 86400)
                },
            }
        if observations and not state["baseline_at"]:
            state["baseline_at"] = now.isoformat()
        local = now.astimezone(ZoneInfo(settings.daily_learning_automation_timezone))
        hour, minute = map(int, settings.daily_learning_automation_after_local_time.split(":")[:2])
        if (local.hour, local.minute) >= (hour, minute):
            key = "strategy:" + local.date().isoformat()
            if key not in state["outbox"] or state["outbox"][key]["status"] == "pending":
                try:
                    snapshot = strategy_snapshot(runtime, now)
                except (OSError, ValueError, TypeError):
                    snapshot = {"strategies": [], "router_reason": None, "router_state": None}
                    status["blockers"].append("strategy_evidence_invalid")
                body, fingerprint = strategy_message(
                    snapshot, state["last_strategy"], local.date().isoformat()
                )
                expires = (local + timedelta(days=1)).replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                _enqueue(state, key, "strategy", body, now, expires, fingerprint=fingerprint)
                if state["outbox"][key]["status"] == "pending":
                    state["outbox"][key].update(body=body, fingerprint=fingerprint)
                    if len(body) > 3900 or not _safe_text("", body):
                        state["outbox"][key]["status"] = "unsafe"
        # Keep notification storage bounded, with unresolved deliveries retained visibly.
        state["outbox"] = {
            key: item
            for key, item in state["outbox"].items()
            if _fresh(item["created_at"], now, RETENTION_DAYS * 86400)
        }
        state["patterns"] = {
            key: item
            for key, item in state["patterns"].items()
            if _fresh(item["seen_at"], now, RETENTION_DAYS * 86400)
        }
        enabled = (
            settings.mode == "paper"
            and settings.live_capital_enabled is False
            and settings.telegram_daily_learning_brief_enabled
            and not settings.telegram_daily_learning_brief_dry_run
        )
        token = secret_value("TELEGRAM_BOT_TOKEN", settings) if live and enabled else None
        target = secret_value("TELEGRAM_GROUP_CHAT_ID", settings) if live and enabled else None
        if live and not (enabled and token and target):
            status["blockers"].append("notification_disabled_or_credentials_missing")
        # A preview must not consume dedupe keys or seed the live baseline.
        if live:
            _atomic(runtime / STATE, state)
        attempts = 0
        for key, item in sorted(
            state["outbox"].items(),
            key=lambda pair: (pair[1]["kind"] != "strategy", pair[1]["created_at"]),
        ):
            if item["status"] != "pending":
                continue
            if (_stamp(item["expires_at"]) or now) <= now:
                item["status"] = "expired_unsent"
                continue
            if item["kind"] == "pattern":
                current = observations.get(item["pattern_id"])
                if current is None:
                    continue
                if _digest(current["material"]) != item["material_digest"]:
                    item["status"] = "superseded"
                    continue
            if not (live and enabled and token and target) or attempts >= MAX_SENDS:
                continue
            if (_stamp(item.get("retry_at")) or now) > now:
                continue
            attempts += 1
            item.update(status="sending", attempts=item["attempts"] + 1)
            _atomic(runtime / STATE, state)
            try:
                response = sender(token, target, item["body"])
                message_id = (response.get("result") or {}).get("message_id")
                if response.get("ok") is True and isinstance(message_id, int):
                    item.update(status="sent", message_id=message_id, sent_at=now.isoformat())
                    status["sent_this_pass"] += 1
                    if item["kind"] == "strategy":
                        state["last_strategy"] = {
                            "fingerprint": item["fingerprint"],
                            "sent_at": now.isoformat(),
                        }
                elif response.get("ok") is False:
                    item.update(
                        status="pending", retry_at=(now + timedelta(minutes=15)).isoformat()
                    )
                else:
                    item["status"] = "delivery_uncertain"
            except urllib.error.HTTPError as exc:
                # An explicit rejection is retryable; an ambiguous transport failure is not.
                item.update(
                    status="pending",
                    error_type=f"HTTP_{exc.code}",
                    retry_at=(now + timedelta(minutes=15)).isoformat(),
                )
            except Exception as exc:  # noqa: BLE001 - no token-bearing exception strings.
                item.update(status="delivery_uncertain", error_type=type(exc).__name__)
            _atomic(runtime / STATE, state)
        status["delivery_counts"] = {
            name: sum(item["status"] == name for item in state["outbox"].values())
            for name in ["pending", "sent", "delivery_uncertain", "unsafe", "expired_unsent"]
        }
        status["baseline_at"] = state["baseline_at"]
        status["daily_strategy_after_local_time"] = (
            settings.daily_learning_automation_after_local_time
        )
        status["timezone"] = settings.daily_learning_automation_timezone
        status["preview_messages"] = (
            [item["body"] for item in state["outbox"].values() if item["status"] == "pending"]
            if not live
            else []
        )
        if any(
            status["delivery_counts"][name]
            for name in ["delivery_uncertain", "unsafe", "expired_unsent"]
        ):
            status["blockers"].append("notification_delivery_needs_attention")
        if any(
            item["attempts"] and item["status"] == "pending" for item in state["outbox"].values()
        ):
            status["blockers"].append("notification_retry_pending")
        if live:
            _atomic(runtime / STATE, state)
    except Exception as exc:  # noqa: BLE001 - notification failure must not block the daily research pass.
        status["blockers"].append(type(exc).__name__)
    status["status"] = "needs_attention" if status["blockers"] else "healthy"
    if live:
        _atomic(runtime / STATUS, status)
    return status
