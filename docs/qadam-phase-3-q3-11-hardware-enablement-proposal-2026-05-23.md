# Qadam Phase 3 - Hardware Enablement Proposal

Date: 2026-05-23

Status: proposal only. No hardware implementation is authorized by this document.

## Purpose

This proposal defines the future approval path for Qadam to move from Phase 3A provider/scheduler readiness into any real quantum-provider interaction.

It does not enable IBM Quantum, AWS Braket, Q-CTRL live calls, provider clients, hardware jobs, schedulers, broker writes, paper orders, execution approvals, or live capital.

## Current Certified Baseline

Phase 3A was certified on 2026-05-23 in `docs/qadam-phase-3-q3-10-phase-3a-certification-audit-2026-05-23.md`.

Certified baseline:

- Q-CTRL credential configured locally, metadata-only, no provider call.
- Qiskit/Aer optional local path absent; classical fallback is active and valid.
- IBM Quantum credential missing.
- AWS Braket credential missing.
- Scheduler disabled.
- Hardware scheduler disabled.
- Hardware submission allowed count: `0`.
- Hardware submitted count: `0`.
- Provider call count: `0`.
- Execution allowed count: `0`.
- Paper order allowed count: `0`.
- Trade candidate created count: `0`.
- Public cockpit exposes sanitized provider/scheduler readiness only.

## Non-Negotiable Locks

These locks remain in force until a later certification explicitly changes them:

- No quantum provider call by default.
- No Q-CTRL live probe by default.
- No Q-CTRL optimization job submission.
- No IBM Quantum Runtime client construction.
- No AWS Braket client construction.
- No hardware backend selection.
- No hardware job submission.
- No autonomous scheduler.
- No queue write.
- No recurring automation.
- No broker write.
- No paper-order submission.
- No live-capital enablement.
- No Head of Quant output may create or advance a trade candidate, risk approval, execution approval, staged order, broker reconciliation write, or paper-submit receipt.

## Approval Roles

Future hardware enablement requires explicit written approval from the Fund Manager before each new authority level.

Approval levels:

1. **Readiness Planning Approval**
   - Allows docs, local checks, and provider SDK import checks.
   - Does not allow provider calls.

2. **Credential Presence Approval**
   - Allows credentials to be added only to `data/runtime/qadam-secrets.env`.
   - Does not allow provider calls.

3. **Metadata Probe Approval**
   - Allows one explicitly flagged metadata-only provider probe.
   - Must not submit a job, create a circuit task, or allocate paid compute.

4. **Sandbox/Simulator Approval**
   - Allows local simulator or provider local simulator checks.
   - Must use deterministic test circuits and no hardware queue.

5. **Single Hardware Probe Approval**
   - Allows one bounded hardware job after a separate certification.
   - Must include explicit provider, device/backend, budget, timeout, cancellation plan, expected result schema, and emergency stop.

6. **Recurring Hardware Scheduler Approval**
   - Out of scope for the first hardware probe.
   - Requires a separate post-probe certification and written approval.

## Required Future Certification Gates

Before any live provider call:

- `./scripts/run_pre_phase3_operational_routine.sh --stage phase3-readiness` passes.
- `./scripts/run_pre_phase3_operational_routine.sh --stage secret-scan` passes.
- Root repo and `landing-page-repo` dirty status are recorded.
- Provider credentials are present locally and never printed.
- Public cockpit remains free of secret values, secret names as values, raw provider responses, local absolute paths, and unsanitized cloud job identifiers.
- Q-CTRL remains classified as error-suppression/optimization support, not a hardware backend.
- IBM/AWS remain blocked unless the specific provider is named in the approval.
- Hardware scheduler remains disabled.
- Broker, paper-order, trade-candidate, and live-capital authority counters remain zero.

Before any hardware job:

- Local simulator check passes through the same output schema.
- Provider metadata probe, if any, was recorded separately and showed no job submission.
- Budget and rate-limit envelope is documented.
- Device/backend selection is named and capped.
- Cancellation/timeout behavior is documented.
- Public-safe job reference policy is documented.
- Emergency stop criteria are documented.
- A new certification file explicitly states that one hardware job is authorized.

## Provider-Specific Proposal

### Q-CTRL

Role: future error-suppression and optimization support.

Allowed later with explicit approval:

- Metadata-only SDK readiness probe.
- Optional optimization-plan dry run that does not submit a provider job.

Still blocked:

- Default provider calls.
- Live probe without `--live-qctrl-readiness` or a future stricter flag.
- Optimization job submission.
- Hardware submission.
- Recommendation authority.
- Signal, risk, execution, paper-order, broker, or live-capital authority.

Required public-safe status:

- `qctrl_configured`
- `qctrl_status`
- `qctrl_live_probe_enabled`
- `qctrl_provider_call_count`
- `qctrl_optimization_job_submitted`
- `secret_value_exposed=false`
- `raw_response_exposed=false`

### IBM Quantum / Qiskit Runtime

Role: future primary hardware backend candidate.

