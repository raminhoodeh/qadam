# Qadam Dashboard D11B New Navigation Contract

Date: 2026-05-26

## Scope

D11B implements the navigation contract created by the D11A information diet
audit. This stage changes dashboard routing and view ownership only. It does
not redesign individual panels, remove audit data, add provider calls, write to
brokers, send Telegram commands, or enable live capital.

## Primary View Contract

The dashboard keeps five registered views and exposes all five as primary Fund
Manager navigation. Overview remains the first-read surface, while Trades,
Evidence, Reasoning, and Operations are no longer hidden behind diagnostics.

| Order | View | Hash | Purpose |
| --- | --- | --- | --- |
| 1 | Overview | `#overview` | First-read operating state. |
| 2 | Trades | `#trades` | Trade lifecycle, paper account, proof state, and postmortems. |
| 3 | Evidence | `#evidence` | Source health, freshness, quorum, and provenance. |
| 4 | Reasoning | `#reasoning` | Hypotheses, evidence interpretation, priors, and quant posture. |
| 5 | Operations | `#operations` | Runtime, system map, safety counters, communications, governance, and diagnostics. |

The `Executive / Terminal` density switcher is removed. The dashboard now uses
view ownership plus an explicit Diagnostics toggle for deeper debug-only panels.

## Section Ownership

| Section id | D11B owner view | Reason |
| --- | --- | --- |
| `mission-control` | Overview | First-read operating summary. |
| `review-sequence` | Overview, debug-only | Hidden in the default cockpit; available only when Diagnostics is enabled. |
| `trade-layer` | Trades | Canonical trade lifecycle. |
| `money` | Trades | Paper account belongs with trade outcomes. |
| `watching` | Evidence | Sources become evidence quality. |
| `cognition` | Reasoning | Main reasoning workspace. |
| `strategy-manifestation` | Reasoning | Strategy state belongs with reasoning. |
| `worldview` | Reasoning | Private priors are reasoning context. |
| `system-map` | Operations | Full system map is diagnostics. |
| `forbidden` | Operations | Full safety detail is diagnostics. |
| `process-console` | Operations | Runtime event stream is diagnostics. |
| `communications` | Operations | Telegram rail is governance/ops detail. |
| `governance` | Operations | Fund Manager notes and approvals are operational controls unless active. |

## Legacy Hash Redirects

Old links remain usable:

| Legacy hash | New view | Target section |
| --- | --- | --- |
| `#sources` | Evidence | `watching` |
| `#performance` | Trades | `money` |
| `#money` | Trades | `money` |
| `#governance` | Operations | `governance` |
| `#communications` | Operations | `communications` |
| `#system-map` | Operations | `system-map` |
| `#process-console` | Operations | `process-console` |
| `#forbidden` | Operations | `forbidden` |
| `#worldview` | Reasoning | `worldview` |
| `#strategy-manifestation` | Reasoning | `strategy-manifestation` |

## Acceptance

- The visible default dashboard nav has Overview, Trades, Evidence, Reasoning,
  and Operations as primary links.
- Diagnostics reveals debug-only details without owning the core views.
- `Sources` is renamed to `Evidence`.
- `Performance` is no longer a primary nav item.
- `Governance` is no longer a primary nav item.
- The density switcher is absent from HTML, CSS, renderer state, and exported
  browser hooks.
- All existing cockpit sections still have an owning view.
- Legacy hashes resolve to the new owner view and preserve target scrolling
  where useful.
- Asset cache keys changed for both `auth.css` and `dashboard.js`.
- Dashboard authority remains read-only and status-derived.
