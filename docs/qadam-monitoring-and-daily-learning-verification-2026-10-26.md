# Monitoring And Daily Learning Verification

26 October 2026, Asia/Dubai. Baseline release: `e61a106a`.

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
approval, strategy change, provider call or certification credit. Today's
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
receipt and no-POST deferral from the last two minutes, a separate successful
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
