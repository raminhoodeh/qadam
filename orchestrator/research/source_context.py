"""Bounded, point-in-time provider context joined to explicit economic channels.

These are testable mechanisms, not inferred profits or executable catalysts.
Decision records retain their packet, so pruning research cache cannot rewrite a trade.
"""

from collections import Counter
from datetime import datetime, timedelta
from hashlib import sha256
import json
import math
import re

from orchestrator.research.source_time import verified_timestamp
from orchestrator.storage.control_plane import ControlPlaneStore

ARTIFACT = "qadam_cross_source_context.json"
MAX_RECEIPTS = 12000
MAX_CURRENT_PER_SOURCE = 25
MAX_PACKET_ROWS = 12
MACRO_KEYS = {"fred", "bls", "bis", "ecb", "un_comtrade"}
MARKET_KEYS = {"yahoo_finance", "tradingview_mcp", "hyperliquid"}
FAMILIES = {
    "energy_supply": {
        "symbols": {"USO", "BNO", "XLE", "CL=F"},
        "terms": r"\b(oil|crude|opec|hormuz|refiner\w*|pipeline|red sea|suez|tanker\w*)\b",
        "mechanism": "Physical disruption -> supply/transport costs -> oil and energy proxies",
    },
    "semiconductors": {
        "symbols": {"NVDA", "SMH", "SOXX", "TSM", "MU", "SNDK"},
        "terms": r"\b(semiconductor\w*|nvidia|tsmc|micron|sandisk|chip\w*|export control\w*|data cent\w*)\b",
        "mechanism": "Demand/capacity or export policy -> issuer cash flows -> semiconductor proxies",
    },
    "defence": {
        "symbols": {"ITA", "XAR", "LMT", "RTX"},
        "terms": r"\b(defen[cs]e|military|missile\w*|lockheed|raytheon|conflict|war|ceasefire)\b",
        "mechanism": "Escalation/procurement or de-escalation -> defence demand and risk premium",
    },
    "macro_liquidity": {
        "symbols": {"SPY", "QQQ", "TLT", "DXY", "SLV", "SIL", "GLD", "XME"},
        "terms": r"\b(inflation|interest rate\w*|treasur\w*|federal reserve|yield\w*|liquidity|silver|gold|payroll\w*)\b",
        "mechanism": "Rates, dollar and liquidity -> discount rates and precious-metal opportunity costs",
    },
}
SYMBOL_TO_FAMILY = {symbol: family for family, config in FAMILIES.items() for symbol in config["symbols"]}
EXTERNAL_ISSUER_FAMILIES = {symbol: "semiconductors" for symbol in ("INTC", "AMD", "AVGO", "ASML", "AMAT", "LRCX")}
CIK_SYMBOLS = {"1045810": ["NVDA"], "1046179": ["TSM"], "936468": ["LMT"], "101829": ["RTX"], "320193": ["AAPL"]}


def _digest(value):
    return sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def _db(runtime):
    return ControlPlaneStore(runtime / "qadam-control-plane.sqlite3")


def _prepare(connection):
    connection.execute("CREATE TABLE IF NOT EXISTS source_context_receipts ("
        "receipt_id TEXT PRIMARY KEY, source_key TEXT NOT NULL, record_key TEXT NOT NULL, "
        "available_at TEXT NOT NULL, last_seen_at TEXT NOT NULL, payload_json TEXT NOT NULL)")
    connection.execute("CREATE INDEX IF NOT EXISTS source_context_record ON "
                       "source_context_receipts(source_key,record_key,last_seen_at)")
    connection.execute("CREATE TABLE IF NOT EXISTS source_context_snapshots ("
        "source_key TEXT PRIMARY KEY, captured_at TEXT NOT NULL, status TEXT NOT NULL, receipt_ids_json TEXT NOT NULL)")


