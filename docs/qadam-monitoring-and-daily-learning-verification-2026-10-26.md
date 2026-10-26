# Monitoring And Daily Learning Verification

Work began 26 October 2026, Asia/Dubai, and verification continued on 27 October.
Baseline release: `e61a106a`. Explicit runtime timestamps below are UTC.

## Demonstrated Fault

The independent readback at about 22:07 Dubai was not healthy: eight services
were stale, the watchdog reported recovery in progress, and the owner was still
on the reviewed build. Canonical broker reconciliation and position protection
were healthy. The earlier green snapshot was not sustained reliability proof.

A live process sample found the dashboard exporter spending most sampled CPU
time in regex-backed secret validation. A separate read-only ten-second profile
identified research-goal journal validation as a hot path. The journal was about
309 MB; `research_goal_summary` read and validated it three times per call, even
when the dashboard requested only eight recent goals. A regression reproduced
the three reads. The roughly 1 GB market-context history is also large, but its
current summary already uses a snapshot and was not changed by this repair.

Holding projection read claims during this work delays conflicting research
writers. Restarting without reducing that workload only repeats the backlog.

## Repair And Boundaries

- The dashboard uses the existing bounded history reader for a maximum of 256
  recent journal records, with a hard 4 MiB byte budget and strict JSON handling.
  Every selected goal still passes the existing semantic and authority validator.
- Counts and labels explicitly describe a recent journal window. The payload
  states that full history was not validated; a bounded view is not a global
  integrity or reliability certificate.
- Default research summaries and explicit store health checks still validate
  complete history, but reuse one validated snapshot rather than rereading it.
  No historical record, active research goal, source, outcome or audit was deleted.
- Malformed, non-object or unsafe recent records and byte-budget exhaustion
  produce degraded results, not healthy empty summaries. Full-history audits
  still detect corruption outside the recent projection window.
- No execution owner, scheduler, database, risk budget, gate, exit rule, provider
  hold or certification requirement was replaced or relaxed.

The bounded lookup took about 0.157 seconds against the actual journal. This is
the goal lookup's measured duration, not the whole dashboard's duration or a
future uptime guarantee.

## Daily Reporting

The existing `qadam-daily-learning-brief` automation was updated through the app.
It remains active at 20:00 Dubai daily in the same project, with the same model,
reasoning effort and local execution environment. No duplicate job was created.

Its report now calls for up to three concrete, source-grounded findings, their
observation times, market relevance, contradictions and uncertainty; lessons
from newly matured independently attributed outcomes; and actual versioned
strategy changes or an explicit unchanged stance. Missing fresh findings or
matured outcomes must be stated, not invented. Catalogue counts and research
scores are not evidence of profitable learning.

The automation retains the exact guarded live wrapper and reconciles its paired
histories and delivery receipts. Existing scheduled Telegram delivery remains
the only sender; the report cannot create another Telegram message, trade,
approval, strategy change, provider call or certification credit. The 26 October
evening brief is confirmed in both histories at 20:04 Dubai, followed by correct
duplicate suppression. No extra send or backfill was performed for this request.

## Verification And Remaining Evidence

Pre-cutover isolated suite: 2,026 passed with 200 existing IBM SDK deprecation
warnings. All seven new regression cases passed, including an explicit guard
that the cockpit requests the bounded path. Four changed Python files passed
Ruff and whitespace checks. The isolated runner disables provider/broker network
access. Post-cutover evidence must come from fresh owner, critic, watchdog,
publication and notification receipts, not these unit-test results.

The existing owner, watchdog, critic, position care and notification services
remain responsible for ongoing operation and recovery. Existing collectors retain
the 24-hour continuity, five real market-session, seven-date legacy and subsequent
20-session economic requirements. A new build or fault cannot inherit elapsed
time from earlier healthy snapshots. No future observation is certified here.

Keep the Mac powered, awake, logged in and connected. Held accounts, unavailable
source access, missing operating bills and lack of off-host disaster recovery
remain explicit limitations. Paper performance and trade frequency do not prove
a repeatable after-cost edge or permanent unattended reliability.

## Follow-Up: Recovery Resource Windows

The first repair passed the complete isolated suite (2,027 tests), was committed
and deployed as `c20d1186`. Subsequent live observation still found stale evidence
producers and an active-discovery dependency circuit. This is not a successful
unattended-reliability sign-off. The explicit release-verification recovery
request was registered through the existing singleton owner, not a second runner.

Recent full entry passes repeatedly returned `deferred_current_market_evidence`.
The specific observed reason was `current_quote_exceeds_approved_notional`: no
broker POST occurred, and the approved notional was not increased. Repeated
entry passes still monopolised paper-state resource windows required by the
evidence producers and delayed the recovery they needed.

