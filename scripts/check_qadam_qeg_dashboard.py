#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_qeg_visibility import build_qeg_visibility, validate_qeg_visibility


if __name__ == "__main__":
    dashboard, _telegram, build_errors = build_qeg_visibility()
    errors = sorted(set([*build_errors, *validate_qeg_visibility()]))
    overview = (dashboard.get("sections") or {}).get("overview") or {}
    print(f"status={'passed' if not errors else 'blocked'}")
    print(f"graph_nodes={overview.get('node_count', 0)}")
    print(f"graph_edges={overview.get('edge_count', 0)}")
    print(f"validated_edges={overview.get('validated_edge_count', 0)}")
    for error in errors:
        print(f"error={error}")
    raise SystemExit(1 if errors else 0)
