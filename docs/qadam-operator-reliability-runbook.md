# Qadam Operator Reliability Runbook

Date: 2026-07-27

This runbook covers Qadam's unattended local operator. It does not create trade
authority. All execution remains paper-only and only the canonical guarded
PaperOps wrapper may submit an eligible paper order.

## Read The State Correctly

| State | Meaning | Operator response |
| --- | --- | --- |
| `running` | The LaunchAgent process and lease are alive. | Check readiness separately. |
| `observing` | Required services, build binding, release, and circuits are healthy. | Leave running and monitor the soak. |
| `researching` | Evidence jobs are running under resource locks. | No intervention unless freshness or a circuit deteriorates. |
| `safely_idle` | No eligible research or paper setup is due. | No action; this is healthy. |
| `retrying` | A bounded transient retry is pending. | Wait for its retry deadline. |
| `degraded` | A service circuit or stale dependency prevents a complete loop. | Follow the failure class below. |
| `action_required` | Credentials, disk, schema, or a safety boundary needs review. | Resolve the named request; never clear it blindly. |

Process liveness is not trading readiness. A clean no-trade conclusion is not a
failure, and dashboard publication is not paper-trading authority.

## Canonical Checks

Run these from `/Users/raminhoodeh/Desktop/qadam`:

```bash
.venv/bin/python scripts/check_qadam_state_root.py
.venv/bin/python scripts/check_qadam_artifact_ownership.py
.venv/bin/python scripts/check_qadam_resource_locks.py
.venv/bin/python scripts/check_qadam_artifact_generations.py
.venv/bin/python scripts/check_qadam_operator_service.py
.venv/bin/python scripts/check_qadam_permanent_operator_reliability.py
```

The permanent certification may report `provisional_soak` after implementation.
That is expected until 24 real hours, at least 120 real operator sessions, and a
US market open/closed transition have been observed without a failure. Simulated
or backfilled time receives no credit.

## Safe Drain And Restart

Use the reviewed restart script rather than killing workers independently:

```bash
scripts/restart_qadam_operator_safely.sh
```

It checks the state root, ownership registry, resource locks, and generation
protocol before replacing the installed LaunchAgent. The running build identity
must match the current service contract and rendered LaunchAgent template.

## Failure Classes

### Temporary artifact contention

`EAGAIN`, `EBUSY`, `EDEADLK`, `ESTALE`, or `resource_lock_busy` is classified as
`concurrent_artifact_access`. Qadam retries with a bounded delay. Do not delete
lock files. Kernel locks release when a process exits; stale diagnostic mirrors
are reconciled by `check_qadam_resource_locks.py`.

Pattern scoring additionally pins its templates, universes, eligibility map,
provider-alignment manifest, and alignment records into one content-addressed
input snapshot before reading them. The large alignment file is pinned to its
atomic inode rather than copied on every cycle. A producer transition during
capture is reported as `score_tape_input_snapshot_unstable`, retried three times
inside the scorer, and then handled as temporary artifact contention. If a
content-addressed completed partition genuinely differs from its expected hash,
Qadam records a `research_integrity_hold` and never overwrites it.

After ordinary contention exhausts its initial retry budget, the operator may
attempt at most three same-fingerprint stability revalidations. Each successful
revalidation must execute the real command sequence, and three consecutive
passes are required to close the circuit. Repeated failure remains open for
review rather than retrying forever.

### Provider outage or rate limit

Network timeouts and provider 5xx responses use bounded provider retries. HTTP
429 honors the retry window. Persistent failures become a precise repair request
without changing source trust or creating synthetic evidence.

### Credential action

401/403 or an explicitly missing required credential needs operator review.
Never place secrets in runtime artifacts, Git, Telegram, or dashboard output.

### Parser or schema drift

A changed provider payload fails closed as `parser_schema_drift`. Preserve the
raw response, repair and test the parser, then perform three real revalidation
passes. Do not reinterpret malformed data as an empty successful response.

### Evidence maturity or no trade

Incomplete forward windows, no qualified setup, Akber hold, Router hold, and a
safe no-trade decision are research states, not code defects. They must not open
a defect circuit.

### Low disk

The state-root preflight stops unattended writes below the hard free-space
floor and warns before it. Remove only reviewed caches or old unleased
generations. Never delete current generation pointers, raw provider evidence,
paper lineage, receipts, or the incident archive.

### Public receiver absent

Local dashboard generation remains healthy. The separate
`public_status_publication` service records an optional transport hold when no
receiver is configured. Production publication still fails closed when an
explicit deploy gate requires it.

### Code defect

The affected service circuit opens. Capture the traceback and build identity,
fix and test the defect, then run:

```bash
.venv/bin/python scripts/repair_qadam_operator_circuit.py --service-id SERVICE_ID
```

The circuit closes only after three consecutive executions of the real command
sequence with matching code, environment, and generation evidence. Guarded
PaperOps cannot be repaired through this shortcut.

### Safety violation

Any live endpoint, live-capital request, unauthorized broker import, proof
leakage, or authority mutation fails closed. Stop the operator, preserve the
incident archive, and inspect the policy boundary before restart.

## Incident Preservation

Before a risky repair or migration:

```bash
.venv/bin/python scripts/capture_qadam_operator_incident.py
```

The incident archive is append-only evidence. Do not rewrite old receipts or
manually erase circuits to make the dashboard appear healthy.

## PaperOps Verification

Only after the operator is healthy, run the canonical wrapper exactly:

```bash
.venv/bin/python scripts/run_paperops_autonomous_pass.py
```

Read the result only from
`data/runtime/paperops_autonomous_pass_summary.json`. Safely idle is acceptable
when no setup exists. Never force a setup, staged order, approval, fill, proof
record, or elapsed trial day to clear readiness.

## Reliability Boundary

Qadam cannot guarantee that hardware, networks, providers, the laptop, or future
software will never fail. The permanent repair guarantees a narrower and
testable property: known file races are coordinated; complete generations are
published atomically; temporary failures retry safely; real defects fail closed;
and every recovery is evidenced before readiness returns.
