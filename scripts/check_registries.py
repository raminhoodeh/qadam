#!/usr/bin/env python3
"""Validate Qadam's non-live registries and governance comment store."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings
from orchestrator.governance import GovernanceStore
from orchestrator.resource_registry import resource_registry_summary
from orchestrator.world_model import world_model_summary


def main() -> int:
    settings = Settings.from_env()
    resources = resource_registry_summary()
    world_model = world_model_summary()
    governance = GovernanceStore(ROOT / settings.runtime_dir / "foundation_check_governance_comments.jsonl", settings)
    comment = governance.add_comment(
        author_email=settings.fund_manager_allowlist[0],
        author_name="Foundation Check",
        target_type="system",
        target_key="phase_0_registry_check",
        body="Registry and governance comment store verified.",
        tags=("foundation", "check"),
    )
    governance_health = governance.health()

    print(f"resource_registry_status={resources['status']}")
    print(f"resource_count={resources['resource_count']}")
    print(f"resource_categories={resources['categories']}")
    print(f"resource_production_active_count={resources['production_active_count']}")
    print(f"world_model_status={world_model['status']}")
    print(f"world_model_corpus_file_count={world_model['corpus_file_count']}")
    print(f"world_model_claim_count={world_model['claim_count']}")
    print(f"world_model_foundational_prior_count={world_model['foundational_prior_count']}")
    print(f"governance_status={governance_health['status']}")
    print(f"governance_comment_id={comment.comment_id}")
    print(f"governance_comment_count={governance_health['comment_count']}")

    if resources["production_active_count"] != 0:
        print("resource_registry_has_unvalidated_active_resources=true")
        return 1
    if world_model["corpus_file_count"] != 4:
        print("world_model_corpus_file_count_mismatch=true")
        return 1
    if world_model["claim_count"] < 4:
        print("world_model_claim_count_too_low=true")
        return 1
    if world_model["claim_count"] != world_model["foundational_prior_count"]:
        print("world_model_claims_must_start_as_foundational_prior=true")
        return 1
    if governance_health["status"] != "ok":
        print("governance_store_not_ok=true")
        return 1

    print("registry_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
