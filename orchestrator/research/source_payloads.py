"""Extract observations from provider envelopes without promoting metadata to data."""

from datetime import datetime, timezone
import json
import math


def number(value):
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("provider_nonfinite_value")
    return result


def utc_epoch(value):
    numeric = number(value)
    return datetime.fromtimestamp(numeric / 1000 if numeric > 100_000_000_000 else numeric,
                                  timezone.utc).isoformat()


def provider_records(key, payload):
    if key == "polymarket" and isinstance(payload, dict) and "provider_payload" in payload:
        rows = []
        for row in payload["provider_payload"]:
            if row.get("active") is not True or row.get("closed") is not False or row.get("archived") is True:
                continue
            outcomes = row.get("outcomes", [])
            prices = row.get("outcomePrices", [])
            outcomes = json.loads(outcomes) if isinstance(outcomes, str) else outcomes
            prices = json.loads(prices) if isinstance(prices, str) else prices
            if not outcomes or len(outcomes) != len(prices):
                raise ValueError("polymarket_outcome_prices_missing")
            numeric = [number(value) for value in prices]
            if any(value < 0 or value > 1 for value in numeric):
                raise ValueError("polymarket_price_out_of_range")
            rows.append({"id": row["id"], "title": row["question"],
                         "observed_at": row.get("updatedAt"),
                         "outcome_prices": dict(zip(outcomes, numeric)),
                         "liquidity": number(row.get("liquidityNum", 0)),
                         "volume_24h": number(row.get("volume24hr", 0)),
                         "best_bid": row.get("bestBid"), "best_ask": row.get("bestAsk"),
                         "condition_id": row.get("conditionId"), "end_date": row.get("endDate"),
                         "price_role": "indicative_market_context_not_executable_quote"})
        return rows
    if key == "kalshi" and isinstance(payload, dict) and "items" in payload:
        return [{**row, "id": str(row["match_id"]),
                 "market_comparison": {k: row.get(k) for k in ("kalshi", "polymarket", "spread", "score")},
                 "publication_timestamp_known": False,
                 "price_role": "aggregator_suggested_match_not_verified_equivalent_contracts"}
                for row in payload["items"]]
    if key == "usgs" and isinstance(payload, dict) and "features" in payload:
        return [{"id": row["id"], "title": row["properties"]["title"],
                 "observed_at": utc_epoch(row["properties"]["time"]),
                 "value": number(row["properties"]["mag"]) if row["properties"].get("mag") is not None else None,
                 "unit": "earthquake_magnitude",
                 "measurements": {"magnitude": row["properties"].get("mag"),
                                  "coordinates": row.get("geometry", {}).get("coordinates"),
                                  "provider_updated_at": utc_epoch(row["properties"]["updated"]) if row["properties"].get("updated") else None}}
                for row in payload["features"]]
    if isinstance(payload, dict) and isinstance(payload.get("records"), list):
        if key == "space_track_celestrak" and not payload.get("sample"):
            return [{"id": f"{row['NORAD_CAT_ID']}:{row['EPOCH']}", "title": row["OBJECT_NAME"],
                     "observed_at": row["EPOCH"], "reference_period": row["EPOCH"],
                     "publication_timestamp_known": False,
                     "measurements": {name: row.get(name) for name in (
                         "NORAD_CAT_ID", "OBJECT_ID", "EPOCH", "MEAN_MOTION", "ECCENTRICITY",
                         "INCLINATION", "RA_OF_ASC_NODE", "ARG_OF_PERICENTER", "MEAN_ANOMALY")}}
                    for row in payload["records"]]
        if key == "stock_act" and not payload.get("sample"):
            # A transaction date is not when the disclosure became public. The
            # scraper's relative publication text lacks a verified timezone.
            return [{"id": ":".join(str(row.get(name, "")) for name in (
                        "politician_link", "traded_issuer_link", "traded", "type", "owner", "size", "published")),
                     "title": f"Capitol Trades: {row.get('politician_name')} {row.get('type')} {row.get('traded_issuer_ticker') or row.get('traded_issuer_name')}",
                     "reference_period": row.get("traded"), "publication_timestamp_known": False,
                     "measurements": {name: row.get(name) for name in (
                         "politician_name", "traded_issuer_ticker", "traded_issuer_name", "traded",
                         "published", "filed_after", "type", "size", "price", "owner")}}
                    for row in payload["records"]]
        return payload["records"]
    if key == "bls":
        if payload.get("status") != "REQUEST_SUCCEEDED":
            raise ValueError("bls_provider_request_failed")
        rows = []
        for series in payload.get("Results", {}).get("series", []):
            for point in series.get("data", [])[:12]:
                period = f"{point['year']}-{point['period']}"
                rows.append({"id": f"{series['seriesID']}:{period}",
                             "title": f"BLS {series['seriesID']} {period}: {point['value']}",
                             "series_id": series["seriesID"], "value": number(point["value"]),
                             "reference_period": period, "publication_timestamp_known": False})
        if not rows:
            raise ValueError("bls_observations_missing")
        return rows
    if key == "ecb":
        dimensions = payload.get("structure", {}).get("dimensions", {}).get("observation", [])
        dates = next((x["values"] for x in dimensions if x.get("id") == "TIME_PERIOD"), [])
        rows = []
        for dataset in payload.get("dataSets", []):
            for series in dataset.get("series", {}).values():
                for index, observation in series.get("observations", {}).items():
                    period = dates[int(index)]["id"]
                    rows.append({"id": f"ECB:EXR.D.USD.EUR.SP00.A:{period}",
                                 "title": f"ECB USD per EUR reference rate {period}: {observation[0]}",
                                 "series_id": "EXR.D.USD.EUR.SP00.A", "value": number(observation[0]),
                                 "reference_period": period, "unit": "USD_per_EUR",
                                 "publication_timestamp_known": False})
        if not rows:
            raise ValueError("ecb_observations_missing")
        return sorted(rows, key=lambda row: row["reference_period"], reverse=True)[:25]
    if key == "sec_edgar":
        recent = payload.get("filings", {}).get("recent")
        if not isinstance(recent, dict) or "accessionNumber" not in recent:
            raise ValueError("sec_recent_filings_missing")
        rows = []
        for i, accession in enumerate(recent["accessionNumber"][:25]):
            form, stamp = recent["form"][i], recent["acceptanceDateTime"][i]
            rows.append({"id": accession, "title": f"SEC {form} filing by {payload.get('name')} ({accession})",
                         "observed_at": stamp, "cik": str(payload.get("cik")), "form": form,
                         "filing_date": recent["filingDate"][i], "accession_number": accession})
        return rows
    if key == "internet_outage":
        if not isinstance(payload.get("data"), list) or payload.get("error"):
            raise ValueError("ioda_alert_response_invalid")
        rows = []
        for row in payload["data"]:
            entity = row["entity"]
            rows.append({"id": f"{entity['code']}:{row['datasource']}:{row['time']}:{row['level']}",
                         "title": f"IODA {entity['name']} {row['datasource']} connectivity {row['level']}: {row['value']}",
                         "observed_at": utc_epoch(row["time"]), "value": number(row["value"]),
                         "baseline_value": number(row["historyValue"]), "country_code": entity["code"],
                         "measurement_method": row.get("method"), "alert_level": row["level"]})
        return rows
    if key == "arcgis_usace":
        if "features" not in payload or payload.get("error"):
            raise ValueError("arcgis_feature_response_required")
        rows = []
        for feature in payload["features"]:
            attrs = feature.get("attributes", {})
            stamp = utc_epoch(attrs["DTG"])
            rows.append({"id": f"{attrs.get('BASIN')}:{attrs.get('STORMNUM')}:{stamp}",
                         "title": f"NOAA/Esri observed cyclone {attrs.get('STORMNAME', attrs.get('NAME', 'unnamed'))}: {attrs.get('INTENSITY', attrs.get('MAXWIND', 'unknown'))} knots",
                         "observed_at": stamp,
                         "measurements": {k: v for k, v in attrs.items() if isinstance(v, (str, int, float, type(None)))},
                         "publication_timestamp_known": False})
        return rows
    if key == "hyperliquid":
        if not isinstance(payload, list) or len(payload) != 2:
            raise ValueError("hyperliquid_asset_context_missing")
        universe, contexts = payload[0].get("universe", []), payload[1]
        if len(universe) != len(contexts):
            raise ValueError("hyperliquid_asset_context_mismatch")
        rows = []
        for asset, context in zip(universe, contexts):
            if asset.get("name") not in {"BTC", "ETH", "SOL"}:
                continue
            rows.append({"id": asset["name"], "title": f"Hyperliquid {asset['name']} mark {context['markPx']}, funding {context['funding']}",
                         "value": number(context["markPx"]), "funding_rate": number(context["funding"]),
                         "open_interest": number(context["openInterest"]), "unit": "USD",
                         "publication_timestamp_known": False})
        return rows
    return None