def capture_context(runtime, captured, validations, *, now, selected_sources=None):
    inserted = 0
    with _db(runtime).transaction() as connection:
        _prepare(connection)
        for source_key in (selected_sources if selected_sources is not None else captured):
            result = captured.get(source_key, {})
            validation = validations.get(source_key)
            validation = validation if isinstance(validation, dict) else vars(validation) if validation is not None else {}
            if (validation.get("validation_status") != "live"
                    or validation.get("sample_fixture") is not False or result.get("degraded")
                    or not result.get("raw_archive_path") or source_key in {"alpaca", "telegram", "conflict_tracker"}):
                connection.execute("INSERT OR REPLACE INTO source_context_snapshots VALUES (?,?,?,?)",
                                   (source_key, now.isoformat(), "unavailable", "[]"))
                continue
            receipt_ids = []
            for event in result.get("events", [])[:50]:
                from orchestrator.research_goal import _contains_secret_like_value
                if not isinstance(event, dict) or _contains_secret_like_value(event):
                    continue
                raw = event.get("raw_payload") or {}
                if any(raw.get(flag) is True for flag in ("sample", "status_only", "derived", "summary_fallback_to_source_description")):
                    continue
                if raw.get("event_evidence_eligible") is False:
                    continue
                summary = str(event.get("normalised_summary") or "").strip()[:600]
                if not summary:
                    continue
                provider_time = None if raw.get("event_timestamp_fallback_to_fetch_time") else verified_timestamp(event.get("ingested_at"))
                if provider_time and datetime.fromisoformat(provider_time) > now + timedelta(minutes=5):
                    continue
                # Time-independent material identity stops unchanged downloads
                # becoming new research observations on every poll.
                material = {key: value for key, value in raw.items() if key not in {
                    "retrieved_at", "fetched_at", "ingested_at", "available_at", "endpoint",
                    "provider_response_sha256", "library_versions", "terms_note"}}
                record_key = str(raw.get("record_id") or raw.get("accession_number") or raw.get("original_url")
                                 or raw.get("url") or raw.get("symbol") or raw.get("series_id") or _digest(summary))[:300]
                receipt_id = "source-context:" + _digest([source_key, record_key, material, summary, provider_time])[:32]
                row = {"receipt_id": receipt_id, "source_key": source_key, "record_key": record_key,
                       "summary": summary, "provider_observed_at": provider_time,
                       "timestamp_role": raw.get("timestamp_role") or ("provider_observation" if provider_time else "forward_only_first_seen"),
                       "publication_timestamp_verified": raw.get("timestamp_role") == "provider_publication",
                       "raw": material}
                encoded = json.dumps(row, sort_keys=True)
                if len(encoded.encode()) > 8192:
                    continue
                cursor = connection.execute("INSERT OR IGNORE INTO source_context_receipts VALUES (?,?,?,?,?,?)",
                    (receipt_id, source_key, record_key, now.isoformat(), now.isoformat(), encoded))
                inserted += cursor.rowcount
                receipt_ids.append(receipt_id)
                connection.execute("UPDATE source_context_receipts SET last_seen_at=? WHERE receipt_id=?",
                                   (now.isoformat(), receipt_id))
            connection.execute("INSERT OR REPLACE INTO source_context_snapshots VALUES (?,?,?,?)",
                (source_key, now.isoformat(), "live", json.dumps(receipt_ids)))
        # Bounded research retention. Submitted decision packets keep their own
        # immutable copy; this cache never changes broker/position history.
        connection.execute("DELETE FROM source_context_receipts WHERE receipt_id IN ("
            "SELECT receipt_id FROM source_context_receipts ORDER BY last_seen_at DESC, receipt_id LIMIT -1 OFFSET ?)",
            (MAX_RECEIPTS,))
    return inserted


