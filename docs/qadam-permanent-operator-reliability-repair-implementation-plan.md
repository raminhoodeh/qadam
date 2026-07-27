# Qadam Permanent Operator Reliability Repair Implementation Plan

Date: 2026-07-27

Status: Draft for reviewed implementation

Plan ID: `qadam-permanent-operator-reliability-repair-v1`

Short name: `PORR`

Parent plans:

- `docs/qadam-operator-ready-edge-engine-implementation-plan.md`
- `docs/qadam-autonomous-experimental-paper-epoch-implementation-plan.md`
- `docs/qadam-clean-paper-epoch-operational-readiness-implementation-plan.md`

This plan is a focused reliability amendment to OR-18 and OR-19. It does not
create another operator stack, another research pipeline, or another PaperOps
route. It repairs the existing operator service and makes its readiness claim
depend on durable, real-runtime evidence.

## Dynamic Plan Status

<!-- QADAM_PORR_DYNAMIC_STATUS_START -->

| Field | Current Value |
| --- | --- |
| Plan version | `1.0` |
| Plan state | `draft_not_started` |
| Current phase | `PORR-0` |
| Operator service | `running_guarded_paper` |
| Observation ready | `false` |
| Open circuits | `4` |
| Open repair requests | `5` |
| Stale services | `6` |
| Canonical PaperOps summary | `stale_degraded_command_failure` |
| Live capital | `disabled` |
| Dashboard UX restructuring | `forbidden` |

<!-- QADAM_PORR_DYNAMIC_STATUS_END -->

Only a dedicated PORR status updater may refresh the delimited block above.
It may not alter this plan's phases, safety boundaries, acceptance criteria,
authority model, or paper-only posture.

## 1. Executive Decision

Qadam must not be declared observation-ready merely because:

- its LaunchAgent process exists;
- a checker passes once;
- a mocked executor returns success;
- circuit files were manually cleared;
- a dashboard projection refreshed;
- the Alpaca Paper account is reachable; or
- no unsafe broker write occurred.

The permanent repair has four parts:

1. Move mutable research coordination onto an explicit artifact ownership,
   immutable snapshot, and resource-locking protocol.
2. Classify temporary contention, evidence holds, optional publication state,
   code defects, and safety violations differently.
3. Revalidate failed services with their real commands and real files before
   closing a circuit.
4. Require a sustained installed-service soak, including a US market-session
   transition, before `observation_ready=true` can be certified.

The word "permanent" in this plan means the known failure cannot recur through
the same uncontrolled file race or failure-classification path, and future
failures recover or stop with precise evidence. It does not mean software can
never encounter a new provider, operating-system, hardware, or code failure.

## 2. Incident Baseline

### 2.1 Current Runtime State

The 2026-07-27 runtime audit found:

| Area | Current state | Interpretation |
| --- | --- | --- |
| Operator process | Running | The scheduler process is alive. |
| Operational readiness | `true` | Installation and basic safety contracts are present. |
| Observation readiness | `false` | The complete evidence-to-decision loop is not healthy. |
| Open circuits | `4` | Four services are blocked from normal execution. |
| Repair queue | `5` open, `0` critical | One aggregate freshness item and four service failures remain unresolved. |
| Freshness | `7` fresh, `6` stale | The service graph is not current end to end. |
| PaperOps invocation probe | `false` | The installed-service probe has not proved a fresh canonical delegation. |
| Router | No setup and no handoff | There is no current tradeable setup. |
| Paper submit enablement | Blocked pending prerequisites | No qualified setup or staged order exists. |
| Broker writes | `0` | Safety boundaries held. |

### 2.2 Exact Failed Services

| Service | Failing command or boundary | Actual failure | Incorrect consequence |
| --- | --- | --- | --- |
| `source_ingestion` | `scripts/check_qadam_point_in_time_evidence.py` | `OSError: [Errno 11] Resource deadlock avoided` while streaming a source partition | Classified as `code_defect`; circuit opened. |
| `research_evidence_validation` | `scripts/check_qadam_forward_labels.py` | Point-in-time evidence rebuild returned the same `EDEADLK` condition | Classified as `code_defect`; circuit opened. |
| `challenger_research` | `scripts/check_qadam_forward_labels.py` | The same shared evidence path failed during challenger execution | Classified as `code_defect`; circuit opened after repeated attempts. |
| `dashboard_refresh` | `scripts/publish_qadam_public_status.py` | Local dashboard checks passed, but the optional receiver was not configured | Entire dashboard refresh was classified as a code defect. |

### 2.3 Why The 2026-07-21 Repair Was Insufficient

Commit `e6b09c76` correctly:

- placed pattern scoring and challenger research in the same service-level
  concurrency group;
- prevented some score-plane overlap;
- allowed interrupted challenger jobs to be explicitly revalidated;
- improved Alpaca mirror retry behavior; and
- corrected clean-account certification predicates.

It did not:

- define artifact-level read and write ownership across all services;
- protect source-history, point-in-time evidence, labels, scoring, learning,
  daily briefs, and dashboard readers through one shared protocol;
- make source partitions immutable for long-running readers;
- classify macOS file contention as retryable;
- isolate optional status publication from local dashboard generation;
- run real competing readers and writers in the circuit tests; or
- require sustained installed-runtime health after the initial passing
  snapshot.

