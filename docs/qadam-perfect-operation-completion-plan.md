# Qadam Perfect Operation Completion Plan

Date: 2026-07-06

## Purpose

This plan defines the remaining development required for Qadam to reach an
operationally complete state.

In this document, "perfect" does not mean guaranteed profit, guaranteed paper
trades every day, or a system that never waits. Markets do not permit that
honestly.

"Perfect" means:

- Qadam is continuously ingesting the intended data universe.
- Qadam has enough point-in-time historical memory to test whether signals led
  prices.
- Qadam can discover, document, validate, reject, shadow-test, or route
  patterns across the whole data universe and trading universe.
- Akber's filter receives complete practical trading inputs instead of failing
  because evidence is missing.
- Router can produce a final decision for every setup.
- PaperOps can receive only clean paper-review candidates through the guarded
  Alpaca Paper route.
- The dashboard and Telegram explain the system in human language.
- The system remains paper-only, fail-closed, public-safe, and unable to create
  live-capital authority.
- A final certification command can answer whether the whole system is running
  as designed.

The target answer after completion is:

```text
Yes. Qadam is operationally complete and running as designed. It is ingesting,
testing, routing, explaining, and safely paper-trading only when evidence and
gates permit. There are no unresolved system blockers.
```

If there is no valid market setup at that moment, the answer should still be
"yes" only if Qadam can clearly show that it is waiting because the market has
not produced a qualified setup, not because the system is stale, degraded, or
missing evidence.

## Current Baseline

Latest verified local checks showed:

- Dashboard view model: `qsase_dashboard_visibility_ready`.
- Cockpit status: `cockpit_status_check=ok`.
- Evidence quality engine:
  `qsase_evidence_quality_ready_with_tradeability_holds`.
- Evidence records: `5`.
- Paper-review candidates: `0`.
- Held-for-evidence records: `5`.
- Validated edges: `0`.
- Akber passes: `0`.
- Akber holds: `14`.
- Akber missing-context records: `16`.
- Router paper-review candidates: `0`.
- Router holds: `14`.
- Source freshness ratio from the checker: `1.0`.
- Historical complete forward-window ratio from the checker: `0.0132`.
- Historical missing windows from the checker: `6150`.
- Paper orders created by QSASE: `0`.
- Broker writes created by QSASE: `0`.
- Live capital enabled: `false`.

The main blocker is not execution authority. The main blocker is evidence
quality.

Qadam can safely show its state and preserve the guarded PaperOps boundary, but
it does not yet have enough complete source-price evidence for Akber and Router
to pass current patterns into paper-review candidacy.

## Non-Negotiable Boundaries

Every phase in this plan must preserve:

- `live_capital_enabled=false`.
- No live broker endpoints.
- No live credentials loaded.
- No secrets or `.env` edits.
- No forced trades.
- No backfilled or simulated elapsed time in the 30-day paper growth trial.
- No paper proof ledger credit from backtests, shadow runs, synthetic data, or
  dashboard artifacts.
- No dashboard or Telegram command authority.
- No LLM, quantum, dashboard, Telegram, or source adapter direct broker writes.
- Alpaca Paper submission only through guarded PaperOps.
- Q-CTRL paper consultation hold unless its recorded gate passes.
- Multiple paper trades per day only when each setup is distinct, lineaged,
  idempotent, risk-approved, source-quorum-clean, and routed through guarded
  Alpaca Paper.

## Definition Of Done

Qadam is operationally complete only when all of the following are true.

### System Freshness

- Every required source category has a scheduled ingestion job.
- Every source has freshness, trust, outage, latency, and quorum contribution.
- Source freshness target during active market windows is at least `95%` for
  required sources.
- Optional sources can be degraded without blocking, but their degradation is
  visible and not counted as quorum.
- No required source silently reports as connected when it is stale.

### Historical Memory

- Point-in-time source-price memory exists for all currently traded or watched
  core instruments.
- Complete forward-window coverage reaches at least `80%` for instruments that
  can produce paper-review candidates.
