# Execution Owner Expiry Recovery

## Incident Review: 24 September 2026

The canonical execution hold originated on 15 September, not during the
24 September LM Studio outage. The operating ledger records:

- Owner `paperops-autonomous-pass:92614:b6db03d33078` acquired its lease at
  `2026-09-15T07:08:25.075401+00:00`, expiring at `09:08:25.075401+00:00`.
- Post-pass reconciliation recorded an untyped `ExecutionOwnerError` freeze
  at `2026-09-15T09:16:46.139092+00:00`.
- The same owner released its lease at `09:16:53.235104+00:00`, with no
  intervening ownership event.

The timing supports lease expiry. The old handler discarded the exception's
specific check, so the historical record alone does not prove which ownership
check failed. Automatically treating every `ExecutionOwnerError` as retryable
would be unsafe: it also includes missing leases, wrong tokens and conflicts.

## Repair Contract

New failures preserve a narrow typed reason only when the sole failed owner
check is `lease_fresh`. They remain frozen until a new valid owner obtains two
distinct, fresh broker observations with agreeing position-protection digests.
The reliability critic can request this normal guarded reconciliation path.
It cannot edit the ledger directly or retry an order submission itself.

Legacy untyped incidents require an explicit operator-reviewed command:

```sh
.venv/bin/python scripts/repair_qadam_owner_expiry.py \
  --review-incident-at <exact-execution-state-timestamp>
```

The command takes the canonical pass lock and execution lease, performs two
broker GET refreshes, and checks the exact incident and journal evidence. Both
readbacks must be fresh, distinct, passed and flat: no broker positions, broker
open orders or canonical active orders. Missing or conflicting lease history,
subsequent different holds, stale observations and unknown ownership errors
cannot be silently cleared. Recovery records the supporting journal and
reconciliation IDs transactionally. No order submission command is invoked.

The reviewed September incident was recovered with these reconciliations:

- `reconciliation:b44141ef0b7371dac9568431`
- `reconciliation:a70a26b4748921a819470d94`

Both came from `owner-expiry-review:49662`. Broker writes: zero. Historical
orders and evidence were not deleted or relabelled.

## Separate Startup Blocker

The macOS kernel reports `xpcproxy` denied access to Qadam's launch-agent
stdout logs under Desktop. The failure occurs before the operator starts.
Restarting PostgreSQL and loading Gemma restored those dependencies but did
not resolve this OS-level denial. Background activity is enabled in Settings;
the visible Python Desktop-folder permission is also enabled.

The user approved changing the five installed launch agents' log destinations
to `~/Library/Logs/Qadam`. The installers and template parity check now use
that path. Original launch-agent definitions were preserved in
`~/Library/LaunchAgents/qadam-before-log-repair-20260924`; old logs remain in
place. No macOS security settings or permissions were changed.

Resident verification also exposed a stale-report recovery gap. The open-market
coordinator was skipped outside market hours even when explicitly requested by
the healer to refresh its derived reports. The recovery receipt then counted
that calendar skip as success. Recovery now runs this coordinator only with
`--no-paperops` outside market hours and requires a completed work receipt;
ordinary scheduling still waits for the market. Tests cover both open and
closed circuits and refuse the exception if the broker-disabled flag is absent.

Restored startup and fresh service receipts are operational evidence, not a
guarantee against future outages. Unattended reliability certification still
requires the configured real-time soak; no elapsed time is simulated.