The previous tests used successful test executors to prove state transitions.
They did not prove that the real command sequence and real research files could
survive sustained concurrency.

## 3. Objectives

This plan must achieve all of the following:

1. Eliminate uncoordinated access to mutable research artifacts.
2. Ensure long-running readers operate against one immutable evidence
   generation.
3. Ensure writers never expose partial files or partial manifests.
4. Make every autonomous writer have exactly one declared owner.
5. Prevent two LaunchAgents or workers from mutating the same logical artifact
   without a shared lock contract.
6. Recover automatically from safe, temporary file contention.
7. Fail closed on real code defects and safety violations.
8. Keep evidence maturity and no-trade states out of the defect circuit path.
9. Keep optional publication failures out of local dashboard health.
10. Close circuits only after real, repeated successful execution.
11. Preserve the existing Qadam dashboard layout and UX.
12. Preserve the guarded Alpaca Paper route and all paper-only boundaries.
13. Produce one canonical reliability certification that cannot pass from a
    momentary or projection-only snapshot.
14. Leave a concise operator runbook for future failures.

## 4. Non-Goals

This plan must not:

- force a strategy, setup, paper order, fill, return, or proof record;
- weaken Akber, Router, risk, Q-CTRL, duplicate exposure, drawdown, source
  quorum, or idempotency gates;
- enable live capital or live broker endpoints;
- grant LLM, quantum, dashboard, Telegram, or operator-service broker
  credentials;
- make the dashboard or Telegram command-capable;
- simulate real elapsed time or backfill the 30-day paper growth trial;
- alter historical evidence to make an edge pass;
- silently edit source trust, risk limits, or execution authority;
- delete incident receipts or rewrite historical audit records;
- replace the current dashboard UX with an older implementation; or
- treat a safe no-trade result as a reliability failure.

## 5. Immutable Safety Invariants

Every PORR phase must preserve these invariants:

| Invariant | Required value |
| --- | --- |
| Capital mode | Paper only |
| Live capital | Disabled |
| Live broker endpoint | Denied |
| Broker-write owner | Canonical guarded PaperOps wrapper only |
| Direct broker imports in operator service | Forbidden |
| Paper order retries | Never automatic outside canonical idempotency logic |
| Dashboard and Telegram authority | Read-only and command-disabled |
| LLM and quantum execution authority | None |
| Proof eligibility | Real closed Qadam-origin paper trades with complete lineage only |
| Backtest and shadow proof credit | Forbidden |
| Simulated elapsed time | Forbidden |
| Autonomous code editing | Forbidden |
| Secret and `.env` mutation | Forbidden |
| Existing dashboard structure | Protected |

## 6. Target Reliability Architecture

### 6.1 Operating Flow

```text
provider or source producer
  -> write immutable partition in staging
  -> flush, fsync, checksum, validate
  -> publish immutable generation manifest
  -> atomically switch current-generation pointer
  -> emit producer receipt

consumer
  -> acquire short shared manifest lock
  -> resolve one generation ID
  -> register reader lease
  -> release manifest lock
  -> stream immutable files from that generation
  -> verify checksums and generation identity
  -> release reader lease
  -> publish output as a new immutable generation

operator service
  -> schedule from dependency generations, not only wall-clock cadence
  -> acquire declared resource claims
  -> execute real command
  -> classify the result
  -> update receipt, circuit, repair, and freshness state
```

### 6.2 Canonical State Root

Mutable hot state must have one canonical local state root, separate from Git
tracking and protected from cloud-placeholder behavior.

Target default on macOS:

```text
~/Library/Application Support/Qadam/
  runtime/
  research/
  staging/
  locks/
  leases/
  archive/
```

Implementation requirements:

- Introduce one non-secret `QADAM_STATE_ROOT` setting with a safe macOS
  default.
- Continue supporting the current repository paths during a reviewed migration
  window.
- Refuse unattended research when the state root is Git-trackable, a cloud
  placeholder, read-only, on a non-atomic filesystem, or below the disk safety
  threshold.
- Detect macOS `dataless`, offline, File Provider, and unsupported mount states.
- Keep public dashboard exports as explicit copies, never as the canonical
  mutable runtime source.
- Do not move secrets or modify `.env` automatically.

If characterization proves the current state root is fully local and reliable,
the migration may retain it temporarily, but the state-root abstraction is
still required.

### 6.3 Artifact Ownership Registry

Create a machine-readable registry declaring every hot artifact:

```json
{
  "artifact": "qadam_point_in_time_provider_alignment.jsonl",
  "logical_resource": "point_in_time_evidence",
  "producer": "source_ingestion",
  "consumers": [
    "pattern_scoring",
    "research_evidence_validation",
    "challenger_research"
  ],
  "write_mode": "immutable_generation",
  "lock_mode": "exclusive_pointer_publish",
  "retention_generations": 3,
  "paper_authority": false
}
```

Rules:

- Exactly one active producer owns each artifact.
- Multi-producer artifacts are forbidden unless a dedicated append-only ledger
  protocol explicitly supports them.
- Every reader and writer must appear in the registry.
- LaunchAgents, manual scripts, daily learning, deployment scripts, dashboard
  exporters, and test utilities are included in the ownership audit.
- Undeclared writes fail preflight.

### 6.4 Resource Claims

Replace service-only `concurrency_group` assumptions with explicit resource
claims.

Initial resources:

