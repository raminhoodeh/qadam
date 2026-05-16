#!/usr/bin/env python3
"""Report local store readiness for the Qadam foundation."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings
from orchestrator.local_store import local_store_health


def main() -> int:
    require_running = "--require-running" in sys.argv
    health = local_store_health(Settings.from_env())
    print(f"local_store_status={health['status']}")
    print(f"local_store_directories={health['summary']['directory_count']}")
    print(f"local_store_missing_directories={health['summary']['missing_directories']}")
    print(f"local_store_reachable_services={health['summary']['reachable_services']}")
    print(f"local_store_offline_services={health['summary']['offline_services']}")

    for service in health["services"]:
        print(f"{service['key']}_status={service['status']}")
        print(f"{service['key']}_fallback={service['fallback']}")

    if health["status"] == "error":
        print("local_store_check=failed")
        return 1
    if require_running and health["status"] != "ok":
        print("local_store_required_services_not_running=true")
        return 1

    print("local_store_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
