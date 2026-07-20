#!/usr/bin/env python3
"""Fail if current Qadam surfaces drift from the active operating contract."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CURRENT_FACING_PATHS = (
    "cockpit/public/whitepaper/index.html",
    "landing-page-repo/whitepaper/index.html",
    "landing-page-repo/guide/index.html",
    "landing-page-repo/dashboard.js",
    "cockpit/lib/health.ts",
    "docs/api-key-setup.md",
    "docs/api-specs.md",
    "docs/qadam-dashboard-implementation-plan.md",
    "docs/qadam-dashboard-navigation-ux-plan.md",
    "docs/qadam-dashboard-overhaul-master-implementation-plan.md",
    "docs/qadam-foundational-architecture-plan.md",
    "docs/qadam-for-fund-managers.md",
    "docs/qadam-implementation-plan.md",
    "docs/qadam-master-implementation-plan.md",
    "docs/qadam-modular-implementation-plan.md",
    "docs/qadam-phase-5-layer-b-implementation-plan.md",
    "docs/qadam-phase-7-demo-proof-implementation-plan.md",
    "docs/qadam-resource-registry.md",
    "docs/qadam-user-guide.md",
    "docs/qadam-whitepaper.md",
    "orchestrator",
    "scripts",
)

PUBLIC_DOCUMENTATION_PATHS = {
    Path("cockpit/public/whitepaper/index.html"),
    Path("landing-page-repo/whitepaper/index.html"),
    Path("landing-page-repo/guide/index.html"),
    Path("docs/qadam-for-fund-managers.md"),
    Path("docs/qadam-user-guide.md"),
    Path("docs/qadam-whitepaper.md"),
}

EXACT_FORBIDDEN = (
    "first_release_gbp_1000_trial",
    "PHASE7_PAPER_ACCOUNT_STARTING_GBP = 1000",
)

TRIAL_DEFAULT_PATTERN = re.compile(r"QADAM_TRIAL_BALANCE_GBP[^\n]+[\"']1000[\"']")
LEGACY_CAPITAL_PATTERN = re.compile(
    r"(&pound;1000(?!00)|£1000(?!00)|£1,000|GBP 1000(?!00)|GBP 1,000)",
    re.IGNORECASE,
)
LEGACY_PUBLIC_GBP_100K_PATTERN = re.compile(
    r"(&pound;\s*100,?000|£\s*100,?000|GBP\s*100,?000)",
    re.IGNORECASE,
)
ACCOUNT_CONTEXT_TERMS = (
    "account",
    "allocation",
    "balance",
    "capital",
    "equity",
    "paper",
    "proof",
    "starting",
    "test",
    "trial",
)
RISK_CAP_ALLOW_TERMS = (
    "risk cap",
    "max risk",
    "max_risk",
    "max notional",
    "single-order",
    "single order",
    "notional",
)
NINETY_DAY_ALLOWED_TERMS = ("old", "older", "historical", "stale")
NINETY_DAY_PROOF_TERMS = ("proof", "harness", "demo", "run", "calendar")


def _iter_files() -> list[Path]:
    files: list[Path] = []
    for rel_path in CURRENT_FACING_PATHS:
        path = ROOT / rel_path
        if path.is_dir():
            files.extend(
                candidate
                for candidate in path.rglob("*")
                if candidate.is_file()
                and candidate.name != "check_qadam_operational_consistency.py"
                and not re.search(r" \d+$", candidate.stem)
                and candidate.suffix in {".py", ".js", ".ts", ".tsx", ".md", ".html"}
            )
        elif path.exists():
            files.append(path)
    return sorted(set(files))


def _is_allowed_legacy_capital_context(line: str) -> bool:
    lowered = line.lower()
    return any(term in lowered for term in RISK_CAP_ALLOW_TERMS)


def _has_account_context(line: str) -> bool:
    lowered = line.lower()
    return any(term in lowered for term in ACCOUNT_CONTEXT_TERMS)


def main() -> int:
    failures: list[str] = []
    for path in _iter_files():
        rel = path.relative_to(ROOT)
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for line_number, line in enumerate(lines, start=1):
            for marker in EXACT_FORBIDDEN:
                if marker in line:
                    failures.append(f"{rel}:{line_number}: forbidden legacy marker: {marker}")
            if TRIAL_DEFAULT_PATTERN.search(line):
                failures.append(f"{rel}:{line_number}: QADAM_TRIAL_BALANCE_GBP defaults to 1000")
            if LEGACY_CAPITAL_PATTERN.search(line) and _has_account_context(line):
                if not _is_allowed_legacy_capital_context(line):
                    failures.append(f"{rel}:{line_number}: legacy GBP 1,000 account language")
            if rel in PUBLIC_DOCUMENTATION_PATHS and LEGACY_PUBLIC_GBP_100K_PATTERN.search(line):
                failures.append(f"{rel}:{line_number}: public documentation must use the USD Alpaca Paper baseline")
            if "90-day" in line or "90 day" in line.lower():
                lowered = line.lower()
                if (
                    any(term in lowered for term in NINETY_DAY_PROOF_TERMS)
                    and not any(term in lowered for term in NINETY_DAY_ALLOWED_TERMS)
                ):
                    failures.append(f"{rel}:{line_number}: current-facing 90-day proof language")

    if failures:
        print("qadam_operational_consistency=failed")
        for failure in failures:
            print(failure)
        return 1

    print("qadam_operational_consistency=ok")
    print("paper_account_scope=first_release_usd_100000_alpaca_paper")
    print("paper_account_currency=USD")
    print("paper_account_reference_baseline_usd=100000")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