| Resource | Examples | Reader mode | Writer mode |
| --- | --- | --- | --- |
| `source_lake` | Provider/source normalized partitions | Shared generation lease | Exclusive generation publish |
| `price_lake` | Price partitions and market snapshots | Shared generation lease | Exclusive generation publish |
| `point_in_time_evidence` | Aligned source-price records | Shared generation lease | Exclusive generation publish |
| `score_plane` | Pattern score tapes | Shared generation lease | Exclusive generation publish |
| `label_plane` | Forward labels and cost models | Shared generation lease | Exclusive generation publish |
| `edge_registry` | Statistical and promotion records | Shared | Exclusive publish |
| `paper_state` | Broker mirror and lifecycle records | Shared read | Canonical owner only |
| `dashboard_projection` | Local public-safe view models | Shared read | Exclusive local publish |
| `public_status_transport` | Signed external status copy | None | Independent optional publish |

Every service declares `reads`, `writes`, and `append_ledgers`. The scheduler
derives compatibility from those claims rather than relying on one string
group.

### 6.5 Global Lock Order

When a job needs more than one resource, it must acquire locks in this order:

```text
source_lake
-> price_lake
-> point_in_time_evidence
-> score_plane
-> label_plane
-> edge_registry
-> paper_state
-> dashboard_projection
-> public_status_transport
```

Rules:

- No reverse acquisition is permitted.
- Lock acquisition is bounded and emits a receipt.
- Long scans do not hold the manifest pointer lock. They hold a lease on an
  immutable generation instead.
- An integration probe may not bypass resource locks.
- Lock metadata records owner PID, service ID, command, acquired time,
  generation ID, and expiry policy.
- Stale locks require owner-process verification before recovery.

### 6.6 Immutable Generation Protocol

Each mutable research plane uses:

```text
resource/
  generations/
    <generation-id>/
      manifest.json
      data-*.jsonl
      checksums.json
      completion.json
  current.json
  staging/
```

Writer protocol:

1. Acquire the resource's exclusive publish lock.
2. Create a unique staging generation.
3. Write new files without modifying a published generation.
4. Flush and `fsync` every file.
5. Validate schema, row counts, provenance, point-in-time fields, and checksum.
6. Write `completion.json` last.
7. Rename staging into the immutable generation directory.
8. Atomically replace `current.json` with the new generation pointer.
9. Release the publish lock.
10. Emit a receipt containing the prior and new generation IDs.

Reader protocol:

1. Acquire the short shared pointer lock.
2. Read and validate `current.json` once.
3. Register a reader lease for that generation.
4. Release the pointer lock.
5. Stream only files listed by that generation's manifest.
6. Confirm checksum and completion marker before using output.
7. Release the lease on success, hold, interruption, or error.

Garbage collection protocol:

- Retain at least three successful generations.
- Never delete a leased generation.
- Never delete the generation referenced by `current.json`.
- Quarantine incomplete staging directories after a safe age threshold.
- Record every deletion in an append-only maintenance ledger.

## 7. Failure Taxonomy And Retry Policy

### 7.1 Required Failure Classes

The operator must distinguish:

| Class | Example | Automatic action |
| --- | --- | --- |
| `evidence_maturing_hold` | No forward labels have matured | Complete with hold; no circuit. |
| `optional_transport_unconfigured` | Public receiver not configured | Complete local service; record optional hold. |
| `concurrent_artifact_access` | `EDEADLK`, `EAGAIN`, `EBUSY`, generation changed | Release, back off, and retry safely. |
| `transient_provider_network` | DNS, timeout, provider 5xx | Bounded retry with jitter. |
| `rate_limit` | HTTP 429 | Respect `Retry-After`; bounded retry. |
| `credential_operator_action` | 401, 403, missing approved key | Open operator-action circuit. |
| `parser_schema_drift` | Provider response changed | Open repair circuit; quarantine affected input. |
| `stale_artifact` | Required producer missed freshness deadline | Run declared safe producer, then revalidate. |
| `disk_resource_pressure` | Low disk, inode exhaustion | Stop writers; preserve readers; operator action. |
| `interrupted_resumable_job` | Sleep, SIGTERM, network loss | Resume from checkpoint. |
| `research_integrity_hold` | Leakage or negative-control breach | Quarantine promotion; continue observation. |
| `code_defect` | Deterministic exception under stable inputs | Stop affected service and write repair request. |
| `safety_violation` | Live endpoint or unauthorized broker write attempt | Hard stop and require explicit review. |

### 7.2 Errno Mapping

At minimum:

- `EDEADLK`, `EAGAIN`, `EBUSY`, and `ESTALE` map to
  `concurrent_artifact_access` when the affected path is a declared research
  artifact.
- `ENOENT` maps to `concurrent_artifact_access` only if a manifest generation
  changed during acquisition; otherwise it is `stale_artifact` or
  `code_defect` according to ownership evidence.
- `ENOSPC` maps to `disk_resource_pressure`.
- Permission errors map to configuration or code defect only after state-root
  permissions and ownership are captured.

Every error record includes the path, operation, errno, resource, generation,
service, owner PID, active lease count, retry attempt, and sanitized traceback.

### 7.3 Retry Rules

- Retries are allowed only for idempotent research reads, immutable generation
  writes, and explicitly resumable workers.
