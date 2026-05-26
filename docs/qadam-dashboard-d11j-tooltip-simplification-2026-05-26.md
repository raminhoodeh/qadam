# Qadam Dashboard D11J - Tooltip Simplification

Date: 2026-05-26

## Purpose

D11J makes dashboard hover help secondary again. The previous tooltip system
was technically complete, but it carried too much onboarding and repeated the
same authority paragraphs in many sections. That made the dashboard feel more
complicated than the actual operating model.

## Changes

- Replaced long `Use it to / Watch for / Boundary` hover cards with the compact
  `Shows / Watch / Limits` contract.
- Added `data-tooltip-contract="compact"` to every dashboard section tooltip so
  the contract is explicit and testable.
- Shortened section help to one summary sentence plus three short rows.
- Kept authority boundaries, but reduced them to local limits instead of
  repeating the full safety rail in every panel.
- Tightened tooltip width and row spacing so hover cards read as quick labels,
  not secondary dashboard cards.
- Updated the dynamic single safety strip renderer to use the same compact
  tooltip contract as the static dashboard shell.

## Acceptance

- Every dashboard tooltip uses the compact contract.
- No tooltip uses the old `Use it to`, `Watch for`, or `Boundary` labels.
- Tooltip body text stays short enough to scan without covering the workspace.
- Essential operating meaning is still visible in the panels themselves; tooltips
  clarify, but do not carry the main onboarding burden.
- Runtime authority, provider calls, broker writes, Telegram command behavior,
  proof-credit rules, and live-capital state are unchanged.
