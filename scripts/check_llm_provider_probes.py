#!/usr/bin/env python3
"""Check safe Gemini and LM Studio provider probes."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.intelligence import provider_status


def main() -> int:
    parser = argparse.ArgumentParser(description="Run safe provider readiness probes.")
    parser.add_argument("--local-live", action="store_true", help="Call LM Studio /models on the configured local URL.")
    parser.add_argument("--gemini-live", action="store_true", help="Call Gemini model-list endpoint without generation.")
    args = parser.parse_args()

    status = provider_status(local_live=args.local_live, gemini_live=args.gemini_live)
    frontier = status["frontier_llm"]
    local = status["local_llm"]

    print(f"llm_provider_status={status['status']}")
    print(f"gemini_configured={frontier['credential_configured']}")
    print(f"gemini_mode={frontier['mode']}")
    print(f"gemini_probe_status={frontier['probe_status']}")
    print(f"gemini_model_count={frontier.get('model_count', 0)}")
    print(f"local_provider={local['provider']}")
    print(f"local_model={local['model']}")
    print(f"local_mode={local['mode']}")
    print(f"local_probe_status={local['probe_status']}")
    print(f"local_model_available={local['model_available']}")
    print(f"local_available_model_count={local['available_model_count']}")

    if args.local_live and local["probe_status"] != "ok":
        return 1
    if args.gemini_live and frontier["probe_status"] != "ok":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