- Use exponential backoff with jitter.
- Retry budgets are persisted across process restarts.
- Paper order submission is never retried by the generic operator retry layer.
- A generation writer that fails before pointer publication leaves the prior
  generation current.
- Exhausted temporary contention moves to a timed half-open circuit, not an
  immediate permanent code-defect circuit.

## 8. Circuit Breaker State Machine

### 8.1 States

```text
closed
-> retry_wait
-> half_open
-> closed

closed
-> open_action_required
-> half_open_after_change
-> closed

closed
-> quarantined_safety
```

### 8.2 Transition Requirements

- `closed -> retry_wait`: temporary failure with retry budget remaining.
- `retry_wait -> half_open`: backoff elapsed and resource dependencies are
  healthy.
- `half_open -> closed`: three consecutive real command successes against the
  current code and artifact generation.
- `half_open -> retry_wait`: the same temporary failure recurs.
- `closed -> open_action_required`: deterministic code, credential, parser, or
  storage action is required.
- `open_action_required -> half_open_after_change`: code hash, configuration
  fingerprint, provider schema, or required artifact generation materially
  changed.
- `quarantined_safety`: only an explicit reviewed operator action can release
  it.

### 8.3 Revalidation Evidence

Circuit closure must never be based on a mocked success executor in production
certification. It requires:

- the actual service command sequence;
- the installed Python environment;
- the configured state root;
- current provider-safe settings;
- current artifact generations;
- resource locks enabled;
- three consecutive successful receipts;
- no unauthorized writes; and
- freshness of all outputs produced by the service.

Unit tests may use mocks to test state-machine branches, but mocked receipts
are explicitly ineligible for runtime readiness.

## 9. Dashboard And Publication Separation

Split the current `dashboard_refresh` responsibilities:

### 9.1 `dashboard_refresh_local`

- Builds local operator and public-safe dashboard projections.
- Runs certification and portfolio parity checks.
- Writes only local generation-based projection artifacts.
- Must not depend on network publication.

### 9.2 `public_status_publication`

- Reads one completed signed dashboard generation.
- Publishes only when a receiver is configured.
- Reports `optional_transport_unconfigured` when absent in normal operator
  mode.
- Uses `--require-configured` only in explicit deployment certification.
- Cannot affect local observation readiness unless publication is explicitly a
  required release gate.

The dashboard may display publication as `not configured`, `fresh`, `stale`, or
`transport issue`, but the existing page structure and UX remain unchanged.

## 10. Implementation Phases

## PORR-0 - Preserve Incident Evidence And Quiesce Writers

### Objective

Create a reproducible incident baseline before any repair changes runtime
state.

### Work

- Record Git commit, dirty worktree paths, Python environment, LaunchAgent
  definitions, process IDs, state-root path, filesystem type, mount flags,
  cloud/File Provider state, and disk availability.
- Archive copies of the current circuit, repair, receipt-index, worker, lease,
  freshness, PaperOps summary, and operator status artifacts.
- Preserve the complete receipt ledger; do not rewrite or truncate it.
- Stop new research writes through a reviewed maintenance window while keeping
  broker state read-only.
- Confirm no active writer remains before migration.
- Do not clear circuits in this phase.

### Artifacts

- `data/runtime/qadam_porr_incident_baseline.json`
- `data/runtime/qadam_porr_process_inventory.json`
- `data/runtime/qadam_porr_filesystem_preflight.json`
- `data/runtime/archive/porr-<timestamp>/`

### Acceptance

- The failure is reproducible or fully evidenced from receipts.
- All incident files have checksums.
- No audit evidence is deleted.
- Paper-only safety remains active.

## PORR-1 - Build The Artifact Ownership And Dependency Graph

### Objective

Identify every writer and reader before changing lock behavior.

### Work

- Statically scan `orchestrator/`, `scripts/`, tests, launchd templates, and
  deployment scripts for runtime and research writes.
- Instrument dynamic writes during characterization.
- Map every service command to artifacts read, written, appended, or published.
- Include the operator service, historical worker, daily learning brief,
  PaperOps wrapper, dashboard exporters, deployment scripts, and manual
  checkers.
- Fail on undeclared or multiple writers.
- Generate a directed producer-consumer graph and detect cycles.

### Code And Contracts

- `config/qadam_runtime_artifact_ownership.json`
- `orchestrator/qadam_artifact_ownership.py`
- `scripts/check_qadam_artifact_ownership.py`

### Runtime Artifacts

- `data/runtime/qadam_artifact_ownership_audit.json`
- `data/runtime/qadam_artifact_dependency_graph.json`
- `data/runtime/qadam_artifact_multi_writer_violations.jsonl`

### Acceptance

- Every hot artifact has one producer contract.
- Every autonomous process is represented.
- Multi-writer violation count is zero.
- Dependency cycles are explicitly resolved or rejected.

## PORR-2 - Introduce The Canonical Local State Root

### Objective

Remove hot mutable state from unsafe or ambiguous filesystem behavior.

### Work

- Add `QADAM_STATE_ROOT` to typed non-secret configuration.
- Implement local filesystem, atomic rename, advisory lock, disk, inode, and
  cloud-placeholder preflight probes.
- Add compatibility resolution for current repo-relative paths.
- Build a resumable state migration tool using copy, checksum, fsync, and
  atomic activation.