- Leakage checks pass.
- Every source event used in a test has provenance and an observed timestamp.
- Backtests and replays cannot advance the 30-day paper growth trial or create
  paper proof ledger credit.

### Pattern Recognition

- Qadam searches across the full source universe and full trading universe
  before mapping patterns into strategy families.
- Linear tests produce explicit hit rate, expectancy, drawdown, false-positive,
  and regime-control results.
- Nonlinear and quantum-inspired tests produce usefulness scores, ambiguity
  labels, and fallback labels.
- Pattern records clearly distinguish found, documented, validated,
  shadow-ready, paper-review candidate, and rejected.
- At least one validated-edge pathway can graduate when evidence is sufficient.

### Akber Filter

- Akber receives complete practical confirmation inputs:
  volatility context, technical confirmation, volume or flow evidence, pricing
  gap evidence, catalyst strength, invalidation, and paperability.
- `akber_missing_context_count` is `0` for every setup that reaches Router.
- Akber can pass, hold, or veto based on evidence rather than missing fields.
- Akber pass remains non-execution authority.

### Strategy And Router

- Strategy Foundry only converts validated patterns into hypotheses.
- Every hypothesis has source-price lineage, Research Goal lineage, instrument
  mapping, invalidation, risk concept, strategy family, and paperability.
- Router produces exactly one final state per setup:
  reject, watchlist, shadow-only, hold, repair-requested,
  blocked-safety-boundary, or paper-review candidate.
- Router output alone cannot create an order.
- A paper-review candidate exists only after evidence, Akber, source quorum,
  paperability, duplicate exposure, risk, drawdown, and Q-CTRL checks are clean.

### PaperOps

- PaperOps receives only upstream handoff records, not raw patterns.
- Handoff records preserve candidate identity, Research Goal lineage,
  idempotency material, source quorum, Akber state, quantum state, risk state,
  duplicate exposure, drawdown, and guarded Alpaca Paper route state.
- The canonical PaperOps wrapper can run without degraded command failure.
- Paper lifecycle state is always explained:
  submitted, accepted, filled, open, stale, cancel/replace needed, closed, or
  postmortem due.
- No order sits in ambiguous state without lifecycle explanation.

### Learning

- Every trade, hold, rejection, missed setup, shadow result, and system defect
  is attributed to source, model, quantum review, Akber, Router, PaperOps, risk,
  execution, and route state.
- Source-trust, strategy-weight, Akber-threshold, and model-weight updates are
  proposals only.
- Learning can explain whether Qadam improved because a component helped,
  blocked correctly, blocked incorrectly, or lacked enough evidence.

### Dashboard And Telegram

- Dashboard order remains:
  portfolio value, current holdings, trading history, Hedge Fund Team, source
  intelligence network, trading universe, strategy universe, pattern
  recognition findings, Akber filter state, trade candidates, Router/PaperOps
  decision, learning ledger.
- Source Intelligence Network keeps category cards with expandable granular
  sources and APIs.
- Trading Universe appears before Strategy Universe and shows categories plus
  individual watched/tradable instruments.
- Pattern sections explain:
  detected signal, market affected, evidence, what Qadam thinks, what confirms
  it, what blocks the trade, and next action.
- Telegram summaries are short, specific, deduped, review-only, and unable to
  create commands or trades.
- Anti-slop checks reject duplicate, generic, repetitive, or harsh wording.

### Operations

- GitHub push works securely without embedding tokens in chat or shell history.
- Production deployment has preflight, deploy receipt, live alias verification,
  and dashboard/status parity checks.
- A self-healing loop distinguishes refreshable runtime defects from code
  defects.
- Runtime defects can trigger safe retries and artifact regeneration.
- Code defects create a repair request with failing check, suspected component,
  and proposed fix, but do not silently modify code without tests and commit
  discipline.

## Phase 1: Secure Repo And Deploy Closure

Objective: remove operational friction that prevents finished work from being
committed, pushed, deployed, and audited.

Build:

- Configure secure GitHub authentication for both the root repo and
  `landing-page-repo`.
- Add a `scripts/check_git_deploy_readiness.py` checker.
- Report root ahead/behind, dashboard ahead/behind, dirty protected files,
  ignored runtime artifacts that are intentionally tracked, and last deploy
  receipt.
- Fail if production claims "live" while local commits are not pushed, unless
  the output explicitly labels the state as deployed-but-not-pushed.

Artifacts:

- `data/runtime/qadam_git_deploy_readiness.json`
- `data/runtime/qadam_live_deploy_closure.json`

Acceptance:

- `git push origin HEAD:qadam-foundation` works.
- `git -C landing-page-repo push origin HEAD:main` works.
- Production deploy receipt includes commit SHAs that exist on the remotes.
- Dashboard and cockpit JSON return HTTP 200 from `qadam.trade`.

## Phase 2: Fresh Source Reliability Layer

Objective: make every source category fresh, explicit, and schedulable.

Build:

- A source reliability orchestrator that normalizes all source adapters into
  one contract:
  source id, category, adapter, last observed timestamp, latency, freshness
  state, trust state, outage reason, quorum contribution, and safety boundary.
- Scheduled ingestion for:
  geopolitics, macro, market prices, prediction markets, Reddit/social,
  filings/capitol trades, physical-world signals, and technical/order-flow
  data.
- Repair deferred/partial adapters where possible.
- Keep supplemental-only sources labeled honestly.
- Add source staleness probes that fail closed.

Likely files:

- `orchestrator/qsase_source_reliability.py`
- `scripts/check_qsase_source_reliability.py`
- `data/runtime/qsase_source_reliability.json`
- `data/runtime/qsase_source_outage_log.jsonl`

Acceptance:

- Required-source freshness is at least `95%` during active windows.
- Every offline source has a clear outage reason.
- Source quorum never counts stale, optional, supplemental-only, or
  single-source evidence as sufficient by itself.
- Dashboard source categories and granular source rows match the runtime
  contract.

## Phase 3: Point-In-Time Historical Memory Completion

Objective: fix the main evidence-quality bottleneck by backfilling aligned,
leakage-safe source-price windows.

Build:

- A historical memory completion runner that builds forward windows for every
  valid source event and watched instrument.
- Alignment windows by horizon:
  intraday, 1 day, 3 day, 5 day, 10 day, 20 day, and 30 day.
- Price series for all approved trading-universe proxies.
- Provenance for source event timestamp, ingestion timestamp, and price
  timestamp.
- Leakage checks that reject any record using future data.
- Coverage scoring per source, category, instrument, strategy family, and
  regime.

Likely files:

- `orchestrator/qsase_historical_memory_completion.py`
- `scripts/check_qsase_historical_memory_completion.py`
- `data/runtime/qsase_historical_memory_completion.json`
- `data/runtime/qsase_source_price_forward_windows.jsonl`
- `data/runtime/qsase_historical_memory_leakage_audit.json`

Acceptance:

- Complete forward-window coverage is at least `80%` for paperable core
  instruments.
- Missing windows are classified by source gap, price gap, market holiday,
  instrument unsupported, or ingestion outage.
- Historical replay cannot create candidates, orders, proof credit, or paper
  trial elapsed time.

## Phase 4: Market Confirmation And Akber Input Builder

Objective: stop Akber holding because practical confirmation fields are
missing.

Build:

- A market confirmation builder that creates complete confirmation packets for
  each candidate pattern.
- Required packet fields:
  volatility context, trend/technical state, volume or flow confirmation,
  pricing-gap evidence, catalyst strength, liquidity state, invalidation,
  time window, and paperability.
- Source-specific evidence adapters:
  Alpaca paper/account mirror, TradingView, Yahoo/yfinance if enabled,
  prediction-market odds, options/flow when available, Bookmap/order-flow when
  available.
- A missing-field repair queue that tells the source layer exactly what is
  missing.

Likely files:

