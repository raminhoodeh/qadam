#!/usr/bin/env python3
"""Initialize and check the embedded local Chroma Knowledge Graph."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.chroma_store import knowledge_graph_health
from orchestrator.config import Settings


def main() -> int:
    health = knowledge_graph_health(Settings.from_env())
    print(f"knowledge_graph_status={health['status']}")
    print(f"knowledge_graph_backend={health['backend']}")
    print(f"knowledge_graph_collection={health['collection']}")
    print(f"knowledge_graph_path={health['path']}")
    print(f"knowledge_graph_count={health.get('count', 0)}")
    if health["status"] != "ok":
        print(f"knowledge_graph_error={health.get('error')}")
        return 1
    print("knowledge_graph_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