- Keep bulk research data ignored and untracked.
- Update LaunchAgent templates to use the resolved state root without
  embedding secrets.

### Code And Checks

- `orchestrator/qadam_state_root.py`
- `scripts/check_qadam_state_root.py`
- `scripts/migrate_qadam_state_root.py`
- `tests/test_qadam_state_root.py`

### Acceptance

- The state root supports locks and atomic rename.
- No hot path is Git-trackable or a cloud placeholder.
- Migration is resumable and checksum-complete.
- Rollback can restore the prior pointer without deleting either copy.

## PORR-3 - Implement Immutable Artifact Generations

### Objective

Make partial and in-place research updates invisible to readers.

### Work

- Implement generation writer, reader lease, checksum, completion marker,
  atomic pointer, and retention APIs.
- Extend or wrap `AtomicArtifactStore`; do not create conflicting write APIs.
- Make incomplete staging generations non-readable.
- Add generation provenance to every output.
- Add safe garbage collection with lease awareness.

### Code And Checks

- `orchestrator/qadam_artifact_generations.py`
- `scripts/check_qadam_artifact_generations.py`
- `scripts/repair_qadam_incomplete_generations.py`
- `tests/test_qadam_artifact_generations.py`

### Acceptance

- Readers observe either the prior complete generation or the next complete
  generation, never a partial combination.
- Process termination at every writer step leaves a valid current pointer.
- Checksums and row counts match.
- Leased generations cannot be removed.

## PORR-4 - Implement Resource Locks And Leases

### Objective

Coordinate services based on the artifacts they use.

### Work

- Add typed resource claims to service definitions.
- Implement shared pointer locks, exclusive publish locks, and reader leases.
- Enforce global lock order.
- Record lock ownership in a public-safe runtime mirror.
- Detect and recover only genuinely stale locks.
- Remove integration-probe lock bypasses.

### Code And Checks

- `orchestrator/qadam_resource_locks.py`
- `scripts/check_qadam_resource_locks.py`
- `data/runtime/qadam_resource_lock_state.json`
- `data/runtime/qadam_resource_lock_events.jsonl`
- `tests/test_qadam_resource_locks.py`

### Acceptance

- Conflicting writers cannot run together.
- Compatible readers can run together.
- No lock-order inversion is possible.
- A killed process releases or safely expires its lease.
- Integration probes respect the same resource protocol.

## PORR-5 - Migrate Source And Price Producers

### Objective

Publish provider and market data through complete immutable generations.

### Work

- Migrate historical source acquisition manifests and normalized partitions.
- Migrate live source refresh outputs.
- Migrate price history and market mirror outputs where they feed research.
- Preserve provider provenance, cursors, publication times, checksums,
  point-in-time status, and cost accounting.
- Ensure resumable workers never mutate a published partition.
- Coalesce no-op refreshes rather than publishing identical generations.

### Primary Existing Modules

- `orchestrator/qadam_source_history_acquisition.py`
- `orchestrator/qadam_point_in_time_evidence.py`
- source heartbeat and live-refresh modules
- Alpaca Paper mirror reader

### Acceptance

- Source and price writers publish through the generation API only.
- Provider interruption leaves the prior generation current.
- Logical duplicate count is zero.
- Point-in-time provenance is unchanged or stronger.

## PORR-6 - Migrate Evidence, Score, Label, Edge, And Learning Consumers

### Objective

Make the complete research chain generation-consistent.

### Work

- Update point-in-time evidence to resolve one source and price generation per
  run.
- Update pattern scoring to bind output to the exact evidence generation.
- Update forward labels to bind to score generation and outcome cutoff.
- Update statistical, nonlinear, quantum, edge, Akber, shadow, Router,
  attribution, and daily-learning readers.
- Refuse mixed-generation joins.
- Record all input generation IDs in output provenance.
- Add exact offending path diagnostics around partition reads.

### Acceptance

- One research result can be reproduced from generation IDs and code hash.
- Mixed-generation count is zero.
- Score-before-label and leakage checks still pass.
- Research holds remain non-executable.
- No downstream artifact advances when an upstream generation is incomplete.

## PORR-7 - Replace Scheduler Concurrency Groups With Resource Scheduling

### Objective

Make scheduler decisions reflect actual shared resources.

### Work

- Extend service definitions with `reads`, `writes`, `appends`, and dependency
  generation requirements.
- Derive runnable compatibility from resource claims.
- Trigger downstream work from new successful generation receipts, while
  retaining cadence deadlines as a safety net.
- Coalesce repeated not-due and unchanged-generation work.
- Prevent manual, scheduled, daily-learning, and worker jobs from bypassing the
  same ownership protocol.
- Preserve the canonical PaperOps delegation boundary.

### Acceptance

- Source ingestion cannot race its evidence reader.
- Pattern scoring, validation, and challenger research cannot race their
  shared planes.
- Dashboard readers never block long research scans unnecessarily.
- Paper lifecycle polling remains independent and read-only.
- No generic scheduler path directly calls a broker.

## PORR-8 - Correct Failure Classification And Retry

### Objective

Ensure safe temporary conditions recover while genuine defects remain visible.

### Work

- Implement the required failure taxonomy and errno mapping.
- Parse structured command envelopes before falling back to text matching.
- Add `concurrent_artifact_access` bounded retry and jitter.
- Treat evidence maturity as successful hold state.
- Treat unconfigured optional publication as an optional hold.
- Persist retry budgets and dependency fingerprints.
- Include path and lock context in repair requests.