- `orchestrator/qsase_market_confirmation.py`
- `scripts/check_qsase_market_confirmation.py`
- `data/runtime/qsase_market_confirmation_packets.jsonl`
- `data/runtime/qsase_akber_input_completeness.json`

Acceptance:

- `akber_missing_context_count=0` for Router-eligible setups.
- Akber holds are based on real evidence insufficiency, not absent fields.
- Supplemental market data cannot satisfy source quorum alone.

## Phase 5: Validated Edge Graduation

Objective: create a defensible mechanism for moving from pattern to validated
edge.

Build:

- A validated-edge graduation engine.
- Graduation criteria:
  repeat count, lead-lag consistency, expectancy, hit rate, max drawdown,
  false-positive rate, regime stability, source-before-price evidence, and
  out-of-sample survival.
- Rejection criteria:
  overfit, source lag, price-before-source, insufficient windows,
  unstable regime, non-paperable expression, or safety-boundary conflict.
- A human-readable explanation for every graduation or rejection.

Likely files:

- `orchestrator/qsase_validated_edge_graduation.py`
- `scripts/check_qsase_validated_edge_graduation.py`
- `data/runtime/qsase_validated_edges.jsonl`
- `data/runtime/qsase_edge_rejections.jsonl`

Acceptance:

- `validated_edge_count` can become greater than `0` only through explicit
  evidence.
- Every validated edge links to historical windows, pattern ids, source ids,
  instruments, and strategy hypotheses.
- No validated edge can create an order.

## Phase 6: Full-Universe Linear And Nonlinear Pattern Search Upgrade

Objective: make the pattern engine genuinely cross-universe instead of
compartmentalized.

Build:

- A matrix search across all qualified sources and all watched instruments.
- Linear tests:
  lag correlation, event study, walk-forward regression, factor controls,
  expectancy, drawdown, and false-positive review.
- Nonlinear tests:
  source interaction, path dependence, regime-conditioned relationships,
  anomaly clustering, cross-asset sequence effects, and quantum-inspired
  ambiguity/usefulness review.
- Quantum state labeling:
  actual provider, local simulator, deterministic classical fallback, or
  unavailable.
- Ranking that prioritizes tradeability, evidence quality, and expected value
  rather than activity count.

Likely files:

- `orchestrator/qsase_full_universe_pattern_search_v2.py`
- `orchestrator/qsase_linear_pattern_lab_v2.py`
- `orchestrator/qsase_nonlinear_quantum_pattern_lab_v2.py`
- `scripts/check_qsase_pattern_search_v2.py`

Acceptance:

- Pattern findings are distinct, ranked, and non-repetitive.
- Every pattern explains source signal, price relationship, market affected,
  evidence, confidence, blocker, and next action.
- Quantum review cannot approve trades or bypass PaperOps.

## Phase 7: Strategy Foundry V2

Objective: convert validated edges into tradeable strategy hypotheses without
skipping evidence.

Build:

- Strategy hypothesis builder that consumes only validated or explicitly
  watchlisted patterns.
- Fields:
  strategy family, new-family proposal if needed, instrument, direction,
  thesis, evidence lineage, Research Goal lineage, invalidation, risk concept,
  time stop, paperability, and expected learning value.
- Rejected-hypothesis ledger for overfit, unsafe, unpaperable, duplicate, weak,
  or source-quorum-deficient hypotheses.

Likely files:

- `orchestrator/qsase_strategy_foundry_v2.py`
- `scripts/check_qsase_strategy_foundry_v2.py`
- `data/runtime/qsase_strategy_hypotheses_v2.jsonl`
- `data/runtime/qsase_rejected_strategy_hypotheses_v2.jsonl`

Acceptance:

- Strategy hypotheses are not trades.
- Hypotheses can be traced back to source-price evidence.
- New strategy families can be proposed, but not silently activated.

## Phase 8: Akber Filter V2

Objective: make Akber's filter a complete, measurable, practical trading gate.

Build:

- Six-stage Akber review over every hypothesis:
  context, catalyst, confirmation, risk, execution, and postmortem learning.
