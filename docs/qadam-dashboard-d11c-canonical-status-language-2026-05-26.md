# Qadam Dashboard D11C Canonical Status Language

Date: 2026-05-26

## Scope

D11C standardizes how `/dashboard/` explains status. This is a display-language
stage only. It does not change backend status values, source state, provider
calls, broker writes, Telegram command authority, or live-capital state.

## Problem

The old dashboard overused generic words like `online`, `pending`, and
`blocked`. Those terms are useful CSS tones, but they are not precise enough for
Fund Manager reading. In particular, `blocked` mixed together safety stops,
missing setup, waiting for evidence, disabled features, and actual faults.

## Canonical Vocabulary

| Canonical label | Tone | Meaning |
| --- | --- | --- |
| Current | online | Fresh enough to read as the current public-safe state. |
| Read-only | online | Visible for monitoring only; cannot mutate Qadam state. |
| Paper only | online | Paper/demo state only. |
| Live capital off | online | Real-money trading authority is off. |
| Dry run | pending | Simulation or notification test mode without live send/write authority. |
| Waiting for evidence | pending | Normal hold while source, model, risk, or review evidence is not complete. |
| Missing setup | degraded | Required configuration, credentials, source material, or exported status is missing. |
| Degraded | degraded | Available but impaired, stale, partial, or lower confidence. |
| Local only | local-only | Present only in local/private runtime context. |
| Non-executable | blocked | Can inform review, but cannot create or execute a trade action. |
| Safety stop | blocked | A deliberate safety, authority, risk, or policy stop is holding the path. |
| Fault | blocked | Unexpected failure or unsafe condition needing operator review. |

## Renderer Contract

The renderer now exposes a canonical status display layer:

- `CANONICAL_STATUS_LANGUAGE`
- `canonicalStatusRecord`
- `canonicalStatusLabel`
- `canonicalStatusTone`
- `canonicalBadgeText`

The mapping is display-only. Raw backend strings remain available in the
underlying models and detailed diagnostics. Canonical labels are applied to
generic status pills and exact status-token badges, while domain-specific terms
such as `Blocked idea` or `Postmortem due` remain intact.

## Acceptance

- The renderer defines the canonical vocabulary above.
- Generic status pills render canonical labels instead of raw `Blocked`,
  `Pending`, or `Online`.
- Exact raw status-token badges render canonical labels where safe.
- The dashboard keeps existing safety boundaries explicit, including paper-only,
  read-only, broker-write stop, and live-capital-off language.
- Existing status tones and CSS classes remain compatible with previous checks.
- Dashboard authority remains read-only and status-derived.
