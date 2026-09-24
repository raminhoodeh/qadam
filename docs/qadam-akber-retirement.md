# Akber Retirement And Qadam Decision Ownership

## Scope

The September 24, 2026 change retires Akber as a current decision authority.
Qadam's strategy-decision policy selects paper setups from canonical research
and current evidence. It does not implement Akber's six-stage checklist, consult
Akber replay thresholds, or infer approval from archived passes.

Missing optional technical, flow, volatility, pricing-gap and quantum confirmation
reduces proposed conviction/size at this stage. Direction, an active entry trigger,
traceable source context, liquidity, invalidation and a paperable expression are
still required. Portfolio risk remains responsible for economics and sizing;
the existing bounded unknown-expectancy discovery route is unchanged.

This is autonomy over paper strategy selection, not unrestricted broker access,
live capital, guaranteed activity, or guaranteed profitability. Position limits,
aggregate and correlated exposure, daily loss, Q-CTRL, exits, reconciliation,
idempotency and the single PaperOps execution owner remain mandatory.

## Contracts

Current artifacts are `qadam_strategy_decision_inputs.jsonl`,
`qadam_strategy_decision_results.jsonl`, `qadam_strategy_decision_summary.json`
and `qadam_strategy_decision_checks.json`. Policy `qadam-autonomous-paper.1`
declares owner `qadam_autonomous` and `akber_authority_retired=true`.

Some V3 packet keys and lineage identifiers retain `akber_` names for wire
compatibility. They are aliases, not Akber evaluations. Current decisions carry
a separate `strategy_decision_id`. Risk and Router require the new owner,
schema and policy; old result files cannot authorize or veto current entries.
Old history remains immutable for audit. Existing positions remain under their
original protection and exit policies, independent of this admission change.

The old command entrypoint delegates to the new service. The retired evaluator
is retained only for historical research and regression tests. The source and
foundry scheduler service is now `strategy_research`; canonical decision
generation is owned by `canonical_tradeability`. Historical replay calibration
is not a prerequisite for this current decision policy.

## Acceptance

- A broker-disabled canonical journey reaches the guarded PaperOps handoff
  without invoking the old evaluator.
- Old Akber approvals cannot satisfy the new risk/Router authority contract.
- Optional missingness changes size; missing essential execution evidence holds.
- Invalid direction, fixture evidence, mixed generations and malformed packets
  cannot be converted into approval.
- Negative economics, duplicate exposure and hard position limits retain their
  separate risk and execution tests.
- No-hypothesis idle is reported honestly and needs no historical Akber replay.

Passing tests demonstrates the contract migration, not a profitable strategy or
an unattended operational soak. Production readiness must be established from
the deployed build, fresh artifacts and resident service health after release.

## Release Verification: 24 September 2026

- Core implementation: `cafcb7d0`, fast-forwarded into the installed checkout
  and pushed to its operating branch. Dashboard candidate: `9bacd527`, pushed
  to frontend `main`; Vercel publication has not passed preflight.
- Full Python suite: 1,436 passed. Changed Python lint passed. The 18-check
  non-homepage regression suite, documentation parity and dedicated policy UI
  tests passed. Whitepaper and a labelled decision-panel fixture were inspected
  in the browser; the authenticated guide was not visually verified locally.
- The broker-disabled canonical journey reached a guarded PaperOps handoff
  without invoking the retired evaluator. Tests reject archived handoffs,
  mixed-generation packets and stale empty foundry state.
- A guarded manual compiler/decision check at `2026-09-24T10:17:09Z` produced
  the current Qadam policy receipt with `akber_authority_retired=true`, zero
  hypotheses and zero broker writes. This is not unattended health evidence.
- launchd refused the operator, watchdog and Telegram service before startup
  with `Operation not permitted`. The denial was present before the cutover.
  The restart did not acquire a live operator lease.
- A fresh canonical PaperOps pass at `2026-09-24T10:19:14Z` remained blocked:
  inactive unattended automation and the existing execution freeze
  `post_paperops_submission_reconciliation_failed:ExecutionOwnerError`.
  It submitted zero paper orders and had no accepted Router handoff.
- Production preflight remains blocked. The freeze was not cleared, the
  deployment gate was not bypassed, and no claim of unattended operational
  readiness or increased trading frequency is made.

Activation still requires resolving the macOS background-start permission,
reviewing the exact execution-owner incident through the reconciliation
contract, obtaining a fresh successful guarded pass, then completing production
preflight and verifying the resident service and public release.
