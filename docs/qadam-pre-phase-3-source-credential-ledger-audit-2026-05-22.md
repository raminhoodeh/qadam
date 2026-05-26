# Qadam Pre-Phase-3 Source And Credential Ledger Audit - 2026-05-22

This is the Stage P3-2 source and credential ledger audit for `docs/qadam-pre-phase-3-implementation-plan.md`.

## Audit Decision

Stage P3-2 is complete.

The canonical source registry remains stable at 35 sources across 5 pipelines, the 19 promoted adapter contracts remain represented, source and credential blockers are visible, and the live-source checks stay read-only and fail-closed. The stage does not grant signal confidence, risk approval, broker write authority, paper-order authority, live-capital authority, or quantum hardware authority.

Known degraded or blocked data paths are recorded below. They are acceptable for P3-2 because they are explicit, masked, and non-executing. They must be considered before P3-5 shadow intelligence and P3-9 certification.

## Commands Run

Source registry and adapter contract checks:

```bash
.venv/bin/python scripts/check_phase1_data_spine.py
.venv/bin/python scripts/check_source_heartbeat.py
```

Credential and live-source checks:

```bash
.venv/bin/python scripts/refresh_acled_token.py --write --validate-read
.venv/bin/python scripts/check_supplied_credentials.py
.venv/bin/python scripts/check_phase1_live_source_hardening.py --live
```

Secret assignment scan for Git-facing files:

```bash
rg -n "^[A-Z0-9_]*(KEY|SECRET|TOKEN|PASSWORD|PRIVATE_KEY|BEARER|ACCESS_TOKEN|REFRESH_TOKEN)=[^[:space:]]+" docs orchestrator scripts README.md .env.example
```

The scan returned no matches.

## Registry Status

`scripts/check_phase1_data_spine.py` passed.

Key results:

- `source_count=35`
- `expected_source_count=35`
- `pipeline_count=5`
- `promoted_adapter_count=19`
- `missing_credential_source_count=12`
- `deferred_count=3`
- `test_observation_count=35`
- Boundary: read-only deterministic observations only; no signal confidence or execution authority.

`scripts/check_source_heartbeat.py` passed.

Key results:

- Checked at: `2026-05-22T18:09:59.123909+00:00`
- `source_count=35`
- `expected_source_count=35`
- `promoted_adapter_count=19`
- `deferred_count=3`
- `missing_credential_source_count=12`
- Environment map: `data/runtime/data_environment_map.json`

Environment map summary:

- Summary status: ok.
- Pipeline distribution: conflict 5, macro 6, market 9, physical 7, social 8.
- Runtime status distribution:
  - `deferred`: 3
  - `derived`: 1
  - `fallback_only`: 1
  - `live_optional`: 12
  - `local_bridge_required`: 1
  - `ready_to_build`: 7
  - `unavailable_missing_credentials`: 10

Registry-level missing credential sources:

- `wingbits`
- `ais_maritime`
- `space_track_celestrak`
- `un_comtrade`
- `unusual_whales`
- `kalshi`
- `rapidapi`
- `coinglass`
- `chainlink`
- `twitter_x`
- `reddit`
- `github`

Registry-level deferred or unresolved sources:

- `space_track_celestrak`
- `usgs`
- `stock_act`

Note: the 12-source missing credential count covers the full 35-source registry. The live-source hardening check reports missing credentials only for the 19 promoted adapter paths it exercises.

## Supplied Credential Ledger

`scripts/check_supplied_credentials.py` passed.

Provider summary:

- `provider_count=9`
- `live_count=6`
- `degraded_count=1`
- `missing_count=1`
- `deferred_count=1`
- Status distribution: `deferred=1`, `degraded=1`, `live=6`, `missing_credentials=1`
- Report: `data/runtime/supplied_credential_validation.json`

Provider statuses:

- `nasa_firms`: live, configured, events 0.
- `fred`: live, configured, events 3.
- `acled`: degraded, configured, events 1, reason `live_fetch_error:HTTPStatusError`.
- `alpaca`: live, configured, events 1.
- `telegram`: live, configured, events 1.
- `gemini`: live, configured, events 50; model-list only, no text generation.
- `lm_studio`: live, configured, events 2; model-list only, no inference.
- `kalshi`: deferred, reason `deferred_due_to_current_location`.
- `unusual_whales`: missing credentials, reason `useful_missing_batch_a_key`.

Stage decisions:

- Keep Kalshi deferred until location, eligibility, and account-access conditions change.
- Keep UnusualWhales classified as the useful missing Batch A key.
- Keep Gemini and LM Studio validation limited to model-list probes unless a later stage explicitly enables controlled inference.

## ACLED Token Refresh

`scripts/refresh_acled_token.py --write --validate-read` completed.

