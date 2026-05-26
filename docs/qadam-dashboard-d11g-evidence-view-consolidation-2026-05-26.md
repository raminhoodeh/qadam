# Qadam Dashboard D11G - Evidence View Consolidation

Date: 2026-05-26

## Scope

D11G consolidates the Evidence view so it answers one question: whether current
observations are backed by source quality, factual evidence, and corroboration.

## Changes

- Renamed the visible Evidence panel from Watching / Live source state to
  Evidence / Source reliability and corroboration.
- Removed the duplicate Watching panel brief and separate static source summary
  strip.
- Added one consolidated evidence readout with source, credential, signal
  influence, Yahoo Finance, and Preference/PREF status.
- Grouped detail into four review drawers:
  - Setup evidence.
  - Source reliability.
  - Supplemental context.
  - Factual evidence packets.
- Moved the detailed source ledger into a single advanced diagnostic drawer.
- Added explicit factual-evidence boundaries that prevent sources, evidence
  packets, supplemental context, or the browser UI from creating orders.

## Authority Boundary

D11G is presentation-only. It does not change source collection, evidence
generation, signal integrity, risk policy, broker writes, provider calls,
Telegram command behavior, proof-credit rules, or live-capital state.

## Acceptance

- `scripts/check_dashboard_d11g_evidence_view_consolidation.js` validates the
  static shell, renderer, CSS, grouped Evidence view, cache key, public-safe
  copy, and unchanged authority boundary.
- Existing source, watching, acceptance, renderer, and responsive dashboard
  checks must continue to pass.
