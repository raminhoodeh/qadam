"""Private world-model claim cards for the How The World Works corpus."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


CORPUS_DIR = Path("how-the-world-works")


@dataclass(frozen=True)
class WorldModelClaim:
    key: str
    source_path: str
    claim: str
    claim_type: str
    actors: tuple[str, ...]
    mechanism: str
    observable_signatures: tuple[str, ...]
    live_sources_to_check: tuple[str, ...]
    market_channels: tuple[str, ...]
    corroboration_status: str = "foundational_prior"
    postmortem_score: float | None = None
    evidence_boundary: str = "Private prior only; cannot affect signal confidence without live-source corroboration."

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


CLAIM_CARDS: tuple[WorldModelClaim, ...] = (
    WorldModelClaim(
        "narrative_coordination_as_market_force",
        "how-the-world-works/how-the-world-really-works-v1.md",
        "Belief systems and mass narratives can function as coordination technology, shaping attention, fear, risk appetite, and institutional permission.",
        "narrative_control",
        ("media", "institutions", "markets", "retail_public"),
        "Narratives compress complex power relationships into emotionally legible stories that can move behaviour before hard data arrives.",
        (
            "synchronized language shifts across news and social feeds",
            "market repricing before official data confirms the story",
            "gap between physical-world indicators and public narrative intensity",
        ),
        ("gdelt", "rss", "x", "reddit", "telegram"),
        ("prediction_markets", "defence", "semiconductors", "crude_oil"),
    ),
    WorldModelClaim(
        "institutional_self_preservation_blind_spot",
        "how-the-world-works/how-the-world-really-works-v2.md",
        "Institutions may frame self-preservation as public necessity, creating blind spots in official explanations during stress events.",
        "institutional_incentive",
        ("governments", "central_banks", "regulators", "large_media"),
        "Organizations protect legitimacy, funding, and continuity; official accounts can lag or soften inconvenient operational reality.",
        (
            "policy language shifts after market stress",
            "official statements contradicting flow or satellite evidence",
            "delayed acknowledgement of operational constraints",
        ),
        ("fred", "ecb", "bis", "sec_edgar", "gdelt", "nasa_firms"),
        ("rates", "equities", "prediction_markets", "crude_oil"),
    ),
    WorldModelClaim(
        "hierarchical_power_flows_through_energy_security_and_money",
        "how-the-world-works/how-the-world-really-works-v3.md",
        "The visible political order sits on deeper flows of energy access, security guarantees, dollar liquidity, shipping routes, and institutional control.",
        "power_hierarchy",
        ("united_states", "china", "gulf_states", "brics", "banks", "military_alliances"),
        "Financial, military, and energy systems reinforce one another; stress in one layer can reveal who depends on whom.",
        (
            "reserve-flow changes",
            "shipping or chokepoint disruption",
            "defence posture changes",
            "commodity stockpile behaviour",
        ),
        ("fred", "bis", "un_comtrade", "ais_maritime", "nasa_firms", "conflict_tracker"),
        ("crude_oil", "silver", "defence", "semiconductors", "fx"),
    ),
    WorldModelClaim(
        "us_china_grand_bargain_scenario",
        "how-the-world-works/how-the-world-works-v4.md",
        "A US-China bargain could trade financial-market access, Treasury/stablecoin demand, chip constraints, energy access, Taiwan posture, and Iran pressure into one macro settlement.",
        "geopolitical_scenario",
        ("united_states", "china", "taiwan", "iran", "gulf_states", "chipmakers", "stablecoin_issuers"),
        "Great-power bargaining can bundle apparently separate files when each side needs monetary, energy, technology, and security concessions.",
        (
            "stablecoin or Treasury-demand policy changes",
            "semiconductor export-control adjustments",
            "Taiwan military posture changes",
            "Iran or Gulf-energy diplomatic shifts",
            "China market-opening signals",
        ),
        ("sec_edgar", "fred", "un_comtrade", "gdelt", "conflict_tracker", "space_track_celestrak"),
        ("semiconductors", "defence", "crude_oil", "prediction_markets", "rates"),
    ),
    WorldModelClaim(
        "shadow_networks_as_coordination_risk",
        "how-the-world-works/how-the-world-really-works-v2.md",
        "Informal elite networks, private incentives, and ritualized trust systems can coordinate outcomes before formal institutions disclose them.",
        "hidden_coordination",
        ("political_elites", "financial_elites", "security_networks", "private_capital"),
        "Small trusted networks can create early alignment, while public institutions later formalize or rationalize the decision path.",
        (
            "unusual cross-sector timing",
            "policy leaks followed by market positioning",
            "repeated actor overlap across apparently separate events",
        ),
        ("sec_edgar", "stock_act", "unusual_whales", "gdelt", "patents", "github"),
        ("defence", "semiconductors", "prediction_markets", "equities"),
    ),
)


def corpus_files(root: Path | None = None) -> list[dict[str, Any]]:
    root = root or CORPUS_DIR
    files = sorted(root.glob("*.md"))
    return [
        {
            "path": str(path),
            "exists": path.exists(),
            "size_bytes": path.stat().st_size if path.exists() else 0,
        }
        for path in files
    ]


def world_model_claims() -> list[dict[str, Any]]:
    return [claim.to_dict() for claim in CLAIM_CARDS]


def world_model_claim_detail(key: str) -> dict[str, Any]:
    for claim in CLAIM_CARDS:
        if claim.key == key:
            return claim.to_dict()
    raise KeyError(f"unknown world-model claim: {key}")


def world_model_summary() -> dict[str, Any]:
    claims = world_model_claims()
    files = corpus_files()
    uncorroborated = [
        claim["key"] for claim in claims if claim["corroboration_status"] == "foundational_prior"
    ]
    return {
        "status": "ok",
        "corpus_dir": str(CORPUS_DIR),
        "corpus_file_count": len(files),
        "claim_count": len(claims),
        "foundational_prior_count": len(uncorroborated),
        "uncorroborated_claims": uncorroborated,
        "evidence_boundary": "World-model claims are private priors, not factual evidence or trade triggers.",
        "files": files,
    }