def _relevance(row):
    raw, source = row["raw"], row["source_key"]
    text = row["summary"].lower()
    issuer_symbols = {str(value).upper() for value in raw.get("issuer_symbols", [])}
    issuer_symbols.update(CIK_SYMBOLS.get(str(raw.get("cik", "")).lstrip("0"), []))
    if source in MARKET_KEYS:
        symbol = str(raw.get("qadam_symbol") or raw.get("symbol") or "").upper()
        if source == "hyperliquid":
            return {"macro_liquidity"}, set(), "crypto_leverage_context_not_equity_confirmation"
        return ({SYMBOL_TO_FAMILY[symbol]} if symbol in SYMBOL_TO_FAMILY else set()), {symbol}, "market_confirmation"
    if source in MACRO_KEYS:
        if source == "un_comtrade":
            code = str(raw.get("cmdCode") or "")
            family = {"2709": "energy_supply", "8542": "semiconductors", "93": "defence"}.get(code)
            return ({family} if family else set()), set(), "structural_context"
        return set(FAMILIES), set(), "macro_regime_context"
    if source == "sec_edgar":
        role = "issuer_filing_content" if raw.get("filing_content_verified") is True else "issuer_filing_metadata"
        return {SYMBOL_TO_FAMILY[symbol] for symbol in issuer_symbols if symbol in SYMBOL_TO_FAMILY}, issuer_symbols, role
    if source == "stock_act":
        symbol = str((raw.get("measurements") or {}).get("traded_issuer_ticker") or "").upper()
        return ({SYMBOL_TO_FAMILY[symbol]} if symbol in SYMBOL_TO_FAMILY else set()), {symbol}, "disclosure_context_not_transaction_time"
    if source == "reddit" and raw.get("source_variant") == "tradewithcongress_public_atom":
        families = {SYMBOL_TO_FAMILY.get(symbol) or EXTERNAL_ISSUER_FAMILIES.get(symbol)
                    for symbol in issuer_symbols}
        return families - {None}, issuer_symbols, "unverified_congressional_discussion_secondary"
    if source == "ais_maritime":
        # This subscription observes a corridor, not a global shipping index.
        lat, lon = raw.get("latitude"), raw.get("longitude")
        valid = isinstance(lat, (int, float)) and isinstance(lon, (int, float)) and 12 <= lat <= 31 and 31 <= lon <= 61
        return ({"energy_supply"} if valid else set()), set(), "corridor_position_not_disruption_proof"
    if source == "gps_jamming":
        lat, lon = raw.get("latitude"), raw.get("longitude")
        if isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
            if 12 <= lat <= 31 and 31 <= lon <= 61:
                return {"energy_supply"}, set(), "corridor_navigation_context_not_jamming_proof"
            if 20 <= lat <= 27 and 118 <= lon <= 124:
                return {"semiconductors"}, set(), "taiwan_navigation_context_not_supply_loss_proof"
        return set(), set(), "geospatial_context_outside_frozen_corridors"
    if source == "usgs":
        measurements = raw.get("measurements") or {}
        coords = measurements.get("coordinates") or []
        magnitude = measurements.get("magnitude")
        if len(coords) >= 2 and isinstance(magnitude, (int, float)) and magnitude >= 5.5:
            lon, lat = coords[:2]
            if 20 <= lat <= 27 and 118 <= lon <= 124:
                return {"semiconductors"}, set(), "taiwan_earthquake_not_confirmed_factory_damage"
            if 12 <= lat <= 31 and 31 <= lon <= 61:
                return {"energy_supply"}, set(), "corridor_earthquake_not_confirmed_supply_loss"
        return set(), set(), "geophysical_context_outside_frozen_exposure"
    if source == "arcgis_usace":
        measurements = raw.get("measurements") or {}
        lat, lon = measurements.get("latitudeNumeric"), measurements.get("longitudeNumeric")
        if isinstance(lat, (int, float)) and isinstance(lon, (int, float)) and 18 <= lat <= 32 and -100 <= lon <= -75:
            return {"energy_supply"}, set(), "gulf_cyclone_not_confirmed_production_loss"
        return set(), set(), "cyclone_outside_frozen_gulf_exposure"
    families = {family for family, config in FAMILIES.items() if re.search(config["terms"], text)}
    # Event-market updates and sports headlines unrelated to these economic
    # channels never become confirmation for an equity or commodity idea.
    return families, set(), "event_market_context" if source in {"polymarket", "kalshi"} else "reported_catalyst"