Allowed later with explicit approval:

- SDK import check.
- Credential presence check without printing token.
- Metadata-only service/backend availability probe.
- One bounded hardware job only after a separate certification.

Still blocked:

- Runtime service construction by default.
- Backend selection by default.
- Job submission by default.
- Scheduler or recurring automation.

First hardware-job envelope, if later approved:

- Job type: deterministic test circuit derived from the existing local schema.
- Shot count: smallest provider-supported practical count, capped in the certification.
- Backend: named explicitly in certification.
- Timeout: short fixed timeout.
- Budget: hard cap recorded before submission.
- Output: stored as sanitized metadata and normalized measurement summary only.

### AWS Braket

Role: future secondary hardware backend candidate.

Allowed later with explicit approval:

- SDK import check.
- Credential/profile/region presence check without printing values.
- Metadata-only device availability probe.
- One bounded task only after a separate certification.

Still blocked:

- Braket client construction by default.
- Device selection by default.
- Task submission by default.
- Scheduler or recurring automation.

First hardware-task envelope, if later approved:

- Device: explicitly named in certification.
- Region: explicitly named in certification.
- Task type: deterministic test circuit derived from the existing local schema.
- Shot count: smallest practical count, capped in the certification.
- Timeout: short fixed timeout.
- Budget: hard cap recorded before submission.
- Output: sanitized metadata and normalized measurement summary only.

## Dry-Run And Cancellation Behavior

Every future provider path must support dry-run first.

Dry-run output must include:

- intended provider
- intended backend/device
- intended job type
- expected input schema version
- expected output schema version
- budget cap
- timeout
- cancellation policy
- `provider_call_allowed=false`
- `job_submission_allowed=false`
- `hardware_submission_allowed=false`

Cancellation behavior must be provider-specific before any real job:

- IBM Quantum: document whether a queued/runtime job can be cancelled through the selected SDK and what state transitions are expected.
- AWS Braket: document whether a queued/running task can be cancelled and which final states count as stopped, failed, completed, or unknown.
- Q-CTRL: document that no optimization job is submitted unless a later certification explicitly allows it.

If cancellation cannot be verified safely, the first live probe must be metadata-only and no hardware job may be submitted.

## Budget And Rate Limits

No hardware budget is authorized by this proposal.

Future certification must define:

- maximum spend for the single job
- maximum jobs per run
- maximum jobs per day
- maximum provider API calls per run
- maximum retry count, default `0`
- maximum runtime duration
- maximum queue wait duration

Default proposed first-probe caps:

- provider API calls: `1` metadata probe or `1` hardware submission, not both unless separately approved
- hardware jobs per run: `1`
- hardware jobs per day: `1`
- automatic retries: `0`
- autonomous scheduler: disabled
- recurring automation: disabled

## Public-Safe Job Reference Policy

Future provider job IDs must not be exported raw until a sanitizer is certified.

Public status may expose:

- provider key
- backend/device label if not sensitive
- job type
- local sanitized job reference
- status class
- submitted/queued/completed timestamps rounded or normalized
- output schema version
- counts and authority counters

Public status must not expose:

- API keys
- account identifiers
- organization identifiers
- raw job IDs unless explicitly sanitized
- raw provider responses
- local absolute paths
- cloud console URLs
- raw circuit payloads if they include account or job metadata

Recommended public-safe job reference:

```text
provider_job_ref = sha256(provider_key + raw_job_id + local_salt)[:16]
```

The salt must remain local and uncommitted. The raw provider job ID may be stored only in local ignored runtime files.

## Emergency Stop Criteria

Any future hardware path must stop immediately if any of these occur:

- provider budget cap would be exceeded
- queue wait exceeds certified timeout
- SDK returns an unknown or ambiguous submission state
- duplicate job risk is detected
- cancellation behavior is unknown when cancellation is required
- any authority counter becomes non-zero unexpectedly
- any public-safe scan detects a secret, raw provider response, local path, or unsanitized cloud identifier
- cockpit status cannot export after the probe
- dashboard checks fail after the probe
- Signal Integrity, Strategy Lead, Risk Agent, Execution Policy, broker reconciliation, or paper-submit receipt boundaries change unexpectedly

Emergency stop output must record the blocked reason locally without creating broker, order, execution, scheduler, or hardware retry authority.

## Required Future Files Before Implementation

Before any implementation stage that can call a provider, create a new proposal or certification with:

- exact stage name
- provider
- approval level
- credential posture
- SDK/package posture
- budget
- rate limits
- timeout
- cancellation policy
- dry-run output
- public-safe status schema
- rollback plan
- emergency stop plan
- explicit command to run
- explicit command to verify no authority was gained

## Decision

Phase 3B hardware implementation is not authorized.

Qadam may proceed from Q3-11 to the next master-plan build target with hardware still blocked. Any live provider call, Q-CTRL optimization job, IBM Quantum job, AWS Braket task, provider-mediated hardware submission, hardware scheduler, or recurring automation requires a separate future certification and explicit human approval.