### Acceptance

- Injected `EDEADLK` does not become `code_defect` on its first occurrence.
- Repeated deterministic exceptions do become code defects.
- Optional publication absence does not fail local dashboard refresh.
- Evidence maturity cannot open a circuit.
- PaperOps still has no generic retry.

## PORR-9 - Replace Circuit Repair With Real Revalidation

### Objective

Make circuit state reflect demonstrated current health.

### Work

- Implement the specified state machine.
- Require real command execution for runtime repair.
- Require three consecutive successful revalidation receipts.
- Bind revalidation to code hash, environment hash, service contract hash, and
  artifact generation IDs.
- Automatically revalidate safe services after material change or timed
  transient backoff.
- Deduplicate repair requests by service, failure fingerprint, and generation.
- Resolve repair requests only when closure evidence exists.

### Acceptance

- Deleting or editing the circuit JSON cannot certify repair.
- Mocked test receipts cannot close production circuits.
- Safety circuits require explicit review.
- Every closed circuit links to three real successful receipts.
- Recurrent identical failure reopens the circuit with one deduplicated repair
  item.

## PORR-10 - Split Dashboard Refresh From Public Publication

### Objective

Keep the local operating picture healthy when optional publication is absent.

### Work

- Create separate service definitions and receipts.
- Add explicit runtime and deploy modes to the publisher.
- Keep `--require-configured` for production deploy certification.
- Make operator mode report a non-failing `not_configured` state.
- Ensure signed public status still fails closed when a release explicitly
  requires publication.
- Preserve the current dashboard layout, protected routes, and UX assets.

### Acceptance

- Every local dashboard command succeeds with the receiver absent.
- Publication state remains visible and truthful.
- Production deployment still fails when required publication cannot occur.
- No dashboard authority or broker path is introduced.

## PORR-11 - Bind The Installed Service To The Verified Build

### Objective

Prevent code, environment, LaunchAgent, and runtime drift.

### Work

- Record commit, dirty-worktree digest, Python executable, dependency lock
  digest, service-contract hash, state-root identity, and LaunchAgent template
  digest in the service lease and status.
- Refuse readiness when the installed service runs an unverified older command
  or working directory.
- Make installation and restart explicit and idempotent.
- Detect duplicate old LaunchAgents and stale worker PIDs without killing
  unrelated processes.
- Add a controlled drain/restart operation.

### Acceptance

- The status names the exact running build.
- The installed plist matches the reviewed template.
- One operator instance owns the service lease.
- Restart preserves resumable jobs and receipts.
- A dirty worktree is visible and cannot masquerade as a committed release.

## PORR-12 - Build Real Concurrency And Chaos Tests

### Objective

Test the conditions that escaped the previous repair.

### Required Test Families

1. **Artifact atomicity:** terminate writers before and after every publish
   step.
2. **Reader/writer contention:** run source acquisition while point-in-time
   evidence scans the prior generation.
3. **Score/label contention:** run scoring, validation, and challenger requests
   concurrently.
4. **Daily-learning contention:** trigger the scheduled brief while dashboard
   and learning attribution refresh.
5. **Errno injection:** inject `EDEADLK`, `EAGAIN`, `EBUSY`, `ESTALE`, `ENOSPC`,
   and permission errors.
6. **Publication modes:** absent receiver, transport error, 401/403, success,
   and required deploy mode.
7. **Process interruption:** sleep, SIGTERM, hard worker exit, and restart.
8. **Filesystem state:** local APFS, low disk, unsupported/cloud placeholder,
   stale temp generation, and stale lease.
9. **Circuit recovery:** transient retry, code-change revalidation, repeated
   failure, safety quarantine, and real three-pass closure.
10. **Negative authority:** direct broker import, live endpoint, proof credit,
    simulated time, and Telegram command probes.

### Test Requirements

- Use real subprocesses and temporary real files for integration tests.
- Keep unit mocks only for isolated state-machine branches.
- Run with randomized interleavings and deterministic seeds.
- Preserve failed-test artifacts for diagnosis.
- Assert no partial generation is ever observed.

### Acceptance

- The historical incident is reproduced by a characterization test before the
  fix and prevented after the fix.
- At least 1,000 randomized reader/writer interleavings pass.
- All authority-negative probes pass.
- No test relies on simulated market time for final soak credit.

## PORR-13 - Migrate Runtime And Revalidate Existing Circuits

### Objective

Move the installed system onto the repaired protocol without losing evidence.

### Migration Procedure

1. Enter the reviewed maintenance window.
2. Drain workers and verify no active writer remains.
3. Archive current state and checksums.
4. Migrate state root if required.
5. Convert current complete artifacts into generation zero without changing
   content.
6. Validate ownership, checksum, provenance, and point-in-time contracts.
7. Install the updated service definition.
8. Run source ingestion three times with real files.
9. Run evidence validation three times with real files.
10. Run challenger research three times with real files.
11. Run local dashboard refresh three times with publication disabled.
12. Close each circuit only through its real revalidation receipts.
13. Resolve repair requests only from linked evidence.
14. Restart normal cadence scheduling.

### Acceptance

- Four affected services have three real successful receipts each.
- `open_circuit_count=0`.
- Unresolved repair request count is zero.
- Historical receipts remain intact.
- No artifact content changes solely due to migration.
- Broker-write count remains zero during migration.