The scheduler now permits a narrow, short yield of a new full entry retry when
an existing recovery has waited at least five minutes and an eligible conflicting
input producer remains pending. This requires a verified clean-build full-pass
receipt no older than its normal cadence plus one minute, a no-POST deferral
generated within that pass and no older than five minutes, a separate successful
position-care receipt and output from the last two minutes, and a closed care
circuit. Care must remain selected. Position care itself never yields through
this rule. Unknown, ambiguous, stale or mismatched receipts preserve the normal
execution path. Running jobs are not interrupted; no lock or pre-submit check is
bypassed. The skip creates no recovery success, health or observation credit.

Focused scheduler, owner and checkpointed-recovery verification: 189 passed;
the final isolated full suite passed all 2,048 tests with the same 200 existing
IBM SDK deprecation warnings. Changed-code Ruff and whitespace checks passed.
Regression cases cover the real dispatcher decision as well as failed, blocked,
stale, future, wrong-build and probe care, ambiguous broker submission, expired
entry results, actionable entries and ineligible recovery work. Post-release
health must still be established from fresh actual producer completions and
publication, not by treating this test result or recovery request as proof.

## Follow-Up: Truthful Publication Freshness

During release verification, the standalone public-bridge checker reported fresh
delivery despite a payload generated at 18:02 UTC being resent at 18:49 UTC.
The operator correctly retained the stale-output fault, but the standalone
check looked only at delivery time. A regression reproduced that false green.

The checker now reuses the operator's canonical ten-minute payload-freshness
rule in addition to checking the delivery receipt's own clock. Missing, expired
or future payload timestamps and future delivery receipts cannot pass. Payload
and receipt ages are separately visible. Authentication, signature and parity
requirements are unchanged. Six new timestamp cases and the adjacent recovery
tests passed (93 focused tests). Fresh delivery of stale data is not recovery.
Final full isolated verification including this repair: 2,054 passed with 200
existing IBM SDK deprecation warnings. Changed-code Ruff and whitespace passed.

## Follow-Up: Full Database Audit I/O

Subsequent observation caught an actual lifecycle-worker timeout: the lifecycle
control-plane audit consumed its remaining 229-second command budget while the
service held paper-state resources. Position care consequently missed its
freshness deadline. That miss was not relabelled healthy. The 512 MiB authority
database, its trading records and its integrity requirements were not deleted,
pruned or relaxed.

Read-only ordinary-I/O integrity probes exceeded 8- and 15-second diagnostic
budgets. Memory-mapped reads completed the same full structural check in about
8.9 seconds; the entire structural, foreign-key and business-consistency report
completed in about 2.9 seconds on a read-only probe and 12.2 seconds through the
actual store connection under concurrent load. These are individual measurements,
not guaranteed durations. A separate count-query probe did not justify replacing
counts, batching lifecycle writes or changing authority, so none was changed.

Only the audit connection on macOS now requests a bounded 512 MiB read mapping.
Normal connections retain their previous settings. Full `integrity_check`,
foreign-key checks, semantic consistency queries, WAL, fencing, disk ceilings
and transaction durability remain intact. Tests trace the actual SQL and verify
both the unchanged checks and connection-local scope; non-macOS behavior stays
unchanged. Focused store, bridge and capacity-recovery verification: 51 passed.