Key results:

- `refresh_status=refreshed`
- `grant_type_used=refresh_token`
- `access_token_received=True`
- `refresh_token_received=True`
- `expires_at=2026-05-23T18:10:15.323229+00:00`
- `secret_file_updated=True`
- `read_validation_status=degraded`
- `read_validation_status_code=403`
- Report: `data/runtime/acled_token_refresh.json`

Interpretation:

- Local ACLED token plumbing works and refreshed the ignored local credential material.
- The remaining blocker is provider entitlement, account scope, or read permission, because the validation read returns HTTP 403.
- The refreshed secret material is local-only and must not be committed.
- ACLED remains degraded and fail-closed for signal confidence.

## Live Source Hardening

`scripts/check_phase1_live_source_hardening.py --live` passed.

Summary:

- Mode: `live_read_only`
- `source_count=19`
- `live_or_sample_count=9`
- `configured_or_public_count=12`
- `degraded_count=3`
- `missing_credentials_count=7`
- Status distribution: `degraded=3`, `live=9`, `missing_credentials=7`
- Report: `data/runtime/phase1_live_source_validation.json`
- Boundary: read-only; cannot change signal confidence, create trade candidates, send broker orders, or enable execution.

Promoted adapter statuses:

- `gdelt`: degraded, public, events 0, reason `gdelt_http_error:ConnectTimeout`.
- `oref`: degraded, public, events 0, reason `oref_http_or_parse_error:HTTPStatusError`.
- `nasa_firms`: live, configured, events 0.
- `fred`: live, configured with optional key, events 3.
- `rss`: live, public, events 49.
- `acled`: degraded, configured, events 1, reason `live_fetch_error:HTTPStatusError`.
- `unusual_whales`: missing credentials, events 0.
- `polymarket`: live, public, events 25.
- `kalshi`: missing credentials in promoted-adapter live check, events 0; policy status remains deferred due current location.
- `alpaca`: live, configured, events 1.
- `ais_maritime`: missing credentials, events 0.
- `wingbits`: missing credentials, events 0.
- `bls`: live, public with missing auth for private scope, events 1.
- `ecb`: live, public, events 1.
- `un_comtrade`: missing credentials, events 0.
- `sec_edgar`: live, public with missing auth for private scope, events 1.
- `reddit`: missing credentials, events 0.
- `twitter_x`: missing credentials, events 0.
- `telegram`: live, configured, events 1.

Interpretation:

- GDELT, Oref, and ACLED degraded during live reads, but the adapter contract completed and recorded explicit reasons.
- Public-source degradation is not converted into a positive signal.
- Missing provider keys are represented as missing credentials, not runtime crashes.
- Kalshi remains functionally unavailable until the policy and access constraints change.

## Secret Hygiene

Git-facing files scanned:

- `docs`
- `orchestrator`
- `scripts`
- `README.md`
- `.env.example`

The env-assignment scan found no raw provider keys, secrets, tokens, passwords, bearer tokens, access tokens, refresh tokens, or private keys in those paths.

Important local-only files touched or referenced by checks:

- `data/runtime/qadam-secrets.env`
- `data/runtime/acled_token_refresh.json`
- `data/runtime/supplied_credential_validation.json`
- `data/runtime/phase1_live_source_validation.json`
- `data/runtime/data_environment_map.json`

These are runtime artifacts or local credential state and must stay out of Git-facing docs and public cockpit output.

## Documentation Delta

No P3-2 provider requirement changes were discovered that require new changes to `docs/api-specs.md` or `docs/qadam-api-key-acquisition-plan.md`.

The earlier Yahoo Finance documentation amendments remain separate P3-2A capability-review work. Yahoo Finance is not active in this P3-2 ledger and does not change the canonical 35-source count in this audit.

## P3-2 Acceptance Checklist

- All 35 canonical sources are still represented.
- All 5 source pipelines are still represented.
- All 19 promoted adapter paths are covered by sample/read-only contracts.
- Missing, degraded, and deferred source states are explicit.
- ACLED token refresh completed without committing token material.
- ACLED read validation remains degraded with HTTP 403 and is fail-closed.
- Kalshi remains deferred until eligibility/account access changes.
- UnusualWhales remains the useful missing Batch A key.
- Live-source checks are read-only and fail-closed.
- Credential state in docs and public-facing outputs is masked.
- No source can raise signal confidence by itself.
- No broker write, paper order, live capital, or quantum hardware authority is enabled.

## Next Stage

Proceed to P3-2A Yahoo Finance Capability Review.

Do not treat Yahoo Finance as an active market-confirmation adapter until the wrapper, sample-mode check, live-mode check, cache/rate-limit behavior, archive behavior, and public-safe status contract are implemented.