def _reference_current(row, now):
    period = str(row["raw"].get("reference_period") or "")
    if not period:
        return True
    text = period.replace("-M", "-")
    try:
        if re.fullmatch(r"\d{4}", text):
            reference = datetime(int(text), 12, 31, tzinfo=now.tzinfo)
        else:
            reference = datetime.fromisoformat(text[:10] + ("-01" if len(text) == 7 else "")).replace(tzinfo=now.tzinfo)
        limit = {"un_comtrade": 1100, "bls": 75, "bis": 100, "ecb": 7, "gps_jamming": 4}.get(row["source_key"], 7)
        return -1 <= (now - reference).days <= limit
    except (ValueError, TypeError):
        return False


def _factors(rows):
    factors = []
    for row in rows:
        raw = row["raw"]
        for key in ("value", "delta", "pct_change", "funding_rate", "open_interest", "last_close",
                    "percent_move", "volume_ratio", "rolling_volatility_20d",
                    "navigation_accuracy_degraded_pct", "speed_knots", "primaryValue"):
            value = raw.get(key)
            if type(value) in (int, float) and math.isfinite(value):
                factors.append({"source_key": row["source_key"], "series_or_record": raw.get("series_id") or row["record_key"],
                    "measurement": key, "value": value, "unit": raw.get("unit"),
                    "reference_period": raw.get("reference_period") or raw.get("date"),
                    "available_at": row["available_at"], "receipt_ref": row["receipt_id"],
                    "measured_incremental_predictive_value": None})
    yields = {item["series_or_record"]: item for item in factors
              if item["source_key"] == "fred" and item["measurement"] == "value"}
    ten, two = yields.get("DGS10"), yields.get("DGS2")
    if ten and two and ten["reference_period"] and ten["reference_period"] == two["reference_period"]:
        factors.append({"source_key": "fred", "measurement": "matched_date_10y_minus_2y",
            "value": ten["value"] - two["value"], "unit": "percentage_points",
            "reference_period": ten["reference_period"],
            "available_at": max(ten["available_at"], two["available_at"]),
            "receipt_refs": [ten["receipt_ref"], two["receipt_ref"]],
            "measured_incremental_predictive_value": None})
    return factors