- Stage scoring with plain-English pass/hold/veto reasons.
- Ablation testing that compares outcomes with and without Akber's filter.
- Threshold proposals for human review.

Likely files:

- `orchestrator/qsase_akber_filter_v2.py`
- `scripts/check_qsase_akber_filter_v2.py`
- `data/runtime/qsase_akber_filter_v2.json`
- `data/runtime/qsase_akber_stage_records_v2.jsonl`

Acceptance:

- Akber can pass at least one historically valid setup in replay when evidence
  genuinely supports it.
- Akber can hold or veto fresh setups with specific missing evidence.
- Akber pass cannot create execution approval.

## Phase 9: Shadow Simulator And Counterfactual Lab V2

Objective: prove whether a proposed setup deserves paper-review before it
touches PaperOps.

Build:

- Historical and forward shadow runs for each hypothesis.
- Counterfactual variants:
  trade now, wait for confirmation, veto, alternate stop, alternate target,
  alternate Akber threshold, and no-order.
- Metrics:
  expectancy, drawdown, hit rate, missed opportunity, false positive,
  time-in-trade, and learning value.
- Shadow rejection records for setups that look plausible but do not survive.

Likely files:

- `orchestrator/qsase_shadow_simulator_v2.py`
- `scripts/check_qsase_shadow_simulator_v2.py`
- `data/runtime/qsase_shadow_results_v2.jsonl`
- `data/runtime/qsase_shadow_counterfactuals_v2.jsonl`

Acceptance:

- Shadow success cannot create paper proof ledger credit.
- Shadow results can support Router review only when lineage is complete.
- Failed shadow results create learning records and rejection reasons.

## Phase 10: Router V2 And PaperOps Handoff Completion

Objective: make the final pre-PaperOps decision clean, singular, and
explainable.

Build:

- Router state machine with exactly one output per setup.
- Required states:
  reject, watchlist, shadow-only, hold, repair-requested,
  blocked-safety-boundary, and paper-review candidate.
- Handoff builder that converts only `paper-review candidate` outputs into
  upstream PaperOps records.
- Guard enforcement:
  source quorum, Research Goal lineage, candidate identity, idempotency,
  duplicate exposure, drawdown, risk, Akber, quantum state, Q-CTRL hold, and
  guarded Alpaca Paper route.

Likely files:

- `orchestrator/qsase_strategy_router_v2.py`
- `orchestrator/qsase_paperops_handoff_v2.py`
- `scripts/check_qsase_router_v2.py`
- `scripts/check_qsase_paperops_handoff_v2.py`

Acceptance:

- Router creates no orders.
- PaperOps handoff creates no orders.
- PaperOps sees clean handoff records when and only when all review gates pass.
- "Why not trading now" is a single clear answer.

## Phase 11: Paper Lifecycle And Proof Ledger Completion

Objective: make paper trades observable from idea to postmortem.

Build:

- Lifecycle monitor for submitted, accepted, filled, open, stale, cancel/replace
  review, closed, postmortem due, and proof-eligible states.
- Stale accepted-order policy:
  continue waiting, cancel/replace, or no-action with reason.
- Proof lineage auditor from Research Goal through candidate, approval, staged
  order, submitted order, fill, close, and postmortem.
- Proof eligibility gate that rejects missing lineage.

Likely files:

- `orchestrator/qsase_paper_lifecycle_v2.py`
- `orchestrator/qsase_proof_ledger_v2.py`
- `scripts/check_qsase_paper_lifecycle_v2.py`
- `scripts/check_qsase_proof_ledger_v2.py`

Acceptance:

- No paper order is ambiguous.
- Closed paper trades can graduate to the paper proof ledger only with complete
  lineage.
- Backtests, shadow runs, and synthetic checks cannot grant proof credit.

## Phase 12: Learning Attribution And Recursive Improvement

Objective: make Qadam improve from outcomes without silently mutating policy.

Build:

- Attribution across:
  sources, models, quantum review, Akber, Router, PaperOps, risk, execution,
  source quorum, and market regime.
