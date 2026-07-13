"""Shared public contract for Qadam's governed learning loop."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


QADAM_OPERATING_FLOW: list[dict[str, str]] = [
    {"id": "observe", "label": "Observe", "description": "Watch sources and markets."},
    {"id": "patterns", "label": "Find patterns", "description": "Look for source-price relationships."},
    {"id": "decide", "label": "Test and decide", "description": "Challenge evidence, filters, and risk."},
    {"id": "trade_event", "label": "Trade or research event", "description": "Record what Qadam did or deliberately did not do."},
    {"id": "learn", "label": "Learn and improve", "description": "Turn outcomes into governed lessons and tests."},
    {"id": "observe_again", "label": "Observe again", "description": "Use only approved versions in the next cycle."},
]

LEARNING_LOOP_STEPS: list[dict[str, Any]] = [
    {
        "number": 1,
        "id": "outcome_or_research_event",
        "label": "Outcome or research event",
        "description": "A paper result, rejected idea, held setup, missed opportunity, or operating event is recorded.",
        "page": "results",
    },
    {
        "number": 2,
        "id": "supported_lesson",
        "label": "Supported lesson",
        "description": "Qadam records only what the evidence supports and keeps reference-only history separate.",
        "page": "results",
    },
    {
        "number": 3,
        "id": "proposed_improvement",
        "label": "Proposed improvement",
        "description": "A specific, measurable change is proposed. Nothing changes yet.",
        "page": "improvements",
    },
    {
        "number": 4,
        "id": "historical_test",
        "label": "Historical test",
        "description": "The proposal is tested on point-in-time historical evidence.",
        "page": "improvements",
    },
    {
        "number": 5,
        "id": "forward_observation",
        "label": "Forward observation",
        "description": "Qadam watches the proposal in real time without placing an order.",
        "page": "improvements",
    },
    {
        "number": 6,
        "id": "review",
        "label": "Review",
        "description": "Evidence, risk, failure conditions, and alternatives are reviewed.",
        "page": "improvements",
    },
    {
        "number": 7,
        "id": "applied_version",
        "label": "Applied version",
        "description": "Only an approved, versioned change can become active.",
        "page": "improvements",
    },
    {
        "number": 8,
        "id": "next_observe_cycle",
        "label": "Next Observe cycle",
        "description": "The approved change returns to Observe with monitoring and a rollback rule.",
        "page": "improvements",
    },
]

PAGE_STAGE_IDS = {
    "results": ["outcome_or_research_event", "supported_lesson"],
    "improvements": [
        "proposed_improvement",
        "historical_test",
        "forward_observation",
        "review",
        "applied_version",
        "next_observe_cycle",
    ],
}


def build_learning_loop_overview(page: str) -> dict[str, Any]:
    if page not in PAGE_STAGE_IDS:
        raise ValueError(f"Unknown learning-loop page: {page}")
    page_stage_ids = PAGE_STAGE_IDS[page]
    return {
        "contract_version": "qadam_learning_loop.v1",
        "title": "How evidence changes Qadam's next cycle",
        "context": (
            "Learn and Improve closes Qadam's operating loop. A result or research event can influence the next "
            "Observe cycle only after it becomes a supported lesson, survives testing, and is approved as a versioned change."
        ),
        "operating_flow": deepcopy(QADAM_OPERATING_FLOW),
        "current_operating_stage": "learn",
        "steps": deepcopy(LEARNING_LOOP_STEPS),
        "page": page,
        "page_stage_ids": list(page_stage_ids),
        "page_scope": (
            "This page covers stages 1-2: what happened and what the evidence supports."
            if page == "results"
            else "This page covers stages 3-8: how a supported lesson is tested, reviewed, and returned to Observe."
        ),
        "next_page": (
            {"module_id": "learn", "view_id": "improvements", "label": "Continue to proposed improvements"}
            if page == "results"
            else {"module_id": "observe", "view_id": "sources", "label": "Return to the next Observe cycle"}
        ),
    }


def validate_learning_loop_overview(overview: Any, *, expected_page: str) -> list[str]:
    if not isinstance(overview, dict):
        return ["learning_loop_overview_missing"]
    errors: list[str] = []
    steps = overview.get("steps") if isinstance(overview.get("steps"), list) else []
    expected_ids = [step["id"] for step in LEARNING_LOOP_STEPS]
    expected_labels = [step["label"] for step in LEARNING_LOOP_STEPS]
    if [step.get("id") for step in steps] != expected_ids:
        errors.append("learning_loop_step_order_invalid")
    if [step.get("label") for step in steps] != expected_labels:
        errors.append("learning_loop_step_labels_invalid")
    if overview.get("page") != expected_page:
        errors.append("learning_loop_page_invalid")
    if overview.get("page_stage_ids") != PAGE_STAGE_IDS.get(expected_page):
        errors.append("learning_loop_page_scope_invalid")
    if overview.get("current_operating_stage") != "learn":
        errors.append("learning_loop_operating_context_invalid")
    if len(overview.get("operating_flow") or []) != len(QADAM_OPERATING_FLOW):
        errors.append("learning_loop_operating_flow_invalid")
    return errors
