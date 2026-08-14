# Qadam Compounding Evidence Graph And Higher-Frequency Paper Discovery Implementation Plan

Date: 2026-08-12

Status: Implemented and certified; five-real-market-day evidence trial running

Scope: Additive evolution of Qadam's existing paper-only edge engine. This plan
does not replace the current dashboard, the 41-source and 19-instrument baseline,
the five configured strategy families, the emerging power sleeve, Pattern Score
V3, Akber's 6-Stage Filter, Router, portfolio risk, or canonical PaperOps.

Phase prefix: `QEG` means Qadam Evidence Graph. `CEG` is deliberately not used
because it is an actual power-market instrument symbol in Qadam's emerging
power sleeve.

## 1. Executive Decision

Qadam already gathers a broad evidence universe, runs historical and forward
research, records candidate patterns, forms strategy hypotheses, applies Akber,
and can submit bounded paper experiments through guarded Alpaca Paper. Its next
constraint is that these activities still behave too much like separate files
and repeated research cycles.

The next evolution is a single, temporal, provenance-backed knowledge system
that connects:

- source observations;
- world events and entities;
- instruments and exposure relationships;
- external claims and references;
- patterns and hypotheses;
- historical and forward experiments;
- strategy versions;
- Akber, risk, and Router decisions;
- paper orders, positions, and outcomes;
- postmortems and improvement proposals.

The graph must make every new cycle start with what Qadam already knows. A
failed hypothesis must remain queryable by its evidence, regime, parameters,
cost assumptions, rejection reason, and subsequent market outcome. A promising
relationship must be traceable from the original provider observation through
testing and strategy admission to any paper result.

This change should also increase legitimate paper-trade frequency. It will do
that by:

1. finding more distinct, economically plausible relationships across the full
   source and instrument universe;
2. prioritising relationships that are current, paperable, and close to a
   decision rather than merely interesting;
3. converting available evidence into the exact typed fields required by each
   strategy profile;
4. preserving the existing `discovery_micro` lane for small, under-evidenced
   but complete paper experiments;
5. allowing multiple independent setups in one day when each setup has unique
   lineage, identity, idempotency material, risk capacity, and no exposure
   conflict;
6. learning from holds, vetoes, missed opportunities, trades, and non-trades so
   gate calibration improves from evidence rather than intuition.

The plan does not introduce a trade quota, lower hard portfolio-risk controls,
manufacture triggers, or promise a trade every day. Its operating target is:

> If one or more complete, distinct, low-risk paper setups exist, Qadam should
> evaluate and route each within one fresh market-hours decision cycle instead
> of losing them to disconnected artifacts, unavailable-field mismatches, or
> stale sequencing.

## 2. Relationship To Existing Qadam Plans

This plan is additive. It must reuse and extend, not fork or reimplement:

- `docs/qadam-operator-ready-edge-engine-implementation-plan.md` for the
  canonical research-to-PaperOps stage ladder;
- `docs/qadam-backtest-completion-implementation-plan.md` for point-in-time
  history, the experiment registry, statistical controls, strategy translation,
  and forward tournaments;
- `docs/qadam-evidence-fit-active-paper-trading-overhaul-implementation-plan.md`
  for evidence profiles, same-generation packets, `discovery_micro`, Akber
  recalibration, risk alignment, and active paper conversion;
- `docs/qadam-permanent-operator-reliability-repair-implementation-plan.md` for
  artifact ownership, immutable generations, locking, retry, circuit repair,
  storage safety, and installed-service certification;
- the existing dashboard route structure and established UX;
- the canonical `scripts/run_paperops_autonomous_pass.py` broker-write route.

Where an existing contract is already certified, this plan must consume it.
Where an existing artifact is legacy, contradictory, or projection-only, this
plan must record an adapter or deprecation path rather than silently creating a
second source of truth.

## 3. Drafting Baseline To Reverify At QEG-0

The implementation must regenerate current truth before changing policy. The
drafting baseline is:

- 41 registered sources across six evidence families;
- 19 watched instruments in the frozen core universe;
- five configured strategy families;
- one separate emerging power-market sleeve;
- three evidence profiles: event-catalyst, regime-state, and
  market-dislocation;
- a provider-backed historical lake and completed backtest machinery;
- Pattern Score V3 and Strategy Foundry V3;
- a validated-strategy lane and a bounded `discovery_micro` lane;
- a frozen runtime `discovery_micro` target of US$500 to US$1,000, where the
  minimum is not a forced floor, and a US$5,000 absolute paper-trade ceiling;
- a separate backtest-plan risk ladder of `R1` US$500, `R2` US$1,250, `R3`
  US$2,500, and `R4` US$5,000 that must be reconciled with the runtime policy
  before automatic tier promotion is enabled;
- a maximum of three concurrent discovery positions and one position per
  correlated cluster;
- zero currently validated canonical edges at the time this plan was drafted;
- an older Phase 6 graph implementation that is a blocked staging gate and a
  one-result read-only view, not a durable current evidence graph;
- proposal-only self-improvement and promotion artifacts that do not yet form
  complete persistent experiment memory;
- an attached Qadam research document containing 136 unique URLs, including 65
  social-media links, mixed with current design, obsolete design, future ideas,
  and unverified external claims.

These are drafting facts, not permanent constants. QEG-0 must write the current
verified baseline and identify every drift before later phases proceed.

## 4. Objectives

### 4.1 Knowledge Objectives

- Convert disconnected artifacts into one rebuildable temporal evidence graph.
- Preserve every positive, negative, held, vetoed, duplicate, and inconclusive
  research outcome.
- Make source provenance, publication time, availability time, validity range,
  parser version, and evidence independence first-class.
- Distinguish observations, external claims, inferred relationships, tested
  relationships, validated edges, strategies, and execution outcomes.
- Detect when a new hypothesis duplicates or trivially parameter-tunes an old
  failed hypothesis.
- Allow graph questions across the whole evidence and trading universe without
  granting graph output authority.

### 4.2 Edge-Discovery Objectives

- Search for source-to-price, source-to-source, entity-to-instrument,
  cross-asset, divergence, regime, and path-dependent relationships.
- Require an economic mechanism and falsifier before expensive testing.
- Allocate most research capacity to focused programmes while reserving a
  bounded whole-universe challenger budget.
- Apply transparent classical methods before nonlinear or quantum review.
- Measure whether a quantum method adds out-of-sample value beyond a matched
  classical method.
- Translate surviving evidence into a refinement of a core family or an
  emerging pattern-sourced strategy.

### 4.3 Paper-Activity Objectives

- Keep discovery scans fresh during relevant market sessions.
- Maintain a ranked actionability queue separate from the research score.
- Evaluate every complete actionable setup within one decision cycle.
- Permit multiple distinct paper setups per day when risk and exposure allow.
- Prevent stale sequencing, unavailable-field mismatches, and duplicate
  identity from suppressing otherwise valid experiments.
- Use conservative sizing and evidence haircuts instead of converting every
  evidence limitation into a permanent hold.
- Preserve positive current expectancy after costs, current spread and
  liquidity, invalidation, duplicate-exposure, drawdown, route, and idempotency
  requirements.

### 4.4 Learning Objectives

- Turn every outcome and non-outcome into attributable evidence.
- Create improvement proposals automatically.
- Test proposal challengers automatically on frozen evidence.
- Automatically admit declarative paper-strategy versions only inside a
  pre-authorised paper-risk envelope and only after deterministic criteria pass.
- Keep code changes, prompt changes, provider purchases, live capital, and risk
  envelope expansion outside autonomous authority.

## 5. Non-Goals

This plan will not:

- guarantee profit or a minimum number of trades;
- turn research scores into probabilities of profit;
- lower the hard daily-loss, drawdown, exposure, liquidity, spread,
  idempotency, duplicate-exposure, route, or broker reconciliation controls;
