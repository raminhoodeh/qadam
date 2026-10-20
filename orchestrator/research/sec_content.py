"""One bounded recent SEC filing per collection pass; no links from filing HTML.

The submissions index remains usable when optional document access is denied.
Only archived, cited text is economic evidence; index availability is not content.
"""

from datetime import datetime, timedelta
from hashlib import sha256
from html.parser import HTMLParser
import json
import re

import httpx

from orchestrator.research.economic_events import extract_changes, sentences
from orchestrator.research.source_time import retry_after_seconds, verified_timestamp
from orchestrator.storage.control_plane import ControlPlaneStore

MAX_BYTES = 2_000_000
MAX_CACHE_ROWS = 32
FORMS = {"10-Q", "10-K", "8-K", "20-F", "6-K"}


class FilingText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.hidden = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "head", "ix:hidden"}:
            self.hidden += 1
        if tag in {"p", "div", "br", "tr"} and not self.hidden:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in {"script", "style", "head", "ix:hidden"}:
            self.hidden = max(0, self.hidden - 1)

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def filing_candidate(payload, *, now):
    recent = payload.get("filings", {}).get("recent") or {}
    cik = str(payload.get("cik") or "")
    if not re.fullmatch(r"\d{1,10}", cik):
        return None
    for index, accession in enumerate(recent.get("accessionNumber", [])[:25]):
        def field(key):
            values = recent.get(key) or []
            return values[index] if index < len(values) else None
        stamp = verified_timestamp(field("acceptanceDateTime"))
        document = str(field("primaryDocument") or "")
        if (field("form") not in FORMS or not stamp or not re.fullmatch(r"\d{10}-\d{2}-\d{6}", str(accession))
                or not re.fullmatch(r"[A-Za-z0-9_-]+\.(?:htm|html)", document)
                or not timedelta(0) <= now - datetime.fromisoformat(stamp) <= timedelta(days=3)):
            continue
        url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession.replace('-', '')}/{document}"
        return {"url": url, "accession_number": accession, "observed_at": stamp,
                "form": field("form"), "filing_date": field("filingDate"), "cik": cik}
    return None


def extract_filing_quotes(content, issuers):
    parser = FilingText()
    parser.feed(content)
    text = "\n".join(re.sub(r"\s+", " ", row).strip() for row in "".join(parser.parts).splitlines())
    selected, seen = [], set()
    for _start, _end, sentence in sentences(text):
        if not 20 <= len(sentence) <= 550 or sentence in seen:
            continue
        features = extract_changes(sentence, family="semiconductors", issuer_symbols=issuers)
        if not any(row["reported_change"] not in {"unresolved", "negated_or_unchanged"} for row in features):
            continue
        seen.add(sentence)
        selected.append(sentence)
        if len(selected) == 8:
            break
    return selected


async def enrich_recent_filing(client, payload, *, headers, runtime, now):
    """Cache receipts, including failures/cooldowns, without holding a DB lock over I/O."""
    candidate = filing_candidate(payload, now=now)
    if not candidate:
        payload["_qadam_filing_content_status"] = "no_recent_supported_primary_document"
        return
    if "@" not in headers.get("User-Agent", ""):
        payload["_qadam_filing_content_status"] = "declared_sec_user_agent_required"
        return
    store = ControlPlaneStore(runtime / "qadam-control-plane.sqlite3")
    with store.transaction() as connection:
        connection.execute("CREATE TABLE IF NOT EXISTS sec_content_cache (url TEXT PRIMARY KEY, fetched_at TEXT NOT NULL, retry_at TEXT NOT NULL, payload_json TEXT NOT NULL)")
        previous = connection.execute("SELECT retry_at,payload_json FROM sec_content_cache WHERE url=?", (candidate["url"],)).fetchone()
    if previous and now < datetime.fromisoformat(previous[0]):
        result = json.loads(previous[1])
    else:
        result = {**candidate, "status": "document_unavailable", "quotes": []}
        retry = now + timedelta(hours=24)
        try:
            # No redirects, attachments or arbitrary filing-supplied URLs.
            async with client.stream("GET", candidate["url"], headers=headers, timeout=8, follow_redirects=False) as response:
                response.raise_for_status()
                if response.status_code != 200 or "html" not in response.headers.get("content-type", "").lower():
                    raise ValueError("filing_content_type_or_redirect_not_supported")
                body = bytearray()
                async for chunk in response.aiter_bytes():
                    body.extend(chunk)
                    if len(body) > MAX_BYTES:
                        raise ValueError("filing_exceeds_bounded_content_budget")
            result.update(status="content_verified", document_sha256=sha256(body).hexdigest(),
                quotes=extract_filing_quotes(body.decode("utf-8", errors="replace"), payload.get("tickers") or []),
                retrieved_at=now.isoformat(), content_bytes=len(body))
        except (httpx.HTTPError, ValueError) as exc:
            result["error_type"] = str(exc) if isinstance(exc, ValueError) else type(exc).__name__
            if isinstance(exc, httpx.HTTPStatusError):
                result["http_status"] = exc.response.status_code
                delay = retry_after_seconds(exc.response.headers.get("Retry-After"), now=now) or 0
                retry = max(retry, now + timedelta(seconds=delay))
        with store.transaction() as connection:
            connection.execute("INSERT OR REPLACE INTO sec_content_cache VALUES (?,?,?,?)",
                (candidate["url"], now.isoformat(), retry.isoformat(), json.dumps(result, sort_keys=True)))
            connection.execute("DELETE FROM sec_content_cache WHERE url IN (SELECT url FROM sec_content_cache ORDER BY fetched_at DESC,url LIMIT -1 OFFSET ?)", (MAX_CACHE_ROWS,))
    payload["_qadam_filing_content_status"] = result["status"]
    payload["_qadam_filing_content"] = result
