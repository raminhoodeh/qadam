# Qadam Defragmentation Cleanup - 2026-06-04

## Status

This pass cleaned user-facing plan drift and dashboard fallback contradictions without weakening execution safety.

## Cleaned

- Added `docs/README.md` as the documentation index so the master implementation plan remains the active source of truth.
- Normalized the dashboard fallback paper-account copy to the current GBP 100,000 paper-account mandate.
- Removed stale fallback wording that implied the old GBP 1,000 paper account was still the account balance. GBP 1,000 remains only a possible single-order/notional risk cap where explicitly stated by backend status.

## Left Intentionally Guarded

- Live capital remains disabled.
- UI-to-broker, Telegram-to-broker, and LLM-to-broker routes remain blocked.
- Quantum hardware submission remains blocked unless a later hardware enablement gate explicitly passes.
- Prediction market writes remain guarded placeholders until a paper/sandbox venue is explicitly approved.
- The active PaperOps route may submit multiple Alpaca paper trades per day only when distinct qualified setups pass risk, idempotency, source-quorum, drawdown, and broker-readiness gates.

## Remaining Defragmentation Work

1. Split `orchestrator/cockpit_status.py` into domain status builders while preserving the public-safe schema.
2. Split `scripts/check_cockpit_status.py` into domain validators and one top-level runner.
3. Add a single provider-state registry for `live`, `degraded`, `missing_credentials`, `deferred`, and `stub` statuses.
4. Retire hidden legacy dashboard panels once all hash/deep-link compatibility checks are updated.
5. Consolidate PT/Q/RS/Phase vocabulary into a public PaperOps lifecycle glossary.
