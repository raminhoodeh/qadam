# Qadam Dashboard D11H - Reasoning View Consolidation

Date: 2026-05-26

## Scope

D11H consolidates the Reasoning view so it reads as one research notebook with
clear boundaries between prior, evidence, hypothesis, blocker, and reviewer.

## Changes

- Removed the duplicate Cognition panel brief from the Reasoning view.
- Added one consolidated reasoning readout that answers whether an idea can move
  beyond research.
- Grouped reasoning detail into three primary drawers:
  - Prior and evidence basis.
  - Hypotheses and blockers.
  - Review chain and quant annotation.
- Moved legacy cognition details into one advanced diagnostics drawer.
- Kept private priors separate from factual evidence.
- Kept hypotheses separate from candidates and orders.
- Kept Research Analyst, Strategy Lead, Signal Integrity, and Head of Quant
  output challenge-only / annotation-only.

## Authority Boundary

D11H is presentation-only. It does not change reasoning, source ingestion,
signal integrity, risk policy, broker writes, provider calls, Telegram command
behavior, proof-credit rules, or live-capital state.

## Acceptance

- `scripts/check_dashboard_d11h_reasoning_view_consolidation.js` validates the
  static shell, renderer, CSS, grouped Reasoning view, cache key, public-safe
  copy, and unchanged authority boundary.
- Existing reasoning, cognition, renderer, responsive, and deployment preflight
  checks must continue to pass.
