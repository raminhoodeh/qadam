# Qadam Public Status Bridge Setup

## Purpose

The production dashboard cannot read files from Ramin's laptop directly. Qadam
therefore publishes only the already validated, public-safe
`data/runtime/cockpit-status.json` snapshot over an outbound HTTPS connection.
The receiver cannot call the laptop, run a command, approve research, create an
order, write to Alpaca, or grant proof credit.

## Required Operator Setup

1. Provision a private Vercel Blob store for the dashboard project. The legacy
   Supabase table remains a supported fallback, but is no longer required.
2. Generate two independent high-entropy values: a bearer publish token and an
   HMAC-SHA256 signing key. Do not commit either value.
3. Add these production-only Vercel environment variables to the dashboard
   project:
   - `QADAM_STATUS_PUBLISH_TOKEN`
   - `QADAM_STATUS_BRIDGE_SIGNING_KEY`
   - `BLOB_READ_WRITE_TOKEN` (created by Vercel when the Blob store is linked)
4. Store the same publish token and signing key through Qadam's existing local
   secret mechanism. On macOS they may be stored as Keychain generic passwords
   under account `qadam`, with services prefixed by `qadam:`. The publisher
   defaults to `https://www.qadam.trade/api/cockpit-status-publish`, avoiding
   the apex-domain redirect for signed POST bodies.
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
