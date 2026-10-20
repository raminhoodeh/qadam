"""Prioritised position care inside the one canonical PaperOps owner."""

from datetime import datetime, timezone
from hashlib import sha256
import json


def handoff_digest(rows):
    identities = []
    for wrapper in rows:
        if not isinstance(wrapper, dict):
            continue
        row = wrapper.get("source_handoff") or wrapper
        identities.append({key: row.get(key) for key in (
            "handoff_id", "paperops_handoff_id", "evidence_digest", "proposed_quantity",
            "proposed_notional_usd", "expires_at", "active_paper_epoch_id")})
    identities.sort(key=lambda row: json.dumps(row, sort_keys=True))
    return sha256(json.dumps(identities, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def full_review_due(summary, digest, *, now=None):
    now = now or datetime.now(timezone.utc)
    try:
        last = datetime.fromisoformat(str(summary.get("generated_at")).replace("Z", "+00:00"))
        age = (now - last).total_seconds()
    except (TypeError, ValueError):
        return True
    return bool(age < 0 or age >= 1200 or summary.get("scheduled_handoff_digest") != digest
                or summary.get("status") not in {"ready_idle", "ready_actionable", "ready", "operational"})


def protect_positions(settings):
    from orchestrator.qadam_canonical_exit_engine import build_canonical_exit_engine, validate_canonical_exit_engine
    artifact = build_canonical_exit_engine(settings, execute_due_exits=True)
    errors = validate_canonical_exit_engine(artifact)
    return artifact, errors
