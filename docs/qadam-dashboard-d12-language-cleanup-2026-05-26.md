# Qadam Dashboard D12 Language Cleanup

Date: 2026-05-26

## Goal

Make the dashboard read like a paper-trading operating console rather than an
implementation log.

## Scope

- Public dashboard shell copy.
- Rendered Overview copy.
- Safety-strip wording.
- User-guide language that describes the default dashboard.
- Acceptance checks that previously preserved old wording.

No runtime authority changed. This pass does not enable provider calls, broker
writes, Telegram commands, learning writes, or live capital.

## Copy Contract

Default dashboard language should use:

- Dashboard
- Paper Trading
- Data Sources
- Strategy
- Risk
- Trade Ideas
- Paper Orders
- Paper Trades
- Account
- Safety Status
- Activity
- System Map

Default dashboard language should not use implementation or leftover wording
such as:

- D9 secure bridge
- System Operating Map
- proof-credit inference
- UI-to-broker path
- LLM-to-broker path
- public-safe cockpit snapshot
- Strategy manifestation
- shadow-only toggles
- Fund Manager read
- Reading rule
- paper states

## Implemented Changes

- Renamed the page title and hero to `Qadam Dashboard` and
  `Paper Trading Overview`.
- Replaced `Single safety strip` with `Safety Status`.
- Replaced broker-path jargon with direct user-facing safety statements:
  `Dashboard cannot place orders`, `AI cannot bypass risk checks`, and
  `Performance proof requires verified records`.
- Replaced Overview filler copy with direct explanations of status, sources,
  strategies, thoughts, trade ideas, and paper capacity.
- Replaced `Eligible setups` with `Potential setups` in the Overview.
- Replaced `Candidates` with `Trade ideas` in the rendered lifecycle labels.
- Replaced `Fund Manager read` with `Current summary`.
- Replaced `Reading rule` with `How to read this`.
- Replaced `Python COO` display copy with `Qadam Orchestrator` or
  `Python records the system`.
- Replaced paper-state wording with `paper trades` or `paper trade states`.
- Updated protected guide wording to match the new Safety Status labels.
- Added `scripts/check_dashboard_d12_language_cleanup.js`.

## Acceptance

The D12 checker verifies:

- The dashboard uses the new cache key.
- The public hero uses paper-trading language.
- Safety Status uses plain safety copy.
- The rendered Overview has the new setup, trade-idea, summary, and map copy.
- Default shell and rendered Overview do not include the banned leftover terms.
- No secrets are exposed by the changed static or renderer files.

## Authority Boundary

D12 is a language and usability cleanup only. Qadam remains paper-only,
read-only from the browser, and live capital remains off.
