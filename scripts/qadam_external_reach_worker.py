#!/usr/bin/env python3
"""Isolated public-document fetch worker.

The worker accepts one JSON request and writes one JSON result. It has no Qadam
imports, no shell execution, no credential support and no authenticated mode.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener


ALLOWED_TRANSPORTS = {"official_web", "rss", "github_api"}


class SameHostRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        source = urlparse(req.full_url)
        target = urlparse(newurl)
        if source.hostname != target.hostname or target.scheme != "https":
            raise HTTPError(newurl, code, "cross-host redirect denied", headers, fp)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _result(*, request: dict[str, Any], state: str, **values: Any) -> dict[str, Any]:
    return {
        "schema_version": "qadam_external_reach_worker.v1",
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "request_id": request.get("request_id"),
        "origin_id": request.get("origin_id"),
        "transport": request.get("transport"),
        "state": state,
        **values,
    }


def run(request: dict[str, Any]) -> dict[str, Any]:
    transport = str(request.get("transport") or "")
    url = str(request.get("url") or "")
    allowed_domains = {str(value).lower() for value in request.get("allowed_domains") or []}
    maximum = int(request.get("max_response_bytes") or 0)
    timeout = min(60, max(1, int(request.get("timeout_seconds") or 30)))
    parsed = urlparse(url)
    if transport not in ALLOWED_TRANSPORTS:
        return _result(request=request, state="denied", error="transport_not_allowed")
    if parsed.scheme != "https" or not parsed.hostname:
        return _result(request=request, state="denied", error="https_url_required")
    if parsed.hostname.lower() not in allowed_domains:
        return _result(request=request, state="denied", error="domain_not_allowed")
    if maximum <= 0 or maximum > 2_000_000:
        return _result(request=request, state="denied", error="response_limit_invalid")
    headers = {
        "Accept": "application/json, application/atom+xml, application/rss+xml, text/xml, text/html;q=0.8",
        "User-Agent": "QadamResearch/1.0 public-evidence contact=operator@qadam.trade",
    }
    if request.get("if_none_match"):
        headers["If-None-Match"] = str(request["if_none_match"])
    if request.get("if_modified_since"):
        headers["If-Modified-Since"] = str(request["if_modified_since"])
    try:
        response = build_opener(SameHostRedirectHandler()).open(
            Request(url, headers=headers), timeout=timeout
        )
        body = response.read(maximum + 1)
        if len(body) > maximum:
            return _result(request=request, state="rejected", error="response_too_large")
        content_type = str(response.headers.get("Content-Type") or "").split(";")[0].strip()
        return _result(
            request=request,
            state="retrieved",
            final_url=response.geturl(),
            status_code=int(getattr(response, "status", 200)),
            content_type=content_type,
            etag=response.headers.get("ETag"),
            last_modified=response.headers.get("Last-Modified"),
            content_sha256=hashlib.sha256(body).hexdigest(),
            byte_count=len(body),
            content_utf8=body.decode("utf-8", errors="replace"),
        )
    except HTTPError as exc:
        if exc.code == 304:
            return _result(request=request, state="not_modified", status_code=304)
        return _result(request=request, state="provider_error", error=f"http_{exc.code}")
    except (URLError, TimeoutError, OSError) as exc:
        return _result(request=request, state="provider_error", error=type(exc).__name__)


def main() -> int:
    if len(sys.argv) != 3:
        return 64
    request_path = Path(sys.argv[1]).resolve()
    output_path = Path(sys.argv[2]).resolve()
    try:
        request = json.loads(request_path.read_text(encoding="utf-8"))
        if not isinstance(request, dict):
            raise ValueError("request must be an object")
        payload = run(request)
    except Exception as exc:  # Fail closed without exposing request content.
        payload = {
            "schema_version": "qadam_external_reach_worker.v1",
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "state": "worker_error",
            "error": type(exc).__name__,
        }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_suffix(output_path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(output_path)
    return 0 if payload.get("state") in {"retrieved", "provider_error"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
