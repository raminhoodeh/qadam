# Qadam Dashboard D11N - Documentation And Guide Alignment

Date: 2026-05-26

D11N aligns the protected User Guide with the simplified D11 dashboard. The
guide now teaches the dashboard as five primary views rather than a long list
of old implementation panels.

## Scope

- Rewrite the first tour around Overview, Trades, Evidence, Reasoning, and
  Operations.
- Explain the single safety strip as the global authority readout.
- Explain the two-level system map: Overview mini-map for quick orientation and
  Operations full map for diagnostics.
- Move old panel names into an implementation-term mapping instead of telling
  users to open them directly.
- Update the daily operating routine so blocked/no-trade states are treated as
  potentially healthy control outcomes.
- Keep the protected guide route, Supabase allowlist behavior, and guide link
  from the dashboard unchanged.

## Acceptance

- `docs/qadam-user-guide.md` uses the same five-view language as `/dashboard/`.
- `landing-page-repo/guide/index.html` uses the same five-view language as
  `/dashboard/`.
- `scripts/check_protected_user_guide.js` no longer enforces obsolete
  standalone panel instructions.
- `scripts/check_dashboard_d11n_documentation_guide_alignment.js` passes.
- The dashboard deployment preflight runs the D11N checker.

## Authority Boundary

D11N changes documentation and guide copy only. It does not change provider
calls, broker routes, Telegram command behavior, paper-trading permissions,
proof credit, learning writes, or live-capital state.
