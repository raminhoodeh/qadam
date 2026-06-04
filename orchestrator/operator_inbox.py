"""RS-7 operator inbox, Telegram, and human oversight contract.

The operator inbox is a local durable review rail for founding Fund Managers.
It can show what needs attention, what may be acknowledged/commented on, and
what Telegram can summarize. It cannot approve trades, place orders, create
trade candidates, enable live capital, or turn Telegram into a command path.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.event_log import EventLog


OPERATOR_INBOX_SCHEMA_VERSION = 1
OPERATOR_INBOX_RUNTIME_ARTIFACT = "operator_inbox.json"
OPERATOR_INBOX_HISTORY = "operator_inbox_history.jsonl"
OPERATOR_INBOX_ACKNOWLEDGEMENTS = "operator_inbox_acknowledgements.jsonl"
OPERATOR_INBOX_COMMENTS = "operator_inbox_comments.jsonl"
OPERATOR_INBOX_EVENT_LOG = "operator_inbox_events.jsonl"

OPERATOR_INBOX_EVENT_TYPE = "operator_inbox_recorded"
OPERATOR_INBOX_COMPONENT = "operator_inbox"

OPERATOR_INBOX_BOUNDARY = (
    "RS-7 operator inbox is a local human-oversight and Telegram summary rail. "
    "Fund Managers can read, acknowledge, comment, and request review, but "
    "inbox items, comments, acknowledgements, dashboard actions, and Telegram "
    "messages cannot create signals, trade candidates, risk approvals, "
    "execution approvals, paper orders, broker writes, Q-CTRL jobs, or live "
    "capital authority."
)

ITEM_CLASSES = {
    "source_degraded",
    "credential_expiring",
    "research_goal_needs_review",
    "strategy_challenge_ready",
    "signal_blocked",
    "paper_trade_candidate_ready",
    "paper_order_submitted",
    "position_opened",
    "position_closed",
    "postmortem_due",
    "kill_switch_triggered",
}

SEVERITIES = {"info", "low", "medium", "high", "critical"}
ITEM_STATUSES = {"open", "acknowledged", "closed", "expired"}
ALLOWED_ACTIONS = {
    "acknowledge",
    "comment",
    "request_review",
    "open_dashboard_section",
    "view_source_artifact",
}
FORBIDDEN_ACTIONS = {
    "create_signal",
    "create_trade_candidate",
    "approve_risk",
    "approve_execution",
    "stage_order",
    "submit_order",
    "modify_order",
    "resize_position",
    "close_position",
    "write_broker",
    "run_qctrl_job",
    "enable_live_capital",
    "telegram_trade_command",
}
READ_ONLY_COMMANDS = (
    "/status",
    "/sources",
    "/research-goals",
    "/trades",
    "/blocked",
    "/portfolio",
    "/worldview",
    "/postmortems",
)
TELEGRAM_NOTIFICATION_CLASSES = {
    "source_degraded",
    "trade_candidate",
    "blocked_trade",
    "staged_paper_order",
    "submitted_paper_order",
    "open_position",
    "closed_trade",
    "postmortem_due",
    "insight_digest",
}
AUTHORITY_FIELDS = (
    "signal_authority",
    "trade_candidate_creation_allowed",
    "risk_handoff_allowed",
    "risk_approval_allowed",
    "execution_allowed",
    "execution_approval_allowed",
    "paper_order_allowed",
    "broker_write_allowed",
    "telegram_command_authority",
    "qctrl_provider_call_allowed",
    "live_capital_enabled",
)
PUBLIC_STATUS_FIELDS = {
    "schema_version",
    "status",
    "generated_at",
    "item_count",
    "open_item_count",
    "acknowledged_item_count",
    "closed_item_count",
    "expired_item_count",
    "high_or_critical_item_count",
    "telegram_related_item_count",
    "postmortem_due_item_count",
    "paper_trade_related_item_count",
    "comment_count",
    "acknowledgement_count",
    "recent_items",
    "allowed_read_commands",
    "read_command_count",
    "telegram_notification_classes",
    "telegram_notifications_allowed",
    "telegram_live_send_allowed",
    "telegram_command_authority",
    "comment_authority",
    "comment_can_approve_trades",
    "ack_can_approve_trades",
    "signal_authority",
    "trade_candidate_creation_allowed",
    "risk_handoff_allowed",
    "risk_approval_allowed",
    "execution_allowed",
    "execution_approval_allowed",
    "paper_order_allowed",
    "broker_write_allowed",
    "qctrl_provider_call_allowed",
    "live_capital_enabled",
    "operator_action_authority",
    "public_safe",
    "validation_error_count",
    "boundary",
}

PROHIBITED_PUBLIC_PATTERNS = (
    re.compile(r"\d{6,}:[A-Za-z0-9_-]{20,}"),
    re.compile(r"\bghp_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bvcp_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bAIza[0-9A-Za-z_-]{20,}\b"),
    re.compile(r"\bsb_secret_[0-9A-Za-z_-]{12,}\b"),
    re.compile(r"/Users/|/private/|/var/folders/|\\Users\\"),
    re.compile(r"chat_id|username|first_name|last_name|bot_token", re.IGNORECASE),
)


@dataclass(frozen=True)
class OperatorInboxItem:
    schema_version: int
    item_id: str
    item_class: str
    created_at: str
    expires_at: str
    severity: str
    owner: str
    source_artifact: str
    source_ref: str
    dashboard_section: str
    summary: str
    required_action: str
    allowed_actions: tuple[str, ...]
    forbidden_actions: tuple[str, ...]
    acknowledged_by: str | None
    acknowledged_at: str | None
    comment_count: int
    status: str
    telegram_notification_class: str | None
    telegram_notification_allowed: bool
    signal_authority: bool
    trade_candidate_creation_allowed: bool
    risk_handoff_allowed: bool
    risk_approval_allowed: bool
    execution_allowed: bool
    execution_approval_allowed: bool
    paper_order_allowed: bool
    broker_write_allowed: bool
    telegram_command_authority: bool
    qctrl_provider_call_allowed: bool
    live_capital_enabled: bool
    boundary: str

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["allowed_actions"] = list(self.allowed_actions)
        payload["forbidden_actions"] = list(self.forbidden_actions)
        return payload


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_time(value: Any) -> datetime:
    if isinstance(value, str) and value:
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
        except ValueError:
            pass
    return datetime.now(timezone.utc)


def _runtime_path(settings: Settings, filename: str) -> Path:
    path = Path(settings.runtime_dir) / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _hash_item(item_class: str, source_ref: str, summary: str) -> str:
    digest = hashlib.sha256(
        json.dumps(
            {
                "item_class": item_class,
                "source_ref": source_ref,
                "summary": summary[:160],
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()[:16]
    return f"rs7:{item_class}:{digest}"


def _clean_text(value: Any, *, limit: int = 260) -> str:
    text = re.sub(r"\s+", " ", str(value or "").replace("\x00", " ")).strip()
    for pattern in PROHIBITED_PUBLIC_PATTERNS:
        text = pattern.sub("[redacted]", text)
    return text[:limit] or "No summary exported."


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            try:
                payload = json.loads(stripped)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                rows.append(payload)
    return rows


def _default_forbidden() -> tuple[str, ...]:
    return tuple(sorted(FORBIDDEN_ACTIONS))


def _default_allowed() -> tuple[str, ...]:
    return (
        "acknowledge",
        "comment",
        "request_review",
        "open_dashboard_section",
        "view_source_artifact",
    )


def _comment_counts(comments: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for comment in comments:
        item_id = str(comment.get("item_id") or "")
        if item_id:
            counts[item_id] = counts.get(item_id, 0) + 1
    return counts


def _ack_map(acks: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for ack in acks:
        item_id = str(ack.get("item_id") or "")
        if item_id:
            latest[item_id] = ack
    return latest


def _item(
    *,
    item_class: str,
    generated_at: str,
    severity: str,
    owner: str,
    source_artifact: str,
    source_ref: str,
    dashboard_section: str,
    summary: str,
    required_action: str,
    telegram_notification_class: str | None = None,
    expiry_days: int = 7,
    acknowledgements: dict[str, dict[str, Any]] | None = None,
    comment_counts: dict[str, int] | None = None,
) -> OperatorInboxItem:
    if item_class not in ITEM_CLASSES:
        raise ValueError(f"invalid operator inbox item class: {item_class}")
    if severity not in SEVERITIES:
        raise ValueError(f"invalid operator inbox severity: {severity}")
    source_ref_clean = _clean_text(source_ref, limit=180)
    summary_clean = _clean_text(summary, limit=360)
    item_id = _hash_item(item_class, source_ref_clean, summary_clean)
    created_dt = _parse_time(generated_at)
    ack = (acknowledgements or {}).get(item_id)
    acknowledged_at = str(ack.get("acknowledged_at")) if ack else None
    status = "acknowledged" if ack else "open"
    return OperatorInboxItem(
        schema_version=OPERATOR_INBOX_SCHEMA_VERSION,
        item_id=item_id,
        item_class=item_class,
        created_at=generated_at,
        expires_at=(created_dt + timedelta(days=expiry_days)).isoformat(),
        severity=severity,
        owner=owner,
        source_artifact=_clean_text(source_artifact, limit=160),
        source_ref=source_ref_clean,
        dashboard_section=dashboard_section,
        summary=summary_clean,
        required_action=_clean_text(required_action, limit=300),
        allowed_actions=_default_allowed(),
        forbidden_actions=_default_forbidden(),
        acknowledged_by="founding_fund_manager" if ack else None,
        acknowledged_at=acknowledged_at,
        comment_count=(comment_counts or {}).get(item_id, 0),
        status=status,
        telegram_notification_class=telegram_notification_class,
        telegram_notification_allowed=telegram_notification_class in TELEGRAM_NOTIFICATION_CLASSES,
        signal_authority=False,
        trade_candidate_creation_allowed=False,
        risk_handoff_allowed=False,
        risk_approval_allowed=False,
        execution_allowed=False,
        execution_approval_allowed=False,
        paper_order_allowed=False,
        broker_write_allowed=False,
        telegram_command_authority=False,
        qctrl_provider_call_allowed=False,
        live_capital_enabled=False,
        boundary=OPERATOR_INBOX_BOUNDARY,
    )


def _add_unique(items: list[OperatorInboxItem], item: OperatorInboxItem) -> None:
    if item.item_id not in {existing.item_id for existing in items}:
        items.append(item)


def _build_items_from_payload(
    payload: dict[str, Any],
    *,
    acknowledgements: dict[str, dict[str, Any]],
    comment_counts: dict[str, int],
) -> list[OperatorInboxItem]:
    generated_at = str(payload.get("generated_at") or _now())
    items: list[OperatorInboxItem] = []

    for source in list(payload.get("watching") or [])[:80]:
        if not isinstance(source, dict):
            continue
        status = str(source.get("status") or "unknown")
        credential = str(source.get("credential_status") or "unknown")
        source_name = str(source.get("source_name") or source.get("source_key") or "source")
        if status in {"degraded", "blocked", "missing", "offline"}:
            _add_unique(
                items,
                _item(
                    item_class="source_degraded",
                    generated_at=generated_at,
                    severity="medium" if status == "degraded" else "high",
                    owner="COO / source spine",
                    source_artifact="watching",
                    source_ref=source_name,
                    dashboard_section="Evidence",
                    summary=f"{source_name} is {status}: {source.get('degraded_reason') or source.get('readiness') or 'source needs review'}",
                    required_action="Check source credential, provider status, latency, and whether source quorum still passes without this feed.",
                    telegram_notification_class="source_degraded",
                    acknowledgements=acknowledgements,
                    comment_counts=comment_counts,
                ),
            )
        if credential in {"missing", "missing_credentials", "degraded", "expiring", "expired"}:
            _add_unique(
                items,
                _item(
                    item_class="credential_expiring",
                    generated_at=generated_at,
                    severity="medium",
                    owner="Fund Manager / source credentials",
                    source_artifact="watching",
                    source_ref=source_name,
                    dashboard_section="Sources",
                    summary=f"{source_name} credential status is {credential}.",
                    required_action="Provide or refresh credentials when this source is needed for a live research quorum.",
                    telegram_notification_class="source_degraded",
                    acknowledgements=acknowledgements,
                    comment_counts=comment_counts,
                ),
            )

    cognition = payload.get("cognition") if isinstance(payload.get("cognition"), dict) else {}
    for goal in list(cognition.get("research_goal_records") or [])[:12]:
        if not isinstance(goal, dict):
            continue
        status = str(goal.get("status") or goal.get("stored_status") or "unknown")
        if status not in {"closed_no_trade", "closed", "expired"}:
            _add_unique(
                items,
                _item(
                    item_class="research_goal_needs_review",
                    generated_at=generated_at,
                    severity="low" if status in {"watching", "open"} else "medium",
                    owner="Research Analyst / Fund Manager",
                    source_artifact="cognition.research_goal_records",
                    source_ref=str(goal.get("goal_id") or goal.get("hypothesis") or "research_goal"),
                    dashboard_section="Reasoning",
                    summary=goal.get("hypothesis") or goal.get("summary") or "Research Goal requires review.",
                    required_action="Review missing corroboration, worldview lens, and whether evidence should advance or close as no-trade.",
                    telegram_notification_class="insight_digest",
                    acknowledgements=acknowledgements,
                    comment_counts=comment_counts,
                ),
            )

    strategy_packets = [packet for packet in cognition.get("strategy_lead_packets", []) if isinstance(packet, dict)]
    if strategy_packets:
        _add_unique(
            items,
            _item(
                item_class="strategy_challenge_ready",
                generated_at=generated_at,
                severity="medium",
                owner="Strategy Lead / Fund Manager",
                source_artifact="cognition.strategy_lead_packets",
                source_ref="strategy_lead_challenge_queue",
                dashboard_section="Reasoning",
                summary=f"{len(strategy_packets)} Strategy Lead packets are available for challenge review.",
                required_action="Review whether the Strategy Lead challenged evidence quality, contradiction pressure, and market confirmation correctly.",
                telegram_notification_class="insight_digest",
                acknowledgements=acknowledgements,
                comment_counts=comment_counts,
            ),
        )

    trade_layer = payload.get("trade_layer") if isinstance(payload.get("trade_layer"), dict) else {}
    for blocked in list(trade_layer.get("blocked") or [])[:12]:
        if not isinstance(blocked, dict):
            continue
        _add_unique(
            items,
            _item(
                item_class="signal_blocked",
                generated_at=generated_at,
                severity="medium",
                owner="Signal Integrity / Risk",
                source_artifact="trade_layer.blocked",
                source_ref=str(blocked.get("intent_id") or blocked.get("signal_id") or blocked.get("instrument") or "blocked_signal"),
                dashboard_section="Trades",
                summary=blocked.get("blocked_reason") or blocked.get("summary") or "A trade signal is blocked before execution.",
                required_action="Review the block reason; comment only if evidence, risk, or market context needs correction.",
                telegram_notification_class="blocked_trade",
                acknowledgements=acknowledgements,
                comment_counts=comment_counts,
            ),
        )
    for candidate in list(trade_layer.get("candidates") or [])[:12]:
        if not isinstance(candidate, dict):
            continue
        _add_unique(
            items,
            _item(
                item_class="paper_trade_candidate_ready",
                generated_at=generated_at,
                severity="high",
                owner="Risk Agent / Execution Auditor",
                source_artifact="trade_layer.candidates",
                source_ref=str(candidate.get("intent_id") or candidate.get("instrument") or "paper_candidate"),
                dashboard_section="Trades",
                summary=candidate.get("thesis") or candidate.get("catalyst") or "Paper trade candidate is ready for guarded review.",
                required_action="Confirm the candidate is distinct, source-backed, and still within risk limits. Do not approve through comments or Telegram.",
                telegram_notification_class="trade_candidate",
                acknowledgements=acknowledgements,
                comment_counts=comment_counts,
            ),
        )

    capital = payload.get("capital") if isinstance(payload.get("capital"), dict) else {}
    for order in list(capital.get("orders") or [])[:8]:
        if not isinstance(order, dict):
            continue
        _add_unique(
            items,
            _item(
                item_class="paper_order_submitted",
                generated_at=generated_at,
                severity="medium",
                owner="Execution Auditor / PaperOps",
                source_artifact="capital.orders",
                source_ref=str(order.get("order_id") or order.get("instrument") or "paper_order"),
                dashboard_section="Portfolio",
                summary=f"Paper order mirrored for {order.get('instrument') or 'instrument'} with status {order.get('status') or 'unknown'}.",
                required_action="Confirm broker reconciliation and lifecycle polling are reflected in the dashboard.",
                telegram_notification_class="submitted_paper_order",
                acknowledgements=acknowledgements,
                comment_counts=comment_counts,
            ),
        )
    for position in list(capital.get("open_positions") or [])[:8]:
        if not isinstance(position, dict):
            continue
        _add_unique(
            items,
            _item(
                item_class="position_opened",
                generated_at=generated_at,
                severity="medium",
                owner="Portfolio Monitor",
                source_artifact="capital.open_positions",
                source_ref=str(position.get("instrument") or position.get("symbol") or "open_position"),
                dashboard_section="Portfolio",
                summary=f"Open paper position: {position.get('instrument') or position.get('symbol') or 'instrument'}; P&L {position.get('unrealized_pnl_gbp', 'unknown')}.",
                required_action="Monitor thesis validity, stop/exit readiness, and whether lifecycle polling remains healthy.",
                telegram_notification_class="open_position",
                acknowledgements=acknowledgements,
                comment_counts=comment_counts,
            ),
        )
    for closed in list(capital.get("closed_trades") or [])[:8]:
        if not isinstance(closed, dict):
            continue
        _add_unique(
            items,
            _item(
                item_class="position_closed",
                generated_at=generated_at,
                severity="medium",
                owner="Postmortem Loop",
                source_artifact="capital.closed_trades",
                source_ref=str(closed.get("trade_id") or closed.get("instrument") or "closed_trade"),
                dashboard_section="Portfolio",
                summary=f"Closed paper trade: {closed.get('instrument') or 'instrument'}; postmortem {closed.get('postmortem_status') or 'unknown'}.",
                required_action="Review realized result and ensure postmortem marker is present before learning updates.",
                telegram_notification_class="closed_trade",
                acknowledgements=acknowledgements,
                comment_counts=comment_counts,
            ),
        )

    rs6 = payload.get("paper_lifecycle_portfolio_postmortem")
    if isinstance(rs6, dict) and _int(rs6.get("postmortem_due_count")):
        _add_unique(
            items,
            _item(
                item_class="postmortem_due",
                generated_at=generated_at,
                severity="high",
                owner="Postmortem Loop / Fund Manager",
                source_artifact="paper_lifecycle_portfolio_postmortem",
                source_ref="closed_trade_postmortem_queue",
                dashboard_section="Portfolio",
                summary=f"{rs6.get('postmortem_due_count')} closed paper trades have postmortem-due markers.",
                required_action="Complete or explicitly defer postmortems before any learning-loop update treats the result as mature evidence.",
                telegram_notification_class="postmortem_due",
                acknowledgements=acknowledgements,
                comment_counts=comment_counts,
            ),
        )

    kill_switch = payload.get("phase5_kill_switch_ledger")
    if isinstance(kill_switch, dict):
        active = _int(kill_switch.get("active_kill_switch_count") or kill_switch.get("active_count"))
        blocking = _int(kill_switch.get("blocking_kill_switch_count") or kill_switch.get("blocking_count"))
        if active or blocking:
            _add_unique(
                items,
                _item(
                    item_class="kill_switch_triggered",
                    generated_at=generated_at,
                    severity="critical",
                    owner="COO / Fund Manager",
                    source_artifact="phase5_kill_switch_ledger",
                    source_ref="kill_switch_ledger",
                    dashboard_section="Operations",
                    summary=f"Kill-switch ledger reports {active} active and {blocking} blocking switches.",
                    required_action="Investigate the kill-switch state. Comments can request review but cannot mutate switch state.",
                    telegram_notification_class="source_degraded",
                    acknowledgements=acknowledgements,
                    comment_counts=comment_counts,
                ),
            )

    return sorted(
        items,
        key=lambda item: (
            {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}.get(item.severity, 5),
            item.item_class,
            item.source_ref,
        ),
    )


class OperatorInboxStore:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings.from_env()
        self.runtime_path = _runtime_path(self.settings, OPERATOR_INBOX_RUNTIME_ARTIFACT)
        self.history_path = _runtime_path(self.settings, OPERATOR_INBOX_HISTORY)
        self.acknowledgements_path = _runtime_path(self.settings, OPERATOR_INBOX_ACKNOWLEDGEMENTS)
        self.comments_path = _runtime_path(self.settings, OPERATOR_INBOX_COMMENTS)
        self.event_log_path = _runtime_path(self.settings, OPERATOR_INBOX_EVENT_LOG)

    def acknowledgements(self) -> list[dict[str, Any]]:
        return _read_jsonl(self.acknowledgements_path)

    def comments(self) -> list[dict[str, Any]]:
        return _read_jsonl(self.comments_path)

    def acknowledge_item(
        self,
        *,
        item_id: str,
        actor_label: str = "founding_fund_manager",
        note: str = "",
    ) -> dict[str, Any]:
        record = {
            "schema_version": OPERATOR_INBOX_SCHEMA_VERSION,
            "item_id": _clean_text(item_id, limit=180),
            "actor_label": "founding_fund_manager",
            "note": _clean_text(note, limit=300),
            "acknowledged_at": _now(),
            "risk_approval_allowed": False,
            "paper_order_allowed": False,
            "broker_write_allowed": False,
            "live_capital_enabled": False,
            "boundary": OPERATOR_INBOX_BOUNDARY,
        }
        _append_jsonl(self.acknowledgements_path, record)
        return record

    def add_comment(
        self,
        *,
        item_id: str,
        body: str,
        actor_label: str = "founding_fund_manager",
        status: str = "open",
    ) -> dict[str, Any]:
        if status not in {"open", "resolved", "rejected", "implemented"}:
            raise ValueError(f"invalid operator inbox comment status: {status}")
        record = {
            "schema_version": OPERATOR_INBOX_SCHEMA_VERSION,
            "item_id": _clean_text(item_id, limit=180),
            "actor_label": "founding_fund_manager",
            "body": _clean_text(body, limit=600),
            "status": status,
            "created_at": _now(),
            "comment_can_approve_trades": False,
            "risk_approval_allowed": False,
            "paper_order_allowed": False,
            "broker_write_allowed": False,
            "live_capital_enabled": False,
            "boundary": OPERATOR_INBOX_BOUNDARY,
        }
        _append_jsonl(self.comments_path, record)
        return record

    def read_artifact(self) -> dict[str, Any]:
        return _read_json(self.runtime_path)


def build_operator_inbox(
    payload: dict[str, Any],
    *,
    settings: Settings | None = None,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    store = OperatorInboxStore(settings=settings)
    generated_at = str(payload.get("generated_at") or _now())
    acknowledgements = store.acknowledgements()
    comments = store.comments()
    ack_by_item = _ack_map(acknowledgements)
    comment_count_by_item = _comment_counts(comments)
    items = _build_items_from_payload(
        payload,
        acknowledgements=ack_by_item,
        comment_counts=comment_count_by_item,
    )
    item_payloads = [item.to_dict() for item in items]
    counts_by_status = {status: 0 for status in ITEM_STATUSES}
    for item in items:
        counts_by_status[item.status] = counts_by_status.get(item.status, 0) + 1
    artifact = {
        "schema_version": OPERATOR_INBOX_SCHEMA_VERSION,
        "status": "ok",
        "generated_at": generated_at,
        "item_count": len(items),
        "open_item_count": counts_by_status.get("open", 0),
        "acknowledged_item_count": counts_by_status.get("acknowledged", 0),
        "closed_item_count": counts_by_status.get("closed", 0),
        "expired_item_count": counts_by_status.get("expired", 0),
        "high_or_critical_item_count": sum(1 for item in items if item.severity in {"high", "critical"}),
        "telegram_related_item_count": sum(1 for item in items if item.telegram_notification_allowed),
        "postmortem_due_item_count": sum(1 for item in items if item.item_class == "postmortem_due"),
        "paper_trade_related_item_count": sum(
            1
            for item in items
            if item.item_class
            in {
                "paper_trade_candidate_ready",
                "paper_order_submitted",
                "position_opened",
                "position_closed",
                "postmortem_due",
            }
        ),
        "comment_count": len(comments),
        "acknowledgement_count": len(acknowledgements),
        "items": item_payloads,
        "recent_items": item_payloads[:12],
        "allowed_read_commands": list(READ_ONLY_COMMANDS),
        "read_command_count": len(READ_ONLY_COMMANDS),
        "telegram_notification_classes": sorted(TELEGRAM_NOTIFICATION_CLASSES),
        "telegram_notifications_allowed": True,
        "telegram_live_send_allowed": False,
        "telegram_command_authority": False,
        "comment_authority": "comment_and_request_review_only",
        "comment_can_approve_trades": False,
        "ack_can_approve_trades": False,
        "operator_action_authority": "read_acknowledge_comment_request_review_only",
        "signal_authority": False,
        "trade_candidate_creation_allowed": False,
        "risk_handoff_allowed": False,
        "risk_approval_allowed": False,
        "execution_allowed": False,
        "execution_approval_allowed": False,
        "paper_order_allowed": False,
        "broker_write_allowed": False,
        "qctrl_provider_call_allowed": False,
        "live_capital_enabled": False,
        "runtime_artifact": f"data/runtime/{OPERATOR_INBOX_RUNTIME_ARTIFACT}",
        "history_artifact": f"data/runtime/{OPERATOR_INBOX_HISTORY}",
        "acknowledgement_artifact": f"data/runtime/{OPERATOR_INBOX_ACKNOWLEDGEMENTS}",
        "comment_artifact": f"data/runtime/{OPERATOR_INBOX_COMMENTS}",
        "event_log_artifact": f"data/runtime/{OPERATOR_INBOX_EVENT_LOG}",
        "public_safe": True,
        "validation_errors": [],
        "validation_error_count": 0,
        "boundary": OPERATOR_INBOX_BOUNDARY,
    }
    errors = validate_operator_inbox(artifact)
    artifact["validation_errors"] = errors
    artifact["validation_error_count"] = len(errors)
    artifact["status"] = "ok" if not errors else "degraded"
    return artifact


def validate_operator_inbox(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if artifact.get("schema_version") != OPERATOR_INBOX_SCHEMA_VERSION:
        errors.append("schema_version_mismatch")
    if artifact.get("public_safe") is not True:
        errors.append("not_public_safe")
    for field in AUTHORITY_FIELDS:
        if artifact.get(field) is not False:
            errors.append(f"authority_enabled:{field}")
    if artifact.get("telegram_command_authority") is not False:
        errors.append("telegram_command_authority_enabled")
    if artifact.get("telegram_live_send_allowed") is not False:
        errors.append("telegram_live_send_allowed")
    if artifact.get("comment_can_approve_trades") is not False:
        errors.append("comment_can_approve_trades")
    if artifact.get("ack_can_approve_trades") is not False:
        errors.append("ack_can_approve_trades")
    commands = artifact.get("allowed_read_commands", [])
    if tuple(commands) != READ_ONLY_COMMANDS:
        errors.append("allowed_read_commands_mismatch")
    for command in commands:
        if command not in READ_ONLY_COMMANDS:
            errors.append(f"unexpected_read_command:{command}")
        if any(token in command for token in ("buy", "sell", "approve", "close", "resize")):
            errors.append(f"unsafe_command:{command}")
    items = artifact.get("items", [])
    if not isinstance(items, list):
        errors.append("items_not_list")
        items = []
    if _int(artifact.get("item_count")) != len(items):
        errors.append("item_count_mismatch")
    for item in items:
        if not isinstance(item, dict):
            errors.append("item_not_dict")
            continue
        if item.get("schema_version") != OPERATOR_INBOX_SCHEMA_VERSION:
            errors.append(f"item_schema_version_mismatch:{item.get('item_id', 'unknown')}")
        if item.get("item_class") not in ITEM_CLASSES:
            errors.append(f"item_class_invalid:{item.get('item_class')}")
        if item.get("severity") not in SEVERITIES:
            errors.append(f"item_severity_invalid:{item.get('item_id', 'unknown')}")
        if item.get("status") not in ITEM_STATUSES:
            errors.append(f"item_status_invalid:{item.get('item_id', 'unknown')}")
        allowed = set(item.get("allowed_actions") or [])
        if not allowed.issubset(ALLOWED_ACTIONS):
            errors.append(f"item_allowed_actions_invalid:{item.get('item_id', 'unknown')}")
        forbidden = set(item.get("forbidden_actions") or [])
        missing_forbidden = FORBIDDEN_ACTIONS - forbidden
        if missing_forbidden:
            errors.append(f"item_forbidden_actions_incomplete:{item.get('item_id', 'unknown')}")
        for field in AUTHORITY_FIELDS:
            if item.get(field) is not False:
                errors.append(f"item_authority_enabled:{item.get('item_id', 'unknown')}:{field}")
        if item.get("telegram_notification_class") is not None:
            if item.get("telegram_notification_class") not in TELEGRAM_NOTIFICATION_CLASSES:
                errors.append(f"item_telegram_class_invalid:{item.get('item_id', 'unknown')}")
        if "cannot create signals" not in str(item.get("boundary") or ""):
            errors.append(f"item_boundary_weak:{item.get('item_id', 'unknown')}")
    public_encoded = json.dumps(public_operator_inbox_status(artifact), sort_keys=True)
    for pattern in PROHIBITED_PUBLIC_PATTERNS:
        if pattern.search(public_encoded):
            errors.append("public_secret_or_identifier_leak")
            break
    if "cannot create signals" not in str(artifact.get("boundary") or ""):
        errors.append("boundary_missing_no_signal")
    if "cannot create signals" not in str(artifact.get("boundary") or ""):
        errors.append("boundary_weak")
    return sorted(set(errors))


def write_operator_inbox(
    payload: dict[str, Any],
    *,
    settings: Settings | None = None,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    store = OperatorInboxStore(settings=settings)
    artifact = build_operator_inbox(payload, settings=settings)
    _write_json(store.runtime_path, artifact)
    _append_jsonl(store.history_path, artifact)
    event_log = EventLog(path=store.event_log_path, echo=False)
    entry = event_log.write(
        OPERATOR_INBOX_EVENT_TYPE,
        OPERATOR_INBOX_COMPONENT,
        {
            "status": artifact["status"],
            "item_count": artifact["item_count"],
            "open_item_count": artifact["open_item_count"],
            "high_or_critical_item_count": artifact["high_or_critical_item_count"],
            "postmortem_due_item_count": artifact["postmortem_due_item_count"],
            "paper_trade_related_item_count": artifact["paper_trade_related_item_count"],
            "validation_error_count": artifact["validation_error_count"],
            "telegram_command_authority": False,
            "paper_order_allowed": False,
            "broker_write_allowed": False,
            "live_capital_enabled": False,
        },
    )
    artifact["event_log_written"] = True
    artifact["event_log_event_count"] = 1
    artifact["event_log_created_at"] = entry.created_at
    artifact["event_log_correlation_id"] = entry.correlation_id
    _write_json(store.runtime_path, artifact)
    return artifact


def operator_inbox_status(*, settings: Settings | None = None) -> dict[str, Any]:
    store = OperatorInboxStore(settings=settings)
    payload = store.read_artifact()
    if payload:
        return payload
    return {
        "schema_version": OPERATOR_INBOX_SCHEMA_VERSION,
        "status": "missing",
        "generated_at": _now(),
        "item_count": 0,
        "open_item_count": 0,
        "acknowledged_item_count": 0,
        "closed_item_count": 0,
        "expired_item_count": 0,
        "high_or_critical_item_count": 0,
        "telegram_related_item_count": 0,
        "postmortem_due_item_count": 0,
        "paper_trade_related_item_count": 0,
        "comment_count": 0,
        "acknowledgement_count": 0,
        "items": [],
        "recent_items": [],
        "allowed_read_commands": list(READ_ONLY_COMMANDS),
        "read_command_count": len(READ_ONLY_COMMANDS),
        "telegram_notification_classes": sorted(TELEGRAM_NOTIFICATION_CLASSES),
        "telegram_notifications_allowed": True,
        "telegram_live_send_allowed": False,
        "telegram_command_authority": False,
        "comment_authority": "comment_and_request_review_only",
        "comment_can_approve_trades": False,
        "ack_can_approve_trades": False,
        "operator_action_authority": "read_acknowledge_comment_request_review_only",
        "signal_authority": False,
        "trade_candidate_creation_allowed": False,
        "risk_handoff_allowed": False,
        "risk_approval_allowed": False,
        "execution_allowed": False,
        "execution_approval_allowed": False,
        "paper_order_allowed": False,
        "broker_write_allowed": False,
        "qctrl_provider_call_allowed": False,
        "live_capital_enabled": False,
        "public_safe": True,
        "validation_errors": ["operator_inbox_missing"],
        "validation_error_count": 1,
        "boundary": OPERATOR_INBOX_BOUNDARY,
    }


def public_operator_inbox_status(artifact: dict[str, Any] | None = None) -> dict[str, Any]:
    if artifact is None:
        artifact = operator_inbox_status()
    public = {field: artifact.get(field) for field in sorted(PUBLIC_STATUS_FIELDS)}
    public["recent_items"] = [
        {
            "item_id": str(item.get("item_id") or ""),
            "item_class": str(item.get("item_class") or ""),
            "severity": str(item.get("severity") or ""),
            "status": str(item.get("status") or ""),
            "owner": str(item.get("owner") or ""),
            "dashboard_section": str(item.get("dashboard_section") or ""),
            "summary": _clean_text(item.get("summary"), limit=260),
            "required_action": _clean_text(item.get("required_action"), limit=260),
            "allowed_actions": [
                action for action in list(item.get("allowed_actions") or []) if action in ALLOWED_ACTIONS
            ],
            "telegram_notification_allowed": item.get("telegram_notification_allowed") is True,
            "telegram_notification_class": item.get("telegram_notification_class"),
            "comment_count": _int(item.get("comment_count")),
            "acknowledged": item.get("status") == "acknowledged",
            "created_at": item.get("created_at"),
            "expires_at": item.get("expires_at"),
        }
        for item in list(artifact.get("recent_items") or [])[:12]
        if isinstance(item, dict)
    ]
    return public


def operator_inbox_public_status(*, settings: Settings | None = None) -> dict[str, Any]:
    return public_operator_inbox_status(operator_inbox_status(settings=settings))
