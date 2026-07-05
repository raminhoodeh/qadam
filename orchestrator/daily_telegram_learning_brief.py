"""Daily Telegram learning brief for Qadam's edge loop.

Stage 6A turns the daily edge findings into a plain-language Telegram-ready
learning note. It is outbound-only and never gains command, trading, broker,
strategy-mutation, quantum-provider, or live-capital authority.
"""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from typing import Any
import urllib.error
import urllib.parse
import urllib.request

from orchestrator.config import Settings
from orchestrator.daily_edge_findings import validate_daily_edge_findings_brief
from orchestrator.event_log import EventLog
from orchestrator.promotion_gates import validate_promotion_gates
from orchestrator.secrets import secret_status, secret_value
from orchestrator.telegram_comms import FORBIDDEN_TELEGRAM_TEXT
from orchestrator.telegram_human_brief import TELEGRAM_HUMAN_BRIEF_FALSE_FIELDS
from orchestrator.telegram_message_quality import (
    telegram_human_message_style,
    telegram_message_fingerprint,
    telegram_message_specificity,
)


DAILY_TELEGRAM_LEARNING_BRIEF_SCHEMA_VERSION = 1
DAILY_TELEGRAM_LEARNING_BRIEF_RUNTIME_ARTIFACT = "daily_telegram_learning_brief.json"
DAILY_TELEGRAM_LEARNING_BRIEF_HISTORY = "daily_telegram_learning_brief_history.jsonl"
DAILY_TELEGRAM_LEARNING_BRIEF_EVENT_LOG = "daily_telegram_learning_brief_events.jsonl"
DAILY_TELEGRAM_LEARNING_BRIEF_EVENT_TYPE = "daily_telegram_learning_brief_recorded"
DAILY_TELEGRAM_LEARNING_BRIEF_COMPONENT = "daily_telegram_learning_brief"

DAILY_TELEGRAM_LEARNING_BRIEF_STATUSES = {
    "daily_telegram_learning_brief_blocked",
    "daily_telegram_learning_brief_dry_run_ready",
    "daily_telegram_learning_brief_ready_to_send",
    "daily_telegram_learning_brief_sent",
    "daily_telegram_learning_brief_failed",
    "daily_telegram_learning_brief_already_sent",
}

DAILY_TELEGRAM_LEARNING_BRIEF_BOUNDARY = (
    "Daily Telegram Learning Brief is an outbound plain-language learning note "
    "for Qadam's daily edge loop. It can explain source/price patterns, quantum "
    "review, and proposed learning implications, but it cannot create trade "
    "candidates, approve risk, approve execution, submit or close broker orders, "
    "handle Telegram commands, call quantum providers, mutate strategy, expose "
    "secrets or chat ids, grant proof credit, deploy code, or enable live capital."
)

PATTERN_QUALITATIVE_FOCUS = {
    "oil": "shipping/GPS/fire/flight vs CL=F, BZ=F, USO and XLE",
    "silver": "rates, trade and mining flow vs SI=F, SLV, SIL and PAAS",
    "semiconductors": (
        "export/news, filings, patents, GitHub and transport vs SMH, SOXX, "
        "NVDA, AMD, TSM and ASML"
    ),
    "prediction_markets": "Polymarket/Kalshi odds vs news/social/conflict",
    "defence": "conflict, maritime/flight, GPS and filings vs ITA, XAR, LMT, RTX and NOC",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runtime_dir(settings: Settings | None = None) -> Path:
    return Path((settings or Settings.from_env()).runtime_dir)


def daily_telegram_learning_brief_paths(
    settings: Settings | None = None,
) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / DAILY_TELEGRAM_LEARNING_BRIEF_RUNTIME_ARTIFACT,
        runtime / DAILY_TELEGRAM_LEARNING_BRIEF_HISTORY,
        runtime / DAILY_TELEGRAM_LEARNING_BRIEF_EVENT_LOG,
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
                and payload.get("message_class") == "daily_telegram_learning_brief"
                and payload.get("target") == "group"
                and payload.get("status") == "sent"
            ):
                key = str(payload.get("delivery_key") or "")
                if key:
                    keys.add(key)
    return keys


