# Qadam Operator Reliability Runbook

Date: 2026-09-02

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
.venv/bin/python scripts/check_qadam_hedge_fund_team_health.py
.venv/bin/python scripts/check_qadam_self_healing_recovery_coverage.py
.venv/bin/python scripts/check_qadam_reliability_critic.py
.venv/bin/python scripts/check_qadam_reliability_watchdog.py
.venv/bin/python scripts/check_qadam_telegram_readonly_interface.py
```

The permanent certification may report `provisional_soak` after implementation.
That is expected until 24 real hours, at least 120 real operator sessions, and a
US market open/closed transition have been observed without a failure. Simulated
or backfilled time receives no credit.

## Independent Reliability Critic

`com.qadam.reliability-critic` runs one bounded review at load and every three
hours thereafter. It is independent from the minute-level operator loop and
never owns execution. Each pass reads the operator lease, service freshness,
circuit breakers, repair queues, transactional control-plane reconciliation,
Router explanation, guarded PaperOps summary, and market-session state. Before
the critic classifies the system, it also requires a current hedge-fund team
receipt: real Local Gemma inference, real Gemini inference, current or
healthy-idle quant review, and all ten trading stages mapped to their registered
services.

The team receipt deliberately distinguishes provider connectivity from actual
work. A reachable endpoint, configured key, dry contract, fixture, or queued
packet does not count as completed model analysis. The Local Research Analyst
must produce an accepted live inference receipt and the Strategy Lead must
produce an accepted Gemini assessment for the current three-hour cycle.

The critic distinguishes four healthy outcomes:

- `healthy_idle_explained`: no setup advanced, and the Router supplied a typed reason.
- `healthy_observing`: the pipeline is fresh with no unexplained stall.
- `healthy_actionable_waiting_market_session`: a setup is ready for a real market window.
- `healthy_actionable`: a setup is ready during the current market session.

It may refresh read-only projections, restart the reviewed operator LaunchAgent
when the owner is genuinely down, or revalidate a non-PaperOps idempotent
service circuit. It may also restart LM Studio and reload the already configured
local model, then rerun the probe. It verifies telemetry twice after any repair. A code defect,
credential issue, safety violation, disk fault, broker disagreement, policy
change, or persistent failure creates a deterministic repair packet instead of
being changed silently.

The critic cannot invoke PaperOps, submit or cancel orders, change risk limits,
approve strategies, edit code, alter secrets, send Telegram commands, grant
proof, or enable live capital. A lack of trades alone is never treated as a
runtime failure.

Install or refresh the schedule explicitly:

```bash
scripts/install_qadam_reliability_critic_launch_agent.sh --load
```

Inspect one pass and its independent check:

```bash
.venv/bin/python scripts/run_qadam_reliability_critic.py --repair
.venv/bin/python scripts/check_qadam_hedge_fund_team_health.py
.venv/bin/python scripts/check_qadam_reliability_critic.py
```

Canonical artifacts are:

- `data/runtime/qadam_reliability_critic_status.json`
- `data/runtime/qadam_reliability_critic_history.jsonl`
- `data/runtime/qadam_reliability_critic_repair_packet.json`
- `data/runtime/qadam_reliability_critic_checks.json`
- `data/runtime/qadam_hedge_fund_team_health.json`
- `data/runtime/qadam_hedge_fund_team_health_checks.json`
- `data/runtime/qadam_frontier_strategy_lead_assessments.jsonl`
- `data/runtime/qadam_team_health_telegram_status.json`

## Five-Minute Reliability Watchdog

`com.qadam.reliability-watchdog` runs independently every five minutes. It does
not perform research or trading work. It verifies that every service in the
operator registry has an explicit bounded recovery mode, reads the current
operator lease and service classification, and distinguishes four conditions:

- Healthy monitoring, where no action is needed.
- A full heal queued behind a live operator cycle.
- A full heal making progress, including a legitimate bounded worker.
- A genuinely stopped owner, stalled request, or repairable service failure.

For a repairable service failure the watchdog wakes the independent critic
instead of duplicating its repair logic. If the singleton operator is absent,
or if a full-heal request has exceeded the declared timeout with no live worker,
the watchdog restarts the reviewed operator LaunchAgent. A ten-minute action
cooldown prevents restart loops. It never kills a live resumable worker merely
because a request is old.

Install or refresh it explicitly:

```bash
scripts/install_qadam_reliability_watchdog_launch_agent.sh --load
```

Inspect it with:

```bash
.venv/bin/python scripts/run_qadam_reliability_watchdog.py --report-only
.venv/bin/python scripts/check_qadam_self_healing_recovery_coverage.py
.venv/bin/python scripts/check_qadam_reliability_watchdog.py
```

Canonical artifacts are:

- `data/runtime/qadam_self_healing_recovery_coverage.json`
- `data/runtime/qadam_reliability_watchdog_status.json`
- `data/runtime/qadam_reliability_watchdog_history.jsonl`
- `data/runtime/qadam_reliability_watchdog_checks.json`

Every `ServiceDefinition` must declare a `recovery_mode`. Registration fails
closed if its retry class, duration, provider budget, PaperOps relationship, or
command sequence is incompatible with that mode. The operator, critic, checker,
and permanent certification all use this one contract. A service can therefore
no longer be monitored without also having a validated recovery disposition.

Full-heal requests publish `requested`, `in_progress`, and terminal status,
along with the current phase, current services, completed services, owner PID,
and progress timestamp. After a process restart, an `in_progress` request stays
eligible for idempotent resumption on the same code and service contract.

## Telegram Inspection Interface

The configured group can inspect Qadam and the independent reliability critic
without gaining operating authority:

| Query | Readout |
| --- | --- |
| `/status` | Operator, hedge-fund team, ten-stage pipeline, PaperOps, portfolio, circuits and repairs. |
| `/portfolio` | Paper equity, P&L, cash and current holdings. |
| `/trading` | Latest Router and guarded PaperOps decision state. |
| `/patterns` | Highest-ranked current research patterns. |
| `/health` | Gemma, Gemini, quant, ten-stage pipeline, service freshness, circuits and repairs. |
| `/repairs` | Reliability critic, team blockers and repair queue. |
| `/help` | The read-only command list. |

Install or refresh the 30-second group interface and register its scoped bot
menu with:

```bash
scripts/install_qadam_telegram_readonly_interface_launch_agent.sh --load
.venv/bin/python scripts/check_qadam_telegram_readonly_interface.py
```

The service shares the existing `getUpdates` stream under one non-blocking file
lock. A failed response remains retryable and visibly degrades the communication
interface, but it does not grant authority or block an otherwise valid PaperOps
pass. Telegram cannot trigger a repair, approve a setup, submit an order, change
risk, edit code, reveal secrets, grant proof, or enable live capital.

The reliability critic also sends one concise proactive health update per
three-hour slot. It reports whether the four automated team roles completed
their work, how many of the ten trading stages are healthy, whether a bounded
LM Studio recovery ran, and the current typed reason for activity or inactivity.
Successful sends are deduplicated; failed sends remain eligible for retry.

To stop only this query service:

```bash
scripts/uninstall_qadam_telegram_readonly_interface_launch_agent.sh
```

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

Retention maintenance and live disk pressure are separate states. A leased
generation or a bounded cleanup failure is recorded for repair, but it does not
freeze unrelated write services while the live filesystem remains above its
free-space and used-ratio recovery thresholds. Genuine live disk pressure still
blocks all write and append services until those thresholds recover.
Cloud-offloaded research placeholders are never hydrated by routine retention;
their cleanup remains a supervised maintenance operation.

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
every registered service has a validated recovery disposition; stalled healing
is detected independently within a five-minute schedule; and every recovery is
evidenced before readiness returns. Permanent certification also remains blocked
until the watchdog is installed, loaded, fresh, and healthy.
