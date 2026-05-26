# Qadam Dashboard D11I - Operations View

Date: 2026-05-26

## Scope

D11I consolidates the Operations view so it reads as one operating control room
rather than a stack of separate runtime, safety, communications, process, and
governance cards.

## Changes

- Added one consolidated Operations readout for nodes, bridge posture, runtime
  events, hard blocks, authority flags, Telegram queue, comments, and
  live-capital state.
- Grouped Operations detail into four review drawers:
  - Runtime, bridge, and safety.
  - Operating team and data plumbing.
  - Full system map and event trail.
  - Governance and communications audit.
- Kept the full expandable System Operating Map inside Operations, with edge
  states, node diagnostics, and the closed-loop logging rule.
- Merged the visible process-console, hard-block, Telegram, and governance
  readouts into the Operations workspace to reduce duplicate visible cards.
- Kept the legacy Operations panels in the DOM for compatibility and status
  renderer coverage, but hid them from the visible Operations tab.
- Redirected legacy operations hashes such as `#communications`,
  `#process-console`, `#forbidden`, and `#governance` to the consolidated
  Operations readout.

## Authority Boundary

D11I is presentation-only. It does not change source ingestion, runtime
execution, broker writes, provider calls, Telegram command behavior,
proof-credit rules, paper-order submission, learning writes, or live-capital
state.

## Acceptance

- `scripts/check_dashboard_d11i_operations_view.js` validates the static shell,
  renderer, CSS, grouped Operations view, legacy panel hiding, cache key,
  public-safe copy, and unchanged authority boundary.
- Existing operations, governance, communications, renderer, responsive, and
  deployment preflight checks must continue to pass.