- Outcome classes:
  backtest, shadow, paper trade, non-trade, rejection, missed opportunity, and
  system defect.
- Proposal queues:
  source trust proposal, strategy weight proposal, Akber threshold proposal,
  model routing proposal, and data-source repair proposal.
- Human approval boundary for every mutation.

Likely files:

- `orchestrator/qsase_learning_attribution_v2.py`
- `scripts/check_qsase_learning_attribution_v2.py`
- `data/runtime/qsase_learning_attribution_v2.json`
- `data/runtime/qsase_policy_proposals_v2.jsonl`

Acceptance:

- Qadam can explain what helped, what hurt, what blocked correctly, what blocked
  incorrectly, and what should change.
- No proposal mutates live or paper policy without explicit approval.

## Phase 13: Dashboard Completion

Objective: make the public dashboard show the whole fund clearly and
commercially.

Build:

- Preserve and verify the required dashboard order:
  portfolio value, current holdings, trading history, Hedge Fund Team, source
  intelligence network, trading universe, strategy universe, pattern
  recognition findings, Akber filter state, trade candidates, Router/PaperOps
  decision, learning ledger.
- Hedge Fund Team cards:
  Python COO, local LLM Research Analyst, frontier LLM Strategy Lead, quantum
  Head of Quant, plus risk/execution/learning roles if useful.
- Source category cards with expandable source/API rows.
- Trading Universe category cards with watched instruments.
- Pattern insight cards that show meaning before counts.
- Akber and Router modules that translate internal names into plain English.
- Anti-slop checks for repetition, duplicated cards, generic text, harsh copy,
  stale labels, and contradictory portfolio values.

Likely files:

- `orchestrator/qsase_dashboard_view_model_v2.py`
- `landing-page-repo/dashboard.js`
- `scripts/check_qsase_dashboard_view_model_v2.py`
- `scripts/check_dashboard_pattern_intelligence.js`

Acceptance:

- A non-technical user can understand what Qadam owns, watches, thinks, blocks,
  and will do next.
- Portfolio value, cash, chart, holdings, and trading history agree.
- Dashboard is read-only and public-safe.

## Phase 14: Telegram Completion

Objective: make Telegram useful without being repetitive or authoritative.

Build:

- Short specific message candidates for:
  pattern found, pattern blocked, paper-review candidate, paper order submitted,
  paper fill, paper close, learning update, and system defect.
- Dedupe ledger based on event identity, not text alone.
- Quality gate that rejects generic, repeated, too-long, harsh, or internal-only
  wording.
- Dashboard Communications mirror.

Likely files:

- `orchestrator/qsase_telegram_summary_v2.py`
- `scripts/check_qsase_telegram_summary_v2.py`
- `data/runtime/qsase_telegram_summary_v2.json`

Acceptance:

- Telegram sends no commands.
- Telegram cannot create trades, candidates, approvals, broker writes, or proof.
- Repeated messages are blocked unless the underlying state changed.

## Phase 15: Self-Healing Operations

Objective: make Qadam detect and repair safe runtime failures, and create clear
repair requests for code defects.

Build:

- Self-healing supervisor with three tiers:
  refresh, quarantine, and repair request.
- Refresh tier:
  rerun stale artifact builders, retry transient network calls, rebuild cockpit
  mirrors, refresh dashboard view-model artifacts.
- Quarantine tier:
  mark broken sources optional/degraded, remove them from quorum, and explain
  the reduced coverage.
- Repair-request tier:
  write a specific defect artifact when code, schema, credentials, or adapter
  logic is broken.
- No autonomous code editing without explicit implementation workflow, tests,
  and commit.

Likely files:

- `orchestrator/qadam_self_healing_supervisor.py`
- `scripts/run_qadam_self_healing_supervisor.py`
- `scripts/check_qadam_self_healing_supervisor.py`
- `data/runtime/qadam_self_healing_state.json`
- `data/runtime/qadam_repair_requests.jsonl`

Acceptance:

