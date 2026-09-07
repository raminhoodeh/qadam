"""Durable, research-only provider revisions and local overflow replay."""

from datetime import datetime, timedelta
from hashlib import sha256
import json
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from orchestrator.storage.control_plane import ControlPlaneStore


def identity(source_key, event, summary, observed_at):
    raw = event.get("raw_payload") or {}
    # Fetch bookkeeping is not a provider revision. Numeric and textual provider
    # fields remain in the material hash, even when the summary has not changed.
    ignored = {"record_id", "id", "source", "source_key", "provider", "sample",
               "fetched_at", "retrieved_at", "ingested_at", "available_at"}
    material = {key: value for key, value in raw.items() if key not in ignored}
    digest = sha256(json.dumps([summary, material], sort_keys=True, default=str).encode()).hexdigest()
    url = str(raw.get("original_url") or raw.get("canonical_url") or "")
    parts = urlsplit(url)
    query = urlencode(sorted((key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if not key.lower().startswith("utm_") and key.lower() not in {"fbclid", "gclid"}))
    canonical = urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path, query, "")) if parts.scheme in {"http", "https"} else ""
    record = str(raw.get("record_id") or raw.get("id") or canonical or
                 f"{summary}:{observed_at[:10]}")
    logical = sha256(f"{source_key}:{record}".encode()).hexdigest()
    # Only an explicit common original URL establishes syndication, not similar
    # wording. Different providers retain separate, auditable receipts.
    syndicated_material = {key: value for key, value in material.items()
                           if key not in {"original_url", "canonical_url"}}
    group = sha256(json.dumps([canonical, summary, syndicated_material], sort_keys=True, default=str).encode()).hexdigest() if canonical else logical
    legacy = {"source_key": source_key, "summary": summary,
              "provider_record_id": raw.get("record_id") or raw.get("id")}
    if not legacy["provider_record_id"]:
        legacy["observed_day"] = observed_at[:10]
    return {"event_ref": f"{source_key}:event:{sha256((logical + digest).encode()).hexdigest()[:24]}",
            "legacy_event_ref": f"{source_key}:event:{sha256(json.dumps(legacy, sort_keys=True, default=str).encode()).hexdigest()[:24]}",
            "provider_record_key": logical, "material_sha256": digest,
            "economic_event_id": group, "syndication_key": group if canonical else None}


class SourceInbox:
    def __init__(self, runtime):
        self.store = ControlPlaneStore(runtime / "qadam-control-plane.sqlite3")

    def capture(self, events):
        corrections = []
        with self.store.transaction() as connection:
            for event in events:
                event_id = "source-receipt:" + event["event_ref"]
                if connection.execute("SELECT 1 FROM operating_events WHERE event_id=?", (event_id,)).fetchone():
                    continue
                previous = connection.execute(
                    "SELECT payload_json FROM operating_events WHERE aggregate_type='source_receipt' "
                    "AND aggregate_id=? ORDER BY rowid DESC LIMIT 1",
                    (event.get("provider_record_key", event["event_ref"]),)).fetchone()
                prior = json.loads(previous[0]) if previous else {}
                row = {**event, "supersedes_event_ref": prior.get("event_ref"),
                       "supersedes_legacy_event_ref": prior.get("legacy_event_ref")}
                encoded = json.dumps(row, sort_keys=True, separators=(",", ":"))
                if len(encoded.encode()) > 8192:
                    raise ValueError("source_receipt_exceeds_normalized_record_budget")
                connection.execute(
                    "INSERT INTO operating_events VALUES (?,?,?,?,?,?,?)",
                    (event_id, "source_receipt", event.get("provider_record_key", event["event_ref"]),
                     "provider_correction" if prior else "provider_observation", encoded,
                     sha256(encoded.encode()).hexdigest(), event["available_at"]))
                if prior:
                    corrections.append(row)
        return corrections

    def acknowledge(self, event_ref, state, at):
        payload = json.dumps({"event_ref": event_ref, "state": state}, sort_keys=True)
        with self.store.transaction() as connection:
            connection.execute("INSERT OR IGNORE INTO operating_events SELECT ?,?,?,?,?,?,? "
                "WHERE EXISTS (SELECT 1 FROM operating_events WHERE event_id=?)",
                ("source-ack:" + event_ref, "source_ack", event_ref, state, payload,
                 sha256(payload.encode()).hexdigest(), at, "source-receipt:" + event_ref))

    def reconcile_goals(self, refs, at):
        with self.store.transaction() as connection:
            for ref in refs:
                payload = json.dumps({"event_ref": ref, "state": "goal_created"}, sort_keys=True)
                connection.execute("INSERT OR IGNORE INTO operating_events SELECT ?,?,?,?,?,?,? "
                    "WHERE EXISTS (SELECT 1 FROM operating_events WHERE event_id=?)",
                    ("source-ack:" + ref, "source_ack", ref, "goal_created", payload,
                     sha256(payload.encode()).hexdigest(), at, "source-receipt:" + ref))

    def pending(self, *, limit, now):
        cutoff = (now - timedelta(hours=72)).isoformat()
        with self.store.connect() as connection:
            records = connection.execute(
                "SELECT r.payload_json FROM operating_events r WHERE r.aggregate_type='source_receipt' "
                "AND NOT EXISTS (SELECT 1 FROM operating_events a WHERE a.event_id='source-ack:' || "
                "json_extract(r.payload_json,'$.event_ref')) ORDER BY r.rowid LIMIT ?", (limit,)).fetchall()
        pending, expired = [], 0
        for record in records:
            row = json.loads(record[0])
            if datetime.fromisoformat(row["observed_at"]) < datetime.fromisoformat(cutoff):
                self.acknowledge(row["event_ref"], "expired_without_research", now.isoformat())
                expired += 1
            else:
                pending.append(row)
        return pending, expired

    def completed_syndication(self, key):
        if not key:
            return False
        with self.store.connect() as connection:
            return connection.execute(
                "SELECT 1 FROM operating_events r JOIN operating_events a ON "
                "a.event_id='source-ack:' || json_extract(r.payload_json,'$.event_ref') "
                "WHERE r.aggregate_type='source_receipt' AND a.event_type='goal_created' "
                "AND json_extract(r.payload_json,'$.syndication_key')=? LIMIT 1", (key,)).fetchone() is not None

    def audit(self):
        with self.store.connect() as connection:
            receipts = connection.execute("SELECT count(*) FROM operating_events WHERE aggregate_type='source_receipt'").fetchone()[0]
            states = dict(connection.execute(
                "SELECT a.event_type,count(*) FROM operating_events a JOIN operating_events r "
                "ON r.event_id='source-receipt:' || a.aggregate_id "
                "WHERE a.aggregate_type='source_ack' GROUP BY a.event_type"))
        return {"receipt_count": receipts, "terminal_states": states,
                "unconsumed_receipt_count": receipts - sum(states.values()),
                "replay_source": "durable_local_provider_receipts", "paper_order_allowed": False}
