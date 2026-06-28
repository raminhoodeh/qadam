#!/usr/bin/env python3
"""Focused QSASE-0 calendar boundary check."""

from check_qsase_governance_safety_contract import run_governance_component_check


if __name__ == "__main__":
    raise SystemExit(run_governance_component_check("calendar_boundary"))