- permit live capital;
- permit direct LLM, dashboard, Telegram, graph, or quantum broker access;
- allow an external article, social-media claim, graph edge, or model opinion to
  satisfy source quorum by itself;
- let strategies rewrite Python until a backtest turns green;
- allow holdout reuse, hidden parameter searches, or simulated elapsed time;
- require quantum review on a calendar cadence;
- install a large external graph database when a local rebuildable store is
  sufficient;
- replace the dashboard layout or its protected routes;
- create a second PaperOps route.

## 6. Constitutional Boundaries

Every phase must preserve all of the following:

- Alpaca Paper only;
- canonical PaperOps is the only broker-write actor;
- live-capital authority is false;
- models never receive broker credentials;
- observation and graph writes cannot create trade authority;
- historical evidence cannot become current trigger evidence;
- backtest, shadow, and graph results cannot become proof credit;
- research score is not a probability or execution approval;
- a quantum run is not quantum advantage;
- a discovery paper experiment is not a validated edge;
- missing data remains typed and visible;
- fixture, sample, configured-only, stale, and unavailable states never count as
  provider-backed live evidence;
- no forced trade, calendar backfill, or synthetic current catalyst;
- multiple daily submissions require distinct Research Goal lineage, candidate
  identity, idempotency key, exposure cluster, and complete risk decision;
- no automatic enlargement of the US$5,000 ceiling or total risk envelope;
- no automatic mutation of executable code, live-capital strategy, or
  live-capital policy;
- all automated paper-strategy changes are versioned, reversible, bounded, and
  declarative;
- Telegram and the dashboard remain public-safe and command-disabled;
- raw research data and graph indexes remain under ignored research paths and
  cannot be committed to Git.

## 7. Core Architecture Decision

### 7.1 One Graph, Four Trust Layers

The graph is one logical system with four explicitly separated trust layers:

| Layer | Content | Write policy | Trading authority |
| --- | --- | --- | --- |
| A. Observed | Provider responses, normalized observations, events, prices, contracts, entities | Automatic append after schema, provenance, and checksum validation | None |
| B. Inferred | Model-extracted claims, entity links, exposure links, candidate relationships | Automatic append as `provisional_inference` after deterministic validation | None |
| C. Tested | Backtest, shadow, ablation, negative-control, and quantum/classical results | Automatic append from certified test producers | None |
| D. Governed | Validated edges, strategy versions, Akber decisions, risk decisions, Router decisions, orders, outcomes, promotions | Written only by the existing owning stage and authority contract | Only canonical downstream stages retain their existing bounded authority |

Automatic graph ingestion therefore becomes useful without giving a graph
backend the power to approve learning, change policy, or trade.

The older Q6-10 graph gate governed proposed postmortem-learning writes. It must
remain a legacy reference and must not be weakened or silently repurposed.
Automatic Layer A observation indexing and Layer B provisional inference are a
new evidence-storage responsibility, not approval of a learning conclusion.
Any migration of old learning-memory records must retain their approval state
and enter Layer C or D only through the applicable governed owner.

### 7.2 Storage Architecture

Use a local-first, rebuildable architecture suitable for the M5 laptop:

1. Append-only canonical graph events under ignored
   `data/research/qadam_temporal_evidence_graph/events/`.
2. Compressed immutable partitions for large historical node and edge records.
3. A local SQLite WAL-mode materialized query index using Python's standard
   library, with foreign keys, FTS5 where available, and deterministic indexes.
4. A graph manifest containing generation ID, parent generation, schema
   version, checksums, row counts, disk use, and source watermarks.
5. Small dashboard-safe projections under `data/runtime/`.
6. A complete rebuild command that recreates the SQLite index from canonical
   events without information loss.

The SQLite index is disposable and rebuildable. The append-only event log and
immutable provider artifacts remain canonical. Chroma or another vector store
may be used only as a derived semantic-retrieval index, never as source truth.

### 7.3 Canonical Node Types

The initial ontology must support:

- `source_provider`;
- `source_feed`;
- `source_observation`;
- `reference_document`;
- `external_claim`;
- `world_event`;
- `entity`;
- `country`;
- `sector`;
- `instrument`;
- `execution_proxy`;
- `prediction_contract`;
- `market_regime`;
- `feature`;
- `pattern_relationship`;
- `research_goal`;
- `hypothesis`;
- `experiment_definition`;
- `experiment_result`;
- `validated_edge`;
- `strategy_family`;
- `strategy_version`;
- `shadow_decision`;
- `akber_decision`;
- `portfolio_risk_decision`;
- `router_decision`;
- `paperops_handoff`;
- `paper_order`;
- `paper_position`;
- `paper_outcome`;
- `postmortem`;
- `improvement_proposal`;
- `repair_request`.

### 7.4 Canonical Edge Types

The initial ontology must support:

- `reported_by`;
- `published_by`;
- `mentions`;
- `located_in`;
- `affects`;
- `exposed_to`;
- `proxy_for`;
- `corroborates`;
- `contradicts`;
- `precedes`;
- `co_occurs_with`;
- `derived_from`;
- `supports`;
- `weakens`;
- `duplicates`;
- `supersedes`;
- `tested_by`;
- `failed_in_regime`;
- `succeeded_in_regime`;
- `maps_to_strategy`;
- `generated_strategy`;
- `filtered_by`;
- `held_by`;
- `vetoed_by`;
- `passed_by`;
- `routed_to`;
- `executed_as`;
- `resulted_in`;
- `attributed_to`;
- `proposed_change_to`.

### 7.5 Temporal And Provenance Contract

Every graph record must include, where applicable:

- stable `node_id` or `edge_id`;
- schema version;
- graph generation ID;
- source artifact reference;
- source provider and source feed;
- provider record identity;
- event time;
- publication time;
- first availability time;
- ingestion time;
- valid-from and valid-to times;
- supersession reference;
- content or payload checksum;
- parser and normalizer version;
- evidence state;
- source trust state;
- source independence cluster;
- confidence or score type, never an unlabeled number;
- supporting and contradicting evidence references;
- public-safety classification;
- authority flags fixed to false unless the record is a projection of an
  existing governed downstream decision.

No future information may be visible to a point-in-time graph query.

## 8. Claim And Reference Intake Contract

The attached Qadam document is the first graph-intake pilot. It must be copied
by checksum from its temporary attachment path into an ignored raw intake
directory before that temporary path disappears.

Drafting source identity:

- temporary path:
  `/tmp/codex-remote-attachments/019ea17c-4579-73d1-9bda-81dc99971a47/9EF4B29C-62DB-43AA-B15C-D17A3E1FD36E/1-Qadam-3366fe2ecf3780dcabeec1e27c28365e.md`;
- byte size: `115896`;
- SHA-256:
  `0961d7296975372614d440ff002e41d269671b8b51a631642b25c47e5c2de6f5`.

QEG-0 must preserve this source or fail with an explicit reattachment request
if it is unavailable or its checksum differs.

Each paragraph, claim, URL, paper, repository, product, anecdote, and design
statement must become a separate record. The original document remains an
immutable source snapshot.

Reference-library records must use a separate `research_reference` namespace.
They may connect to a hypothesis through `informs_research_question`, but they
must not enter source quorum, Pattern Score, market confirmation, or trade
evidence queries unless a separately registered provider-backed market
observation independently satisfies the normal evidence contract.

Collection must respect provider terms, robots restrictions, copyright,
licensing, and retention rules. Where full-text acquisition is not permitted,
store only allowed metadata, provenance, claim summaries, and short compliant
excerpts. A URL's presence in the attachment is not permission to scrape it.

### 8.1 Source Classes

