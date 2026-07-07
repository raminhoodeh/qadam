"""Qadam next-generation Telegram VNext.

This layer prepares short, specific, deduped Telegram note candidates from the
next-generation dashboard state. It is a review-only communications mirror: it
does not send messages, accept commands, create trade candidates, create
approvals, place orders, call brokers, mutate policy, or grant proof credit.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator.config import Settings

SCHEMA_VERSION = "qadam_telegram_vnext.v1"
PHASE_ID = "qadam_next_generation_phase_13_telegram_vnext"

PRIMARY_ARTIFACT = "qadam_telegram_vnext.json"
CANDIDATES_ARTIFACT = "qadam_telegram_next_generation_candidates.json"
DEDUPE_LEDGER_ARTIFACT = "qadam_telegram_next_generation_dedupe_ledger.jsonl"
QUALITY_ARTIFACT = "qadam_telegram_next_generation_quality.json"
DELIVERY_RECEIPTS_ARTIFACT = "qadam_telegram_next_generation_delivery_receipts.jsonl"
COMMUNICATIONS_MIRROR_ARTIFACT = "qadam_telegram_next_generation_dashboard_communications_mirror.json"
DASHBOARD_SUMMARY_ARTIFACT = "qadam_telegram_vnext_dashboard_summary.json"
EVENTS_ARTIFACT = "qadam_telegram_vnext_events.jsonl"

DASHBOARD_VNEXT_DOWNSTREAM_ARTIFACT = "qadam_dashboard_vnext_downstream_sections.json"
DASHBOARD_VNEXT_SUMMARY_ARTIFACT = "qadam_dashboard_vnext_dashboard_summary.json"
PATTERN_ENGINE_V2_SUMMARY_ARTIFACT = "qadam_pattern_engine_v2_dashboard_summary.json"
AKBER_FILTER_V2_SUMMARY_ARTIFACT = "qadam_akber_filter_v2_dashboard_summary.json"
ROUTER_V2_SUMMARY_ARTIFACT = "qadam_router_v2_dashboard_summary.json"
LEARNING_ATTRIBUTION_V2_SUMMARY_ARTIFACT = "qadam_learning_attribution_v2_dashboard_summary.json"
PAPER_LIFECYCLE_V2_SUMMARY_ARTIFACT = "qadam_paper_lifecycle_v2_dashboard_summary.json"

MESSAGE_STATUSES = {
    "message_ready_for_review",
    "message_rejected_duplicate",
    "message_rejected_quality",
    "message_rejected_unsafe",
}

AUTHORITY_FLAGS = {
    "review_only": True,
    "public_safe": True,
    "paper_only": True,
    "command_disabled": True,
    "telegram_live_send_allowed": False,
    "telegram_command_path_enabled": False,
    "telegram_trade_command_enabled": False,
    "command_created": False,
    "trade_candidate_created": False,
    "qualified_setup_created": False,
    "risk_approval_created": False,
    "execution_approval_created": False,
    "paper_order_allowed": False,
    "paper_order_created": False,
    "broker_write_allowed": False,
    "broker_write_count": 0,
    "live_broker_endpoint_allowed": False,
    "proof_credit_allowed": False,
    "paper_proof_ledger_credit_allowed": False,
    "live_capital_enabled": False,
    "paper_growth_trial_calendar_advance_allowed": False,
    "simulated_elapsed_time_allowed": False,
}

FALSE_AUTHORITY_FIELDS = {key for key, value in AUTHORITY_FLAGS.items() if value is False}
ZERO_AUTHORITY_FIELDS = {key for key, value in AUTHORITY_FLAGS.items() if type(value) is int and value == 0}

GENERIC_PHRASES = (
    "qadam codebase upgrade",
    "codebase upgrade",
    "what changed:",
    "why it matters:",
    "what to check:",
    "detected update areas:",
    "system update",
    "status update",
    "many systems updated",
    "strategy modules active",
    "everything is running",
    "ai-powered",
    "advanced ai",
    "cutting edge",
    "seamless",
    "game-changing",
    "robust insights",
    "dynamic insights",
)

HARSH_PHRASES = (
    "slop",
    "nonsense",
    "broken",
    "failed",
    "failure",
)

INTERNAL_ONLY_PHRASES = (
    "qsase_",
    "degraded_command_failure",
    "paperops handoff",
    "q-ctrl",
    "broker write",
    "proof ledger credit",
)

UNSAFE_PATTERNS = (
    re.compile(r"^\s*/\w+", re.MULTILINE),
    re.compile(r"\b(?:buy|sell|short|close|cancel|replace|approve|submit)\s+[A-Z]{1,8}\b", re.IGNORECASE),
    re.compile(r"\b(?:place order|submit order|approve trade|grant proof|enable live capital)\b", re.IGNORECASE),
)

REQUIRED_LINES = ("title", "evidence", "state", "blocker")


@dataclass(frozen=True)
class TelegramVNextBundle:
    primary: dict[str, Any]
    candidates: dict[str, Any]
    quality: dict[str, Any]
    dedupe_records: list[dict[str, Any]]
    delivery_receipts: list[dict[str, Any]]
    communications_mirror: dict[str, Any]
    dashboard_summary: dict[str, Any]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _runtime_dir(settings: Settings | None = None) -> Path:
    active_settings = settings or Settings.from_env()
    path = Path(active_settings.runtime_dir)
    if not path.is_absolute():
        path = _repo_root() / path
    return path


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def _json_dump(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _jsonl_line(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True) + "\n"


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _read_jsonl(path: Path, limit: int | None = None) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    if limit is not None:
        lines = lines[-limit:]
    records: list[dict[str, Any]] = []
    for line in lines:
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            records.append(payload)
    return records


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_json_dump(payload), encoding="utf-8")


def _append_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for record in records:
            handle.write(_jsonl_line(record))


def _hash_id(parts: list[Any], prefix: str) -> str:
    raw = "|".join(str(part) for part in parts)
    return f"{prefix}:{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:20]}"


def _artifact_ref(filename: str) -> str:
    return f"data/runtime/{filename}"


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _short(value: Any, fallback: str = "not recorded", limit: int = 110) -> str:
    text = " ".join(str(value or "").replace("\n", " ").split()).strip()
    if not text:
        text = fallback
    if len(text) <= limit:
        return text
    clipped = text[: max(0, limit - 1)].rstrip(" ,.;:")
    if " " in clipped:
        clipped = clipped.rsplit(" ", 1)[0].rstrip(" ,.;:")
    return clipped


def _humanize(value: Any, fallback: str = "not recorded", limit: int = 110) -> str:
    text = _short(value, fallback=fallback, limit=limit)
    text = text.replace("_", " ")
    text = re.sub(r"\b[a-z]+:", "", text).strip()
    return text[:1].upper() + text[1:] if text else fallback


def _authority_block() -> dict[str, Any]:
    return dict(AUTHORITY_FLAGS)


def _load_context(settings: Settings | None = None) -> dict[str, Any]:
    runtime = _runtime_dir(settings)
    return {
        "runtime_dir": runtime,
        "dashboard_vnext_downstream": _read_json(runtime / DASHBOARD_VNEXT_DOWNSTREAM_ARTIFACT),
        "dashboard_vnext_summary": _read_json(runtime / DASHBOARD_VNEXT_SUMMARY_ARTIFACT),
        "pattern_engine_v2_summary": _read_json(runtime / PATTERN_ENGINE_V2_SUMMARY_ARTIFACT),
        "akber_filter_v2_summary": _read_json(runtime / AKBER_FILTER_V2_SUMMARY_ARTIFACT),
        "router_v2_summary": _read_json(runtime / ROUTER_V2_SUMMARY_ARTIFACT),
        "learning_attribution_v2_summary": _read_json(runtime / LEARNING_ATTRIBUTION_V2_SUMMARY_ARTIFACT),
        "paper_lifecycle_v2_summary": _read_json(runtime / PAPER_LIFECYCLE_V2_SUMMARY_ARTIFACT),
        "dedupe_history": _read_jsonl(runtime / DEDUPE_LEDGER_ARTIFACT, limit=1000),
    }


def _section(context: dict[str, Any], display_name: str) -> dict[str, Any]:
    downstream = _safe_dict(context.get("dashboard_vnext_downstream"))
    for section in _safe_list(downstream.get("sections")):
        if _safe_dict(section).get("display_name") == display_name:
            return _safe_dict(section)
    return {}


def _signal_summary(card: dict[str, Any]) -> str:
    signal = str(card.get("detected_signal") or "")
    signal = re.sub(r"^Do\s+", "", signal, flags=re.IGNORECASE)
    signal = signal.split(" imply ", 1)[0]
    signal = signal.rstrip(" ?.")
    return _humanize(signal, fallback="source and price evidence", limit=96)


def _state_line(stage: str, tradeability: str) -> str:
    stage_text = stage.lower().replace("_", " ") or "documented"
    if "paper" in tradeability.lower():
        return f"{stage_text}; ready for paper review only"
    return f"{stage_text}; not tradeable yet"


def _message_fingerprint(message_class: str, event_identity: dict[str, Any], body: str) -> str:
    raw = {
        "message_class": message_class,
        "event_identity": event_identity,
        "body": body,
    }
    return hashlib.sha256(json.dumps(raw, sort_keys=True).encode("utf-8")).hexdigest()


def score_telegram_vnext_message(body: str) -> dict[str, Any]:
    text = str(body or "")
    lower = text.lower()
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    title_present = bool(lines and lines[0].lower().startswith("qadam "))
    evidence_present = any(line.lower().startswith("evidence:") and len(line.split(":", 1)[1].strip()) >= 8 for line in lines)
    state_present = any(line.lower().startswith("state:") and len(line.split(":", 1)[1].strip()) >= 4 for line in lines)
    blocker_present = any(line.lower().startswith("blocker:") and len(line.split(":", 1)[1].strip()) >= 4 for line in lines)
    generic_hits = [phrase for phrase in GENERIC_PHRASES if phrase in lower]
    harsh_hits = [phrase for phrase in HARSH_PHRASES if phrase in lower]
    internal_hits = [phrase for phrase in INTERNAL_ONLY_PHRASES if phrase in lower]
    unsafe_hits = [pattern.pattern for pattern in UNSAFE_PATTERNS if pattern.search(text)]
    errors: list[str] = []
    if not title_present:
        errors.append("missing_qadam_title")
    if not evidence_present:
        errors.append("missing_evidence_line")
    if not state_present:
        errors.append("missing_state_line")
    if not blocker_present:
        errors.append("missing_blocker_line")
    if len(text) > 320:
        errors.append("body_too_long")
    if len(lines) > 5:
        errors.append("too_many_lines")
    if generic_hits:
        errors.append("generic_language")
    if harsh_hits:
        errors.append("harsh_language")
    if internal_hits:
        errors.append("internal_only_language")
    if unsafe_hits:
        errors.append("unsafe_command_or_authority_language")
    specificity_score = 20
    specificity_score += 15 if title_present else 0
    specificity_score += 20 if evidence_present else 0
    specificity_score += 15 if state_present else 0
    specificity_score += 15 if blocker_present else 0
    specificity_score += 10 if len(text) <= 240 else 0
    specificity_score += 5 if len(lines) <= 5 else 0
    specificity_score -= 25 * len(generic_hits)
    specificity_score -= 25 * len(harsh_hits)
    specificity_score -= 25 * len(internal_hits)
    specificity_score -= 40 * len(unsafe_hits)
    specificity_score = max(0, min(100, specificity_score))
    return {
        "schema_version": SCHEMA_VERSION,
        "passed": not errors,
        "specificity_status": "specific" if specificity_score >= 80 and not errors else "not_specific",
        "specificity_score": specificity_score,
        "human_style_status": "human" if len(text) <= 320 and len(lines) <= 5 and not harsh_hits and not generic_hits else "needs_edit",
        "line_count": len(lines),
        "character_count": len(text),
        "required_lines": {
            "title": title_present,
            "evidence": evidence_present,
            "state": state_present,
            "blocker": blocker_present,
        },
        "generic_hits": generic_hits,
        "harsh_hits": harsh_hits,
        "internal_hits": internal_hits,
        "unsafe_hits": unsafe_hits,
        "errors": sorted(set(errors)),
    }


def _candidate(
    *,
    message_class: str,
    event_identity: dict[str, Any],
    body: str,
    generated_at: str,
    source_artifact_refs: list[str],
) -> dict[str, Any]:
    fingerprint = _message_fingerprint(message_class, event_identity, body)
    quality = score_telegram_vnext_message(body)
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_telegram_vnext_message_candidate",
        "message_candidate_id": _hash_id([SCHEMA_VERSION, message_class, fingerprint], "qadam-telegram-vnext"),
        "generated_at": generated_at,
        "message_class": message_class,
        "event_identity": event_identity,
        "event_fingerprint": fingerprint,
        "body": body,
        "quality": quality,
        "status": "message_ready_for_review" if quality["passed"] else "message_rejected_quality",
        "source_artifact_refs": source_artifact_refs,
        "delivery": {
            "telegram_live_send_allowed": False,
            "live_send_attempted": False,
            "live_send_succeeded": False,
            "send_state": "review_only_no_live_send",
        },
        "authority": _authority_block(),
        "command_created": False,
        "trade_candidate_created": False,
        "risk_approval_created": False,
        "execution_approval_created": False,
        "paper_order_created": False,
        "broker_write_count": 0,
        "proof_credit_allowed": False,
        "live_capital_enabled": False,
    }


def build_telegram_vnext_candidates(context: dict[str, Any], generated_at: str) -> list[dict[str, Any]]:
    pattern_section = _section(context, "Pattern Recognition Findings")
    akber_section = _section(context, "Akber Filter State")
    router_section = _section(context, "Router / PaperOps Decision")
    learning_section = _section(context, "Learning Ledger")
    pattern_cards = [_safe_dict(card) for card in _safe_list(pattern_section.get("cards"))]
    top_pattern = pattern_cards[0] if pattern_cards else {}
    akber_summary = _safe_dict(context.get("akber_filter_v2_summary"))
    router_summary = _safe_dict(context.get("router_v2_summary"))
    learning_summary = _safe_dict(context.get("learning_attribution_v2_summary"))
    dashboard_summary = _safe_dict(context.get("dashboard_vnext_summary"))

    pattern_market = _short(top_pattern.get("market_affected"), "watched market", 42)
    pattern_stage = _short(top_pattern.get("stage"), "documented research finding", 52)
    pattern_tradeability = _short(top_pattern.get("tradeability_state"), "not tradeable yet", 48)
    pattern_blocker = _humanize(top_pattern.get("what_blocks_the_trade"), "Akber needs practical confirmation", 102)
    pattern_body = "\n".join(
        [
            "Qadam pattern note:",
            f"{pattern_market} pattern is under review.",
            f"Evidence: {_signal_summary(top_pattern)}.",
            f"State: {_state_line(pattern_stage, pattern_tradeability)}.",
            f"Blocker: {pattern_blocker}.",
        ]
    )

    akber_hold_count = int(akber_summary.get("hold_count", 0) or 0)
    akber_pass_count = int(akber_summary.get("pass_count", 0) or 0)
    akber_body = "\n".join(
        [
            "Qadam filter note:",
            f"{akber_hold_count} setup(s) are held before trade review.",
            "Evidence: catalyst, technical, volume, volatility and liquidity context are incomplete.",
            f"State: {akber_pass_count} passed; {akber_hold_count} held for more confirmation.",
            "Blocker: practical confirmation is missing.",
        ]
    )

    reviewed_count = int(router_summary.get("decision_count", 0) or 0)
    paper_review_count = int(router_summary.get("paper_review_candidate_count", 0) or 0)
    why_not = _humanize(
        router_summary.get("why_not_trading_now_plain_english") or router_section.get("single_current_answer"),
        "No setup has cleared the final paper-trade gate",
        112,
    )
    router_body = "\n".join(
        [
            "Qadam trade gate note:",
            "No setup is tradeable right now." if paper_review_count == 0 else f"{paper_review_count} setup(s) await paper review.",
            f"Evidence: {reviewed_count} setup(s) reviewed; {paper_review_count} reached paper review.",
            "State: held before the guarded paper route.",
            f"Blocker: {why_not}.",
        ]
    )

    attribution_count = int(learning_summary.get("attribution_record_count", 0) or 0)
    proposal_count = int(learning_summary.get("proposal_count", 0) or 0)
    learning_body = "\n".join(
        [
            "Qadam learning note:",
            f"{attribution_count} outcome records are attributed.",
            "Evidence: backtest, shadow, filter, router, paper route and paper-trade outcomes.",
            f"State: {proposal_count} improvement proposal(s), none applied automatically.",
            "Blocker: changes require review before use.",
        ]
    )

    protected_count = int(dashboard_summary.get("protected_section_count", 0) or 0)
    downstream_count = int(dashboard_summary.get("downstream_section_count", 0) or 0)
    portfolio_agrees = dashboard_summary.get("all_portfolio_values_agree") is True
    dashboard_body = "\n".join(
        [
            "Qadam dashboard note:",
            "The public mirror is current and portfolio values agree." if portfolio_agrees else "The public mirror needs portfolio parity review.",
            f"Evidence: {protected_count} protected sections and {downstream_count} evidence sections are visible.",
            "State: review-only communications mirror.",
            "Blocker: Telegram cannot send live messages or take commands.",
        ]
    )

    return [
        _candidate(
            message_class="pattern_note",
            event_identity={
                "pattern_id": top_pattern.get("pattern_id") or "no_pattern",
                "market": pattern_market,
                "tradeability_state": pattern_tradeability,
                "blocker": pattern_blocker,
            },
            body=pattern_body,
            generated_at=generated_at,
            source_artifact_refs=[
                _artifact_ref(DASHBOARD_VNEXT_DOWNSTREAM_ARTIFACT),
                _artifact_ref(PATTERN_ENGINE_V2_SUMMARY_ARTIFACT),
            ],
        ),
        _candidate(
            message_class="akber_filter_note",
            event_identity={
                "hold_count": akber_hold_count,
                "pass_count": akber_pass_count,
                "router_eligible_count": akber_summary.get("router_eligible_count", 0),
            },
            body=akber_body,
            generated_at=generated_at,
            source_artifact_refs=[
                _artifact_ref(AKBER_FILTER_V2_SUMMARY_ARTIFACT),
                _artifact_ref(DASHBOARD_VNEXT_DOWNSTREAM_ARTIFACT),
            ],
        ),
        _candidate(
            message_class="router_paper_route_note",
            event_identity={
                "decision_count": reviewed_count,
                "paper_review_candidate_count": paper_review_count,
                "why_not_trading_now_reason": router_summary.get("why_not_trading_now_reason"),
            },
            body=router_body,
            generated_at=generated_at,
            source_artifact_refs=[
                _artifact_ref(ROUTER_V2_SUMMARY_ARTIFACT),
                _artifact_ref(DASHBOARD_VNEXT_DOWNSTREAM_ARTIFACT),
            ],
        ),
        _candidate(
            message_class="learning_note",
            event_identity={
                "attribution_record_count": attribution_count,
                "proposal_count": proposal_count,
                "proposal_applied_count": learning_summary.get("proposal_applied_count", 0),
            },
            body=learning_body,
            generated_at=generated_at,
            source_artifact_refs=[
                _artifact_ref(LEARNING_ATTRIBUTION_V2_SUMMARY_ARTIFACT),
                _artifact_ref(DASHBOARD_VNEXT_DOWNSTREAM_ARTIFACT),
            ],
        ),
        _candidate(
            message_class="dashboard_system_note",
            event_identity={
                "protected_section_count": protected_count,
                "downstream_section_count": downstream_count,
                "portfolio_values_agree": portfolio_agrees,
            },
            body=dashboard_body,
            generated_at=generated_at,
            source_artifact_refs=[
                _artifact_ref(DASHBOARD_VNEXT_SUMMARY_ARTIFACT),
                _artifact_ref(DASHBOARD_VNEXT_DOWNSTREAM_ARTIFACT),
            ],
        ),
    ]


def _apply_dedupe(candidates: list[dict[str, Any]], history: list[dict[str, Any]], generated_at: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    seen = {record.get("event_fingerprint") for record in history if record.get("event_fingerprint")}
    in_run_seen: set[str] = set()
    dedupe_records: list[dict[str, Any]] = []
    receipts: list[dict[str, Any]] = []
    for candidate in candidates:
        duplicate = candidate["event_fingerprint"] in seen or candidate["event_fingerprint"] in in_run_seen
        if candidate["quality"].get("unsafe_hits"):
            candidate["status"] = "message_rejected_unsafe"
        elif not candidate["quality"].get("passed"):
            candidate["status"] = "message_rejected_quality"
        elif duplicate:
            candidate["status"] = "message_rejected_duplicate"
        dedupe_records.append(
            {
                "schema_version": SCHEMA_VERSION,
                "generated_at": generated_at,
                "message_candidate_id": candidate["message_candidate_id"],
                "message_class": candidate["message_class"],
                "event_fingerprint": candidate["event_fingerprint"],
                "message_status": candidate["status"],
                "duplicate_suppressed": candidate["status"] == "message_rejected_duplicate",
                "material_change_required_for_repeat": True,
            }
        )
        receipts.append(
            {
                "schema_version": SCHEMA_VERSION,
                "generated_at": generated_at,
                "message_candidate_id": candidate["message_candidate_id"],
                "message_class": candidate["message_class"],
                "delivery_state": candidate["status"],
                "telegram_live_send_allowed": False,
                "live_send_attempted": False,
                "live_send_succeeded": False,
                "paper_order_created": False,
                "broker_write_count": 0,
                "proof_credit_allowed": False,
                "live_capital_enabled": False,
            }
        )
        in_run_seen.add(candidate["event_fingerprint"])
    return candidates, dedupe_records, receipts


def _quality_payload(candidates: list[dict[str, Any]], generated_at: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_telegram_next_generation_quality",
        "generated_at": generated_at,
        "status": "telegram_vnext_quality_passed"
        if all(candidate.get("quality", {}).get("passed") for candidate in candidates)
        else "telegram_vnext_quality_needs_copy_repair",
        "candidate_count": len(candidates),
        "quality_pass_count": sum(1 for candidate in candidates if candidate.get("quality", {}).get("passed")),
        "specific_count": sum(1 for candidate in candidates if candidate.get("quality", {}).get("specificity_status") == "specific"),
        "human_style_count": sum(1 for candidate in candidates if candidate.get("quality", {}).get("human_style_status") == "human"),
        "generic_rejected_count": sum(1 for candidate in candidates if candidate.get("quality", {}).get("generic_hits")),
        "unsafe_rejected_count": sum(1 for candidate in candidates if candidate.get("quality", {}).get("unsafe_hits")),
        "quality_rows": [
            {
                "message_candidate_id": candidate["message_candidate_id"],
                "message_class": candidate["message_class"],
                "status": candidate["status"],
                "specificity_status": candidate.get("quality", {}).get("specificity_status"),
                "specificity_score": candidate.get("quality", {}).get("specificity_score"),
                "human_style_status": candidate.get("quality", {}).get("human_style_status"),
                "character_count": candidate.get("quality", {}).get("character_count"),
                "errors": candidate.get("quality", {}).get("errors"),
            }
            for candidate in candidates
        ],
        "authority": _authority_block(),
    }


def _communications_mirror(candidates: list[dict[str, Any]], generated_at: str) -> dict[str, Any]:
    latest_messages = [
        {
            "message_candidate_id": candidate["message_candidate_id"],
            "message_class": candidate["message_class"],
            "body": candidate["body"],
            "status": candidate["status"],
            "quality": candidate["quality"],
            "send_allowed": False,
            "mode": "review_only",
            "created_at": generated_at,
        }
        for candidate in candidates[:6]
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_telegram_next_generation_dashboard_communications_mirror",
        "generated_at": generated_at,
        "status": "telegram_vnext_dashboard_communications_mirror_ready",
        "latest_messages": latest_messages,
        "recent_messages": latest_messages,
        "active_message_classes": [candidate["message_class"] for candidate in candidates],
        "pending_queue_count": 0,
        "dry_run_message_count": 0,
        "message_candidate_count": len(candidates),
        "message_ready_count": sum(1 for candidate in candidates if candidate.get("status") == "message_ready_for_review"),
        "message_rejected_duplicate_count": sum(1 for candidate in candidates if candidate.get("status") == "message_rejected_duplicate"),
        "message_rejected_quality_count": sum(1 for candidate in candidates if candidate.get("status") in {"message_rejected_quality", "message_rejected_unsafe"}),
        "telegram_live_send_allowed": False,
        "telegram_command_path_enabled": False,
        "telegram_trade_command_enabled": False,
        "live_send_allowed_count": 0,
        "command_path_enabled_count": 0,
        "failed_count": 0,
        "suppressed_count": sum(1 for candidate in candidates if candidate.get("status") == "message_rejected_duplicate"),
        "send_gate": "review_only_no_live_send",
        "mode": "review_only",
        "public_safe": True,
        "read_only": True,
        "command_disabled": True,
        "boundary": "Telegram VNext is a public-safe review mirror. It cannot take commands, create trade candidates, approve risk, place orders, call brokers, or grant proof credit.",
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_allowed": False,
        "live_capital_enabled": False,
        "authority": _authority_block(),
    }


def _dashboard_summary(primary: dict[str, Any], communications: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_telegram_vnext_dashboard_summary",
        "phase_id": PHASE_ID,
        "generated_at": primary["generated_at"],
        "status": primary["status"],
        "message_candidate_count": primary["message_candidate_count"],
        "message_ready_count": primary["message_ready_count"],
        "message_rejected_duplicate_count": primary["message_rejected_duplicate_count"],
        "message_rejected_quality_count": primary["message_rejected_quality_count"],
        "message_rejected_unsafe_count": primary["message_rejected_unsafe_count"],
        "quality_pass_count": primary["quality_pass_count"],
        "latest_message_preview": communications.get("latest_messages", [{}])[0].get("body") if communications.get("latest_messages") else None,
        "telegram_live_send_allowed": False,
        "telegram_command_path_enabled": False,
        "telegram_trade_command_enabled": False,
        "command_created": False,
        "trade_candidate_created": False,
        "qualified_setup_created": False,
        "risk_approval_created": False,
        "execution_approval_created": False,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_allowed": False,
        "live_capital_enabled": False,
        "public_safe": True,
        "review_only": True,
        "command_disabled": True,
        "boundary": communications["boundary"],
        "authority": _authority_block(),
    }


def build_telegram_vnext(settings: Settings | None = None) -> TelegramVNextBundle:
    context = _load_context(settings)
    generated_at = _iso(_now())
    raw_candidates = build_telegram_vnext_candidates(context, generated_at)
    candidates, dedupe_records, delivery_receipts = _apply_dedupe(raw_candidates, context.get("dedupe_history", []), generated_at)
    status_counts = Counter(candidate["status"] for candidate in candidates)
    quality = _quality_payload(candidates, generated_at)
    communications = _communications_mirror(candidates, generated_at)
    status = "telegram_vnext_ready"
    if status_counts.get("message_rejected_unsafe"):
        status = "telegram_vnext_blocked_unsafe"
    elif status_counts.get("message_rejected_quality"):
        status = "telegram_vnext_needs_copy_repair"
    elif status_counts.get("message_rejected_duplicate") and not status_counts.get("message_ready_for_review"):
        status = "telegram_vnext_ready_duplicate_quiet"
    primary = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_telegram_vnext",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "status": status,
        "public_safe": True,
        "read_only": True,
        "paper_only": True,
        "review_only": True,
        "command_disabled": True,
        "message_candidate_count": len(candidates),
        "message_ready_count": status_counts.get("message_ready_for_review", 0),
        "message_rejected_duplicate_count": status_counts.get("message_rejected_duplicate", 0),
        "message_rejected_quality_count": status_counts.get("message_rejected_quality", 0),
        "message_rejected_unsafe_count": status_counts.get("message_rejected_unsafe", 0),
        "quality_pass_count": quality["quality_pass_count"],
        "dedupe_record_count": len(dedupe_records),
        "delivery_receipt_count": len(delivery_receipts),
        "telegram_live_send_allowed": False,
        "telegram_command_path_enabled": False,
        "telegram_trade_command_enabled": False,
        "command_created": False,
        "trade_candidate_created": False,
        "qualified_setup_created": False,
        "risk_approval_created": False,
        "execution_approval_created": False,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_allowed": False,
        "paper_proof_ledger_credit_allowed": False,
        "live_capital_enabled": False,
        "artifact_refs": {
            "candidates": _artifact_ref(CANDIDATES_ARTIFACT),
            "dedupe_ledger": _artifact_ref(DEDUPE_LEDGER_ARTIFACT),
            "quality": _artifact_ref(QUALITY_ARTIFACT),
            "delivery_receipts": _artifact_ref(DELIVERY_RECEIPTS_ARTIFACT),
            "communications_mirror": _artifact_ref(COMMUNICATIONS_MIRROR_ARTIFACT),
            "dashboard_summary": _artifact_ref(DASHBOARD_SUMMARY_ARTIFACT),
        },
        "boundary": "Telegram VNext writes short review-only message candidates. It cannot create commands, trade candidates, approvals, orders, broker writes, live capital, or proof credit.",
        "authority": _authority_block(),
    }
    candidates_payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_telegram_next_generation_candidates",
        "generated_at": generated_at,
        "status": "qadam_telegram_next_generation_candidates_ready",
        "candidate_count": len(candidates),
        "ready_count": primary["message_ready_count"],
        "duplicate_count": primary["message_rejected_duplicate_count"],
        "quality_reject_count": primary["message_rejected_quality_count"] + primary["message_rejected_unsafe_count"],
        "candidates": candidates,
        "public_safe": True,
        "review_only": True,
        "command_disabled": True,
        "authority": _authority_block(),
    }
    dashboard_summary = _dashboard_summary(primary, communications)
    return TelegramVNextBundle(
        primary=primary,
        candidates=candidates_payload,
        quality=quality,
        dedupe_records=dedupe_records,
        delivery_receipts=delivery_receipts,
        communications_mirror=communications,
        dashboard_summary=dashboard_summary,
    )


def write_telegram_vnext(bundle: TelegramVNextBundle, settings: Settings | None = None) -> dict[str, str]:
    runtime = _runtime_dir(settings)
    runtime.mkdir(parents=True, exist_ok=True)
    paths = {
        "primary": runtime / PRIMARY_ARTIFACT,
        "candidates": runtime / CANDIDATES_ARTIFACT,
        "quality": runtime / QUALITY_ARTIFACT,
        "communications_mirror": runtime / COMMUNICATIONS_MIRROR_ARTIFACT,
        "dashboard_summary": runtime / DASHBOARD_SUMMARY_ARTIFACT,
        "dedupe_ledger": runtime / DEDUPE_LEDGER_ARTIFACT,
        "delivery_receipts": runtime / DELIVERY_RECEIPTS_ARTIFACT,
        "events": runtime / EVENTS_ARTIFACT,
    }
    _write_json(paths["primary"], bundle.primary)
    _write_json(paths["candidates"], bundle.candidates)
    _write_json(paths["quality"], bundle.quality)
    _write_json(paths["communications_mirror"], bundle.communications_mirror)
    _write_json(paths["dashboard_summary"], bundle.dashboard_summary)
    _append_jsonl(paths["dedupe_ledger"], bundle.dedupe_records)
    _append_jsonl(paths["delivery_receipts"], bundle.delivery_receipts)
    _append_jsonl(
        paths["events"],
        [
            {
                "schema_version": SCHEMA_VERSION,
                "generated_at": bundle.primary["generated_at"],
                "event_type": "qadam_telegram_vnext_written",
                "status": bundle.primary["status"],
                "message_candidate_count": bundle.primary["message_candidate_count"],
                "message_ready_count": bundle.primary["message_ready_count"],
                "message_rejected_duplicate_count": bundle.primary["message_rejected_duplicate_count"],
                "paper_order_created_count": 0,
                "broker_write_count": 0,
                "proof_credit_allowed": False,
                "live_capital_enabled": False,
            }
        ],
    )
    return {key: str(path) for key, path in paths.items()}


def build_and_write_telegram_vnext(settings: Settings | None = None) -> tuple[TelegramVNextBundle, dict[str, str], list[str]]:
    bundle = build_telegram_vnext(settings)
    errors = validate_telegram_vnext_bundle(bundle)
    written = write_telegram_vnext(bundle, settings)
    return bundle, written, errors


def load_telegram_vnext(settings: Settings | None = None) -> TelegramVNextBundle:
    runtime = _runtime_dir(settings)
    return TelegramVNextBundle(
        primary=_read_json(runtime / PRIMARY_ARTIFACT),
        candidates=_read_json(runtime / CANDIDATES_ARTIFACT),
        quality=_read_json(runtime / QUALITY_ARTIFACT),
        dedupe_records=_read_jsonl(runtime / DEDUPE_LEDGER_ARTIFACT, limit=1000),
        delivery_receipts=_read_jsonl(runtime / DELIVERY_RECEIPTS_ARTIFACT, limit=1000),
        communications_mirror=_read_json(runtime / COMMUNICATIONS_MIRROR_ARTIFACT),
        dashboard_summary=_read_json(runtime / DASHBOARD_SUMMARY_ARTIFACT),
    )


def validate_telegram_vnext_candidate(candidate: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    candidate_id = candidate.get("message_candidate_id", "unknown")
    if candidate.get("artifact_type") != "qadam_telegram_vnext_message_candidate":
        errors.append(f"candidate_{candidate_id}_artifact_type_invalid")
    if candidate.get("status") not in MESSAGE_STATUSES:
        errors.append(f"candidate_{candidate_id}_status_invalid")
    body = str(candidate.get("body") or "")
    quality = _safe_dict(candidate.get("quality"))
    if len(body) > 320:
        errors.append(f"candidate_{candidate_id}_too_long")
    if quality.get("passed") is not True:
        errors.append(f"candidate_{candidate_id}_quality_not_passed")
    if candidate.get("status") == "message_rejected_quality" and quality.get("unsafe_hits"):
        errors.append(f"candidate_{candidate_id}_unsafe_should_not_be_quality_only")
    if candidate.get("status") == "message_ready_for_review" and quality.get("passed") is not True:
        errors.append(f"candidate_{candidate_id}_ready_without_quality_pass")
    for line_name in REQUIRED_LINES:
        if _safe_dict(quality.get("required_lines")).get(line_name) is not True:
            errors.append(f"candidate_{candidate_id}_missing_{line_name}_line")
    delivery = _safe_dict(candidate.get("delivery"))
    if delivery.get("telegram_live_send_allowed") is not False:
        errors.append(f"candidate_{candidate_id}_live_send_allowed")
    if delivery.get("live_send_attempted") is not False or delivery.get("live_send_succeeded") is not False:
        errors.append(f"candidate_{candidate_id}_live_send_attempted")
    authority = _safe_dict(candidate.get("authority"))
    for field in FALSE_AUTHORITY_FIELDS:
        if authority.get(field) is not False:
            errors.append(f"candidate_{candidate_id}_authority_{field}_must_be_false")
        if candidate.get(field) is not False and field in candidate:
            errors.append(f"candidate_{candidate_id}_{field}_must_be_false")
    for field in ZERO_AUTHORITY_FIELDS:
        if int(authority.get(field, -1) or 0) != 0:
            errors.append(f"candidate_{candidate_id}_authority_{field}_must_be_zero")
        if field in candidate and int(candidate.get(field, -1) or 0) != 0:
            errors.append(f"candidate_{candidate_id}_{field}_must_be_zero")
    if not candidate.get("source_artifact_refs"):
        errors.append(f"candidate_{candidate_id}_missing_source_artifact_refs")
    return sorted(set(errors))


def validate_telegram_vnext_bundle(bundle: TelegramVNextBundle) -> list[str]:
    errors: list[str] = []
    primary = bundle.primary
    if primary.get("artifact_type") != "qadam_telegram_vnext":
        errors.append("primary_artifact_type_invalid")
    if primary.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version_invalid")
    if primary.get("status") not in {
        "telegram_vnext_ready",
        "telegram_vnext_ready_duplicate_quiet",
        "telegram_vnext_needs_copy_repair",
        "telegram_vnext_blocked_unsafe",
    }:
        errors.append("status_invalid")
    for field in ("public_safe", "read_only", "paper_only", "review_only", "command_disabled"):
        if primary.get(field) is not True:
            errors.append(f"{field}_must_be_true")
    for field in FALSE_AUTHORITY_FIELDS:
        if primary.get("authority", {}).get(field) is not False:
            errors.append(f"primary_authority_{field}_must_be_false")
        if field in primary and primary.get(field) is not False:
            errors.append(f"primary_{field}_must_be_false")
    for field in ZERO_AUTHORITY_FIELDS:
        if int(primary.get("authority", {}).get(field, -1) or 0) != 0:
            errors.append(f"primary_authority_{field}_must_be_zero")
    for field in ("paper_order_created_count", "broker_write_count"):
        if int(primary.get(field, -1) or 0) != 0:
            errors.append(f"{field}_must_be_zero")
    candidates = _safe_list(bundle.candidates.get("candidates"))
    if primary.get("message_candidate_count") != len(candidates):
        errors.append("message_candidate_count_mismatch")
    if bundle.candidates.get("candidate_count") != len(candidates):
        errors.append("candidate_payload_count_mismatch")
    for candidate in candidates:
        errors.extend(validate_telegram_vnext_candidate(_safe_dict(candidate)))
    bodies = [candidate.get("body") for candidate in candidates]
    if len(set(bodies)) != len(bodies):
        errors.append("duplicate_message_body_in_run")
    quality = bundle.quality
    if quality.get("candidate_count") != len(candidates):
        errors.append("quality_candidate_count_mismatch")
    if quality.get("quality_pass_count") != len(candidates):
        errors.append("quality_pass_count_mismatch")
    communications = bundle.communications_mirror
    if communications.get("status") != "telegram_vnext_dashboard_communications_mirror_ready":
        errors.append("communications_mirror_status_invalid")
    if communications.get("telegram_live_send_allowed") is not False:
        errors.append("communications_live_send_allowed")
    if communications.get("telegram_command_path_enabled") is not False:
        errors.append("communications_command_path_enabled")
    if communications.get("message_candidate_count") != len(candidates):
        errors.append("communications_candidate_count_mismatch")
    for field in ("paper_order_created_count", "broker_write_count"):
        if int(communications.get(field, -1) or 0) != 0:
            errors.append(f"communications_{field}_must_be_zero")
    if communications.get("proof_credit_allowed") is not False or communications.get("live_capital_enabled") is not False:
        errors.append("communications_authority_boundary_invalid")
    summary = bundle.dashboard_summary
    if summary.get("message_candidate_count") != len(candidates):
        errors.append("dashboard_summary_candidate_count_mismatch")
    if summary.get("telegram_live_send_allowed") is not False or summary.get("telegram_command_path_enabled") is not False:
        errors.append("dashboard_summary_telegram_authority_invalid")
    if summary.get("trade_candidate_created") is not False:
        errors.append("dashboard_summary_trade_candidate_created")
    if summary.get("proof_credit_allowed") is not False or summary.get("live_capital_enabled") is not False:
        errors.append("dashboard_summary_authority_boundary_invalid")
    return sorted(set(errors))


def validate_negative_telegram_vnext_probes() -> list[str]:
    errors: list[str] = []
    generic = score_telegram_vnext_message(
        "Qadam Codebase Upgrade\n"
        "What changed: many systems updated.\n"
        "Evidence: strategy modules active.\n"
        "State: everything is running.\n"
        "Blocker: none."
    )
    unsafe = score_telegram_vnext_message(
        "Qadam trade note:\n"
        "Buy SMH now.\n"
        "Evidence: operator command.\n"
        "State: trade approved.\n"
        "Blocker: none."
    )
    if "generic_language" not in generic.get("errors", []):
        errors.append("generic_probe_not_rejected")
    if "unsafe_command_or_authority_language" not in unsafe.get("errors", []):
        errors.append("unsafe_probe_not_rejected")
    return errors