[SQLite's memory-mapped I/O documentation](https://www.sqlite.org/mmap.html)
explains the read optimisation and its limitations: performance varies, support
depends on the OS, and mapped I/O errors can terminate the audit process. Such
a failure must remain an actual worker failure, not successful audit evidence.
No broader writer-side mapping or cross-platform optimisation was enabled.
The final isolated suite passed all 2,056 tests, with the same 200 IBM SDK
deprecation warnings. All eleven changed Python files passed Ruff; whitespace
checks passed. Runtime recovery and elapsed observation still need actual
post-deployment evidence.

## Due-Time Regression

A further production-cadence check found that the initial two-minute entry-result
window expired before an unforced two-minute retry became due. The dispatcher
regression now uses `force_due=False` and a genuinely due receipt. It failed
before the correction. The window now covers the normal cadence plus at most
one additional minute; older results resume normal review. Position-care limits,
clean-build bindings, no-POST verification and the ban on skip-as-repair credit
remain unchanged. This is bounded scheduling backpressure, not an entry gate or
permission to ignore new execution evidence.

Final verification after the due-time correction: 191 focused scheduler and
recovery tests and all 2,058 isolated tests passed. The same 200 IBM SDK warnings
remain non-failing. Changed-code lint and whitespace checks passed. Release
verification requests only genuinely stale outputs on the final release; it does
not repeatedly force re-ingestion of already fresh, unchanged source evidence.

## Recovered Dependency Must Wake Its Consumer

The live discovery circuit exposed another concrete recovery fault: its three
failed stability checks had scheduled the next probe for 21:42 UTC, after the
regular market session. New evidence-graph and Router work had completed, but
the future cooldown still prevented the downstream read-only check from running.
The circuit was not manually reset and its failures were not erased.

A changed input fingerprint can now wake only a dependency-unavailable,
automatically recoverable consumer after a real successful upstream completion
since the failure. The completion must be fresh, clean-build and contract-bound,
carry published generations and complete input binding, and have a closed
producer circuit. Consumer prerequisites must still be current. Probe work,
future or stale clocks, missing generations, dirty builds and other contracts
do not qualify. Network, credential, safety and execution-service backoffs are
not bypassed.

One failed check records the new failure context and cannot immediately rearm
from the same old producer completion or an unrelated file touch. Three successful
checks of the same executable are still required to close the circuit. A
read-only evaluation against actual runtime evidence confirmed that the repaired
rule would wake this circuit, without clearing it or placing an order.

New asynchronous completion receipts explicitly record `integration_probe=false`.
Legacy receipts missing that field qualify only with completed-worker provenance,
in addition to the other generation, clock and reviewed-build requirements.
An explicit null or a missing worker identity is not accepted. Isolated tests
cover the ordinary dispatcher, three-check closure, repeated failure, legacy
receipt provenance and the protected failure classes. No production fault was
injected and no market-session or profitable-learning credit was manufactured.

Final verification including recovered-dependency wake-up: 212 focused tests
and all 2,079 isolated tests passed, with 200 unchanged IBM SDK deprecation
warnings. All twelve changed Python files passed Ruff; whitespace checks passed.

## Keep Telemetry File I/O Out Of The Execution Writer Slot

Continued live observation found a different failure: the execution lease
heartbeat received `database is locked` inside `BEGIN IMMEDIATE`. Position care
had written a completion artifact, but its lease keeper correctly failed closed;
that artifact was not treated as a successful fenced service receipt. The
existing scoped recovery subsequently earned successful care checks and closed
the circuit. No lease error was ignored, token replaced or TTL increased.

Inspection and an isolated reproduction identified an avoidable contention path:
telemetry retention selected rows, compressed archives, verified them and fsynced
files while holding the same database writer needed by execution heartbeats.
A second lease-style writer failed during that archive callback. Even a
capacity-warning pass with no eligible rows unnecessarily took the writer lock.
This establishes a real defect, not proof that it was the only live lock holder.

Selection and durable archive verification now happen before a short
compare-and-delete transaction. Only verified immutable telemetry rows are
removed; trading, research, idempotency, position and ownership records are not
pruned. A concurrent compactor's already-archived missing rows are idempotent,
but a surviving changed record rolls the deletion batch back. No-eligible-row
passes do not acquire a database writer. Existing archive hashes, crash recovery,
retained recent rows and each service's latest row are preserved.

All 33 focused capacity/recovery tests passed, including heartbeat-writer access
during archive I/O, concurrent compaction, changed-row rollback, corrupt archives
and retention without raising capacity. This change does not make arbitrary
future database contention or infrastructure failures impossible.

Final code verification after the telemetry repair: all 2,083 isolated tests
passed, with 200 unchanged IBM SDK deprecation warnings. All fourteen changed
Python files passed Ruff and whitespace checks. The local calendar rollover was
real; no certification session, observation date or brief delivery was backfilled.

## Align Independent Monitors With Canonical Recovery And Publication Truth

Final monitoring checks found two inconsistent definitions of current state.
The fast watchdog accepted an abandoned previous-build full-heal request because
its service-contract hash still matched. The actual operator correctly rejected
that request's old Git identity, but the watchdog could interpret its dead former
owner as grounds to restart the healthy successor. The watchdog now delegates
request eligibility to the operator's existing canonical validator, including
build identity, allowed services and non-future request age. Old requests remain
visible as obsolete; their history is not deleted or marked successful. Genuine
same-build stalled requests and active-worker restart protection are retained.

The independent critic also trusted a recent signed-publication delivery time
without checking the age of the payload. It now uses the same 600-second payload
rule as the operator and standalone bridge checker, retaining receipt clock and
digest-parity requirements. Its existing repair route rebuilds the dashboard
before publishing; it does not simply resend stale content. Payload age and
currentness are explicit diagnostic fields. Tests reject stale, missing and
future payloads and stale/future receipts, preserve the exact freshness boundary,
and confirm the existing repair route. All 88 focused critic/watchdog tests and
changed-code Ruff checks passed before the full-suite rerun.

These repairs do not expand trading, provider, risk or messaging authority. The
existing daily-learning automation remains active at 20:00 Dubai, using its
existing guarded wrapper and sender. Its report now distinguishes newly observed
insights, contrary evidence, newly matured learning and actual strategy changes
from old findings or an unchanged stance. It must explicitly report when no new
insight or measured lesson exists, rather than manufacture daily progress.

Final full isolated verification: 2,094 tests passed with 200 unchanged IBM SDK
deprecation warnings. All sixteen Python files changed from the baseline passed
Ruff; whitespace checks passed. The unchanged production dashboard release
verified all thirteen routes and 130 lifecycle stages. Actual new-build runtime,
signed-payload freshness and broker truth still require post-cutover checks;
these tests are not elapsed observation or profitability evidence.