- Stale runtime artifacts can be refreshed automatically.
- Source outages do not silently poison quorum.
- Code defects produce clear repair records.
- Self-healing never creates broker writes, live authority, proof credit, or
  hidden policy changes.

## Phase 16: End-To-End Certification

Objective: add one command that determines whether Qadam is operationally
complete.

Build:

- `scripts/check_qadam_operational_perfection.py`.
- It should run or verify every required check:
  source reliability, historical memory, pattern search, Akber input
  completeness, validated edges, Strategy Foundry, Akber filter, shadow
  simulator, Router, PaperOps handoff, lifecycle, proof ledger, learning,
  dashboard, Telegram, safety boundaries, deployment, and self-healing.
- It should write one canonical artifact.

Artifact:

```text
data/runtime/qadam_operational_perfection_certification.json
```

Required top-level fields:

```json
{
  "status": "qadam_operationally_complete",
  "generated_at": "...",
  "paper_only": true,
  "live_capital_enabled": false,
  "required_source_freshness_passed": true,
  "historical_memory_coverage_passed": true,
  "akber_input_completeness_passed": true,
  "validated_edge_pathway_passed": true,
  "router_decision_integrity_passed": true,
  "paperops_guarded_route_passed": true,
  "dashboard_public_contract_passed": true,
  "telegram_boundary_passed": true,
  "self_healing_passed": true,
  "deployment_closure_passed": true,
  "unresolved_blockers": [],
  "why_not_trading_now": "no qualified setup" 
}
```

Acceptance:

- The checker fails if any required component is stale, degraded, missing,
  contradictory, unsafe, or not deployed.
- The checker can distinguish:
  system not complete, system complete but no setup, system complete with paper
  review candidate, and system complete with active paper position.
- The checker never treats forced trades as success.

## Phase 17: Soak Run And Final Live Declaration

Objective: prove Qadam stays complete over time, not only at one checkpoint.

Build:

- A 7-day operational soak.
- Scheduled checks during market windows.
- Daily canonical summaries.
- Dashboard and Telegram review.
- PaperOps autonomous pass review from canonical summary only.
- Incident log for any degraded or blocked state.

Acceptance:

- No unresolved critical blocker remains at the end of the soak.
- Any no-trade period is explained by market/evidence conditions, not system
  failure.
- If a valid setup appears, it can move to PaperOps through the guarded route.
- If no valid setup appears, Qadam still proves that its sensing, testing,
  routing, and explanation layers are current.

## Final Operating Answer Contract

When the plan is complete and the certification passes, the answer to "Is the
whole system working perfectly well?" should be:

```text
Yes. Qadam is operationally complete and running as designed.

It is ingesting fresh sources, maintaining point-in-time source-price memory,
searching for linear and nonlinear patterns across the full data and trading
universe, applying Akber's filter with complete inputs, routing setups through
PaperOps only when evidence passes, tracking paper lifecycle and proof lineage,
learning from outcomes, and showing the state clearly on the dashboard and
Telegram.

It is not guaranteed to trade at every moment. If it is not trading, the reason
is market/evidence discipline rather than a system blocker.
```

If any gate fails, the answer must be:

```text
No. Qadam is not operationally complete yet. The current blocker is: ...
```

## Implementation Order

The work should be implemented in this order:

1. Repo and deployment closure.
2. Source reliability.
3. Historical memory completion.
4. Market confirmation and Akber input builder.
5. Validated-edge graduation.
6. Full-universe pattern search upgrade.
7. Strategy Foundry V2.
8. Akber Filter V2.
9. Shadow Simulator V2.
10. Router V2 and PaperOps handoff completion.
11. Paper lifecycle and proof ledger completion.
12. Learning attribution and recursive improvement.
13. Dashboard completion.
14. Telegram completion.
15. Self-healing operations.
16. End-to-end certification.
17. Soak run and final live declaration.

This order matters. Qadam should not loosen execution to compensate for weak
evidence. It should strengthen evidence until the existing guarded execution
route can safely act.