| Class | Examples | Default posture |
| --- | --- | --- |
| A. Primary | Official provider docs, official APIs, regulatory records, academic papers, official repositories | Eligible for verification and implementation evidence |
| B. Technical secondary | Reputable engineering documentation, transparent technical analyses | Research support after verification |
| C. Vendor or marketing | Product pages, sales claims, performance marketing | Capability lead only |
| D. Social or anecdotal | Instagram, X, Telegram, screenshots, influencer claims | Unverified hypothesis lead only |
| E. Superseded internal | Old Qadam architecture, old universe counts, obsolete v1 language | Preserved as history, excluded from current truth |
| F. Rejected | False, contradicted, unsafe, or irrelevant claims | Searchable negative memory |

### 8.2 Claim States

- `unreviewed`;
- `verified_current`;
- `verified_historical`;
- `partially_verified`;
- `unverified`;
- `contradicted`;
- `superseded`;
- `rejected`;
- `out_of_scope`.

### 8.3 Required Claim Fields

- atomic claim text;
- source reference and content hash;
- source class;
- author or publisher;
- publication and retrieval times;
- original context excerpt within copyright limits;
- verification state and verifier;
- verification evidence;
- current Qadam component affected;
- implementation state;
- hypothesis potential;
- required data;
- falsifier;
- licensing or terms posture;
- public-document eligibility;
- trading-authority flags fixed to false.

Public Whitepaper, User Guide, and resource lists may consume only approved
`verified_current`, `verified_historical`, or clearly labelled research-lead
records. They may not import the complete URL list indiscriminately.

## 9. Persistent Experiment Memory Contract

Every hypothesis and test must receive an immutable attempt identity before the
outcome is visible.

### 9.1 Hypothesis Preregistration

Required fields:

- Research Goal lineage;
- hypothesis family and novelty fingerprint;
- economic mechanism;
- source and graph path;
- affected instrument or proxy;
- expected direction;
- expected horizon;
- entry and invalidation logic;
- evidence profile;
- cost and slippage assumptions;
- baseline model;
- parameter search space;
- train, validation, embargo, and untouched holdout windows;
- multiple-testing family;
- success and failure criteria;
- planned nonlinear or quantum rationale;
- paperability and route state;
- created-at time and immutable checksum.

### 9.2 Attempt And Novelty Detection

Before a new attempt runs, Qadam must compare it with prior attempts using:

- exact input and parameter fingerprint;
- semantic hypothesis similarity;
- graph path overlap;
- source and instrument overlap;
- horizon overlap;
- regime overlap;
- prior rejection reason;
- prior parameter sensitivity.

Possible dispositions:

- `novel_attempt`;
- `independent_replication`;
- `legitimate_challenger`;
- `minor_parameter_variant`;
- `duplicate_attempt`;
- `previously_rejected_same_reason`;
- `new_regime_retest`.

Duplicate and minor-variant attempts remain visible but do not consume a new
holdout or inflate independent evidence counts.

### 9.3 Negative Result Memory

Every failed, held, and inconclusive result must preserve:

- exact failure point;
- market regime;
- data coverage and freshness;
- cost sensitivity;
- baseline comparison;
- false-discovery outcome;
- instability or concentration reason;
- Akber hold or veto reason;
- subsequent counterfactual market outcome;
- conditions under which a retest would be scientifically legitimate.

Negative results are first-class graph nodes. They may suppress duplicate work,
weaken a future hypothesis, or identify a missing-data acquisition priority.

## 10. Bounded Multi-Model Research Contract

The system may fan out independent research, but agent count is not a success
metric.

### 10.1 Role Separation

- Python COO assigns bounded tasks, freezes inputs, enforces budgets, and merges
  only schema-valid outputs.
- Local Gemma extracts entities, claims, mechanisms, contradictions, and
  candidate research questions from high-volume local material.
- Google Gemini challenges the mechanism, proposes alternative explanations,
  and evaluates whether the relationship is economically coherent.
- Classical models measure transparent linear, lagged, regime, graph, and
  nonlinear relationships.
- IBM Quantum and Q-CTRL review only candidates with a documented nonlinear
  rationale and a matched classical challenger.

### 10.2 Independence Before Synthesis

Specialist research tasks should not see each other's conclusions before their
first response. Python then merges their outputs and records agreement,
contradiction, and common-source dependence. This reduces anchoring without
pretending that model agreement is independent provider evidence.

### 10.3 Model Output Boundary

Every model output is a proposed graph delta. A deterministic validator must:

- resolve identities;
- verify cited source records exist;
- classify inference versus observation;
- attach provenance;
- reject unsupported factual assertions;
- deduplicate equivalent relations;
- enforce public and private boundaries;
- write only to the appropriate trust layer.

Models cannot directly commit governed graph records, mutate strategies, or
create orders.

## 11. Full-Universe Graph Discovery Contract

The graph discovery engine must search the full registered evidence and trading
universe while controlling combinatorial and false-discovery risk.

### 11.1 Priority Graph Motifs

1. Provider event -> affected entity -> sector exposure -> instrument response.
2. Physical-world disruption -> supply dependency -> commodity or sector proxy.
3. STOCK Act disclosure -> issuer or sector -> delayed basket repricing.
4. Prediction-market probability -> event mapping -> listed-market divergence.
5. Macro regime -> cross-asset relationship -> proxy direction change.
6. Unusual Whales flow -> existing macro hypothesis confirmation or rejection.
7. Cross-source corroboration with independent provider clusters.
8. Cross-source contradiction that precedes repricing.
9. Source-density and source-agreement interaction, using plain definitions and
   independence controls.
10. Dependency hubs and single points of failure across companies, sectors,
    commodities, infrastructure, and policy.
11. Historical analogue paths with similar evidence, regime, and market state.
12. Pattern decay, reversal, or regime transition.

### 11.2 Resource Allocation

- At least 80% of expensive testing capacity goes to focused, economically
  specified research programmes.
- At most 20% goes to whole-universe challengers until a reviewed proposal
  changes the allocation.
- Each family receives a hypothesis and parameter budget.
- Graph search cannot create thousands of trivial variants outside the declared
  multiple-testing family.
- Paid provider, frontier-model, and quantum calls require a value-of-information
  score and cost budget.

### 11.3 Candidate Record

Every graph-discovered candidate must include:

- a plain-English research question;
- source-to-market path;
- strongest supporting and contradicting evidence;
- source independence;
- first and latest observation times;
- current trigger state;
- economic mechanism;
- alternative explanations;
- falsifier;
- affected instruments and approved proxies;
- evidence profile;
- novelty state;
- expected information value;
- paperability state;
- blocker and next action;
- explicit `is_strategy=false`, `is_trade_candidate=false`, and
  `paper_order_created=false` until downstream stages change those states.

No Layer B-only or model-only relationship may enter statistical testing,
strategy admission, Akber, or PaperOps. It must be anchored to one or more
Layer A provider-backed observations with valid point-in-time provenance.

## 12. Statistical And Forward Validation Contract

Graph discovery does not bypass the existing statistical protocol.

Every historical candidate must undergo, as appropriate:

- point-in-time reconstruction;
- publication and availability-time enforcement;
- purged walk-forward testing;
- untouched holdout testing;
- benchmark comparison;
- factor and regime controls;
- transaction costs, spreads, slippage, delay, and proxy basis risk;
- parameter sensitivity;
- minimum independent observation count;
- false-discovery correction by declared family;
- shuffled-label and placebo controls;
- leakage and survivorship probes;
- stability across time and regimes;
- counterfactual no-order comparison.

Results enter the graph with one of these evidence states:

- `interesting_unvalidated`;
- `historical_candidate`;
- `historically_rejected`;
- `holdout_failed`;
- `cost_failed`;
- `unstable`;
- `forward_shadow_required`;
- `forward_candidate`;
- `validated_edge`.

