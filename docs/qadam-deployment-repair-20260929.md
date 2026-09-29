# Dashboard Deployment Repair - 29 September 2026

## Cause

The dashboard is a separate Git repository nested inside the core checkout. Its
repository-local author configuration was absent even though the core had the
correct identity. Dashboard commits therefore used a machine-local email.
Vercel accepted the Git integration deployment but blocked a separate manual
CLI deployment with `TEAM_ACCESS_REQUIRED`. The CLI continued to display
`Building` instead of reporting that terminal blocked state.

## Repair

- Set the dashboard's repository-local name and email to the actual owner's
  authenticated account identity. No global configuration or published history
  was rewritten; no Vercel permission or subscription was changed.
- Added a preflight account/commit-author check for the owner-operated manual
  workflow. It fails before the maintenance guard and lengthy acceptance run.
- Added bounded CLI execution, explicit API polling for the exact commit and
  project, terminal failure handling, and promotion only after `READY`.
- Production creation uses `--skip-domain --no-wait`; a blocked candidate
  cannot change either production alias through this script.
- Removed unconditional `--force`. A timeout requires inspection of the remote
  deployment rather than an assumed cancellation and blind retry.
- Retained mandatory preflight, both-domain release verification, successful
  receipt gating, Telegram idempotency, paper-only execution boundaries and
  unchanged dashboard assets.

Dashboard release commit: `b3f53734c3c76edf6cb9fc0ac76d2db5ed5b4895`.
Core changes only advance the approved dashboard commit and its regression
assertion; they do not alter trading decisions or broker permissions.

## Verification

The deployment guard has eleven regression tests covering identity mismatch,
CLI and Git metadata, terminal failures, wrong project/commit/target, unknown
states, pending-to-ready transitions, request errors, polling deadlines,
command timeouts, and promotion ordering. Live release results are recorded
separately in the runtime deployment receipt after successful verification.
