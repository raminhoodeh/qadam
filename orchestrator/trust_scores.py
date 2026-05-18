"""Phase 1 Trust Score seed contract."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from orchestrator.config import Settings
from orchestrator.phase1_live_adapters import PHASE1_LIVE_ADAPTERS, phase1_live_adapter_status
from orchestrator.source_health import build_data_environment_map
from world_monitor.source_registry import SOURCE_SPECS


@dataclass(frozen=True)
class TrustScoreSeed:
    source_key: str
    pipeline: str
    tier: int
    score: float
    basis: str
    evidence_status: str
    latency_threshold_passed: bool
    boundary: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _base_score(tier: int) -> float:
    return {1: 0.72, 2: 0.62, 3: 0.54, 4: 0.46}.get(tier, 0.4)


def build_trust_score_seed(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    data_map = build_data_environment_map(settings)
    heartbeat_by_key = {source["source_key"]: source for source in data_map["sources"]}
    seeds: list[TrustScoreSeed] = []
    for source in SOURCE_SPECS:
        heartbeat = heartbeat_by_key.get(source.key, {})
        if source.key in PHASE1_LIVE_ADAPTERS:
            status = phase1_live_adapter_status(source.key, settings)
            score = float(status["trust_score"])
            basis = "promoted_adapter_seed"
        elif source.status == "derived":
            score = 0.5
            basis = "derived_source_placeholder"
        else:
            score = _base_score(source.tier)
            basis = "tier_prior_pending_real_backtest"
        evidence_status = "live_or_sample_observed" if heartbeat.get("promoted_adapter") else "pending_real_data"
        latency_threshold = source.pipeline in {"physical", "market"} and score >= 0.7 and heartbeat.get("runtime_status") in {
            "live_optional",
            "unavailable_missing_credentials",
        }
        seeds.append(
            TrustScoreSeed(
                source_key=source.key,
                pipeline=source.pipeline,
                tier=source.tier,
                score=round(score, 2),
                basis=basis,
                evidence_status=evidence_status,
                latency_threshold_passed=latency_threshold,
                boundary="Trust Score seed is a routing prior until real backtest/live observations replace it.",
            )
        )
    above_half = [seed for seed in seeds if seed.score > 0.5]
    physical_latency = [seed for seed in seeds if seed.pipeline == "physical" and seed.latency_threshold_passed]
    return {
        "status": "ok",
        "seed_count": len(seeds),
        "above_half_count": len(above_half),
        "above_half_threshold_met": len(above_half) >= 20,
        "physical_logistics_latency_pass_count": len(physical_latency),
        "physical_logistics_latency_threshold_met": len(physical_latency) >= 2,
        "real_data_seed_complete": False,
        "seeds": [seed.to_dict() for seed in seeds],
        "boundary": "Current scores are seed priors. The real-data Trust Score benchmark remains incomplete until backtests/live observations are connected.",
    }
