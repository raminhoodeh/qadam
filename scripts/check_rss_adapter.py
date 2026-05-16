#!/usr/bin/env python3
"""Check the RSS read-only source adapter path."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.adapters import RSSAdapter, rss_adapter_status


def _arg_value(prefix: str) -> str | None:
    for arg in sys.argv:
        if arg.startswith(prefix):
            return arg.split("=", 1)[1]
    return None


def _csv_arg(prefix: str) -> tuple[str, ...]:
    value = _arg_value(prefix)
    if not value:
        return ()
    return tuple(item.strip() for item in value.split(",") if item.strip())


async def main() -> int:
    live = "--live" in sys.argv
    keyword_filter = _csv_arg("--keywords=")
    feed_urls = _csv_arg("--feed-urls=")
    adapter = RSSAdapter()

    try:
        envelope = (
            await adapter.fetch_live(feed_urls=feed_urls, keyword_filter=keyword_filter)
            if live
            else adapter.fetch_sample(keyword_filter=keyword_filter)
        )
    except Exception as exc:  # noqa: BLE001 - adapter check should make failures explicit
        print("rss_adapter_status=failed")
        print(f"rss_adapter_error_type={exc.__class__.__name__}")
        print(f"rss_adapter_error={exc!r}")
        return 1

    status = rss_adapter_status()
    print("rss_adapter_status=ok")
    print(f"rss_adapter_mode={'live_read_only' if live else 'sample'}")
    print(f"rss_adapter_source={envelope.source}")
    print(f"rss_adapter_event_count={len(envelope.events)}")
    print(f"rss_adapter_degraded={envelope.degraded}")
    print(f"rss_adapter_degraded_reason={envelope.degraded_reason}")
    print(f"rss_adapter_raw_archive_path={envelope.raw_archive_path}")
    print(f"rss_adapter_archive_exists={status['raw_archive_exists']}")

    if not envelope.events and not envelope.degraded and not keyword_filter:
        print("rss_adapter_event_count_empty=true")
        return 1
    if not envelope.raw_archive_path:
        print("rss_adapter_raw_archive_missing=true")
        return 1

    print("rss_adapter_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
