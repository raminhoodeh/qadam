"""Bounded daily GPSJAM observations from its public, dated CSV exports."""

import csv
from datetime import datetime, timezone
import io


async def _text(client, url):
    chunks, size = [], 0
    async with client.stream("GET", url) as response:
        response.raise_for_status()
        async for chunk in response.aiter_bytes():
            size += len(chunk)
            if size > 2_000_000:
                raise ValueError("gpsjam_payload_size_limit")
            chunks.append(chunk)
    return b"".join(chunks).decode("utf-8-sig")


async def fetch_payload(client, *, now=None):
    now = now or datetime.now(timezone.utc)
    manifest_url = "https://gpsjam.org/data/manifest.csv"
    manifest = list(csv.DictReader(io.StringIO(await _text(client, manifest_url))))
    # Use the provider's latest complete date, never fabricate a current-day snapshot.
    eligible = [row for row in manifest if row.get("suspect") == "false"
                and row.get("source") in {"merged", "airplaneslive", "adsbexchange"}
                and row.get("date", "") < now.date().isoformat()]
    if not eligible:
        raise ValueError("gpsjam_complete_publication_missing")
    latest = max(eligible, key=lambda row: (row["date"], row["source"] == "merged"))
    day = datetime.strptime(latest["date"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
    if (now - day).total_seconds() > 4 * 86400:
        raise ValueError("gpsjam_publication_stale")
    source = "" if latest["source"] == "adsbexchange" else "/" + latest["source"]
    url = f"https://gpsjam.org/data{source}/{latest['date']}-h3_4.csv"
    records = []
    for row in csv.DictReader(io.StringIO(await _text(client, url))):
        good, bad = int(row["count_good_aircraft"]), int(row["count_bad_aircraft"])
        if good < 0 or bad < 0 or not good + bad:
            raise ValueError("gpsjam_invalid_aircraft_counts")
        degraded = max(0, 100 * (bad - 1) / (good + bad))
        records.append({"id": f"{latest['date']}:{row['hex']}", "hex": row["hex"],
                        "title": f"GPSJAM {latest['date']} cell {row['hex']}: {degraded:.1f}% degraded navigation accuracy",
                        "reference_period": latest["date"], "count_good_aircraft": good,
                        "count_bad_aircraft": bad, "navigation_accuracy_degraded_pct": degraded,
                        "publication_timestamp_known": False})
    if not records:
        raise ValueError("gpsjam_observations_missing")
    records.sort(key=lambda row: (-row["navigation_accuracy_degraded_pct"], row["hex"]))
    return {"records": records[:25], "provider_url": url,
            "coverage_cell_count": len(records), "selection": "highest_25_degraded_accuracy_cells",
            "reference_period": latest["date"], "sample": False,
            "scope": "Observed navigation accuracy; not proof of jamming or global absence of interference."}
