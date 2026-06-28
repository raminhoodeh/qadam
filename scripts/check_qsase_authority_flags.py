#!/usr/bin/env python3
"""Focused QSASE-0 universal authority flag check."""

from check_qsase_governance_safety_contract import run_governance_component_check


if __name__ == "__main__":
    raise SystemExit(run_governance_component_check("authority_flags"))
