# Qadam Dashboard D11M - Regression And Acceptance Tests

Date: 2026-05-26

D11M adds a regression gate after the D11A-D11L simplification pass. The
purpose is to prove that the dashboard now reads as a smaller set of useful
operating views without losing the safety, evidence, reasoning, trade, paper
account, or operations contracts that make Qadam auditable.

## Scope

- Add one cross-view regression checker for the simplified dashboard shell.
- Confirm the five-view navigation contract remains canonical: Overview,
  Trades, Evidence, Reasoning, and Operations.
- Confirm the single safety strip remains the only global authority summary.
- Confirm each primary view renders its consolidated D11 content from the
  public-safe status snapshot.
- Confirm public dashboard HTML, CSS, and rendered output do not expose local
  paths, secrets, private payloads, request bodies, or broker identifiers.
- Wire the new checker into the dashboard deployment preflight and acceptance
  dependency list.

## Acceptance

- `scripts/check_dashboard_d11m_regression_acceptance.js` exists and passes.
- `scripts/preflight_dashboard_deployment.sh` runs the D11M checker after the
  D11L checker.
- `scripts/check_dashboard_acceptance.js` treats the D11M checker as an
  acceptance dependency.
- The master dashboard overhaul plan records D11M as complete and moves the
  next performance-focused work to D11N.

## Authority Boundary

D11M is test and documentation work only. It does not change provider calls,
broker routes, Telegram command behavior, paper-trading permissions, proof
credit, learning writes, or live-capital state.