Historical success alone cannot create proof credit or an order.

## 13. Nonlinear And Quantum Contract

Quantum is a challenger lane, not a ceremonial stage.

### 13.1 Admission To Quantum Review

A candidate may enter quantum review only when:

- the relationship is genuinely nonlinear, combinatorial, graph-structured, or
  path-dependent;
- the same point-in-time evidence can be supplied to a classical baseline;
- the expected information value justifies the cost;
- the experiment has a frozen circuit, encoding, backend, shot, and error
  mitigation plan;
- the output metric is linked to out-of-sample prediction or strategy value.

### 13.2 Fair Comparison

Record:

- matched classical model;
- identical train and test evidence;
- simulator, hardware, and Q-CTRL state;
- queue and execution time;
- provider cost;
- repeatability;
- out-of-sample delta;
- net-of-cost strategy delta;
- uncertainty interval;
- conclusion: `quantum_preferred`, `classical_preferred`, `indistinguishable`,
  or `not_measurable`.

Only repeatable out-of-sample incremental value may strengthen a strategy.
Hardware execution by itself cannot.

## 14. Strategy Foundry And Versioning Contract

### 14.1 Four Strategy Destinations

Every surviving pattern must map to exactly one of:

- refinement proposal for one of the five core strategy families;
- emerging pattern-sourced strategy;
- shadow-only research strategy;
- rejected strategy hypothesis.

Qadam is not limited to the core five. The five remain configured frameworks;
new relationships may form emerging strategies after the same evidence and
governance standards.

### 14.2 Declarative Strategy Version

Each strategy version must be data, not rewritten Python. Required fields:

- version and parent version;
- strategy family or emerging identity;
- Research Goal and pattern lineage;
- economic mechanism;
- source and graph paths;
- trigger rules;
- evidence profile;
- direction rule;
- instrument and proxy mapping;
- entry, invalidation, and exit rules;
- time horizon;
- cost model;
- Akber requirements;
- paper-risk tier;
- exposure cluster;
- activation, expiry, rollback, and monitoring rules;
- backtest, forward, and quantum/classical evidence;
- admission state and reason.

### 14.3 Admission States

The progressive path is:

1. `research_relationship`
2. `historical_test_pending`
3. `historical_candidate`
4. `emerging_strategy_proposal`
5. `forward_shadow`
6. `paper_discovery_eligible`
7. `validated_paper_strategy`

`held`, `rejected`, and `retired` are side or terminal states that may occur at
the applicable governed stage. They are not three mandatory steps after a
strategy becomes validated.

Automatic paper admission is allowed only within the existing pre-authorised
paper envelope and after deterministic admission criteria pass. New code,
provider purchases, live-capital authority, and risk expansion beyond the
frozen envelope remain human-reviewed.

## 15. Higher-Frequency Paper Discovery Design

### 15.1 Research Score Versus Actionability

Do not lower Pattern Score until trade count increases. Maintain two separate
views:

- `research_rank`: how interesting and evidentially supported a relationship is;
- `actionability_rank`: whether it has a current trigger, directional rule,
  current market confirmation, complete Akber packet, paperable instrument,
  positive conservative expectancy, current spread and liquidity, free risk
  capacity, and no duplicate exposure.

A lower research-ranked setup may be more actionable than a high-scoring setup
whose catalyst is inactive. The active discovery loop should inspect the top
actionable setups, not only the highest historical scores.

### 15.2 Evidence-Profile Fit

Preserve the current profiles:

- event-catalyst;
- regime-state;
- market-dislocation.

Add a versioned evidence-alternative matrix. Each field must be classified as:

- hard required;
- one-of required alternative;
- optional confirmation;
- unavailable by design;
- not applicable to this profile.

Substitutions receive explicit confidence and size haircuts. Missing current
spread, liquidity, price, invalidation, positive expectancy, route, or risk
capacity cannot be substituted.

### 15.3 Active Discovery Queue

During relevant market hours, each fresh cycle must:

1. refresh source and instrument states;
2. update graph deltas;
3. activate or expire triggers;
4. update the actionability queue;
5. build same-generation evidence packets for the top distinct setups;
6. run Akber;
7. create decision-time shadow snapshots;
8. run portfolio risk and Router;
9. submit every clean setup through canonical PaperOps;
10. record explicit holds, vetoes, and no-action reasons.

The queue must not stop after the first held setup. It should continue through
the bounded top-K list until its per-cycle compute budget is exhausted.

### 15.4 Multiple Distinct Setups Per Day

Multiple paper experiments may be submitted on the same day only when each has:

- distinct Research Goal lineage;
- distinct hypothesis and candidate identity;
- distinct idempotency key;
- different setup trigger or independently justified instrument expression;
- no duplicate or correlated exposure conflict;
- positive conservative expectancy after costs;
- complete invalidation and exit logic;
- passing current liquidity and spread;
- passing Akber, risk, Router, and PaperOps states;
- no daily-loss or drawdown breach;
- risk capacity under the current total and per-cluster limits.

The current runtime and planned promotion policies must be reconciled rather
than blended silently:

- the frozen runtime `discovery_micro` policy currently targets US$500 to
  US$1,000, does not treat US$500 as a forced floor, and permits risk or
  liquidity to require a smaller size or no trade;
- the backtest-completion plan defines a signed automatic-promotion ladder of
  `R1_canary` US$500, `R2_probation` US$1,250, `R3_established` US$2,500, and
  `R4_full_paper_limit` US$5,000;
- QEG-0 must determine which signed policy is canonical for each admission lane
  and fail closed on disagreement;
- until reconciliation passes, the currently installed runtime policy and the
  stricter applicable bound govern;
- every amount is an upper bound rather than a sizing target;
- the absolute ceiling remains US$5,000 unless a separate human-approved policy
  changes it.

Trade frequency cannot independently increase size.

### 15.5 Frequency Success Metrics

Measure:

- fresh scans completed per eligible market session;
- active triggers per day;
- graph candidates considered;
- complete evidence packets built;
- Akber passes, holds, and vetoes by reason;
- Router-ready setups;
- paper submissions and fills;
- distinct versus duplicate setups;
- candidate-to-decision latency;
- eligible-setup-to-submission conversion;
- missed opportunities caused by system defects;
- no-trade days caused by absent evidence versus engineering failure;
- net paper expectancy, drawdown, costs, and benchmark-relative outcomes.

One paper experiment per genuinely eligible market day is a discipline target,
not a quota. A day with no complete setup remains a valid cash decision.

## 16. Compounding Learning Contract

### 16.1 Outcome Attribution

Every trade, non-trade, hold, veto, missed opportunity, and rejected hypothesis
must be attributed across:

- contributing and contradicting sources;
- graph path;
- model and model version;
- classical versus quantum contribution;
- pattern method;
- strategy version;
- Akber stage decision;
- risk and Router decision;
- PaperOps and broker lifecycle;
- execution costs and slippage;
- market regime;
- system defect or provider outage.

### 16.2 Proposal Generation

Postmortems may generate proposals for:

- adding or removing an optional confirmation;
- adjusting a pre-authorised threshold range;
- changing a source trust proposal;
- narrowing an instrument mapping;
- changing an expiry or horizon;
- changing a strategy weight inside a frozen range;
- collecting a missing provider field;
- retiring a failed relationship;
- creating an emerging strategy.

### 16.3 Challenger Testing

Every proposal receives:

- parent version;
- exact change diff;
- rationale tied to outcome evidence;
- frozen comparison dataset;
- incumbent and challenger results;
- overfit and multiple-testing checks;
- forward-shadow requirement;
- rollback rule;
- admission decision.

