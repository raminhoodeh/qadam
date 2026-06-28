#!/usr/bin/env python3
"""Focused QSASE Phase 0 validated edge readiness check."""

from check_qsase_phase0_paperops_reliability_baseline import run_component_check


if __name__ == "__main__":
    raise SystemExit(run_component_check("validated_edge_readiness"))