## PORR-14 - Installed-Service Soak And Market Transition

### Objective

Prove the repaired service under real unattended operation.

### Minimum Soak

- At least 24 continuous real hours.
- Must include one US market close-to-open or open-to-close transition.
- Must include scheduled daily learning.
- Must include source ingestion, price refresh, pattern scoring, validation,
  Akber, shadow, Router, lifecycle polling, dashboard refresh, and one forced
  safe challenger cycle.
- Must include laptop sleep/wake or an equivalent real interruption and
  recovery check.
- Must not use simulated elapsed time.

### Continuous Assertions

- No open or half-open circuits.
- No unresolved repair request.
- No stale required service beyond its declared grace window.
- No mixed-generation research output.
- No duplicate logical writes.
- No unbounded receipt growth from repeated identical skip states.
- No unauthorized order, broker write, proof credit, or live endpoint.
- Dashboard values and runtime state agree.
- Optional publication state is truthful.

### Acceptance

- Soak state is `passed_real_time`.
- All required service receipts are real and fresh.
- Restart recovery is demonstrated.
- Observation readiness remains true across the market transition.
- A safe no-setup/no-order result is accepted as healthy.

## PORR-15 - Permanent Reliability Certification

### Objective

Create one fail-closed certification for this repair and integrate it into
OR-19.

### Create

```text
scripts/check_qadam_permanent_operator_reliability.py
data/runtime/qadam_permanent_operator_reliability_certification.json
data/runtime/qadam_permanent_operator_reliability_checks.json
```

### Required Certification Groups

1. State-root safety.
2. Artifact ownership completeness.
3. Immutable generation integrity.
4. Resource lock and lease health.
5. Failure taxonomy and retry correctness.
6. Circuit real-revalidation lineage.
7. Repair queue resolution.
8. Installed-build identity.
9. Service freshness and dependency generations.
10. Dashboard/publication separation.
11. Real-time soak evidence.
12. Canonical PaperOps freshness.
13. Paper-only negative safety probes.

### Certification States

- `blocked_implementation_incomplete`
- `blocked_migration_required`
- `blocked_open_circuits`
- `blocked_real_revalidation_incomplete`
- `blocked_soak_incomplete`
- `blocked_safety_violation`
- `passed_permanent_operator_reliability`

### Acceptance

The final state passes only when every definition-of-done criterion in Section
14 is true. OR-19 must consume this certification; it may not recreate a weaker
parallel interpretation.

## PORR-16 - Documentation, Dashboard Status, And Operator Runbook

### Objective

Make future failures understandable and recoverable without reading source
code.

### Work

- Add a concise reliability state to the System dashboard without changing
  page structure.
- Show service health, current generation, last successful real run, retry or
  circuit state, and exact operator action.
- Do not display raw tracebacks, secrets, or internal paths publicly.
- Add an operator runbook for:
  - transient contention;
  - provider outage;
  - credential action;
  - parser drift;
  - low disk;
  - stale lock;
  - public receiver absence;
  - code defect;
  - safety violation; and
  - safe service drain and restart.
- Update OR-18 and OR-19 references to this amendment.

### Create Or Update

- `docs/qadam-operator-reliability-runbook.md`
- `docs/qadam-operator-ready-edge-engine-implementation-plan.md`
- dashboard-safe system status view model and checks

### Acceptance

- A non-technical operator can distinguish running, observing, researching,
  safely idle, retrying, degraded, and action-required states.
- No dashboard wording implies that process liveness equals trading readiness.
- Existing dashboard navigation and visual structure remain intact.

## 11. Required Code Change Map

| Area | Primary files | Purpose |
| --- | --- | --- |
| State root | `orchestrator/config.py`, new state-root module | Canonical local mutable storage |
| Ownership | New ownership registry and checker | One writer and declared consumers |
| Generations | `AtomicArtifactStore` integration and new generation module | Immutable publication and reader leases |
| Locks | New resource-lock module | Artifact-level scheduling and lock order |
| Point-in-time evidence | `orchestrator/qadam_point_in_time_evidence.py` | Frozen-generation reads and diagnostics |
| Operator service | `orchestrator/qadam_operator_service.py` | Resource claims, classification, circuits, real revalidation |
| Historical acquisition | Source-history runner and manifests | Immutable provider generations |
| Score and label chain | Score, label, backtest, nonlinear, edge modules | Generation-bound provenance |
| Dashboard | Local view-model checkers | Projection generation without transport coupling |
| Publication | `scripts/publish_qadam_public_status.py` | Optional operator mode and required deploy mode |
| LaunchAgent | Operator and daily-learning templates | Build/state-root identity and single ownership |
| Certification | New PORR checker plus OR-19 integration | Fail-closed durable readiness |
| Tests | Operator, artifact, lock, publication, chaos suites | Real concurrency and recovery evidence |

All implementation work must inspect and preserve current uncommitted changes
in these files. No phase may replace them wholesale from an older commit.

## 12. Test And Verification Matrix