Qadam may automatically run these tests. It may not repeatedly mutate the same
holdout or accept a challenger merely because its in-sample curve improved.

### 16.4 Automatic Paper-Version Promotion

A declarative strategy version may activate automatically for paper discovery
only when:

- the change lies within a pre-authorised parameter and risk envelope;
- the incumbent comparison is fair and frozen;
- holdout, costs, stability, and negative controls pass for its evidence class;
- required forward-shadow evidence passes;
- no risk or authority field expands;
- rollback and monitoring are present;
- the promotion checker passes;
- activation is recorded as a new version, never an overwrite.

Code, prompts, secrets, provider contracts, live capital, and risk-envelope
expansion remain outside automatic promotion.

## 17. Modular Implementation Phases

## QEG-0 - Baseline Freeze, Ownership, And Non-Interference

### Objective

Record exact current truth and prove this programme will extend existing owners
without overwriting certified work or the dashboard UX.

### Build

- Re-run current PaperOps, edge-engine, backtest, evidence-fit, reliability,
  dashboard, and documentation checks.
- Inventory all producers and consumers of source, graph, pattern, experiment,
  strategy, decision, and outcome artifacts.
- Record dirty worktree files and preserve unrelated changes.
- Identify legacy graph artifacts and mark them `legacy_reference_only`.
- Define protected dashboard routes and snapshot current production visuals.
- Register the new phase ladder in dynamic-plan status.

### Artifacts

- `data/runtime/qadam_qeg_baseline.json`
- `data/runtime/qadam_qeg_artifact_ownership.json`
- `data/runtime/qadam_qeg_compatibility_matrix.json`
- `data/runtime/qadam_qeg_dashboard_ux_baseline.json`

### Acceptance

- No source of truth has two active owners.
- Existing safety and PaperOps checks pass or have explicit pre-existing
  blockers.
- Legacy graph artifacts cannot override current state.
- Dashboard route and UX hashes are frozen for regression testing.

## QEG-1 - Temporal Ontology And Authority Contract

### Objective

Define schemas, temporal semantics, trust layers, and write authority before
creating graph data.

### Build

- Implement typed node, edge, claim, experiment, and graph-delta schemas.
- Implement evidence-state and claim-state enumerations.
- Implement temporal and provenance validators.
- Implement authority-field validators for all graph records.
- Define stable identity, alias, dedupe, and supersession rules.
- Define public-safe projection rules.

### Code And Checks

- `orchestrator/qadam_temporal_graph_contracts.py`
- `scripts/check_qadam_temporal_graph_contracts.py`
- focused schema and negative-safety tests.

### Acceptance

- Every record has provenance and time semantics.
- Observation, inference, testing, and governance cannot be confused.
- Unsafe authority probes fail closed.
- Future-dated evidence is rejected from point-in-time queries.

## QEG-2 - Local Graph Store And Deterministic Rebuild

### Objective

Create the append-only event store and rebuildable local query index.

### Build

- Implement append-only graph event partitions.
- Implement atomic generation commits and parent-generation lineage.
- Implement SQLite WAL index and deterministic rebuild.
- Implement FTS and graph-neighbour queries without external services.
- Implement checksums, row counts, dedupe, and crash-safe resume.
- Implement disk ceilings, compression, retention, and rebuildable-index cleanup.
- Register locks and ownership with the permanent reliability system.

### Code And Checks

- `orchestrator/qadam_temporal_graph_store.py`
- `scripts/rebuild_qadam_temporal_graph.py`
- `scripts/check_qadam_temporal_graph_store.py`
- interruption, concurrency, idempotency, corruption, and disk-limit tests.

### Acceptance

- Rebuilding twice produces identical logical records and checksums.
- Interrupted writes leave the previous generation valid.
- Duplicate logical writes do not create duplicate nodes or edges.
- Derived indexes can be deleted and rebuilt safely.
- Research storage cannot become Git-trackable.

## QEG-3 - Claim And Reference Registry

### Objective

Turn the attached Qadam blueprint and its URL library into a classified,
verifiable research corpus rather than operational truth.

### Build

- Copy the attachment into ignored raw intake storage by checksum.
- Parse headings, statements, URLs, papers, repositories, products, and internal
  architecture claims.
- Create atomic claim and reference records.
- Classify all references by source class.
- Reconcile internal claims against current code, docs, and runtime.
- Mark obsolete `v1`, five-agent, 300-market, calendar-quantum, and unimplemented
  options-architecture claims as superseded, proposed, or unverified as
  appropriate.
- Add verification queues for primary and high-value secondary sources.
- Build curated public-resource projections.

### Code And Checks

- `orchestrator/qadam_claim_reference_registry.py`
- `scripts/check_qadam_claim_reference_registry.py`
- `data/runtime/qadam_claim_registry_summary.json`
- `data/runtime/qadam_reference_registry_summary.json`

### Acceptance

- Every imported URL has a source class and verification state.
- Imported social, vendor, performance, or architecture claims cannot become
  market evidence or strategy authority merely because they were indexed.
- Provider-backed social observations may still become research evidence when
  they pass Qadam's normal source, provenance, freshness, and independence
  contracts.
- Current Qadam truth and historical design are separated.
- Public docs cannot consume unreviewed claims as fact.

## QEG-4 - Canonical Source, Event, Entity, And Instrument Graph

### Objective

Materialize current and historical Qadam evidence into the graph.

### Build

- Add adapters for the canonical 41-source registry and 19-instrument universe.
- Ingest provider observations with publication and availability times.
- Resolve entities, sectors, countries, contracts, instruments, and proxies.
- Build event-to-entity, entity-to-sector, sector-to-instrument, and
  instrument-to-proxy relationships.
- Record source independence clusters and shared upstream dependencies.
- Add current price, regime, and contract-state nodes.
- Reconcile the separate power sleeve without silently modifying the core
  universe.

### Code And Checks

- `orchestrator/qadam_temporal_graph_ingestion.py`
- `scripts/check_qadam_temporal_graph_ingestion.py`
- source, identity, proxy, time-leakage, and universe-consistency tests.

### Acceptance

- All 41 sources and 19 instruments have graph identities and truthful states.
- Every evidence path can be traced to provider artifacts.
- No unavailable or forward-only source is represented as historical coverage.
- Entity and proxy ambiguity remains explicit.

## QEG-5 - Persistent Hypothesis And Experiment Memory

### Objective

Create immutable preregistration, novelty, attempt, and negative-result memory.

### Build

- Normalize existing Research Goals, pattern records, experiment registries,
  backtests, shadows, rejections, and postmortems.
- Implement attempt fingerprints and semantic novelty checks.
- Implement multiple-testing family accounting.
- Preserve duplicate and negative attempts without granting independent count.
- Link regimes, failure reasons, and retest conditions.
- Create query APIs for prior similar hypotheses and failure modes.

### Code And Checks

- `orchestrator/qadam_experiment_memory.py`
- `scripts/check_qadam_experiment_memory.py`
- `data/runtime/qadam_experiment_memory_summary.json`
- duplicate, holdout-reuse, novelty, and negative-memory tests.

### Acceptance

- Every new test is preregistered before outcomes are read.
- Duplicate attempts cannot inflate evidence.
- Prior failures are returned during hypothesis generation.
- Holdout reuse and parameter-search drift fail closed.

## QEG-6 - Bounded Independent Research Fan-Out

### Objective

Use Qadam's Python, local LLM, frontier LLM, classical, and quantum roles as
independent specialists whose outputs become validated graph proposals.

### Build

- Add versioned task packets and output schemas for each role.
- Freeze evidence per research round.
- Prevent cross-agent anchoring before first-pass completion.
- Add deterministic merge, contradiction, citation, and unsupported-claim
  checks.
