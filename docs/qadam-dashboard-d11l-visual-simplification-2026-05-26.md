# Qadam Dashboard D11L - Visual Simplification

Date: 2026-05-26

D11L simplifies the dashboard's visual layer after the D11 view-model refactor.
The goal is not to remove detail from Qadam; it is to reduce the visual noise
around the detail so each primary view reads as an operating section rather than
a stack of competing cards.

## Scope

- Flatten primary dashboard panels into section dividers.
- Make the view switcher and safety strip non-sticky dashboard bands.
- Replace heavy panel shadows and decorative gradient surfaces with quiet
  dark-mode surfaces.
- Keep semantic tone through borders, badges, and compact status accents.
- Keep the same public-safe status fields, renderer contract, and safety copy.

## Acceptance

- `landing-page-repo/auth.css` contains the D11L visual simplification contract.
- `/dashboard/` uses the `20260526-advanced-debug-overview` cache key for the
  stylesheet and dashboard renderer.
- Primary panels use transparent section containers with divider lines instead
  of nested glass-card treatment.
- Review groups, metrics, system-map containers, performance panels, and paper
  account cards share the same quiet surface vocabulary.
- `scripts/check_dashboard_d11l_visual_simplification.js` passes.

## Authority Boundary

D11L is CSS and shell-cache work only. It does not change provider calls,
broker routes, Telegram command behavior, paper-trading permissions, proof
credit, learning writes, or live-capital state.
