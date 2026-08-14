#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_qeg_visibility import build_qeg_telegram_projection, validate_qeg_telegram_payload


if __name__ == "__main__":
    payload, build_errors = build_qeg_telegram_projection()
    errors = sorted(set([*build_errors, *validate_qeg_telegram_payload(payload)]))
    print(f"status={'passed' if not errors else 'blocked'}")
    print(f"projection_state={payload.get('status')}")
    print(f"material_changed={str(payload.get('material_changed')).lower()}")
    print(f"delivery_attempted={str(payload.get('delivery_attempted')).lower()}")
    for error in errors:
        print(f"error={error}")
    raise SystemExit(1 if errors else 0)