- Add token, time, provider-call, and concurrency budgets.
- Record model versions, latency, failures, and contribution.

### Code And Checks

- `orchestrator/qadam_graph_research_fanout.py`
- `scripts/check_qadam_graph_research_fanout.py`
- model-unavailable, disagreement, hallucinated-citation, timeout, and budget
  tests.

### Acceptance

- Agent output cannot bypass deterministic graph validation.
- Agreement from models sharing the same source is not counted as independent
  evidence.
- Research continues safely when one model is unavailable.
- No model can write governed graph records or create trading authority.

## QEG-7 - Graph Pattern Discovery And Actionability Ranking

### Objective

Discover distinct relationships across the complete graph and prioritise those
closest to an honest paper decision.

### Build

- Implement the priority graph motifs in Section 11.
- Add historical analogue and path-change queries.
- Add support, contradiction, independence, decay, and regime features.
- Feed graph features into Pattern Score V3 rather than replacing it with an
  opaque graph score.
- Add a separate actionability vector and queue.
- Add novelty, mechanism, falsifier, and paperability gates.
- Continue beyond held top-ranked records to the bounded next records.

### Code And Checks

- `orchestrator/qadam_graph_pattern_discovery.py`
- `orchestrator/qadam_actionability_queue.py`
- `scripts/check_qadam_graph_pattern_discovery.py`
- `scripts/check_qadam_actionability_queue.py`

### Acceptance

- Candidate patterns are distinct and non-repetitive.
- Every pattern explains its evidence path in plain English.
- Research rank and actionability rank are visibly separate.
- The engine can find patterns outside the five core families.
- No pattern creates a strategy, candidate, or order directly.

## QEG-8 - Statistical, Backtest, And Forward-Evidence Integration

### Objective

Bind graph candidates to the existing frozen statistical and forward-testing
machinery.

### Build

- Generate preregistered experiments from eligible graph candidates.
- Freeze the exact graph generation and point-in-time query watermark before
  labels or outcomes are read.
- Reuse the canonical score tape, labels, costs, and point-in-time lake.
- Run focused programmes first and whole-universe challengers within budget.
- Write every result and rejection into experiment memory and graph lineage.
- Add counterfactual no-order and missed-opportunity maturation.
- Prevent graph search from leaking holdout outcomes back into feature design.

### Code And Checks

- `orchestrator/qadam_graph_experiment_bridge.py`
- `scripts/check_qadam_graph_experiment_bridge.py`
- backtest, leakage, false-discovery, cost, and forward-maturity checks.

### Acceptance

- Graph and backtest counts reconcile exactly.
- Every tested relationship has immutable preregistration.
- Negative controls and rejected results remain queryable.
- Historical results cannot become current triggers or paper proof.

## QEG-9 - Nonlinear And Quantum Challenger Integration

### Objective

Apply nonlinear and IBM Quantum methods only where they answer a suitable,
frozen question and measure incremental value fairly.

### Build

- Add nonlinear-suitability scoring and rationale.
- Add matched classical challenger selection.
- Add simulator-before-hardware staging and cost ceilings.
- Link IBM, Q-CTRL, and Qiskit results to exact graph and experiment versions.
- Record classical-preferred and failed quantum outcomes as durable knowledge.
- Prohibit arbitrary weekly or activity-driven quantum runs.

### Code And Checks

- `orchestrator/qadam_graph_quantum_challenger.py`
- `scripts/check_qadam_graph_quantum_challenger.py`
- fairness, lineage, budget, repeatability, and authority tests.

### Acceptance

- Classical and quantum lanes receive identical evidence.
- Hardware state and cost are truthful.
- Quantum output cannot originate or approve a trade.
- Only measurable out-of-sample incremental value affects strategy evidence.

## QEG-10 - Strategy Foundry V4 And Automatic Paper Admission

### Objective

Turn surviving graph evidence into versioned core refinements or emerging
strategies and admit bounded declarative paper versions automatically when
pre-authorised criteria pass.

### Build

- Implement the declarative strategy schema.
- Map graph candidates to core or emerging destinations.
- Link complete source, experiment, strategy, and Research Goal lineage.
- Add rejection and retirement records.
- Add automatic paper-admission checks inside the frozen envelope.
- Require deterministic Python governance to sign each admission with the exact
  strategy version, policy version, evidence hashes, timestamp, and expiry.
- Prohibit Gemma, Gemini, nonlinear models, and quantum review from signing
  their own strategy admission.
- Add version activation, monitoring, expiry, rollback, and supersession.
- Keep code, prompt, provider, live-capital, and expanded-risk changes outside
  automatic authority.

### Code And Checks

- `orchestrator/qadam_strategy_foundry_v4.py`
- `orchestrator/qadam_paper_strategy_admission.py`
- `scripts/check_qadam_strategy_foundry_v4.py`
- `scripts/check_qadam_paper_strategy_admission.py`

### Acceptance

- Qadam is not limited to the five core families.
- Every strategy version is immutable and reversible.
- Weak patterns are rejected before Akber.
- Every automatic admission is deterministic, signed, expiring, and bound to
  exact evidence and policy versions.
- Automatic admission cannot expand risk or create a broker write.

## QEG-11 - Evidence-Fit Akber And Higher-Frequency Discovery Loop

### Objective

Make complete low-risk setups progress reliably without weakening hard market
or portfolio controls.

### Build

- Integrate graph evidence paths into same-generation decision packets.
- Map evidence explicitly into Akber's Context, Catalyst, Confirmation, Risk,
  Execution, and Postmortem Learning stages.
- Implement the evidence-alternative matrix and explicit haircuts.
- Recalibrate soft thresholds from historical and forward ablations.
- Keep hard current spread, liquidity, price, expectancy, invalidation, route,
  and risk requirements.
- Process the bounded top-K actionability queue, not one top record only.
- Create decision-time shadow synchronously before Router evaluation.
- Measure conversion by evidence profile and strategy family.

### Code And Checks

- Extend `orchestrator/qadam_akber_evidence_fit.py`.
- Extend `orchestrator/qadam_akber_filter_v3.py`.
- Add `orchestrator/qadam_graph_active_discovery.py`.
- Add `scripts/check_qadam_graph_active_discovery.py`.

### Acceptance

- Available evidence is no longer reported missing because of contract shape.
- Missing and adverse remain distinct.
- A held first setup does not stop evaluation of other distinct setups.
- Threshold changes have empirical ablation evidence.
- Akber pass remains research eligibility, not execution approval.

## QEG-12 - Multi-Setup Router And Canonical PaperOps Integration

### Objective

Route every distinct clean paper setup through the existing guarded Alpaca
Paper path with no duplicate or exposure ambiguity.

### Build

- Add batch-safe single-state Router decisions per setup.
- Preserve unique candidate identity and idempotency.
- Add exposure-cluster and same-thesis duplicate checks.
- Reconcile current risk capacity after each accepted setup before evaluating
  the next.
- Add submit/fill/open/close lifecycle polling and stale-order policy.
- Keep direct prediction-market instruments research-only unless separately
  governed.
- Ensure canonical PaperOps consumes the new handoff without a parallel route.

### Code And Checks

- Extend `orchestrator/qadam_router_v3_paperops.py`.
- Extend the canonical PaperOps handoff adapter and wrapper.
- Add `scripts/check_qadam_multi_setup_paperops.py`.
- Run idempotency, duplicate, partial-fill, retry, market-close, drawdown, and
  wrong-endpoint negative probes.

### Acceptance

- Every setup has exactly one final Router state.
- Multiple distinct setups may progress in one day.
- Duplicate exposure and retry cannot duplicate orders.
- Only canonical PaperOps can write Alpaca Paper.
- Live-capital endpoint probes fail closed.

## QEG-13 - Outcome Graph, Postmortems, And Self-Improvement

