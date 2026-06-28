#!/usr/bin/env python3
"""Focused QSASE Phase 0 dashboard deploy hygiene check."""

from check_qsase_phase0_paperops_reliability_baseline import run_component_check


if __name__ == "__main__":
    raise SystemExit(run_component_check("dashboard_deploy_hygiene"))