def _archive_delivery(settings: Settings, payload: dict[str, Any]) -> None:
    safe_payload = {
        "schema_version": DAILY_TELEGRAM_LEARNING_BRIEF_SCHEMA_VERSION,
        "created_at": payload.get("created_at") or _now(),
        "target": "group",
        "status": payload.get("status", "unknown"),
        "message_class": "daily_telegram_learning_brief",
        "delivery_key": payload.get("delivery_key"),
        "telegram_message_id": payload.get("telegram_message_id"),
        "failure_category": payload.get("failure_category"),
        "send_requested": payload.get("send_requested") is True,
        "live_send_attempted": payload.get("live_send_attempted") is True,
        "bot_token_exposed": False,
        "chat_id_exposed": False,
        "raw_provider_response_persisted": False,
        "boundary": DAILY_TELEGRAM_LEARNING_BRIEF_BOUNDARY,
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
    raw = f"qadam:daily_telegram_learning_brief:{brief_date}:group"
    return sha256(raw.encode("utf-8")).hexdigest()


def _pattern_names(daily_edge_findings: dict[str, Any]) -> str:
    names: list[str] = []
    for pattern in daily_edge_findings.get("patterns_observed", []):
        if not isinstance(pattern, dict):
            continue
        name = str(pattern.get("market_sleeve") or pattern.get("sleeve_key") or "").strip()
        if name and name not in names:
            names.append(name)
        if len(names) >= 4:
            break
    return ", ".join(names) or "the watched markets"


def _pattern_quality_sentence(daily_edge_findings: dict[str, Any]) -> str:
    clauses: list[str] = []
    for pattern in daily_edge_findings.get("patterns_observed", []):
        if not isinstance(pattern, dict):
            continue
        name = str(pattern.get("market_sleeve") or pattern.get("sleeve_key") or "").strip()
        if not name:
            continue
        sleeve_key = str(pattern.get("sleeve_key") or "").strip()
        focus = PATTERN_QUALITATIVE_FOCUS.get(
            sleeve_key,
            "source signals leading market movement",
        )
        clauses.append(f"{name.lower()} {focus}")
        if len(clauses) >= 5:
            break
    if not clauses:
        return f"The pattern work stayed broad across {_pattern_names(daily_edge_findings)}."
    if len(clauses) == 1:
        return f"The recognised candidate was {clauses[0]}."
    return f"The reads: {'; '.join(clauses)}."


def _portfolio_goal(daily_edge_findings: dict[str, Any]) -> dict[str, Any]:
    goal = daily_edge_findings.get("portfolio_goal_alignment")
    return goal if isinstance(goal, dict) else {}


def _render_learning_message(
    *,
    daily_edge_findings: dict[str, Any],
    promotion_gates: dict[str, Any],
) -> tuple[str, str]:
    source_count = _int(daily_edge_findings.get("source_count"))
    watched_count = _int(daily_edge_findings.get("watched_instrument_count"))
    candidate_count = _int(daily_edge_findings.get("candidate_pattern_count"))
    validated_count = _int(daily_edge_findings.get("validated_edge_count"))
    held_count = _int(promotion_gates.get("promotion_gate_held_count"))
    quantum_backend = str(daily_edge_findings.get("quantum_backend") or "not exported").replace(
        "_",
        " ",
    )
    title = "Qadam"
    body = (
        f"Qadam scanned {source_count} data sources against {watched_count} watched markets "
        f"and found {candidate_count} candidate patterns today. "
        f"{_pattern_quality_sentence(daily_edge_findings)}"
        "\n\n"
        f"The learning stays cautious with {validated_count} validated edges; "
        f"all {held_count} still need thirty-day persistence. Qadam is checking "
        "whether inputs arrive before price or odds move. Source scan, "
        "lead-lag, confirmation, adversarial review, paper safety and the "
        f"quantum core gate passed on {quantum_backend}. This can raise watch priority "
        "only, not create a paper order, risk approval, execution approval or live-capital signal."
    )
    return title, body


def build_daily_telegram_learning_brief(
    *,
    daily_edge_findings: dict[str, Any],
    promotion_gates: dict[str, Any],
    settings: Settings | None = None,
    send_requested: bool = False,
    force_delivery_window: bool = False,
    generated_at: str | None = None,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    generated_at = generated_at or _now()
    validate_daily_edge_findings_brief(daily_edge_findings)
    validate_promotion_gates(promotion_gates)
    brief_date = str(daily_edge_findings.get("brief_date") or generated_at[:10])
    delivery_key = _delivery_key(brief_date)
    title, body = _render_learning_message(
        daily_edge_findings=daily_edge_findings,
        promotion_gates=promotion_gates,
    )
    specificity = telegram_message_specificity(title, body)
    style = telegram_human_message_style(title, body)
    fingerprint = telegram_message_fingerprint(title, body)
    message_safe = _safe_text(title, body)
    bot_configured = secret_status("TELEGRAM_BOT_TOKEN", settings).configured
    group_chat_configured = secret_status("TELEGRAM_GROUP_CHAT_ID", settings).configured
    token = secret_value("TELEGRAM_BOT_TOKEN", settings)
    chat_id = secret_value("TELEGRAM_GROUP_CHAT_ID", settings)
    enabled = settings.telegram_daily_learning_brief_enabled
    dry_run = settings.telegram_daily_learning_brief_dry_run
    already_sent = delivery_key in _sent_delivery_keys(settings)
    eligible = (
        settings.mode == "paper"
        and settings.live_capital_enabled is False
        and daily_edge_findings.get("status") == "daily_edge_findings_ready_for_review"
        and promotion_gates.get("status") == "promotion_gates_ready"
        and daily_edge_findings.get("quantum_mandatory_review_gate_passed") is True
        and specificity["status"] == "specific"
        and style["status"] == "human"
        and message_safe
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
        blockers.append("daily_learning_brief_not_eligible")
    if daily_edge_findings.get("status") != "daily_edge_findings_ready_for_review":
        blockers.append("daily_edge_findings_not_ready")
    if promotion_gates.get("status") != "promotion_gates_ready":
        blockers.append("promotion_gates_not_ready")
    if daily_edge_findings.get("quantum_mandatory_review_gate_passed") is not True:
        blockers.append("quantum_gate_not_passed")
    if specificity["status"] != "specific":
        blockers.append("telegram_message_not_specific")
    if style["status"] != "human":
        blockers.append("telegram_message_not_human")
    if not message_safe:
        blockers.append("telegram_message_not_safe")
    if not enabled:
        blockers.append("daily_learning_brief_disabled")
    if dry_run:
        blockers.append("daily_learning_brief_dry_run")
    if not bot_configured:
        blockers.append("telegram_bot_token_missing")
    if not group_chat_configured:
        blockers.append("telegram_group_chat_missing")
    if already_sent:
        blockers.append("daily_learning_brief_already_sent")

    status = "daily_telegram_learning_brief_blocked"
    if eligible:
        status = (
            "daily_telegram_learning_brief_dry_run_ready"
            if dry_run
            else "daily_telegram_learning_brief_ready_to_send"
        )
    if already_sent:
        status = "daily_telegram_learning_brief_already_sent"

    live_send_attempted = False
    live_send_succeeded = False
    telegram_message_id: int | None = None
    failure_category: str | None = None
    delivery_retry_status: str | None = None

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
                status = "daily_telegram_learning_brief_sent"
            else:
                status = "daily_telegram_learning_brief_failed"
                failure_category = "telegram_api_rejected"
        except Exception as exc:  # noqa: BLE001 - persist sanitized failure only.
            failure_category = type(exc).__name__
            if isinstance(exc, (urllib.error.URLError, TimeoutError, OSError)):
                status = "daily_telegram_learning_brief_ready_to_send"
                delivery_retry_status = "queued_after_transport_failure"
            else:
                status = "daily_telegram_learning_brief_failed"

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
        "schema_version": DAILY_TELEGRAM_LEARNING_BRIEF_SCHEMA_VERSION,
        "artifact_type": "daily_telegram_learning_brief",
        "artifact_id": f"daily-telegram-learning-brief:{brief_date}",
        "stage": "Stage 6A - Daily Telegram Learning Brief",
        "generated_at": generated_at,
        "brief_date": brief_date,
        "status": status,
        "public_safe": True,
        "target": "group",
        "message_class": "daily_telegram_learning_brief",
        "title": title,
        "body": body,
        "paragraph_count": style["paragraph_count"],
        "line_count": style["line_count"],
        "sentence_count": style["sentence_count"],
        "message_fingerprint": fingerprint,
        "message_specificity_status": specificity["status"],
        "message_specificity_score": specificity["score"],
        "message_specificity_reasons": specificity["reasons"],
        "message_human_style_status": style["status"],
        "message_human_style_errors": style["errors"],
        "message_technical_noise_count": style["technical_noise_count"],
        "message_section_header_count": style["section_header_count"],
        "message_safe": message_safe,
        "enabled": enabled,
        "dry_run": dry_run,
        "send_requested": send_requested,
        "force_delivery_window": force_delivery_window,
        "already_sent": already_sent,
        "telegram_live_send_allowed": live_send_allowed,
        "live_send_attempted": live_send_attempted,
        "live_send_succeeded": live_send_succeeded,
        "telegram_message_id_present": telegram_message_id is not None,
        "last_delivery_failure_category": failure_category,
        "delivery_retry_status": delivery_retry_status,
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
        "quantum_gate_passed": (
            daily_edge_findings.get("quantum_mandatory_review_gate_passed") is True
        ),
        "promotion_gate_decision_count": _int(promotion_gates.get("promotion_gate_decision_count")),
        "promotion_review_ready_count": _int(promotion_gates.get("promotion_review_ready_count")),
        "promotion_gate_passed_count": _int(promotion_gates.get("promotion_gate_passed_count")),
        "promotion_gate_held_count": _int(promotion_gates.get("promotion_gate_held_count")),
        "human_approval_missing_count": _int(promotion_gates.get("human_approval_missing_count")),
        "strategy_learning_applied_count": 0,
        "portfolio_goal_alignment": _portfolio_goal(daily_edge_findings),
        "documentation_routes": {
            "runtime_artifact": f"data/runtime/{DAILY_TELEGRAM_LEARNING_BRIEF_RUNTIME_ARTIFACT}",
            "history": f"data/runtime/{DAILY_TELEGRAM_LEARNING_BRIEF_HISTORY}",
            "event_log": f"data/runtime/{DAILY_TELEGRAM_LEARNING_BRIEF_EVENT_LOG}",
            "source_daily_edge_findings": "data/runtime/daily_edge_findings_brief.json",
            "source_promotion_gates": "data/runtime/promotion_gates.json",
            "dashboard_surface": "Communications",
        },
        "boundary": DAILY_TELEGRAM_LEARNING_BRIEF_BOUNDARY,
    }
    for field in TELEGRAM_HUMAN_BRIEF_FALSE_FIELDS:
        artifact[field] = False
    return artifact


def validate_daily_telegram_learning_brief(payload: dict[str, Any]) -> None:
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
        "force_delivery_window",
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
        "strategy_learning_applied_count",
        "portfolio_goal_alignment",
        "documentation_routes",
        "boundary",
        *TELEGRAM_HUMAN_BRIEF_FALSE_FIELDS,
    }
    missing = sorted(required - set(payload))
    if missing:
        raise ValueError(f"Daily Telegram learning brief missing fields: {missing}")
    if payload.get("schema_version") != DAILY_TELEGRAM_LEARNING_BRIEF_SCHEMA_VERSION:
        raise ValueError("Daily Telegram learning brief schema mismatch")
    if payload.get("artifact_type") != "daily_telegram_learning_brief":
        raise ValueError("Daily Telegram learning brief artifact type mismatch")
    if payload.get("status") not in DAILY_TELEGRAM_LEARNING_BRIEF_STATUSES:
        raise ValueError("Daily Telegram learning brief status invalid")
    if payload.get("public_safe") is not True:
        raise ValueError("Daily Telegram learning brief must be public-safe")
    if payload.get("target") != "group":
        raise ValueError("Daily Telegram learning brief target must be group")
    if payload.get("message_class") != "daily_telegram_learning_brief":
        raise ValueError("Daily Telegram learning brief message class mismatch")
    if "outbound plain-language learning note" not in str(payload.get("boundary", "")):
        raise ValueError("Daily Telegram learning brief boundary weak")
    for field in TELEGRAM_HUMAN_BRIEF_FALSE_FIELDS:
        if payload.get(field) is not False:
            raise ValueError(f"Daily Telegram learning brief authority leak: {field}")
    title = str(payload.get("title") or "")
    body = str(payload.get("body") or "")
    if not body.strip():
        raise ValueError("Daily Telegram learning brief body missing")
    if payload.get("message_safe") is not True or not _safe_text(title, body):
        raise ValueError("Daily Telegram learning brief unsafe text")
    lower_body = body.lower()
    for word in ("learning", "quantum", "data sources", "candidate", "paper order"):
        if word not in lower_body:
            raise ValueError(f"Daily Telegram learning brief missing {word}")
    style = telegram_human_message_style(title, body)
    if style["status"] != "human":
        raise ValueError(f"Daily Telegram learning brief not human: {style['errors']}")
    if style["paragraph_count"] != _int(payload.get("paragraph_count")):
        raise ValueError("Daily Telegram learning brief paragraph count mismatch")
    if not 1 <= _int(payload.get("paragraph_count")) <= 2:
        raise ValueError("Daily Telegram learning brief must be one or two paragraphs")
    if _int(payload.get("message_technical_noise_count")) != 0:
        raise ValueError("Daily Telegram learning brief has technical noise")
    if _int(payload.get("message_section_header_count")) != 0:
        raise ValueError("Daily Telegram learning brief has section headers")
    specificity = telegram_message_specificity(title, body)
    if specificity["status"] != "specific":
        raise ValueError(f"Daily Telegram learning brief not specific: {specificity['reasons']}")
    if _int(payload.get("message_specificity_score")) < 70:
        raise ValueError("Daily Telegram learning brief specificity score too low")
    if payload.get("message_specificity_status") != specificity["status"]:
        raise ValueError("Daily Telegram learning brief specificity status mismatch")
    if payload.get("message_human_style_status") != style["status"]:
        raise ValueError("Daily Telegram learning brief style status mismatch")
    if _int(payload.get("source_count")) < 30:
        raise ValueError("Daily Telegram learning brief source count below contract")
    if _int(payload.get("watched_instrument_count")) < 20:
        raise ValueError("Daily Telegram learning brief watched instrument count below contract")
    if _int(payload.get("candidate_pattern_count")) < 5:
        raise ValueError("Daily Telegram learning brief candidate pattern count below contract")
    if payload.get("quantum_required") is not True:
        raise ValueError("Daily Telegram learning brief must require quantum")
    if payload.get("quantum_gate_passed") is not True:
        raise ValueError("Daily Telegram learning brief quantum gate not passed")
    if payload.get("source_daily_edge_findings_status") != "daily_edge_findings_ready_for_review":
        raise ValueError("Daily Telegram learning brief daily findings not ready")
    if payload.get("source_promotion_gates_status") != "promotion_gates_ready":
        raise ValueError("Daily Telegram learning brief promotion gates not ready")
    if _int(payload.get("promotion_gate_decision_count")) != 5:
        raise ValueError("Daily Telegram learning brief promotion decision count mismatch")
    if _int(payload.get("human_approval_missing_count")) < 1:
        raise ValueError("Daily Telegram learning brief must expose missing human approval")
    if _int(payload.get("strategy_learning_applied_count")) != 0:
        raise ValueError("Daily Telegram learning brief cannot apply learning")
    live_send_allowed = payload.get("telegram_live_send_allowed") is True
    if live_send_allowed:
        if payload.get("enabled") is not True:
            raise ValueError("Daily Telegram learning brief live send allowed while disabled")
        if payload.get("dry_run") is not False:
            raise ValueError("Daily Telegram learning brief live send allowed in dry run")
        if payload.get("bot_configured") is not True:
            raise ValueError("Daily Telegram learning brief live send allowed without bot")
        if payload.get("group_chat_configured") is not True:
            raise ValueError("Daily Telegram learning brief live send allowed without group")
        if payload.get("already_sent") is True:
            raise ValueError("Daily Telegram learning brief live send allowed after already sent")
    if payload.get("live_send_succeeded") is True and payload.get("live_send_attempted") is not True:
        raise ValueError("Daily Telegram learning brief sent without attempt")
    if payload.get("telegram_message_id_present") is True and payload.get("live_send_succeeded") is not True:
        raise ValueError("Daily Telegram learning brief message id present without success")
    if "/Users/" in body or "/private/" in body or "qadam.trade/" in body:
        raise ValueError("Daily Telegram learning brief body leaked path or URL")


def write_daily_telegram_learning_brief(
    payload: dict[str, Any],
    settings: Settings | None = None,
) -> dict[str, Any]:
    validate_daily_telegram_learning_brief(payload)
    output_path, history_path, event_path = daily_telegram_learning_brief_paths(settings)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")
    event = {
        "schema_version": DAILY_TELEGRAM_LEARNING_BRIEF_SCHEMA_VERSION,
        "event_type": DAILY_TELEGRAM_LEARNING_BRIEF_EVENT_TYPE,
        "component": DAILY_TELEGRAM_LEARNING_BRIEF_COMPONENT,
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
        "strategy_learning_applied_count": 0,
        "live_capital_enabled": False,
        "boundary": DAILY_TELEGRAM_LEARNING_BRIEF_BOUNDARY,
    }
    with event_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True) + "\n")
    EventLog(echo=False).write(
        event_type=DAILY_TELEGRAM_LEARNING_BRIEF_EVENT_TYPE,
        component=DAILY_TELEGRAM_LEARNING_BRIEF_COMPONENT,
        payload=event,
    )
    return {
        "output_path": str(output_path),
        "history_path": str(history_path),
        "event_path": str(event_path),
    }
