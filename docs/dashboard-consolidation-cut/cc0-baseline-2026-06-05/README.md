# CC0 Baseline - Dashboard Consolidation Cut

This folder is the rollback baseline for the Qadam dashboard Consolidation Cut.
It contains exact file snapshots taken before any CC1+ implementation changes.

## Snapshot Files

| Snapshot | Source |
|---|---|
| `dashboard-index.html` | `landing-page-repo/dashboard/index.html` |
| `dashboard.js` | `landing-page-repo/dashboard.js` |
| `auth.css` | `landing-page-repo/auth.css` |
| `cockpit-status.json` | `landing-page-repo/status/cockpit-status.json` |
| `cockpit-status.signature.json` | `landing-page-repo/status/cockpit-status.signature.json` |

## Snapshot Hashes

| File | SHA-256 |
|---|---|
| `dashboard-index.html` | `788ecd047e7c145b22bae5b9f31a87be4b9906a117dc724d0012b9ec56774a80` |
| `dashboard.js` | `85ade43dac875b0381706d015f2cc9ac12396741539e586a7e9fc380ac1a1195` |
| `auth.css` | `ed2f4919e463e652768e8c79bb9a29c876987b9939f456a96ba11a34a41531c9` |
| `cockpit-status.json` | `fa404cbd694b4e3bdebf18bae41688eeffc93ad62afa91c0315850d425178ffc` |
| `cockpit-status.signature.json` | `3b0bd49a7dafc7e8fdeebea3c74964a2ac33c2de8d27023d8cb8ad3e5fc9ab04` |

## Runtime Snapshot

- `generated_at`: `2026-06-06T00:46:39.976154+00:00`
- top-level status keys: `76`
- `mission_control` keys: `20`
- `diagnostics` sibling exists: `false`
- paper authority: `paper_authorized_idle`
- RS-10: `certified_idle`
- RS-10 current blockers: `0`
- paper balance: `GBP 100073.37`
- equity curve points: `20`

## CC0 Baseline Counts

- `legacy-operations-panel` occurrences in `dashboard/index.html`: `4`
- `build*` view-model functions in `dashboard.js`: `17`
- exact default-markup authority-token count in `dashboard/index.html`: `31`

## Rollback

For a dashboard rollback, restore these snapshots to their source paths, export a fresh cockpit status if needed, then run the normal dashboard preflight and production deploy.