### Objective

Close the loop so every decision improves persistent knowledge.

### Build

- Link fills, positions, exits, costs, and outcomes to exact strategy and graph
  versions.
- Mature no-order, hold, veto, and missed-opportunity counterfactuals.
- Generate source, model, quantum, Akber, risk, Router, and execution
  attribution.
- Generate bounded improvement proposals.
- Run incumbent-versus-challenger tests automatically.
- Promote eligible declarative paper versions and preserve rollback.
- Retire persistently weak hypotheses and strategies.

### Code And Checks

- `orchestrator/qadam_graph_outcome_learning.py`
- `orchestrator/qadam_strategy_challenger_tournament.py`
- `scripts/check_qadam_graph_outcome_learning.py`
- `scripts/check_qadam_strategy_challenger_tournament.py`

### Acceptance

- Every trade and non-trade has complete lineage.
- No outcome silently mutates code, prompts, risk, or live authority.
- Negative results affect future novelty and prioritisation.
- Strategy promotion requires fair challenger evidence and remains reversible.

## QEG-14 - Dashboard, Whitepaper, User Guide, And Telegram

### Objective

Explain the compounding loop and higher-frequency paper-discovery state without
changing the dashboard's protected structure or creating AI-slop surfaces.

### Build

### Dashboard Enrichment

- Preserve every current route and established UX.
- Data Sources: show graph contribution, independence cluster, freshness, and
  verification class inside existing expandable details.
- Trading Universe: show entity, sector, proxy, and strategy relationships.
- Pattern Recognition: show the evidence path, support, contradiction,
  observation range, research rank, actionability, status lifecycle, and next
  destination.
- Quantum Edge: show the exact matched classical comparison and incremental
  conclusion.
- Trading Strategies: show core refinements, emerging strategies, version
  lineage, evidence history, and self-refinement.
- Decision Room: show the active queue, Akber stage, missing versus adverse
  evidence, risk state, and why each setup progressed or stopped.
- Order Monitor: show only real canonical PaperOps and Alpaca Paper lifecycle.
- Results & Lessons: show outcome -> supported lesson.
- Tests & Improvements: show proposal -> challenger -> review -> applied paper
  version -> next Observe cycle.
- System: show graph generation, health, disk use, backlog, and repair state.

### Telegram

- Send only material changes.
- Report the most interesting new relationship, what strengthened or weakened,
  what was rejected, current paper action, and next test.
- Mention quantum only when the quantum conclusion or evidence changed.
- Deduplicate repeated questions and unchanged conclusions.
- Remain short, public-safe, command-disabled, and non-promotional.

### Documentation

- Update the Whitepaper only with verified current claims.
- Update the User Guide with graph status and strategy-version reading guidance.
- Publish a curated resource registry divided into primary references,
  implementation references, research leads, and archived/superseded material.

### Checks

- `scripts/check_qadam_qeg_dashboard.py`
- `scripts/check_qadam_qeg_telegram.py`
- existing dashboard anti-slop, route, accessibility, documentation parity, and
  visual regression checks.

### Acceptance

- No route or protected layout changes.
- No duplicated full lifecycle prose.
- Every number is provenance-backed and freshness-labelled.
- Public surfaces cannot create research, strategy, approval, order, or proof.

## QEG-15 - Autonomous Scheduling, Reliability, And Storage Safety

### Objective

Run the complete graph-assisted research and paper loop unattended without
recreating prior disk, stale-artifact, concurrency, or circuit failures.

### Build

- Add one resource-aware owner for graph updates.
- Integrate with canonical immutable generations, locks, leases, and lock order.
- Define market-hours scan cadence and lower-frequency historical maintenance.
- Add provider, model, graph, disk, and PaperOps circuit classes.
- Add safe retry and revalidation.
- Add backpressure for model and graph queues.
- Add disk soft and hard ceilings.
- Compress canonical research events and prune only rebuildable indexes,
  temporary extracts, and superseded dashboard projections.
- Add restart, sleep, network-loss, provider-rate-limit, and partial-write
  recovery.
- Add a repair queue that cannot edit code or authority silently.

### Code And Checks

- Extend `orchestrator/qadam_operator_service.py` and its resource registry.
- Add `scripts/check_qadam_qeg_operator_reliability.py`.
- Run chaos, concurrency, interruption, low-disk, stale-source, stale-index, and
  broker-unavailable tests.

### Acceptance

- The service resumes from the last complete generation.
- Disk growth remains within the configured daily and total budgets.
- Rebuildable data can be cleaned without losing canonical evidence.
- A dashboard or Telegram failure cannot stop research or PaperOps.
- A research failure cannot create an unsafe broker retry.

## QEG-16 - End-To-End Certification And Real-Market Trial

### Objective

Certify implementation integrity, then measure real conversion over eligible
market time without claiming empirical success early.

### Build

- Create `scripts/check_qadam_compounding_evidence_graph.py`.
- Write
  `data/runtime/qadam_compounding_evidence_graph_certification.json`.
- Run all prior phase checks and negative probes.
- Run a graph-assisted active-discovery trial for at least five eligible market
  days after cutover.
- Continue the current five-market-day evidence-fit trial only if generation,
  policy, and candidate comparability remain valid; otherwise start a clearly
  versioned new trial without backfilled time.
- Publish daily conversion and defect attribution.

### Certification Groups

1. ontology and provenance;
2. temporal leakage and point-in-time queries;
3. graph rebuild and storage safety;
4. claim and reference truth;
5. source and universe reconciliation;
6. experiment memory and novelty;
7. pattern discovery and actionability;
8. backtest and false-discovery controls;
9. quantum/classical fairness;
10. strategy admission and rollback;
11. Akber evidence fit;
12. multi-setup risk, Router, and PaperOps;
13. outcome and learning lineage;
14. dashboard and Telegram quality;
15. reliability and unattended recovery;
16. paper-only and live-capital negative probes.

### Certification States

- `implementation_incomplete`;
- `implementation_certified_evidence_maturing`;
- `active_discovery_trial_running`;
- `active_discovery_trial_complete`;
- `operating_as_designed`;
- `blocked`.

### Acceptance

- Every phase checker passes.
- Every graph record is reconstructable and provenance-backed.
- No duplicate experiment, strategy version, or paper order is created.
- Every complete actionable setup receives a decision within one fresh cycle.
- Multiple distinct setups can route in the same day when risk permits.
- All holds and no-trades have typed, correct reasons.
- No system defect suppresses a setup without a repair record.
- No live-capital, direct broker, proof-credit, or authority probe succeeds.
- The dashboard retains its existing UX and truthfully shows the new state.
- Real-time trial results are reported honestly, including zero-trade days.

## 18. Runtime Artifact Set

Large canonical records remain under ignored research storage. Dashboard-safe
summaries remain under `data/runtime/`.

Required summaries include:

- `qadam_temporal_graph_manifest.json`;
- `qadam_temporal_graph_health.json`;
- `qadam_claim_registry_summary.json`;
- `qadam_reference_registry_summary.json`;
- `qadam_experiment_memory_summary.json`;
- `qadam_graph_pattern_candidates.json`;
- `qadam_actionability_queue.json`;
- `qadam_graph_strategy_versions.json`;
- `qadam_graph_active_discovery_funnel.json`;
- `qadam_graph_outcome_learning_summary.json`;
- `qadam_qeg_repair_queue.json`;
- `qadam_qeg_phase_status.json`;
- `qadam_compounding_evidence_graph_certification.json`.

Every summary must include generated time, source generation, freshness,
authority boundary, and blocker list.

## 19. Test Matrix

### 19.1 Unit And Schema Tests