| Layer | Required verification |
| --- | --- |
| Unit | Lock ordering, errno mapping, retry budgets, circuit transitions, pointer validation |
| Contract | Ownership registry, generation schema, receipt schema, state-root policy |
| Integration | Real subprocess source -> evidence -> score -> label -> edge chain |
| Concurrency | Competing readers/writers with randomized interleavings |
| Interruption | SIGTERM, sleep/wake, process crash, stale lease, resume |
| Filesystem | Atomic rename, low disk, unsupported/cloud state, permissions |
| Publication | Missing receiver, transport failure, auth failure, success, required deploy |
| Operator | Installed LaunchAgent, one instance, exact build identity, fresh receipts |
| PaperOps | Fresh canonical pass, safe idle accepted, guarded route only |
| Safety | No live endpoint, direct write, proof leakage, simulated time, or command path |
| UX | Existing dashboard routes, layout, mobile behavior, and public-safe copy preserved |
| Soak | 24 real hours including US market transition and scheduled learning |

## 13. Rollback Strategy

Every phase must be independently reversible.

Rollback rules:

- Never delete the pre-migration state root.
- Keep generation zero and prior current pointers.
- Stop writers before changing state-root or generation pointers.
- Roll back code and service definitions together.
- Restore the prior LaunchAgent only after verifying its working directory and
  safety environment.
- Keep PaperOps guarded and paper-only during rollback.
- Never roll back by restoring an older dashboard UX bundle.
- If reliability cannot be restored, run in explicit read-only degraded mode
  rather than claiming observation readiness.

Rollback is successful only when the account mirror remains reconciled, no
unauthorized write occurred, runtime artifacts are readable, and the degraded
state is plainly reported.

## 14. Final Definition Of Done

This plan is complete only when all statements below are true simultaneously:

1. The canonical state root is local, writable, lock-capable, atomic, ignored,
   and above disk thresholds.
2. Every hot artifact has exactly one declared producer and all consumers are
   registered.
3. Source, price, point-in-time, score, label, edge, learning, and projection
   planes use complete immutable generations.
4. Readers bind to one generation and mixed-generation joins equal zero.
5. Resource locks and leases follow one enforced global order.
6. Integration probes cannot bypass ownership or locking.
7. `EDEADLK`, `EAGAIN`, `EBUSY`, and `ESTALE` recover through bounded safe
   retry and do not become immediate code defects.
8. Evidence maturity and no-trade states do not open circuits.
9. Optional public publication cannot fail local dashboard refresh.
10. Required production publication still fails closed when explicitly gated.
11. Source ingestion has at least three consecutive real successful receipts.
12. Research evidence validation has at least three consecutive real
    successful receipts.
13. Challenger research has at least three consecutive real successful
    receipts.
14. Local dashboard refresh has at least three consecutive real successful
    receipts with optional publication absent.
15. Every circuit closure links to real command, code, environment, and
    generation evidence.
16. `open_circuit_count=0`.
17. Unresolved repair request count is zero.
18. All 13 services are fresh or explicitly healthy-not-due under their
    declared cadence.
19. `observation_ready=true` remains true throughout the real soak.
20. The installed service build, LaunchAgent, Python environment, and status
    contract hashes agree.
21. The 24-hour real-time soak passes and includes a US market transition.
22. A fresh canonical PaperOps pass completes without
    `degraded_command_failure`; safely idle is acceptable when no setup exists.
23. Paper submission remains blocked unless a genuinely qualified setup and
    staged order pass all existing guards.
24. Broker-write, paper-order, and proof-credit counts remain zero throughout
    repair and soak unless the canonical guarded paper route receives a real
    eligible setup.
25. Live capital and live endpoints remain disabled.
26. No dashboard, Telegram, LLM, quantum, or operator-service authority is
    introduced.
27. The existing dashboard UX, route list, mobile behavior, and protected page
    structure pass regression checks.
28. The PORR certification reports
    `passed_permanent_operator_reliability`.
29. OR-19 consumes the PORR result and cannot pass through an older, weaker
    readiness path.
30. The operator runbook explains every remaining intervention state.

## 15. Execution Order

The phases must run in this order:

```text
PORR-0 preserve and quiesce
-> PORR-1 ownership graph
-> PORR-2 state root
-> PORR-3 immutable generations
-> PORR-4 resource locks
-> PORR-5 producer migration
-> PORR-6 consumer migration
-> PORR-7 scheduler migration
-> PORR-8 failure and retry repair
-> PORR-9 circuit revalidation repair
-> PORR-10 dashboard/publication split
-> PORR-11 installed-build binding
-> PORR-12 real concurrency and chaos tests
-> PORR-13 runtime migration and circuit closure
-> PORR-14 real-time soak
-> PORR-15 final certification
-> PORR-16 documentation and runbook
```

PORR-13 must not start before PORR-1 through PORR-12 pass in an isolated test
state root. PORR-15 must not pass before PORR-14 finishes in real elapsed time.

## 16. Operator Outcome

After implementation, leaving Qadam running has a precise meaning:

- source and market evidence refresh through declared owners;
- research jobs read stable evidence snapshots;
- temporary contention recovers without permanent false failure;
- genuine defects stop only the affected work and explain the repair needed;
- optional public publication cannot disable local research;
- the dashboard reports one truthful operating state;
- PaperOps receives only genuinely eligible paper setups through its existing
  guarded route; and
- a no-trade result remains a valid, healthy outcome.

The repair gives Qadam a durable unattended operating substrate. It does not
promise that the available data contains a profitable edge, that an eligible
setup will appear, or that paper returns will be positive.
