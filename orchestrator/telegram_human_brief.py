"""Human Telegram brief for Qadam's daily edge loop.

Stage 5 turns the daily edge findings and promotion-gate state into a short,
public-safe Telegram-ready explanation. It can optionally send through the
Telegram group gate, but it cannot create, approve, submit, or change trades.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from typing import Any
import urllib.parse
import urllib.request

from orchestrator.config import Settings
from orchestrator.daily_edge_findings import validate_daily_edge_findings_brief
from orchestrator.event_log import EventLog
from orchestrator.promotion_gates import validate_promotion_gates
from orchestrator.secrets import secret_status, secret_value
from orchestrator.telegram_comms import FORBIDDEN_TELEGRAM_TEXT
from orchestrator.telegram_message_quality import (
    telegram_human_message_style,
    telegram_message_fingerprint,
    telegram_message_specificity,
)


TELEGRAM_HUMAN_BRIEF_SCHEMA_VERSION = 1
TELEGRAM_HUMAN_BRIEF_RUNTIME_ARTIFACT = "telegram_human_brief.json"
TELEGRAM_HUMAN_BRIEF_HISTORY = "telegram_human_brief_history.jsonl"
TELEGRAM_HUMAN_BRIEF_EVENT_LOG = "telegram_human_brief_events.jsonl"
TELEGRAM_HUMAN_BRIEF_EVENT_TYPE = "telegram_human_brief_recorded"
TELEGRAM_HUMAN_BRIEF_COMPONENT = "telegram_human_brief"

TELEGRAM_HUMAN_BRIEF_STATUSES = {
    "telegram_human_brief_blocked",
    "telegram_human_brief_dry_run_ready",
    "telegram_human_brief_ready_to_send",
    "telegram_human_brief_sent",
    "telegram_human_brief_failed",
    "telegram_human_brief_already_sent",
}

TELEGRAM_HUMAN_BRIEF_BOUNDARY = (
    "Telegram Human Brief is an outbound explanatory note for daily edge "
    "findings, quantum review, and promotion-gate state. It can summarize what "
    "Qadam learned in plain language, but it cannot create trade candidates, "
    "approve risk, approve execution, submit or close broker orders, handle "
    "Telegram commands, call quantum providers, mutate strategy, expose "
    "secrets or chat ids, grant proof credit, deploy code, or enable live "
    "capital."
)

TELEGRAM_HUMAN_BRIEF_FALSE_FIELDS = (
    "telegram_command_path_enabled",
    "telegram_trade_command_enabled",
    "telegram_place_trade_command_enabled",
    "telegram_approve_trade_command_enabled",
    "telegram_reject_trade_command_enabled",
    "telegram_modify_trade_command_enabled",
    "telegram_resize_trade_command_enabled",
    "telegram_close_trade_command_enabled",
    "telegram_cancel_trade_command_enabled",
    "trade_candidate_created",
    "risk_approval_allowed",
    "execution_allowed",
    "paper_execution_allowed",
    "paper_order_allowed",
    "paper_order_staging_allowed",
    "paper_order_submission_allowed",
    "broker_write_allowed",
    "broker_post_allowed",
    "alpaca_post_allowed",
    "order_cancel_allowed",
    "position_close_allowed",
    "position_resize_allowed",
    "strategy_weight_application_allowed",
    "active_strategy_mutation_allowed",
    "quantum_provider_call_allowed",
    "prediction_market_write_allowed",
    "crypto_perps_write_allowed",
    "repository_write_allowed",
    "deploy_allowed",
    "live_endpoint_allowed",
    "live_capital_enabled",
    "phase7_proof_credit_allowed",
    "secret_value_exposed",
    "raw_payload_exposed",
    "raw_provider_response_persisted",
    "authorization_header_exposed",
    "chat_id_exposed",
    "bot_token_exposed",
    "telegram_handle_exposed",
    "broker_order_identifier_exposed",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runtime_dir(settings: Settings | None = None) -> Path:
    return Path((settings or Settings.from_env()).runtime_dir)


def telegram_human_brief_paths(
    settings: Settings | None = None,
) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / TELEGRAM_HUMAN_BRIEF_RUNTIME_ARTIFACT,
        runtime / TELEGRAM_HUMAN_BRIEF_HISTORY,
        runtime / TELEGRAM_HUMAN_BRIEF_EVENT_LOG,
    )


def _delivery_path(settings: Settings) -> Path:
    path = _runtime_dir(settings) / "telegram-deliveries.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _sent_delivery_keys(settings: Settings) -> set[str]:
    path = _delivery_path(settings)
    if not path.exists():
        return set()
    keys: set[str] = set()
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            try:
                payload = json.loads(stripped)
            except json.JSONDecodeError:
                continue
            if (
                isinstance(payload, dict)
                and payload.get("message_class") == "telegram_human_brief"
                and payload.get("target") == "group"
                and payload.get("status") == "sent"
            ):
                key = str(payload.get("delivery_key") or "")
                if key:
                    keys.add(key)
    return keys


def _archive_delivery(settings: Settings, payload: dict[str, Any]) -> None:
    safe_payload = {
        "schema_version": TELEGRAM_HUMAN_BRIEF_SCHEMA_VERSION,
        "created_at": payload.get("created_at") or _now(),
        "target": "group",
        "status": payload.get("status", "unknown"),
        "message_class": "telegram_human_brief",
        "delivery_key": payload.get("delivery_key"),
        "telegram_message_id": payload.get("telegram_message_id"),
        "failure_category": payload.get("failure_category"),
        "send_requested": payload.get("send_requested") is True,
        "live_send_attempted": payload.get("live_send_attempted") is True,
        "bot_token_exposed": False,
        "chat_id_exposed": False,
        "raw_provider_response_persisted": False,
        "boundary": TELEGRAM_HUMAN_BRIEF_BOUNDARY,
    }
    with _delivery_path(settings).open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(safe_payload, sort_keys=True) + "\n")


def _telegram_send(token: str, chat_id: str, text: str) -> dict[str, Any]:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode(
        {
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": "true",
        }
    ).encode("utf-8")
    request = urllib.request.Request(url, data=data, method="POST")
    with urllib.request.urlopen(request, timeout=20) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return payload if isinstance(payload, dict) else {}


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


def _safe_text(title: str, body: str) -> bool:
    text = f"{title}\n{body}"
    return all(not pattern.search(text) for pattern in FORBIDDEN_TELEGRAM_TEXT)


def _delivery_key(brief_date: str) -> str:
    raw = f"qadam:telegram_human_brief:{brief_date}:group"
    return sha256(raw.encode("utf-8")).hexdigest()


def _pattern_names(daily_edge_findings: dict[str, Any]) -> str:
    names: list[str] = []
    for pattern in daily_edge_findings.get("patterns_observed", []):
        if not isinstance(pattern, dict):
            continue
        name = str(pattern.get("market_sleeve") or pattern.get("sleeve_key") or "").strip()
        if name and name not in names:
            names.append(name)
        if len(names) >= 3:
            break
    label = ", ".join(names) or "the watched markets"
    return label[:140].rstrip(", ")


def _portfolio_goal_text(daily_edge_findings: dict[str, Any]) -> str:
    goal = daily_edge_findings.get("portfolio_goal_alignment", {})
    if not isinstance(goal, dict):
        goal = {}
    current = _float(goal.get("current_value_gbp"), 0.0)
    target = _float(goal.get("target_value_gbp"), 200000.0)
    progress = _float(goal.get("progress_to_double_pct"), 0.0)
    if current <= 0:
        return "the 60-day paper portfolio goal"
    return (
        f"the 60-day paper goal, where the account is currently around GBP "
        f"{current:,.0f} against a GBP {target:,.0f} target, about {progress:.2f}% "
        "of the way there"
    )


def _render_human_brief_message(
    *,
    daily_edge_findings: dict[str, Any],
    promotion_gates: dict[str, Any],
) -> tuple[str, str]:
    source_count = _int(daily_edge_findings.get("source_count"))
    watched_count = _int(daily_edge_findings.get("watched_instrument_count"))
    candidate_count = _int(daily_edge_findings.get("candidate_pattern_count"))
    validated_count = _int(daily_edge_findings.get("validated_edge_count"))
    held_count = _int(promotion_gates.get("promotion_gate_held_count"))
    ready_count = _int(promotion_gates.get("promotion_review_ready_count"))
    quantum_status = str(daily_edge_findings.get("quantum_review_status") or "not run").replace(
        "_",
        " ",
    )
    quantum_backend = str(daily_edge_findings.get("quantum_backend") or "the configured backend").replace(
        "_",
        " ",
    )
    names = _pattern_names(daily_edge_findings)
    goal = _portfolio_goal_text(daily_edge_findings)
    title = "Qadam"
    body = (
        f"Qadam reviewed {source_count} data sources against {watched_count} watched markets, "
        f"including {names}. It found {candidate_count} candidate relationships and "
        f"{validated_count} confirmed edges. The quantum review is part of the core test; "
        f"today it came back {quantum_status} through {quantum_backend}, so Qadam can keep "
        "checking whether named source families appear before prices or probabilities move."
        "\n\n"
        f"This means Qadam has material to learn from, but not a shortcut to trade. "
        f"{ready_count} improvements are ready for human review and {held_count} are held for "
        f"more outcome evidence and explicit approval. For {goal}, Qadam may adjust watch "
        "priority, but any paper order still has to pass strategy, risk, quantum, and "
        "Alpaca Paper first."
    )
    return title, body


def build_telegram_human_brief(
    *,
    daily_edge_findings: dict[str, Any],
    promotion_gates: dict[str, Any],
    settings: Settings | None = None,
    send_requested: bool = False,
    force: bool = False,
    generated_at: str | None = None,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    generated_at = generated_at or _now()
    validate_daily_edge_findings_brief(daily_edge_findings)
    validate_promotion_gates(promotion_gates)
    brief_date = str(daily_edge_findings.get("brief_date") or generated_at[:10])
    delivery_key = _delivery_key(brief_date)
    title, body = _render_human_brief_message(
        daily_edge_findings=daily_edge_findings,
        promotion_gates=promotion_gates,
    )
    message_specificity = telegram_message_specificity(title, body)
    message_style = telegram_human_message_style(title, body)
    message_fingerprint = telegram_message_fingerprint(title, body)
    message_safe = _safe_text(title, body)
    bot_configured = secret_status("TELEGRAM_BOT_TOKEN", settings).configured
    group_chat_configured = secret_status("TELEGRAM_GROUP_CHAT_ID", settings).configured
    token = secret_value("TELEGRAM_BOT_TOKEN", settings)
    chat_id = secret_value("TELEGRAM_GROUP_CHAT_ID", settings)
    enabled = settings.telegram_human_brief_enabled
    dry_run = settings.telegram_human_brief_dry_run
    already_sent = delivery_key in _sent_delivery_keys(settings)
    eligible = (
        settings.mode == "paper"
        and settings.live_capital_enabled is False
        and daily_edge_findings.get("status") == "daily_edge_findings_ready_for_review"
        and promotion_gates.get("status") == "promotion_gates_ready"
        and message_safe
        and message_specificity["status"] == "specific"
        and message_style["status"] == "human"
    )
    live_send_allowed = (
        eligible
        and enabled
        and not dry_run
        and bot_configured
        and group_chat_configured
        and not already_sent
    )

    blockers: list[str] = []
    if not eligible:
        blockers.append("human_brief_not_eligible")
    if daily_edge_findings.get("status") != "daily_edge_findings_ready_for_review":
        blockers.append("daily_edge_findings_not_ready")
    if promotion_gates.get("status") != "promotion_gates_ready":
        blockers.append("promotion_gates_not_ready")
    if not message_safe:
        blockers.append("telegram_message_not_safe")
    if message_specificity["status"] != "specific":
        blockers.append("telegram_message_not_specific")
    if message_style["status"] != "human":
        blockers.append("telegram_message_not_human")
    if not enabled:
        blockers.append("telegram_human_brief_disabled")
    if dry_run:
        blockers.append("telegram_human_brief_dry_run")
    if not bot_configured:
        blockers.append("telegram_bot_token_missing")
    if not group_chat_configured:
        blockers.append("telegram_group_chat_missing")
    if already_sent:
        blockers.append("telegram_human_brief_already_sent")

    status = "telegram_human_brief_blocked"
    if eligible:
        status = "telegram_human_brief_dry_run_ready" if dry_run else "telegram_human_brief_ready_to_send"
    if already_sent:
        status = "telegram_human_brief_already_sent"

    live_send_attempted = False
    live_send_succeeded = False
    telegram_message_id: int | None = None
    failure_category: str | None = None

    if send_requested and live_send_allowed:
        live_send_attempted = True
        try:
            assert token is not None
            assert chat_id is not None
            response = _telegram_send(token, chat_id, body)
            if response.get("ok") is True:
                live_send_succeeded = True
                result = response.get("result", {})
                if isinstance(result, dict) and result.get("message_id") is not None:
                    telegram_message_id = int(result["message_id"])
                status = "telegram_human_brief_sent"
            else:
                status = "telegram_human_brief_failed"
                failure_category = "telegram_api_rejected"
        except Exception as exc:  # noqa: BLE001 - persist sanitized failure only.
            status = "telegram_human_brief_failed"
            failure_category = type(exc).__name__

        _archive_delivery(
            settings,
            {
                "created_at": generated_at,
                "status": "sent" if live_send_succeeded else "failed",
                "delivery_key": delivery_key,
                "telegram_message_id": telegram_message_id,
                "failure_category": failure_category,
                "send_requested": send_requested,
                "live_send_attempted": live_send_attempted,
            },
        )

    artifact = {
        "schema_version": TELEGRAM_HUMAN_BRIEF_SCHEMA_VERSION,
        "artifact_type": "telegram_human_brief",
        "artifact_id": f"telegram-human-brief:{brief_date}",
        "stage": "Stage 5 - Telegram Human Brief",
        "generated_at": generated_at,
        "brief_date": brief_date,
        "status": status,
        "public_safe": True,
        "target": "group",
        "message_class": "telegram_human_brief",
        "title": title,
        "body": body,
        "paragraph_count": message_style["paragraph_count"],
        "line_count": message_style["line_count"],
        "sentence_count": message_style["sentence_count"],
        "message_fingerprint": message_fingerprint,
        "message_specificity_status": message_specificity["status"],
        "message_specificity_score": message_specificity["score"],
        "message_specificity_reasons": message_specificity["reasons"],
        "message_human_style_status": message_style["status"],
        "message_human_style_errors": message_style["errors"],
        "message_technical_noise_count": message_style["technical_noise_count"],
        "message_section_header_count": message_style["section_header_count"],
        "message_safe": message_safe,
        "enabled": enabled,
        "dry_run": dry_run,
        "send_requested": send_requested,
        "force": force,
        "already_sent": already_sent,
        "telegram_live_send_allowed": live_send_allowed,
        "live_send_attempted": live_send_attempted,
        "live_send_succeeded": live_send_succeeded,
        "telegram_message_id_present": telegram_message_id is not None,
        "last_delivery_failure_category": failure_category,
        "bot_configured": bot_configured,
        "group_chat_configured": group_chat_configured,
        "delivery_key": delivery_key,
        "blockers": sorted(set(blockers)),
        "blocker_count": len(set(blockers)),
        "source_daily_edge_findings_status": daily_edge_findings.get("status"),
        "source_promotion_gates_status": promotion_gates.get("status"),
        "source_count": _int(daily_edge_findings.get("source_count")),
        "watched_instrument_count": _int(daily_edge_findings.get("watched_instrument_count")),
        "candidate_pattern_count": _int(daily_edge_findings.get("candidate_pattern_count")),
        "validated_edge_count": _int(daily_edge_findings.get("validated_edge_count")),
        "quantum_required": True,
        "quantum_review_status": daily_edge_findings.get("quantum_review_status"),
        "quantum_backend": daily_edge_findings.get("quantum_backend"),
        "quantum_gate_status": daily_edge_findings.get("quantum_mandatory_review_gate_status"),
        "quantum_gate_passed": daily_edge_findings.get("quantum_mandatory_review_gate_passed") is True,
        "promotion_gate_decision_count": _int(promotion_gates.get("promotion_gate_decision_count")),
        "promotion_review_ready_count": _int(promotion_gates.get("promotion_review_ready_count")),
        "promotion_gate_passed_count": _int(promotion_gates.get("promotion_gate_passed_count")),
        "promotion_gate_held_count": _int(promotion_gates.get("promotion_gate_held_count")),
        "human_approval_missing_count": _int(promotion_gates.get("human_approval_missing_count")),
        "outcome_feedback_missing_count": _int(promotion_gates.get("outcome_feedback_missing_count")),
        "portfolio_goal_alignment": deepcopy(daily_edge_findings.get("portfolio_goal_alignment") or {}),
        "documentation_routes": {
            "runtime_artifact": f"data/runtime/{TELEGRAM_HUMAN_BRIEF_RUNTIME_ARTIFACT}",
            "history": f"data/runtime/{TELEGRAM_HUMAN_BRIEF_HISTORY}",
            "event_log": f"data/runtime/{TELEGRAM_HUMAN_BRIEF_EVENT_LOG}",
            "source_daily_edge_findings": "data/runtime/daily_edge_findings_brief.json",
            "source_promotion_gates": "data/runtime/promotion_gates.json",
            "dashboard_surface": "Communications",
        },
        "boundary": TELEGRAM_HUMAN_BRIEF_BOUNDARY,
    }
    for field in TELEGRAM_HUMAN_BRIEF_FALSE_FIELDS:
        artifact[field] = False
    return artifact


def validate_telegram_human_brief(payload: dict[str, Any]) -> None:
    required = {
        "schema_version",
        "artifact_type",
        "artifact_id",
        "stage",
        "generated_at",
        "brief_date",
        "status",
        "public_safe",
        "target",
        "message_class",
        "title",
        "body",
        "paragraph_count",
        "line_count",
        "sentence_count",
        "message_fingerprint",
        "message_specificity_status",
        "message_specificity_score",
        "message_specificity_reasons",
        "message_human_style_status",
        "message_human_style_errors",
        "message_technical_noise_count",
        "message_section_header_count",
        "message_safe",
        "enabled",
        "dry_run",
        "send_requested",
        "force",
        "already_sent",
        "telegram_live_send_allowed",
        "live_send_attempted",
        "live_send_succeeded",
        "telegram_message_id_present",
        "last_delivery_failure_category",
        "bot_configured",
        "group_chat_configured",
        "delivery_key",
        "blockers",
        "blocker_count",
        "source_daily_edge_findings_status",
        "source_promotion_gates_status",
        "source_count",
        "watched_instrument_count",
        "candidate_pattern_count",
        "validated_edge_count",
        "quantum_required",
        "quantum_review_status",
        "quantum_backend",
        "quantum_gate_status",
        "quantum_gate_passed",
        "promotion_gate_decision_count",
        "promotion_review_ready_count",
        "promotion_gate_passed_count",
        "promotion_gate_held_count",
        "human_approval_missing_count",
        "outcome_feedback_missing_count",
        "portfolio_goal_alignment",
        "documentation_routes",
        "boundary",
        *TELEGRAM_HUMAN_BRIEF_FALSE_FIELDS,
    }
    missing = sorted(required - set(payload))
    if missing:
        raise ValueError(f"Telegram human brief missing fields: {missing}")
    if payload.get("schema_version") != TELEGRAM_HUMAN_BRIEF_SCHEMA_VERSION:
        raise ValueError("Telegram human brief schema mismatch")
    if payload.get("artifact_type") != "telegram_human_brief":
        raise ValueError("Telegram human brief artifact type mismatch")
    if payload.get("status") not in TELEGRAM_HUMAN_BRIEF_STATUSES:
        raise ValueError("Telegram human brief status invalid")
    if payload.get("public_safe") is not True:
        raise ValueError("Telegram human brief must be public-safe")
    if payload.get("target") != "group":
        raise ValueError("Telegram human brief target must be group")
    if payload.get("message_class") != "telegram_human_brief":
        raise ValueError("Telegram human brief message class mismatch")
    if "outbound explanatory note" not in str(payload.get("boundary", "")):
        raise ValueError("Telegram human brief boundary weak")
    for field in TELEGRAM_HUMAN_BRIEF_FALSE_FIELDS:
        if payload.get(field) is not False:
            raise ValueError(f"Telegram human brief authority leak: {field}")
    body = str(payload.get("body") or "")
    title = str(payload.get("title") or "")
    if not body.strip():
        raise ValueError("Telegram human brief body missing")
    if payload.get("message_safe") is not True or not _safe_text(title, body):
        raise ValueError("Telegram human brief unsafe text")
    if "quantum" not in body.lower():
        raise ValueError("Telegram human brief must explain quantum review")
    if "paper order" not in body.lower():
        raise ValueError("Telegram human brief must explain paper-order boundary")
    if "data sources" not in body.lower():
        raise ValueError("Telegram human brief must explain source scan")
    if "candidate" not in body.lower():
        raise ValueError("Telegram human brief must explain candidate patterns")
    style = telegram_human_message_style(title, body)
    if style["status"] != "human":
        raise ValueError(f"Telegram human brief not human: {style['errors']}")
    if style["paragraph_count"] != _int(payload.get("paragraph_count")):
        raise ValueError("Telegram human brief paragraph count mismatch")
    if not 1 <= _int(payload.get("paragraph_count")) <= 2:
        raise ValueError("Telegram human brief must be one or two paragraphs")
    if _int(payload.get("message_technical_noise_count")) != 0:
        raise ValueError("Telegram human brief has technical noise")
    if _int(payload.get("message_section_header_count")) != 0:
        raise ValueError("Telegram human brief has section headers")
    specificity = telegram_message_specificity(title, body)
    if specificity["status"] != "specific":
        raise ValueError(f"Telegram human brief not specific: {specificity['reasons']}")
    if _int(payload.get("message_specificity_score")) < 70:
        raise ValueError("Telegram human brief specificity score too low")
    if payload.get("message_specificity_status") != specificity["status"]:
        raise ValueError("Telegram human brief specificity status mismatch")
    if payload.get("message_human_style_status") != style["status"]:
        raise ValueError("Telegram human brief style status mismatch")
    if _int(payload.get("source_count")) < 30:
        raise ValueError("Telegram human brief source count below contract")
    if _int(payload.get("watched_instrument_count")) < 19:
        raise ValueError("Telegram human brief watched instrument count below contract")
    if _int(payload.get("candidate_pattern_count")) < 5:
        raise ValueError("Telegram human brief candidate pattern count below contract")
    if payload.get("quantum_required") is not True:
        raise ValueError("Telegram human brief must require quantum")
    if payload.get("quantum_gate_passed") is not True:
        raise ValueError("Telegram human brief quantum gate not passed")
    if payload.get("source_daily_edge_findings_status") != "daily_edge_findings_ready_for_review":
        raise ValueError("Telegram human brief daily findings not ready")
    if payload.get("source_promotion_gates_status") != "promotion_gates_ready":
        raise ValueError("Telegram human brief promotion gates not ready")
    if _int(payload.get("promotion_gate_decision_count")) != 5:
        raise ValueError("Telegram human brief promotion decision count mismatch")
    if _int(payload.get("promotion_review_ready_count")) != 5:
        raise ValueError("Telegram human brief promotion review-ready count mismatch")
    if _int(payload.get("human_approval_missing_count")) < 1:
        raise ValueError("Telegram human brief must expose missing human approval")
    if payload.get("telegram_command_path_enabled") is not False:
        raise ValueError("Telegram human brief command path enabled")
    live_send_allowed = payload.get("telegram_live_send_allowed") is True
    if live_send_allowed:
        if payload.get("enabled") is not True:
            raise ValueError("Telegram human brief live send allowed while disabled")
        if payload.get("dry_run") is not False:
            raise ValueError("Telegram human brief live send allowed in dry run")
        if payload.get("bot_configured") is not True:
            raise ValueError("Telegram human brief live send allowed without bot")
        if payload.get("group_chat_configured") is not True:
            raise ValueError("Telegram human brief live send allowed without group")
        if payload.get("already_sent") is True:
            raise ValueError("Telegram human brief live send allowed after already sent")
    if payload.get("live_send_succeeded") is True and payload.get("live_send_attempted") is not True:
        raise ValueError("Telegram human brief sent without attempt")
    if payload.get("telegram_message_id_present") is True and payload.get("live_send_succeeded") is not True:
        raise ValueError("Telegram human brief message id present without success")
    if "/Users/" in body or "/private/" in body or "qadam.trade/" in body:
        raise ValueError("Telegram human brief body leaked path or URL")


def write_telegram_human_brief(
    payload: dict[str, Any],
    settings: Settings | None = None,
) -> dict[str, Any]:
    validate_telegram_human_brief(payload)
    output_path, history_path, event_path = telegram_human_brief_paths(settings)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")
    event = {
        "schema_version": TELEGRAM_HUMAN_BRIEF_SCHEMA_VERSION,
        "event_type": TELEGRAM_HUMAN_BRIEF_EVENT_TYPE,
        "component": TELEGRAM_HUMAN_BRIEF_COMPONENT,
        "created_at": payload.get("generated_at") or _now(),
        "brief_date": payload.get("brief_date"),
        "status": payload.get("status"),
        "message_specificity_score": payload.get("message_specificity_score"),
        "message_human_style_status": payload.get("message_human_style_status"),
        "telegram_live_send_allowed": payload.get("telegram_live_send_allowed") is True,
        "live_send_attempted": payload.get("live_send_attempted") is True,
        "live_send_succeeded": payload.get("live_send_succeeded") is True,
        "paper_order_allowed": False,
        "broker_write_allowed": False,
        "live_capital_enabled": False,
        "boundary": TELEGRAM_HUMAN_BRIEF_BOUNDARY,
    }
    with event_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True) + "\n")
    EventLog(echo=False).write(
        event_type=TELEGRAM_HUMAN_BRIEF_EVENT_TYPE,
        component=TELEGRAM_HUMAN_BRIEF_COMPONENT,
        payload=event,
    )
    return {
        "output_path": str(output_path),
        "history_path": str(history_path),
        "event_path": str(event_path),
    }