- node and edge identity;
- temporal validation;
- provenance validation;
- claim classification;
- experiment fingerprinting;
- novelty and duplicate detection;
- strategy version validation;
- evidence-profile alternatives;
- actionability ranking;
- risk and idempotency identity.

### 19.2 Integration Tests

- provider observation -> graph -> pattern;
- pattern -> preregistered experiment -> result;
- result -> strategy version -> Akber;
- Akber -> risk -> Router -> canonical PaperOps;
- fill -> outcome -> postmortem -> proposal -> challenger;
- strategy rollback;
- dashboard and Telegram projection.

### 19.3 Statistical Tests

- point-in-time leakage;
- holdout isolation;
- false-discovery family accounting;
- negative controls;
- regime stability;
- cost and spread sensitivity;
- quantum/classical parity.

### 19.4 Reliability Tests

- crash during graph commit;
- duplicate event replay;
- laptop sleep and restart;
- network loss;
- provider rate limiting;
- model timeout;
- SQLite lock contention;
- disk soft and hard ceilings;
- stale dashboard publication;
- ambiguous broker retry.

### 19.5 Negative Safety Tests

- model attempts governed graph write;
- graph edge attempts strategy promotion;
- social claim attempts source-quorum credit;
- historical event attempts current-trigger use;
- backtest attempts proof credit;
- quantum output attempts trade approval;
- duplicate setup attempts second order;
- strategy version attempts risk-envelope expansion;
- dashboard or Telegram attempts command creation;
- live broker endpoint attempt.

## 20. Dynamic Plan Governance

Implementation must maintain:

- `data/runtime/qadam_qeg_phase_status.json`;
- `docs/qadam-compounding-evidence-graph-active-paper-implementation-log.md`.

After each phase:

1. run its checker;
2. record implementation and empirical status separately;
3. record deviations and discoveries;
4. update later phase assumptions when evidence requires it;
5. preserve all constitutional boundaries;
6. do not mark a phase complete because code exists if real evidence or soak is
   still pending;
7. do not implement later phases when an earlier data or safety contract is
   genuinely blocked.

The dynamic plan may alter implementation details, but not paper-only status,
the canonical broker route, hard risk boundaries, point-in-time discipline,
the protected dashboard structure, or the prohibition on forced trades.

## 21. Implementation Order And Dependencies

```text
QEG-0 baseline
  -> QEG-1 ontology
  -> QEG-2 graph store
  -> QEG-3 claim registry
  -> QEG-4 evidence graph
  -> QEG-5 experiment memory
  -> QEG-6 research fan-out
  -> QEG-7 graph discovery and actionability
  -> QEG-8 backtest and forward bridge
  -> QEG-9 nonlinear and quantum challenger
  -> QEG-10 strategy foundry and paper admission
  -> QEG-11 evidence-fit active discovery
  -> QEG-12 Router and PaperOps
  -> QEG-13 outcome learning
  -> QEG-14 public visibility
  -> QEG-15 unattended reliability
  -> QEG-16 certification and real-market trial
```

QEG-3 and the storage-independent parts of QEG-5 may be developed after QEG-1,
but neither may write canonical graph state before QEG-2 passes. Dashboard work
must not begin before the underlying artifacts are stable.

## 22. Expected Strategy Impact

### Crude Oil Energy Security

- Connect conflict, shipping, physical disruption, energy entities, and crude
  proxies through explicit exposure paths.
- Distinguish repeated headlines from independent evidence.
- Prioritise active disruptions with current listed-market confirmation.

### Defence Geopolitical Repricing

- Link STOCK Act disclosures, defence contracts, conflict events, companies,
  and XAR/ITA/LMT/PPA exposures.
- Treat delayed disclosures as thematic evidence, not real-time triggers.
- Allow a fresh defence catalyst to activate historically supported context.

### Semiconductor Policy And Options Asymmetry

- Link policy, filings, patents, supply dependencies, companies, and sector
  proxies.
- Resolve direction from affected entities and market response.
- Keep options-distribution concepts as under-evidenced until suitable options
  history and current flow are available.

### Silver Macro Liquidity

- Represent rates, liquidity, dollar, gold, equity, and silver regime states as
  numeric temporal nodes.
- Detect regime transitions and historical analogues.
- Use market confirmation appropriate to a regime strategy rather than an event
  catalyst.

### Prediction-Market Geopolitical Dislocation

- Resolve Kalshi and Polymarket contracts to normalized events.
- Compare compatible contract probabilities and listed-market states.
- Track divergence, liquidity, settlement rules, and expiry explicitly.
- Keep direct venue execution outside Alpaca Paper unless separately governed.

### Power Scarcity And Congestion

- Keep the power sleeve emerging until independent evidence matures.
- Connect load, weather, generation, congestion, regional power prices, and
  listed proxies.
- Allow it to become a pattern-sourced strategy through the same admission
  lifecycle rather than manual installation.

## 23. Expected Trade-Frequency Impact

The implementation should increase activity through better conversion, not by
declaring weak patterns valid.

Expected improvements are:

- more strategy-specific current triggers;
- more distinct hypotheses considered per cycle;
- fewer false missing-evidence holds;
- fewer stale decision-time packet failures;
- continued evaluation after the first setup is held;
- faster automatic admission of bounded declarative paper strategies;
- multiple independent same-day setups when risk permits;
- quicker retirement of hypotheses that repeatedly waste research capacity;
- improved source and strategy prioritisation from real outcomes.

The correct post-implementation claim is:

> Qadam is structurally capable of discovering, testing, admitting, and routing
> more distinct low-risk paper experiments without bypassing its hard risk
> controls.

The incorrect claim is:

> Qadam will definitely trade every day or make money.

Those outcomes still depend on real market evidence, execution conditions, and
future performance.

## 24. Final Definition Of Done

The programme is fully implemented only when:

1. One canonical temporal graph covers current sources, events, entities,
   instruments, patterns, experiments, strategies, decisions, and outcomes.
2. The graph rebuilds deterministically from append-only canonical events.
3. Every node and edge has temporal and provenance lineage.
4. The attached blueprint and all references are classified rather than
   imported as truth.
5. Current, historical, proposed, unverified, superseded, and rejected claims
   are separated.
6. Every hypothesis is preregistered and checked against prior attempts.
7. Negative results alter future novelty and research prioritisation.
8. Independent model research is merged deterministically and cannot create
   authority.
9. Full-universe graph search produces distinct, mechanism-backed questions.
10. Statistical, forward, nonlinear, and quantum results preserve fair
    baselines and point-in-time safety.
11. Surviving evidence can refine core strategies or create emerging ones.
12. Declarative paper strategy versions can be admitted automatically only
    inside the frozen paper-risk envelope.
13. Research rank and actionability rank are separate.
14. Available evidence reaches Akber in the correct profile and generation.
15. The active loop evaluates all bounded distinct actionable setups, not only
    the first record.
16. Multiple same-day paper setups are possible without duplicate exposure or
    idempotency failure.
17. Canonical PaperOps remains the only Alpaca Paper write route.
18. Every trade, non-trade, hold, veto, and miss feeds persistent attribution.
19. Improvement proposals receive fair challenger tests and reversible
    versioning.
20. Dashboard UX and routes remain intact and explain the new lineage plainly.
21. Telegram sends only material, concise, non-repetitive research changes.
22. Disk, restart, concurrency, stale-artifact, and provider failures recover
    safely unattended.
23. The umbrella certification passes all safety and integrity probes.
24. The real-market active-discovery trial completes in actual elapsed time and
    reports conversion honestly.

At that point Qadam will have moved from a broad research factory with many
separate artifacts to a compounding evidence system: each observation can form
a relationship, each relationship can become a frozen experiment, each result
can refine strategy selection, each eligible setup can reach a bounded paper
decision, and each outcome makes the next cycle better informed.