def build_context_projection(runtime, *, now):
    with _db(runtime).transaction() as connection:
        _prepare(connection)
        records = connection.execute("SELECT payload_json,available_at,last_seen_at FROM source_context_receipts "
            "ORDER BY last_seen_at DESC,available_at DESC,receipt_id").fetchall()
        snapshots = {row[0]: {"status": row[1], "ids": set(json.loads(row[2]))}
                     for row in connection.execute("SELECT source_key,status,receipt_ids_json FROM source_context_snapshots")}
    selected, keys, counts = [], set(), Counter()
    for payload, first_seen, last_seen in records:
        row = json.loads(payload)
        snapshot = snapshots.get(row["source_key"], {})
        if snapshot.get("status") != "live" or not snapshot.get("ids"):
            continue
        if row["source_key"] != "fred" and row["receipt_id"] not in snapshot["ids"]:
            continue
        key = (row["source_key"], row["record_key"])
        if key in keys or counts[row["source_key"]] >= MAX_CURRENT_PER_SOURCE:
            continue
        keys.add(key)
        if datetime.fromisoformat(last_seen) > now or datetime.fromisoformat(first_seen) > now:
            continue
        observation = row["provider_observed_at"] or (last_seen if row["source_key"] in MACRO_KEYS else first_seen)
        budget = 86400 * (7 if row["source_key"] in MACRO_KEYS else 3)
        if (now - datetime.fromisoformat(observation)).total_seconds() > budget or not _reference_current(row, now):
            continue
        families, symbols, role = _relevance(row)
        row.update(available_at=first_seen, last_verified_at=last_seen,
                   families=sorted(families), issuer_symbols=sorted(symbols), evidence_role=role,
                   historical_backfill_eligible=False, executable_quote=False)
        selected.append(row)
        counts[row["source_key"]] += 1
    packets = []
    for family, config in FAMILIES.items():
        for symbol in sorted(config["symbols"]):
            relevant = [row for row in selected if family in row["families"] and
                        (not row["issuer_symbols"] or symbol in row["issuer_symbols"] or
                         (row["evidence_role"] in {"issuer_filing_metadata", "issuer_filing_content",
                                                   "unverified_congressional_discussion_secondary"}
                          and symbol in {"SMH", "SOXX", "ITA", "XAR"}))]
            # Keep independent roles rather than letting a news burst crowd out
            # slower macro context or the actual market observations.
            relevant.sort(key=lambda row: (row["evidence_role"], row["source_key"], row["receipt_id"]))
            ranked, groups = [], {}
            for row in relevant:
                groups.setdefault((row["source_key"], row["evidence_role"]), []).append(row)
            while groups and len(ranked) < MAX_PACKET_ROWS:
                for key in list(groups):
                    ranked.append(groups[key].pop(0))
                    if not groups[key]:
                        del groups[key]
                    if len(ranked) == MAX_PACKET_ROWS:
                        break
            if not ranked:
                continue
            refs = sorted(row["receipt_id"] for row in ranked)
            roles = sorted({row["evidence_role"] for row in ranked})
            from orchestrator.research.economic_events import VERSION, packet_changes
            changes = packet_changes(ranked, family=family, instrument=symbol)
            packet_id = "cross-source:" + _digest([family, symbol, refs, VERSION])[:32]
            packets.append({"packet_id": packet_id, "instrument": symbol, "family": family,
                "context_generated_at": now.isoformat(),
                "mechanism_hypothesis": config["mechanism"], "receipt_refs": refs, "evidence": ranked,
                "factor_observations": _factors(ranked),
                "economic_changes": changes, "economic_policy_version": VERSION,
                "economic_change_count": len(changes),
                "economic_surprise_state": "reported_prior_only_not_consensus" if any(
                    row["comparison"].get("delta") is not None for row in changes) else "unmeasured",
                "source_keys": sorted({row["source_key"] for row in ranked}), "roles": roles,
                "state": "cross_source_testable_context" if len(roles) >= 2 else "single_role_context",
                "direction": None, "expected_return": None, "validated_edge": False,
                "context_alone_is_not_catalyst": True,
                "test_protocol": {"policy_version": "cross-source-context.1", "forward_only": True,
                    "horizons_market_sessions": [1, 3, 5], "controls": ["no_trade", "SPY", "same_family_price_only"],
                    "purge_overlapping_outcomes": True, "costs_required": True,
                    "incremental_value_required_before_weight_or_size_increase": True}})
    return {"schema_version": "qadam_cross_source_context.v1", "generated_at": now.isoformat(),
            "status": "context_available" if packets else "awaiting_relevant_provider_context",
            "packets": packets, "packet_count": len(packets), "retained_receipt_count": len(records),
            "eligible_current_receipt_count": len(selected), "context_source_keys": sorted(counts),
            "source_receipt_counts": dict(counts), "maximum_receipts": MAX_RECEIPTS,
            "context_sources_used_in_packets": sorted({key for packet in packets for key in packet["source_keys"]}),
            "unmapped_current_receipt_count": sum(not row["families"] for row in selected),
            "economic_change_packet_count": sum(bool(packet["economic_changes"]) for packet in packets),
            "broker_write_count": 0, "live_capital_enabled": False,
            "score_or_size_bonus_allowed": False, "automatic_strategy_mutation_allowed": False}


def context_for_instrument(projection, symbol, *, as_of):
    stamp = verified_timestamp(projection.get("generated_at"))
    current = verified_timestamp(as_of)
    if not stamp or not current or not 0 <= (datetime.fromisoformat(current) - datetime.fromisoformat(stamp)).total_seconds() <= 1800:
        return None
    packet = next((row for row in projection.get("packets", []) if row.get("instrument") == symbol), None)
    packet_stamp = verified_timestamp(packet.get("context_generated_at")) if packet else None
    if (packet and packet_stamp and
            0 <= (datetime.fromisoformat(current) - datetime.fromisoformat(packet_stamp)).total_seconds() <= 1800 and
            all(verified_timestamp(row.get("available_at")) and
                      datetime.fromisoformat(row["available_at"]) <= datetime.fromisoformat(current)
                      for row in packet.get("evidence", []))):
        return packet
    return None
