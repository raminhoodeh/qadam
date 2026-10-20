"""Cited economic changes, not financial sentiment or estimates of trading profit.

The deliberately small vocabulary is a versioned, testable research policy.
Unknown attribution, conditional language and conflicting changes stay unresolved.
"""

from hashlib import sha256
import json
import math
import re

VERSION = "economic-changes.1"
FAMILY_IDS = {
    "semiconductor_policy_options_asymmetry": "semiconductors",
    "semiconductor_policy_asymmetry": "semiconductors",
    "crude_oil_energy_security_disruption": "energy_supply",
    "energy_supply_disruption": "energy_supply",
}
ISSUERS = {
    "NVDA": r"\b(?:NVDA|NVIDIA)\b",
    "TSM": r"\b(?:TSM|TSMC|Taiwan Semiconductor)\b",
    "MU": r"\b(?:MU|Micron)\b",
    "SNDK": r"\b(?:SNDK|SanDisk)\b",
}
SECTOR_PROXIES = {"SMH", "SOXX", "QQQ", "XLE"}
METRICS = {
    "guidance": r"\b(?:guidance|outlook|forecast)\b",
    "revenue": r"\b(?:revenue|sales)\b",
    "orders": r"\b(?:demand|orders|bookings)\b",
    "margin": r"\b(?:margin|margins)\b",
    "backlog": r"\b(?:backlog|order book)\b",
    "capacity": r"\b(?:capacity|fabrication plant|fab capacity)\b",
    "capex": r"\b(?:capex|capital expenditure|investment)\b",
    "inventory": r"\b(?:inventory|inventories|stockpile)\b",
    "physical_supply": r"\b(?:production|output|supply|shipments|exports|pipeline|refinery|refineries|port)\b",
}
UP = r"\b(?:rais\w*|increas\w*|grew|grow\w*|expand\w*|higher|surge\w*|improv\w*|recover\w*|resum\w*|reopen\w*|restor\w*)\b"
DOWN = r"\b(?:cut|cuts|lower\w*|decreas\w*|declin\w*|fell|fall\w*|reduc\w*|halt\w*|disrupt\w*|shutdown|shut down|clos\w*|suspend\w*)\b"
CONDITIONAL = r"\b(?:may|might|could|would|if|possible|potential|risk of|expected to|plans? to|consider\w*|reportedly|unconfirmed)\b"
NEGATION = r"\b(?:not|never|no|deny|denies|denied|without|unchanged|no longer)\b"
NUMBER = r"\$?\s*(\d+(?:,\d{3})*(?:\.\d+)?)\s*(billion|million|thousand|%|percent|bps|barrels(?: per day)?|bpd|days|weeks)?"


def _identity(value):
    return sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()[:32]


def sentences(text):
    """Retain exact citation offsets; do not split decimal points."""
    start = 0
    for boundary in re.finditer(r"\n+|;\s*|(?<=[.!?])\s+(?=[A-Z])|\s+(?:but|however|while)\s+", text):
        raw = text[start:boundary.start()]
        if raw.strip():
            offset = start + len(raw) - len(raw.lstrip())
            yield offset, offset + len(raw.strip()), raw.strip()
        start = boundary.end()
    raw = text[start:]
    if raw.strip():
        offset = start + len(raw) - len(raw.lstrip())
        yield offset, offset + len(raw.strip()), raw.strip()


def _comparison(text):
    match = re.search(r"\bfrom\s*" + NUMBER + r"\s+to\s*" + NUMBER, text, re.I)
    if not match:
        return {"basis": "no_comparable_prior_value", "delta": None}
    before, unit_before, after, unit_after = match.groups()
    unit_before, unit_after = (unit_before or unit_after or "unspecified").lower(), (unit_after or unit_before or "unspecified").lower()
    if unit_before != unit_after or unit_before == "unspecified":
        return {"basis": "incompatible_or_unspecified_units", "delta": None}
    prior, current = float(before.replace(",", "")), float(after.replace(",", ""))
    if not all(math.isfinite(value) for value in (prior, current)):
        return {"basis": "non_finite_measurement", "delta": None}
    return {"basis": "same_statement_reported_prior_not_consensus", "prior_value": prior,
            "current_value": current, "unit": unit_before, "delta": current - prior,
            "relative_change": (current / prior - 1) if prior else None,
            "supporting_text": match.group(0), "consensus_surprise": None}


