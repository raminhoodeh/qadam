#!/usr/bin/env python3
"""Build Qadam's fail-closed permanent operator reliability certificate."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_permanent_operator_reliability import (  # noqa: E402
    build_permanent_reliability_certification,
)


def main() -> int:
    result = build_permanent_reliability_certification()
    print(f"qadam_permanent_reliability_status={result['status']}")
    print(
        "qadam_permanent_reliability_implementation_complete="
        f"{result['implementation_complete']}"
    )
    print(
        "qadam_permanent_reliability_certified="
        f"{result['permanent_reliability_certified']}"
    )
    print(f"qadam_permanent_reliability_blockers={','.join(result['blockers'])}")
    return 0 if result["status"] in {"passed", "provisional_soak"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
