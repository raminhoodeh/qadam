"""Local governance comments for founding Fund Managers."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from orchestrator.config import Settings
from orchestrator.event_log import EventLog

GOVERNANCE_SCHEMA_VERSION = 1
VALID_TARGET_TYPES = {
    "module",
    "signal",
    "trade_candidate",
    "strategy",
    "postmortem",
    "source",
    "resource",
    "world_model",
    "system",
}
VALID_COMMENT_STATUSES = {"suggestion", "accepted", "rejected", "implemented", "open"}
EVENT_LOG_EXPORT_STATUSES = {"accepted", "implemented"}


@dataclass(frozen=True)
class GovernanceComment:
    schema_version: int
    comment_id: str
    author_email: str
    author_name: str
    target_type: str
    target_key: str
    body: str
    tags: tuple[str, ...]
    status: str
    visibility: str
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["tags"] = list(self.tags)
        return payload


class GovernanceStore:
    def __init__(self, path: str | Path | None = None, settings: Settings | None = None) -> None:
        self.settings = settings or Settings.from_env()
        self.path = Path(path or Path(self.settings.runtime_dir) / "governance_comments.jsonl")
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def add_comment(
        self,
        *,
        author_email: str,
        author_name: str,
        target_type: str,
        target_key: str,
        body: str,
        tags: tuple[str, ...] = (),
        status: str = "suggestion",
        log_event: bool = True,
    ) -> GovernanceComment:
        normalized_email = author_email.strip().lower()
        if normalized_email not in self.settings.fund_manager_allowlist:
            raise ValueError("author is not in the founding Fund Manager allowlist")
        if target_type not in VALID_TARGET_TYPES:
            raise ValueError(f"invalid governance target type: {target_type}")
        if status not in VALID_COMMENT_STATUSES:
            raise ValueError(f"invalid governance status: {status}")
        if not body.strip():
            raise ValueError("governance comment body is required")

        comment = GovernanceComment(
            schema_version=GOVERNANCE_SCHEMA_VERSION,
            comment_id=str(uuid4()),
            author_email=normalized_email,
            author_name=author_name.strip() or normalized_email,
            target_type=target_type,
            target_key=target_key.strip() or "general",
            body=body.strip(),
            tags=tuple(tag.strip() for tag in tags if tag.strip()),
            status=status,
            visibility="founding_fund_managers",
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(comment.to_dict(), sort_keys=True) + "\n")
        if log_event and status in EVENT_LOG_EXPORT_STATUSES:
            EventLog(echo=False).write(
                event_type="governance_comment_approved",
                component="governance_forum",
                payload={
                    "comment_id": comment.comment_id,
                    "target_type": comment.target_type,
                    "target_key": comment.target_key,
                    "status": comment.status,
                    "tags": list(comment.tags),
                    "visibility": comment.visibility,
                    "boundary": "Approved governance comment exported to local Event Log without broker authority.",
                },
            )
        return comment

    def read_comments(self, limit: int | None = None) -> tuple[GovernanceComment, ...]:
        if not self.path.exists():
            return ()

        comments: list[GovernanceComment] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    payload = json.loads(stripped)
                    payload["tags"] = tuple(payload.get("tags", ()))
                    comments.append(GovernanceComment(**payload))
                except (TypeError, json.JSONDecodeError) as exc:
                    raise ValueError(f"invalid governance line {line_number} in {self.path}") from exc
        if limit is not None:
            comments = comments[-limit:]
        return tuple(comments)

    def health(self) -> dict[str, Any]:
        try:
            comments = self.read_comments()
        except Exception as exc:  # noqa: BLE001 - health should report the failure
            return {
                "status": "degraded",
                "path": str(self.path),
                "error": str(exc),
            }
        return {
            "status": "ok",
            "path": str(self.path),
            "schema_version": GOVERNANCE_SCHEMA_VERSION,
            "comment_count": len(comments),
            "suggestion_count": sum(1 for comment in comments if comment.status in {"suggestion", "open"}),
            "accepted_count": sum(1 for comment in comments if comment.status == "accepted"),
            "rejected_count": sum(1 for comment in comments if comment.status == "rejected"),
            "implemented_count": sum(1 for comment in comments if comment.status == "implemented"),
            "event_log_export_count": sum(1 for comment in comments if comment.status in EVENT_LOG_EXPORT_STATUSES),
            "allowed_target_types": sorted(VALID_TARGET_TYPES),
            "allowed_statuses": sorted(status for status in VALID_COMMENT_STATUSES if status != "open"),
            "visibility": "founding_fund_managers",
        }


def ensure_d8_sample_governance_comment(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    store = GovernanceStore(settings=settings)
    existing = {
        (comment.target_type, comment.target_key, comment.body)
        for comment in store.read_comments()
    }
    sample_body = "D8 sample: verify the Fund Manager forum can link a suggestion to the trade layer."
    created = False
    if ("module", "trade_layer", sample_body) not in existing:
        store.add_comment(
            author_email=settings.fund_manager_allowlist[0],
            author_name="Founding Fund Manager",
            target_type="module",
            target_key="trade_layer",
            body=sample_body,
            tags=("d8", "forum", "trade_layer"),
            status="suggestion",
            log_event=False,
        )
        created = True
    return {
        "status": "ok",
        "created": created,
        "health": store.health(),
    }