def extract_changes(text, *, family, issuer_symbols=()):
    """Extract atomic changes. A measured increase is not automatically bullish."""
    if family not in {"semiconductors", "energy_supply"}:
        return []
    changes = []
    for start, end, sentence in sentences(text[:24000]):
        metrics = [name for name, pattern in METRICS.items() if re.search(pattern, sentence, re.I)]
        if not metrics:
            continue
        explicit = sorted(symbol for symbol, pattern in ISSUERS.items() if re.search(pattern, sentence, re.I))
        issuers = explicit or sorted(set(issuer_symbols).intersection(ISSUERS))
        up, down = list(re.finditer(UP, sentence, re.I)), list(re.finditer(DOWN, sentence, re.I))
        # Negated directional language must not fall through to a keyword buy.
        negated = bool(re.search(r"\b(?:unchanged|no change|no longer)\b", sentence, re.I)) or any(
            re.search(NEGATION, sentence[max(0, match.start() - 35):match.start()], re.I)
            for match in up + down
        )
        conditional = bool(re.search(CONDITIONAL, sentence, re.I))
        comparison = _comparison(sentence)
        direction = "increase" if up and not down else "decrease" if down and not up else "unresolved"
        if comparison.get("delta") is not None and not (up and down):
            delta = comparison["delta"]
            direction = "increase" if delta > 0 else "decrease" if delta < 0 else "unchanged"
        if negated:
            direction = "negated_or_unchanged"
        impact = "unresolved"
        shock = "economic_change_unresolved"
        metric = metrics[0]
        if family == "semiconductors":
            if metric in {"guidance", "revenue", "orders", "margin"}:
                impact = {"increase": "positive", "decrease": "negative"}.get(direction, "unresolved")
                shock = "issuer_cash_flow_change"
            elif metric == "physical_supply":
                impact = {"increase": "positive", "decrease": "negative"}.get(direction, "unresolved")
                shock = "issuer_delivery_capacity_change"
            else:
                shock = "capacity_cost_or_inventory_requires_interpretation"
            if metric == "guidance" and re.search(r"\b(?:cost|expense|loss)\w*\b", sentence, re.I):
                impact = "unresolved"
                shock = "guidance_measure_requires_interpretation"
        else:
            if "physical_supply" in metrics and "orders" not in metrics:
                metric, shock = "physical_supply", "reported_physical_supply_change"
                impact = {"increase": "negative", "decrease": "positive"}.get(direction, "unresolved")
                if (not re.search(r"\b(?:oil|crude|opec|barrels|bpd)\b", sentence, re.I)
                        or re.search(r"\brefiner\w*\b", sentence, re.I)):
                    impact, shock = "unresolved", "commodity_or_refining_basis_requires_interpretation"
            elif "orders" in metrics:
                metric, shock = "orders", "reported_demand_change"
                impact = {"increase": "positive", "decrease": "negative"}.get(direction, "unresolved")
        if conditional or negated or (family == "semiconductors" and len(issuers) > 1):
            impact = "unresolved"
        changes.append({"feature_id": "economic-change:" + _identity([VERSION, family, issuers, sentence.lower()]),
            "policy_version": VERSION, "family": family, "metric": metric,
            "issuer_symbols": issuers, "issuer_attribution": "explicit_named_issuer" if explicit else
                "filing_issuer" if issuers else "sector_not_issuer_specific",
            "reported_change": direction, "economic_impact": impact, "shock_type": shock,
            "conditional": conditional, "negated": negated, "comparison": comparison,
            "supporting_span": {"start": start, "end": end, "text": sentence},
            "expected_return": None, "incremental_value_measured": False,
            "extraction_probability": None, "paper_order_allowed": False})
    return changes[:24]


def classify_event(strategy_id, text, *, issuer_symbols=()):
    family = FAMILY_IDS.get(strategy_id)
    features = extract_changes(text, family=family, issuer_symbols=issuer_symbols)
    if not features:
        return None
    # An unresolved material clause must not be outvoted by other keyword counts.
    impacts = {row["economic_impact"] for row in features}
    resolved = len(impacts) == 1 and "unresolved" not in impacts
    impact = next(iter(impacts)) if resolved else "unresolved"
    clue = {"positive": "positive_for_strategy_expression", "negative": "negative_for_strategy_expression"}.get(impact, "ambiguous")
    return {"classifier": VERSION, "event": text, "mechanism": features[0]["shock_type"],
            "direction_clue": clue, "confidence": 0.65 if resolved else 0.0,
            "confidence_calibration": "unmeasured_policy_strength_not_probability",
            "matched_terms": sorted({row["metric"] for row in features}),
            "conflicting_mechanism_count": len(impacts) if len(impacts) > 1 else 0,
            "economic_changes": features,
            "catalyst_eligible": not all(row["negated"] or row["reported_change"] == "unchanged" for row in features),
            "invalidation": "The cited economic change reverses, is corrected, or current prices reject the entry thesis.",
            "not_a_probability": True, "not_execution_approval": True}


def instrument_interpretation(classification, symbol):
    """Do not transfer one issuer's cash-flow claim to its competitors or an ETF."""
    features = classification.get("economic_changes") or []
    issuers = sorted({issuer for row in features for issuer in row["issuer_symbols"]})
    unrelated = bool(issuers and symbol not in issuers and symbol not in SECTOR_PROXIES)
    proxy = symbol in SECTOR_PROXIES
    unattributed_issuer = not issuers and any(row.get("family") == "semiconductors" for row in features)
    return {"eligible_subject": not unrelated,
            "direction_clue": "ambiguous" if proxy or unrelated or unattributed_issuer else classification["direction_clue"],
            "economic_subjects": issuers, "market_confirmation_required": proxy or unattributed_issuer,
            "attribution_basis": "sector_proxy_not_direct_issuer_exposure" if proxy else
                "named_issuer_only" if issuers else "sector_not_issuer_specific" if unattributed_issuer else "commodity_mechanism_hypothesis",
            "economic_policy_version": VERSION}


def packet_changes(rows, *, family, instrument):
    result, seen = [], set()
    for row in rows:
        if row.get("evidence_role") not in {"reported_catalyst", "issuer_filing_content"}:
            continue
        for feature in extract_changes(row["summary"], family=family, issuer_symbols=row.get("issuer_symbols", [])):
            classification = {"economic_changes": [feature], "direction_clue":
                {"positive": "positive_for_strategy_expression", "negative": "negative_for_strategy_expression"}.get(feature["economic_impact"], "ambiguous")}
            interpretation = instrument_interpretation(classification, instrument)
            if not interpretation["eligible_subject"] or feature["feature_id"] in seen:
                continue
            seen.add(feature["feature_id"])
            result.append({**feature, "receipt_ref": row["receipt_id"], "source_key": row["source_key"],
                "available_at": row["available_at"], "provider_observed_at": row.get("provider_observed_at"),
                "instrument_interpretation": interpretation})
    return result[:24]
