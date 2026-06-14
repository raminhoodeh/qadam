# Qadam Source/Evidence Deployment Discipline

Date: 2026-06-14

Scope: deployment discipline for the source/evidence/runtime integration work.
No dashboard simplification is included in this stage.

## Contract

Every production dashboard deploy must prove, before deployment, that the source
and evidence runtime work is still coherent and public-safe.

The preflight now runs:

- `scripts/check_evidence_packet_runtime.py`
- `scripts/check_source_evidence_acceptance.py`
- `scripts/check_cockpit_status.py`
- `scripts/check_source_evidence_deployment_discipline.py`

The deployment-discipline checker writes
`data/runtime/source_evidence_deployment_discipline.json` and must report
`source_evidence_deployment_discipline_check=ok`.

## Required Evidence

The checker verifies:

- source/evidence/runtime acceptance is `ok`;
- the production deploy script requires local preflight before Vercel deploy;
- the public cockpit mirror contains the durable evidence runtime, TradingView
  MCP, Bookmap local bridge, and source-gap visibility;
- the detached cockpit-status digest is read-only and aligned to the payload;
- the deployment receipt, when present, carries the deployment URL, production
  aliases, and preflight status.

## Boundary

No broker write authority is granted.

No live capital is enabled.

No paper orders are submitted by this gate.

No provider calls, quantum jobs, proof credit, or trade approvals are created by
this gate.

TradingView MCP and Bookmap local bridge remain read-only supplemental evidence
providers. Alpaca Paper remains the only guarded paper execution route, and this
gate does not call it.
