# Qadam Public Status Bridge Setup

## Purpose

The production dashboard cannot read files from Ramin's laptop directly. Qadam
therefore publishes only the already validated, public-safe
`data/runtime/cockpit-status.json` snapshot over an outbound HTTPS connection.
The receiver cannot call the laptop, run a command, approve research, create an
order, write to Alpaca, or grant proof credit.

## Required Operator Setup

1. Create the private Supabase table by running
   `ops/supabase/qadam_public_status_snapshots.sql` in the Supabase SQL editor.
2. Generate two independent high-entropy values: a bearer publish token and an
   HMAC-SHA256 signing key. Do not commit either value.
3. Add these production-only Vercel environment variables to the dashboard
   project:
   - `QADAM_STATUS_PUBLISH_TOKEN`
   - `QADAM_STATUS_BRIDGE_SIGNING_KEY`
   - `SUPABASE_URL`
   - `SUPABASE_SERVICE_ROLE_KEY`
4. Store the same publish token and signing key through Qadam's existing local
   secret mechanism, together with:
   - `QADAM_STATUS_PUBLISH_ENDPOINT=https://qadam.trade/api/cockpit-status-publish`
5. Redeploy the receiver code after the Vercel variables are present.
6. Run:

   ```bash
   .venv/bin/python scripts/publish_qadam_public_status.py --require-configured
   .venv/bin/python scripts/check_qadam_public_status_bridge.py
   ```

7. Confirm `published=true`, `digest_parity_passed=true`, and no secret value in
   any runtime artifact or deployment log.

## Security Boundary

- Publication is laptop-to-cloud only.
- Payloads are gzip-compressed, SHA-256 digested, and HMAC signed.
- The receiver verifies bearer authentication, signature, digest, payload size,
  paper-only state, and command-disabled state before storage.
- The public GET endpoint returns only the latest accepted signed snapshot.
- Missing or stale publication is shown explicitly; it never falls back to a
  fabricated fresh state.
