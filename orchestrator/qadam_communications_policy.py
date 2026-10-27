"""User-owned outbound preferences, independent of trading and repair authority."""

import json
import os

from orchestrator.paths import project_root

POLICY_PATH = project_root() / "config" / "qadam_communications.json"
ALLOWED = {"paper_fill", "pattern"}


def communications_profile():
    override = os.getenv("QADAM_COMMUNICATION_PROFILE")
    if override in {"all", "trades_and_patterns"}:
        return override
    try:
        policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        if policy.get("schema_version") == "qadam_communications.v1" and policy.get("profile") == "all":
            return "all"
    except (OSError, ValueError, AttributeError):
        pass
    return "trades_and_patterns"


def proactive_allowed(category):
    return communications_profile() == "all" or category in ALLOWED


def interesting_pattern_change(before, after):
    """Workflow progress and changing health/freshness are not market discoveries."""
    keys = ("question", "direction", "symbols", "validated", "net_expectancy", "holdout")
    return any((before or {}).get(key) != after.get(key) for key in keys)
