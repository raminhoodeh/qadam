"""Account for every source's discovery path without claiming an observed edge."""

from collections import Counter


def build_discovery_coverage(sources, instruments, eligibility, scores, collection):
    collected = {row["source_key"]: row for row in collection.get("sources", [])}
    rows = []
    gaps = []
    for source in sorted(sources, key=lambda row: row["source_key"]):
        key = source["source_key"]
        receipt = collected.get(key, {})
        relationships = [row for row in eligibility if row.get("source_key") == key]
        mapped = sorted({row["instrument"] for row in relationships
                         if row.get("mapping_class") in {
                             "causal_strategy_mapping", "broad_discovery_mapping"}})
        inputs = [item for score in scores if not score.get("negative_control")
                  for item in score.get("feature_inputs", []) if item.get("source_key") == key]
        count = int(receipt.get("observation_count") or 0)
        evidence_state = receipt.get("collection_evidence_state", "unverified")
        collection_state = receipt.get("collection_status", "receipt_missing")
        if collection_state == "derived_alias":
            state = "derived_alias_not_independent_evidence"
        elif evidence_state == "operational_only":
            state = "operational_connection_not_research_feed"
        elif collection_state != "collected":
            state = "waiting_for_collection"
        elif not count:
            state = "waiting_for_qualifying_observations"
        elif not mapped or not inputs:
            state = "collected_but_not_reaching_discovery"
            gaps.append(key)
        elif any(row.get("fresh") is True for row in inputs):
            state = "fresh_input_in_pattern_research"
        else:
            state = "mapped_context_not_fresh_event_evidence"
        rows.append({
            "source_key": key, "discovery_state": state,
            "collection_status": collection_state,
            "collection_evidence_state": evidence_state,
            "observation_count": count,
            "mapped_instruments": mapped,
            "scored_input_count": len(inputs),
            "fresh_scored_input_count": sum(row.get("fresh") is True for row in inputs),
            "mapping_class_counts": dict(Counter(row.get("mapping_class") for row in relationships)),
            "upstream_sources": receipt.get("upstream_sources", []),
            "next_action": "repair_source_to_pattern_mapping" if key in gaps
                           else receipt.get("next_action", "verify_collection_receipt"),
        })
    return {
        "catalogue_source_count": len(rows), "instrument_count": len(instruments),
        "expected_pair_count": len(rows) * len(instruments),
        "evaluated_pair_count": len({(row.get("source_key"), row.get("instrument"))
                                     for row in eligibility}),
        "collection_generated_at": collection.get("generated_at"),
        "source_state_counts": dict(Counter(row["discovery_state"] for row in rows)),
        "unmapped_collected_source_keys": gaps,
        "sources": rows,
        "coverage_is_not_pattern_validation": True,
        "catalogue_membership_is_not_provider_evidence": True,
        "pattern_research_grants_order_authority": False,
    }
