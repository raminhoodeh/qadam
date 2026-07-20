# Qadam Past Learning And Backtest Gap Closure Implementation Plan

**Plan ID:** `qadam-past-learning-backtest-gap-closure-v1`

**Status:** Implemented and certified `complete_no_edge_found`

**Prepared:** 19 July 2026

**Scope:** Historical research, point-in-time evidence, backtesting, and
proposal-only learning

**Priority providers:** Kalshi, Unusual Whales, Polymarket, and STOCK Act

## Implementation Result - 20 July 2026

The PLBG overlay is implemented end to end. All implementation-stage checks
from `PLBG-0` through `PLBG-14` pass, and the final certification passes as
`complete_no_edge_found`. Every statistically eligible focus-provider lane was
tested; unavailable lanes were explicitly classified rather than fabricated.

The implemented result:

- inventoried more than 2,200 historical learning and review records without rewriting
  their source files;
- converted repeated legacy pattern prose into 10 distinct, deduplicated
  research questions with no inherited edge, strategy, or execution authority;
- reconciled future learning to the canonical 41-source, 19-instrument, zero
  validated-edge contract;
- retained 746,275 real provider-backed historical rows while separating
  acquisition coverage from empirical test coverage;
- classified all 41 sources and all 19 instruments without a generic missing
  state;
- recorded honest provider limitations for Kalshi, Polymarket, STOCK Act, and
  Unusual Whales;
- evaluated 72,875 derived point-in-time focus rows through 2,652 hypotheses,
  2,532 untouched-holdout results, and 211 executed negative controls;
- tested Kalshi-only, Polymarket-only, prediction-market consensus and
  disagreement, STOCK Act filing events, multi-source interactions, all five
  core strategy families, and strategy-agnostic discovery without finding a
  result that survived every promotion gate;
- preserved the clean paper epoch byte-for-byte and created no trade candidate,
  paper order, broker write, proof credit, or simulated calendar progress; and
- exposed public-safe research progress to the existing dashboard view models
  and a short, review-only Telegram candidate without changing dashboard
  navigation or authority.

Canonical current results are written under `data/runtime/` by
`scripts/run_qadam_learning_backtest_gap_closure.py`; generated runtime
artifacts, rather than the snapshot figures above, remain the source of truth.

## 1. Executive Decision

Qadam should not discard its previous daily learning passes, but it also must
not treat them as validated learning. They are historical records of what the
system noticed, held, rejected, reported, or failed to deliver at a particular
time. Their correct role is to become a typed, deduplicated research-memory
layer that can propose questions for fresh testing.

Qadam should also not describe its first historical backtest as a complete test
of the whole data and trading universe. Historical acquisition reached a valid
terminal state under the frozen OR-3 contract, but the empirical score tape was
materially narrower. This plan closes that difference without fabricating data
or forcing every unavailable source to become historically available.

The implementation has two linked objectives:

1. Convert past automation output into auditable research memory with no
   inherited authority.
2. Expand and rerun Qadam's point-in-time backtest, concentrating first on
   Kalshi, Polymarket, STOCK Act, and Unusual Whales.

The end state is not "Qadam found an edge." The end state is that Qadam has
tested the strongest available historical evidence honestly enough to know
whether an edge exists, does not exist, or cannot yet be measured.

## 2. Current Truth Baseline

The implementation must begin by freezing the following observed baseline.
Every number must be regenerated from canonical artifacts before work starts;
none may be copied into runtime as a hardcoded success value.

### 2.1 Historical Acquisition Baseline

| Measure | Current state |
| --- | ---: |
| Canonical sources | 41 |
| Canonical watched instruments | 19 |
| Historical acquisition partitions | 360 |
| Acquired partitions | 223 |
| Honestly classified unavailable partitions | 137 |
| Remaining unclassified partitions | 0 |
| Provider-backed rows | 746,275 |
| Supplemental feature rows | 0 |
| Unusual Whales eligible rows | 0 |

`complete_with_classified_gaps` means the acquisition contract terminated
honestly. It does not mean every source supplied usable history or every row
entered the statistical test.

### 2.2 Empirical Backtest Baseline

| Measure | Current state |
| --- | ---: |
| Backtested source signals | 5 of 41 |
| Backtested instruments | 17 of 19 |
| Score rows | 40,242 |
| Forward labels | 40,126 |
| Typed missing labels | 116 |
| Independent score-label pairs | 11,933 |
| Walk-forward folds | 1,332 |
| Attempted hypotheses | 360 |
| Validated edges | 0 |
| Leakage violations | 0 |

The five source signals were `kalshi`, `polymarket`, `sec_edgar`, `stock_act`,
and `usgs`. Direct `KALSHI:EVENTS` and `POLYMARKET:EVENTS` instruments were not
backtested. The tested strategy set contained three named core strategies plus
one strategy-agnostic lane; it did not provide direct named coverage of the
full five-family strategy universe.

All 360 historical hypotheses were rejected after the relevant untouched
holdout, cost, stability, baseline, concentration, and false-discovery checks.
That is a valid negative result, not a system failure.

### 2.3 Focus Provider Baseline

| Provider | Current acquired state | Material gap |
| --- | --- | --- |
| Kalshi | 5,034 daily historical rows from 2021-2026; five earlier partitions classified pre-inception | Event rows are useful as signals, but direct contract identity, lifecycle, settlement, and tradable-instrument history are not complete enough for `KALSHI:EVENTS` testing |
| Polymarket | 28,275 daily historical rows from 2023-2026; earlier partitions classified pre-inception or no relevant records | Event rows are useful as signals, but condition, outcome token, lifecycle, liquidity, resolution, and direct-instrument history are incomplete for `POLYMARKET:EVENTS` testing |
| STOCK Act | 29,824 official House filing-index rows from 2016-2026 | Current rows are filing metadata, not parsed transaction details; issuer, buy/sell direction, amount range, amendment, and transaction-date analysis is not yet supported |
| Unusual Whales | Adapter and bounded plan exist, but no provider capture has completed | Credential and terms state are not currently certified, no eligible feature rows exist, and all Unusual Whales ablations are blocked |

### 2.4 Past Learning Baseline

| Measure | Current state |
| --- | ---: |
| Daily automation snapshots | 516 |
| Distinct local dates | 31 |
| Date range | 16 June 2026 to 19 July 2026 |
| Legacy source contract | 37 sources |
| Legacy instrument contract | 21 instruments |
| Strategy learning changes applied | 0 |
| V3 attribution records | 55 |
| V3 improvement proposals | 55 |
| Applied learning versions | 0 |

The old daily summaries sometimes reported one validated edge while the current
canonical registry contains zero. The old count must not be carried forward.
The 516 snapshots are useful only after contract reconciliation, provenance
classification, and deduplication.

## 3. Definition Of Backtest Gap Closure

"Fill all backtest gaps" must not be interpreted as forcing all missing values
to zero. A gap is closed when it reaches exactly one of these states:

| Closure state | Meaning |
| --- | --- |
| `provider_backed_acquired` | The historical record was obtained from an approved provider with complete provenance and usable point-in-time semantics |
| `approved_proxy_with_basis_risk` | A documented proxy is used, and its mismatch to the intended instrument is measured |
| `forward_only` | Reliable history does not exist, but a compliant forward capture has started |
| `terminally_unavailable` | History is unavailable, pre-inception, unsupported, unlicensed, immaterial, or impossible to align; the reason is explicit |

No source, instrument, strategy, or relationship may remain in a generic
`missing` state at certification. Terminal classifications must remain visible
in coverage denominators so the dashboard cannot imply broader evidence than
Qadam actually has.

### 3.1 Relationship To The Existing Qadam Engine

This plan is not a parallel product, replacement architecture, or new feature
stack. It is a focused implementation overlay on the already-built
operator-ready edge engine:

| This plan | Existing canonical ownership |
| --- | --- |
| PLBG-0 to PLBG-3 | OR-0, OR-2R, and OR-3 truth, safety, provider, and acquisition contracts |
| PLBG-4 to PLBG-8 | OR-3 provider-backed historical source and price lake |
| PLBG-9 | OR-4 point-in-time evidence |
| PLBG-10 | OR-5 Pattern Score V3 and OR-6 historical score tape |
| PLBG-11 | OR-7 labels, OR-8 statistical backtest, and OR-9 nonlinear/quantum review |
| PLBG-12 | OR-10 edge evidence and OR-16 learning attribution |
| PLBG-13 | OR-13 forward shadow and the existing proposal-first learning loop |
| PLBG-14 | OR-17 dashboard and Telegram projections |
| PLBG-15 | OR-19 certification |

Implementation should extend the canonical modules where responsibility
already exists, especially:

- `orchestrator/qadam_source_history_acquisition.py`
- `orchestrator/qadam_provider_backfill.py`
- `orchestrator/qadam_point_in_time_evidence.py`
- `orchestrator/qadam_pattern_score_v3.py`
- `orchestrator/qadam_pattern_score_tape.py`
- `orchestrator/qadam_forward_labels.py`
- `orchestrator/qadam_statistical_backtest.py`
- `orchestrator/qadam_edge_registry.py`
- `orchestrator/qadam_learning_attribution_v2.py`

New provider-specific modules should be small adapters behind these canonical
contracts. Downstream readers must not choose between competing V3 and V4 truth
artifacts. Compatibility aliases may remain temporarily, but each domain must
have one canonical writer and one declared schema owner.

## 4. Constitutional Boundaries

This plan is a research and learning plan. It must preserve the following
boundaries in every artifact and negative probe:

- Historical data cannot advance the real 30-day paper growth trial calendar.
- Backtests, simulations, and legacy records cannot receive paper proof ledger
  credit.
- Past learning cannot become a validated edge without a fresh canonical test.
- Provider records cannot create a trade candidate, qualified setup, risk
  approval, execution approval, paper order, broker write, or live-capital
  authority.
- Kalshi, Polymarket, STOCK Act, or Unusual Whales cannot satisfy source quorum
  alone.
- Prediction-market APIs are read-only research inputs under this plan. They are
  not execution venues.
- Unusual Whales remains supplemental and cannot replace Qadam's core baseline.
- Model prose, quantum review, and daily briefs cannot alter labels or
  retroactively change a historical score.
- Strategy, source-weight, model-routing, Akber-threshold, and risk-policy
  changes remain versioned proposals until separately reviewed and approved.
- Raw provider data and credentials remain under ignored research or secure
  secret paths and may never enter Git, dashboard payloads, logs, or Telegram.
- The active clean paper epoch remains isolated. Historical work may run beside
  guarded paper observation, but it cannot reset, pause, rewrite, or backfill
  that epoch.
- No result may promise returns or claim that an edge exists before the
  statistical and forward-evidence gates pass.

## 5. Target End-To-End Flow

```text
Legacy learning inventory
  -> provenance and contract reconciliation
  -> deduplicated research-memory records
  -> pre-registered research questions

Provider acquisition and identity repair
  -> immutable raw evidence
  -> normalized point-in-time records
  -> source and contract identity graphs
  -> source-price alignment

Frozen feature definitions
  -> historical score tape
  -> separate forward labels and cost model
  -> walk-forward and untouched-holdout backtests
  -> provider ablations and negative controls

Supported result
  -> learning attribution
  -> proposal only
  -> forward shadow observation
  -> later human-reviewed strategy refinement
```

Past learning may prioritize a research question, but it may not improve the
historical result merely by being repeated often. Provider data determines the
evidence; the frozen protocol determines whether it survives.

## 6. Canonical Data Contracts

Before provider-specific work begins, implement versioned contracts shared by
all lanes.

### 6.1 `LegacyLearningObservation`

Required fields:

- `legacy_observation_id`
- `original_artifact_path`
- `original_record_hash`
- `observed_at`
- `available_at`
- `local_date`
- `legacy_source_contract_version`
- `legacy_instrument_contract_version`
- `mapped_current_source_ids`
- `mapped_current_instrument_ids`
- `research_question`
- `strategy_family_at_time`
- `pattern_state_at_time`
- `quantum_review_state_at_time`
- `akber_state_at_time`
- `router_state_at_time`
- `reported_edge_count_at_time`
- `canonical_edge_count_after_reconciliation`
- `transport_state`
- `provenance_class`
- `duplicate_cluster_id`
- `eligible_as_historical_observation`
- `ineligibility_reasons`
- `authority`

Allowed provenance classes:

- `provider_lineage_verified`
- `system_snapshot_verified`
- `legacy_contract_reconciled`
- `unresolved_legacy_record`
- `fixture_or_synthetic`
- `transport_only_event`

Only records that existed before the tested outcome and retain adequate input
lineage may become historical observations. The other classes remain audit
memory.

### 6.2 `PredictionMarketContractIdentity`

Required fields:

- provider and venue
- event, series, market, contract, condition, and token identifiers where
  applicable
- title and normalized research theme
- outcome labels and side mapping
- creation, open, close, expiration, suspension, resolution, and settlement
  timestamps
- timestamp at which each state became publicly available
- contract version and identity aliases
- price scale and probability conversion
- liquidity, volume, spread, fee, and open-interest fields where available
- resolution source and result availability time
- archived, deleted, or superseded state
- macro theme and watched-instrument mappings
- provenance and checksum

### 6.3 `CongressionalDisclosureEvent`

Required fields:

- chamber and official document identifier
- filer identity and role
- owner type, including self, spouse, or dependent where available
- transaction date
- filing date
- public availability timestamp
- amendment and supersession lineage
- transaction type
- asset description
- issuer, ticker, CIK, sector, and historical symbol mapping
- disclosed amount range, never a fabricated exact notional
- reporting lag in calendar and trading days
- committee and policy-exposure tags
- source document checksum and parser version
- point-in-time eligibility state

### 6.4 `UnusualWhalesFeatureObservation`

Required fields:

- endpoint and provider record identity
- ticker and historical symbol mapping
- event timestamp
- conservative public availability timestamp
- retrieval timestamp
- feature family
- raw and normalized values
- expiration and strike identity where options are involved
- market-session and timezone state
- delayed, corrected, or revised state
- entitlement and retention class
- raw-retention permission state
- point-in-time eligibility state
- capture and parser versions

### 6.5 `HistoricalExperimentRegistration`

Required fields:

- immutable experiment ID
- research question and prior source
- provider and feature-set version
- strategy-informed or strategy-agnostic lane
- source and instrument universe
- direction and horizon
- entry, exit, cost, and proxy assumptions
- train, validation, and untouched-holdout boundaries
- purging and embargo policy
- baseline and negative-control definitions
- false-discovery family
- success, rejection, and insufficiency criteria
- dataset and code hashes
- authority flags

## 7. Implementation Stages

## PLBG-0 - Baseline Freeze And Safety Lock

### Objective

Freeze the current historical and learning state before any migration or new
provider acquisition changes the evidence set.

### Build

- Add `orchestrator/qadam_learning_backtest_baseline.py`.
- Add `scripts/check_qadam_learning_backtest_baseline.py`.
- Hash the current 41-source and 19-instrument contracts.
- Hash the current backfill manifest, point-in-time alignment, score tape,
  labels, statistical protocol, results, edge registry, daily learning history,
  attribution ledger, proposal ledger, and applied-version ledger.
- Record the active paper epoch identifier without modifying it.
- Assert that research outputs cannot invoke PaperOps or broker writes.
- Assert that `data/research` and provider raw paths are Git-ignored.
- Snapshot disk availability and establish bounded storage, API-call, retry,
  runtime, and provider-cost ceilings.

### Artifacts

- `data/runtime/qadam_learning_backtest_baseline.json`
- `data/runtime/qadam_learning_backtest_gap_registry.json`
- `data/runtime/qadam_learning_backtest_safety_audit.json`

### Acceptance

- Every input artifact has a hash or an explicit missing classification.
- The paper epoch ID and balance are observed but untouched.
- Negative probes prove zero candidates, orders, broker writes, proof credits,
  and paper-calendar changes.

## PLBG-1 - Past Learning Inventory And Quarantine

### Objective

Make every old learning record visible without letting stale contracts enter
the current learning loop.

### Build

- Add `orchestrator/qadam_legacy_learning_inventory.py`.
- Read all daily automation history, daily edge briefs, Telegram learning
  briefs, learning attribution, improvement proposals, quantum reviews, Akber
  results, router results, paper lifecycle outcomes, and delivery receipts.
- Preserve original record hashes and append-only ordering.
- Separate research content from delivery and operational telemetry.
- Detect duplicate reruns, same-day overwrites, repeated generic hypotheses,
  and snapshots whose only change was Telegram transport state.
- Quarantine all records using the obsolete 37-source and 21-instrument
  contracts until PLBG-2 reconciles them.
- Mark old `validated_edge_count=1` claims as
  `legacy_reported_not_canonical` when no matching current edge record exists.
- Never rewrite the source files.

### Artifacts

- `data/runtime/qadam_legacy_learning_inventory.json`
- `data/runtime/qadam_legacy_learning_duplicates.jsonl`
- `data/runtime/qadam_legacy_learning_quarantine.jsonl`
- `data/runtime/qadam_legacy_learning_transport_events.jsonl`

### Checks

- Source immutability check.
- Record-count reconciliation.
- Duplicate-cluster determinism check.
- Legacy edge-count denial test.
- Transport-event exclusion test.

### Acceptance

- Every old record is inventoried exactly once.
- Repeated transport failures do not become trading lessons.
- No quarantined record appears in current Pattern Score, Akber, Router, or
  PaperOps inputs.

## PLBG-2 - Learning Contract Reconciliation

### Objective

Convert eligible old observations into the current 41-source, 19-instrument
research-memory contract.

### Build

- Add explicit source and instrument alias maps.
- Map removed, renamed, merged, split, and newly introduced identifiers.
- Do not invent a mapping when an old instrument has no current equivalent.
- Recompute current edge state from the canonical registry rather than copying
  old counts.
- Reconstruct the evidence available at each observation timestamp where
  provider lineage exists.
- Assign provenance classes and point-in-time eligibility.
- Extract stable research questions, source combinations, market mappings,
  Akber holds, quantum review states, and stated falsifiers.
- Create one normalized observation per distinct system belief, not per rerun.
- Convert recurring unsupported ideas into test-priority metadata, not stronger
  confidence.
- Register research questions before new outcomes are loaded so hypothesis
  selection remains visible to the multiple-testing audit.

### Artifacts

- `data/runtime/qadam_legacy_to_current_contract_map.json`
- `data/research/learning_memory/version=1/legacy_observations.jsonl`
- `data/runtime/qadam_learning_memory_manifest.json`
- `data/runtime/qadam_learning_research_question_registry.jsonl`
- `data/runtime/qadam_learning_memory_rejections.jsonl`

### Acceptance

- Every migrated observation carries original and current lineage.
- The migrated set contains no fixtures or unresolved source identifiers.
- Research-question frequency does not change evidence confidence.
- Applied learning version count remains zero unless a later, separately
  approved proposal completes PLBG-13.

## PLBG-3 - Provider, Licensing, Credential, And Cost Gate

### Objective

Create an auditable acquisition contract for each focus provider before network
capture or archive parsing begins.

### Build

- Refresh official-interface, historical-depth, rate-limit, retention,
  internal-research, redistribution, and future-commercial-relicensing states.
- Record operator approvals separately from code and provider credentials.
- Keep credentials in the strict local secret store or macOS Keychain only.
- Treat every credential previously pasted into chat as exposed and require a
  rotated replacement before network use.
- Verify credentials with bounded read-only probes that never log secret
  material.
- Produce provider-specific request, storage, and cost ceilings.
- Refuse bulk capture if licensing, retention, raw-storage, or API entitlement
  remains unresolved.
- Permit normalized-only storage when raw retention is not approved.
- Record the difference between private internal research and any later
  commercial redistribution or customer use.

### Provider Gates

| Provider | Required gate |
| --- | --- |
| Kalshi | Verify the official read-only historical interface and direct credential state; Oddspipe may assist identity discovery but cannot substitute for official historical evidence |
| Polymarket | Verify Gamma and CLOB public-data terms, archive depth, request limits, and retention treatment |
| STOCK Act | Verify official House and Senate archive access, document retention, parser scope, and chamber coverage |
| Unusual Whales | Verify rotated token, endpoint entitlement, historical range, raw-retention rights, research use, request ceiling, and access expiry |

### Artifacts

- `data/runtime/qadam_focus_provider_contracts.json`
- `data/runtime/qadam_focus_provider_credential_truth.json`
- `data/runtime/qadam_focus_provider_cost_budget.json`
- `data/runtime/qadam_focus_provider_acquisition_readiness.json`

### Acceptance

- No fixture or local import is reported as a live provider connection.
- Every provider is `approved_bounded_capture`, `forward_only`, or
  `blocked_operator_action`.
- No secret value appears in tracked files or runtime summaries.

## PLBG-4 - STOCK Act Transaction Detail Lake

### Objective

Upgrade the current official filing-index history into point-in-time
transaction evidence without overstating what the disclosures reveal.

### Build

- Preserve the existing 29,824 filing-index records as the filing-event layer.
- Add official House and Senate document acquisition jobs where permitted.
- Download and checksum disclosure documents through bounded, resumable jobs.
- Parse actual transaction rows from PDFs, HTML, XML, or structured archives.
- Distinguish transaction date from filing date and public availability time.
- Use public availability time for all historical decisions.
- Track amendments, duplicate filings, replacements, and document versions.
- Normalize purchase, sale, exchange, option, and other transaction types.
- Preserve disclosed value bands as intervals; never convert them into a false
  exact position size.
- Resolve issuer, ticker, CIK, historical symbol, sector, and strategy exposure.
- Record unresolved assets rather than forcing ticker mappings.
- Calculate reporting lag and test lag buckets separately.
- Add filer, household, committee, chamber, sector, and event clusters so many
  related filings do not masquerade as independent source quorum.
- Join with SEC EDGAR only after source-independence controls are applied.

### Research Features

- net disclosed purchase and sale counts by issuer and sector
- lower-bound, midpoint-sensitivity, and upper-bound amount-band features
- filing velocity and change from trailing baseline
- bipartisan or cross-committee agreement
- defence and semiconductor policy exposure
- issuer concentration and crowding
- filing delay and stale-disclosure penalty
- amendment and reversal indicators

### Negative Controls

- random filer assignment
- shuffled filing dates within disclosure-lag buckets
- transaction-date lookahead probe
- unrelated-sector mapping
- duplicated-filing inflation probe

### Artifacts

- `data/runtime/qadam_stock_act_detail_coverage.json`
- `data/runtime/qadam_stock_act_identity_quality.json`
- `data/runtime/qadam_stock_act_point_in_time_audit.json`
- `data/runtime/qadam_stock_act_feature_manifest.json`
- `data/runtime/qadam_stock_act_unresolved_assets.jsonl`

### Acceptance

- Filing metadata and transaction details are separate datasets.
- No score uses a transaction before its public filing became available.
- Amendments and duplicates are lineage-linked.
- Every mapped ticker has confidence, mapping method, and historical validity.

## PLBG-5 - Kalshi Contract Identity And Historical Probability Lake

### Objective

Turn the existing bounded macro contract sample into complete, auditable
prediction-market evidence and determine whether `KALSHI:EVENTS` is actually
backtestable.

### Build

- Preserve the existing 5,034 acquired rows and their pre-inception
  classifications.
- Build event-series-market-contract identity chains.
- Store title, rules, outcomes, status transitions, expiration, settlement,
  suspension, and result availability.
- Acquire complete historical candles or trades for eligible macro contracts at
  the finest approved bounded resolution, beginning with daily data.
- Preserve bid, ask, midpoint, last price, volume, and open interest separately.
- Normalize prices to probabilities without treating a quote as certainty.
- Keep outcome and settlement labels in a separate label plane unavailable to
  the scorer.
- Exclude resolved outcomes from all pre-resolution features.
- Reconcile renamed, superseded, mutually exclusive, and nested contracts.
- Cluster markets representing the same underlying event.
- Map contracts to geopolitical, macro, energy, defence, semiconductor, and
  commodity themes.
- Build two distinct test lanes:
  - Kalshi probability as a source signal for the 17 currently backtestable
    market instruments.
  - `KALSHI:EVENTS` as a direct research instrument only if contract identity,
    liquidity, pricing, costs, and paperability are sufficient.
- Keep direct prediction-market execution disabled.

### Research Features

- probability level and change
- bid-ask spread and liquidity
- volume and open-interest acceleration
- disagreement across related contracts
- divergence from Polymarket and source evidence
- divergence from related market prices
- pre-event repricing speed
- calibration by probability bucket and time to expiry

### Negative Controls

- post-settlement leakage probe
- inverted outcome mapping
- shuffled contract-to-theme mapping
- time-shifted probability series
- duplicate-event inflation probe

### Artifacts

- `data/runtime/qadam_kalshi_contract_identity.json`
- `data/runtime/qadam_kalshi_history_coverage.json`
- `data/runtime/qadam_kalshi_point_in_time_audit.json`
- `data/runtime/qadam_kalshi_feature_manifest.json`
- `data/runtime/qadam_kalshi_direct_instrument_readiness.json`

### Acceptance

- Every price belongs to an unambiguous contract and outcome side.
- No resolution information appears before public resolution time.
- Signal-source and direct-instrument results are reported separately.
- `KALSHI:EVENTS` remains excluded unless every direct-instrument gate passes.

## PLBG-6 - Polymarket Market, Condition, And Token History

### Objective

Build the full identity and lifecycle context needed to use the existing 28,275
price observations safely and evaluate `POLYMARKET:EVENTS` separately.

### Build

- Preserve the existing acquired rows and typed early-year classifications.
- Reconcile Gamma events and markets with CLOB condition and token IDs.
- Store outcome-token mappings, market slugs, question changes, rules,
  categories, creation, open, close, resolution, and archival states.
- Record the public availability time for every metadata revision.
- Acquire approved price, trade, spread, liquidity, and volume histories.
- Distinguish midpoint, trade, best bid, and best ask observations.
- Track fees and liquidity limitations in direct-instrument labels.
- Prevent resolved outcomes or current metadata from leaking into historical
  feature snapshots.
- Handle deleted, archived, duplicate, linked, and mutually exclusive markets.
- Map markets to Qadam themes with versioned deterministic rules and a review
  queue for ambiguous mappings.
- Build two distinct test lanes:
  - Polymarket probability as a source signal for other watched instruments.
  - `POLYMARKET:EVENTS` as a direct research instrument only when identity,
    liquidity, cost, and paperability requirements pass.
- Keep all Polymarket writes disabled.

### Research Features

- probability level and change
- spread and liquidity state
- trade and volume acceleration
- cross-market coherence
- Kalshi-Polymarket disagreement
- source-evidence versus crowd-probability divergence
- market-price versus event-probability divergence
- calibration by category, probability, and time to resolution

### Negative Controls

- outcome-token reversal
- current-metadata leakage probe
- shuffled theme mapping
- time-shifted prices
- duplicate-condition inflation probe

### Artifacts

- `data/runtime/qadam_polymarket_identity_graph.json`
- `data/runtime/qadam_polymarket_history_coverage.json`
- `data/runtime/qadam_polymarket_point_in_time_audit.json`
- `data/runtime/qadam_polymarket_feature_manifest.json`
- `data/runtime/qadam_polymarket_direct_instrument_readiness.json`

### Acceptance

- Every historical price has condition, token, outcome, and market lineage.
- Resolved outcomes are isolated in the label plane.
- Signal-source and direct-instrument results are reported separately.
- `POLYMARKET:EVENTS` remains excluded unless every direct-instrument gate
  passes.

## PLBG-7 - Unusual Whales Historical Archive And Forward Capture

### Objective

Determine whether Unusual Whales adds incremental, point-in-time value to
Qadam's macro strategies without letting it replace the core evidence network.

### Build

- Rotate any token previously shared in chat and install only the replacement
  in the secure local secret store.
- Revalidate provider access, expiry, endpoint entitlement, retention rights,
  and internal-research use before any capture.
- Request or import an official historical export when the standard API does
  not provide sufficient depth.
- Validate export checksums, provider metadata, and public availability
  semantics before normalization.
- If historical depth remains unavailable, classify the source as
  `forward_only` and start a supervised append-only capture.
- Use the existing allowlisted families:
  - Market Tide
  - unusual flow alerts
  - ticker dark-pool prints
  - ticker options-volume history
- Add net premium, Greeks, spot gamma exposure, and implied-volatility features
  only after entitlement and historical semantics are separately approved.
- Keep the full options tape disabled unless its cost, volume, and licensing are
  explicitly approved.
- Begin with the existing 15 US-listed Qadam proxies and extend only through a
  reviewed universe amendment.
- Record event time, conservative availability time, retrieval time, contract
  identity, ticker mapping, and correction state.
- Keep raw payload storage off unless provider terms explicitly permit it.

### Required Ablations

1. Qadam core without Unusual Whales.
2. Qadam core plus Unusual Whales.
3. Unusual Whales only.
4. Time-shifted Unusual Whales negative control.
5. Shuffled Unusual Whales negative control.

### Strategy-Specific Tests

| Strategy | Relevant Unusual Whales evidence |
| --- | --- |
| Crude Oil Energy Security | Options and dark-pool confirmation in `USO`, `BNO`, and `XLE` |
| Defence Repricing | Flow and dark-pool confirmation in `ITA`, `XAR`, `PPA`, and `LMT` |
| Semiconductor Policy | Flow, options volume, IV, and dark-pool confirmation in `SMH`, `SOXX`, `NVDA`, and `QQQ` |
| Silver Macro Liquidity | Flow and options confirmation in `SLV`, `SIL`, `GLD`, and `SPY` |
| Prediction Market Dislocation | Cross-check whether event-probability moves are corroborated by listed-market positioning |

### Artifacts

- existing `unusual_whales_*` artifacts upgraded to V2
- `data/runtime/qadam_unusual_whales_history_coverage.json`
- `data/runtime/qadam_unusual_whales_entitlement_audit.json`
- `data/runtime/qadam_unusual_whales_forward_capture_status.json`
- `data/runtime/qadam_unusual_whales_ablation_manifest.json`

### Acceptance

- A key, fixture, or successful single call does not count as historical
  coverage.
- Every eligible feature has point-in-time lineage.
- Historical absence becomes `forward_only`, not synthetic backfill.
- The core-without-provider baseline is always reported beside provider-added
  results.

## PLBG-8 - Remaining Universe Gap Review

### Objective

Prevent the four focus providers from creating a false claim that the full
41-source universe has been tested.

### Build

- Re-audit all 41 sources and 19 instruments after the four focus lanes.
- Separate acquired-but-not-scored sources from unavailable sources.
- Repair point-in-time vintage handling for macro providers where historical
  releases or revisions can be reconstructed.
- Prioritize high-value missing archives such as GDELT, official NASA FIRMS
  history, patent history, and other source families with a credible historical
  interface.
- Preserve forward-only states for sources such as live social, chat, RSS,
  maritime, aviation, outage, or other feeds when history is not reliable.
- Record approved proxies and basis-risk limits for futures and inaccessible
  instruments.
- Add historical constituent availability or an explicit fixed-universe
  survivorship limitation.
- Do not expand to tick, broad options, or order-flow history unless the
  incremental research question justifies the cost and data volume.

### Artifacts

- `data/runtime/qadam_full_universe_gap_closure_matrix.json`
- `data/runtime/qadam_acquired_not_scored_sources.json`
- `data/runtime/qadam_forward_only_source_registry.json`
- `data/runtime/qadam_proxy_basis_risk_registry.json`
- `data/runtime/qadam_survivorship_bias_audit_v2.json`

### Acceptance

- All 41 sources and 19 instruments have a closure state.
- Dashboard coverage distinguishes acquired, scored, forward-only, and
  terminally unavailable counts.
- No unavailable source is presented as backtested.

## PLBG-9 - Point-In-Time Evidence Rebuild

### Objective

Rebuild the universal source-price substrate with the new provider details and
reconciled learning observations.

### Build

- Re-run alignment from immutable source records and price evidence.
- Enforce `available_at <= decision_at < outcome_available_at`.
- Keep current-revision-only macro data out unless a historical vintage exists.
- Create provider-specific availability rules.
- Add contract-expiry and resolution windows for prediction markets.
- Add filing-delay rules for STOCK Act.
- Add correction and entitlement rules for Unusual Whales.
- Cluster syndicated, duplicated, nested, and economically equivalent events.
- Recalculate source-independence clusters after duplicate detection.
- Classify every unavailable forward window with a typed reason.
- Preserve the existing 6,232 classified legacy windows as lineage, not as an
  unfinished download counter.
- Reopen a legacy classification only when new provider evidence truly closes
  it.

### Artifacts

- V2 versions of the OR-4 alignment artifacts
- `data/runtime/qadam_focus_provider_alignment_summary.json`
- `data/runtime/qadam_learning_observation_alignment.json`
- `data/runtime/qadam_window_reclassification_ledger.jsonl`

### Acceptance

- Leakage violations equal zero.
- Every score input has provider, event, availability, and parser lineage.
- Every missing window has a typed reason.
- Duplicate evidence does not inflate source quorum or sample independence.

## PLBG-10 - Feature Registry And Historical Score Tape V4

### Objective

Create one reproducible score tape that uses all eligible evidence without
letting historical outcomes leak into feature design.

### Build

- Version all focus-provider features in the canonical feature registry.
- Preserve strategy-informed and strategy-agnostic discovery lanes.
- Add explicit missingness indicators rather than silently imputing absence as
  zero.
- Freeze feature definitions before outcomes are joined.
- Record whether a feature originated from past-learning prioritization.
- Include past-learning frequency only as a research-priority field, not as a
  predictive feature, unless separately pre-registered and tested.
- Re-run the score tape across every eligible source, instrument, direction,
  horizon, and regime.
- Preserve unscorable records and typed reasons.
- Write scores before labels and use immutable partitions.
- Cache local-LLM extraction by content, prompt, and model hash.
- Keep frontier-LLM and quantum interpretations outside historical labels.

### Coverage Reports

- by source and source category
- by instrument and market family
- by strategy family
- by feature family
- by time period and regime
- by provider and provenance class
- by scoreable, unscoreable, and terminal state

### Acceptance

- A rerun with identical hashes produces identical scores.
- Labels and future returns do not exist in score partitions.
- Each score explains feature contributions, missing evidence, and penalties.
- Every focus-provider feature can be removed in an ablation without changing
  unrelated features.

## PLBG-11 - Full-Universe Statistical Backtest V4

### Objective

Run a broader empirical test that measures both standalone and incremental
value while controlling for repeated discovery.

### Build

- Register every experiment before evaluating its untouched holdout.
- Use chronological walk-forward folds with purging and embargo.
- Keep a final untouched holdout unavailable to feature tuning.
- Apply transaction costs, spreads, slippage, liquidity, and proxy basis risk.
- Use dependence-aware confidence intervals and block bootstrap methods.
- Track all attempted hypotheses in one false-discovery family registry.
- Compare against unconditional return, simple momentum/reversal,
  strategy-blind linear, and random or shuffled-time baselines.
- Test linear lead-lag, event study, vector analog, state-matrix, divergence,
  cross-asset, regime-conditioned, entropy, nonlinear interaction, and matched
  quantum-assisted methods.
- Require quantum methods to use the same evidence, windows, costs, and holdout
  as their classical baseline.
- Report insufficiency separately from rejection.

### Required Focus Experiments

| Experiment family | Required comparison |
| --- | --- |
| Prediction-market consensus | Kalshi only vs Polymarket only vs both |
| Prediction-market disagreement | Cross-venue divergence vs matched no-divergence windows |
| Prediction-to-market lead-lag | Event probabilities vs all mapped watched instruments |
| Direct prediction instrument | Separate Kalshi and Polymarket lanes only if PLBG-5/6 readiness passes |
| Congressional disclosure | Filing event only vs parsed transaction detail |
| Congressional lag | Filing-date signal vs transaction-date leakage control |
| Congressional concentration | Individual filer vs clustered independent groups |
| Unusual Whales increment | Core without provider vs core plus provider |
| Unusual Whales standalone | Provider only vs provider shuffle and time shift |
| Multi-source interaction | Prediction markets plus STOCK Act plus other independent macro evidence |
| Strategy coverage | All five core families plus strategy-agnostic discovery |

### Promotion Requirements

A result may become a historical edge candidate only when it:

- has adequate independent observations;
- survives chronological walk-forward validation;
- remains positive on an untouched holdout;
- remains positive after realistic costs and proxy basis risk;
- beats a simple matched baseline;
- survives false-discovery adjustment;
- is not concentrated in one date, contract, filer, source, or instrument;
- is stable enough across relevant regimes;
- passes provider-ablation and negative-control checks;
- has complete source-price and experiment lineage.

### Artifacts

- V4 versions of the OR-8 statistical artifacts
- `data/runtime/qadam_focus_provider_backtest_summary.json`
- `data/runtime/qadam_focus_provider_ablation_results.jsonl`
- `data/runtime/qadam_learning_prior_backtest_audit.json`
- `data/runtime/qadam_full_universe_empirical_coverage.json`

### Acceptance

- Results cover every eligible lane and classify every ineligible lane.
- Core and provider-added performance are shown side by side.
- Zero validated edges is an acceptable certified outcome.
- No backtest output mutates a strategy or creates a trade.

## PLBG-12 - Past Learning Re-Evaluation And Attribution

### Objective

Determine which old lessons were supported, contradicted, still unknown, or
merely operational observations after the new backtest.

### Build

- Join migrated learning observations to pre-registered experiment results.
- Classify each legacy lesson as:
  - `supported_by_new_evidence`
  - `contradicted_by_new_evidence`
  - `insufficient_evidence`
  - `operational_only`
  - `transport_only`
  - `not_testable`
- Never rewrite original learning history.
- Create a new V4 attribution record linking original observation, provider
  evidence, backtest result, and current conclusion.
- Record whether Akber holds or vetoes were directionally useful only when a
  valid counterfactual outcome exists.
- Record whether quantum review added measurable incremental value over the
  matched classical result.
- Reject circular claims where the same old observation both generated and
  validated a hypothesis without an untouched holdout.

### Artifacts

- `data/runtime/qadam_past_learning_reassessment.json`
- `data/runtime/qadam_learning_attribution_v4.jsonl`
- `data/runtime/qadam_supported_lesson_candidates.jsonl`
- `data/runtime/qadam_rejected_legacy_lessons.jsonl`

### Acceptance

- Every migrated lesson has one current evidence state.
- No lesson is called verified solely because it appeared repeatedly.
- No Akber or quantum contribution is claimed without a matched counterfactual.

## PLBG-13 - Proposal-First Improvement And Forward Validation

### Objective

Turn supported historical findings into reviewable changes, then collect real
forward evidence before any strategy refinement affects guarded paper review.

### Build

- Produce versioned proposals for feature, source, strategy, Akber, model-route,
  or quantum-usage changes.
- Include expected benefit, historical evidence, failure modes, rollback,
  affected strategies, and required forward-observation period.
- Require explicit approval for research application.
- Write approved research versions to the applied-learning ledger without
  changing execution authority.
- Run champion-versus-challenger forward shadow observations.
- Track trade-now, wait, veto, no-order, and alternate-threshold outcomes.
- Measure missed opportunities and avoided losses.
- Require real elapsed market time; no backfill or simulated forward time.
- Keep the daily learning automation aligned to the current 41-source,
  19-instrument, zero-or-current-edge canonical contract.
- Remove obsolete hardcoded 37-source and 21-instrument counts.
- Make daily briefs report current evidence changes rather than repeating a
  generic five-pattern summary.

### Artifacts

- `data/runtime/qadam_improvement_proposals_v4.jsonl`
- `data/runtime/qadam_applied_learning_versions_v2.jsonl`
- `data/runtime/qadam_forward_learning_experiments.jsonl`
- `data/runtime/qadam_daily_learning_contract_v2.json`

### Acceptance

- Every applied research version has approval, rollback, and lineage.
- No proposal mutates capital, broker, risk, or execution authority.
- Forward results use real timestamps and actual future outcomes.
- Daily learning counts match the current canonical universe.

## PLBG-14 - Dashboard And Telegram Research Visibility

### Objective

Expose the work clearly without changing the established dashboard route or
module structure.

### Build

- Preserve the existing dashboard UX and protected navigation.
- Enrich existing Pattern Recognition, Trading Strategies, Decision Room,
  Results & Lessons, and Tests & Improvements surfaces only.
- Show four separate coverage numbers:
  - provider rows acquired;
  - sources with scoreable point-in-time evidence;
  - sources classified forward-only;
  - sources classified terminally unavailable.
- Explain that historical acquisition completeness and empirical backtest
  completeness are different.
- Show focus-provider cards with identity, history, point-in-time, feature, and
  ablation readiness.
- Show "Past observations re-evaluated" rather than "lessons applied" until an
  applied version exists.
- Show direct prediction-market instruments as unavailable until their
  readiness checks pass.
- Use plain-English summaries of what changed, what was tested, what survived,
  what failed, and what happens next.
- Keep Telegram notes short, specific, deduplicated, and review-only.

### Acceptance

- The dashboard never says all 41 sources were backtested when fewer were
  scoreable.
- Unavailable history is not presented as an error if it is properly typed.
- No dashboard or Telegram interaction creates authority.

## PLBG-15 - End-To-End Certification

### Objective

Create one fail-closed checker that certifies the learning migration and
historical gap-closure work without certifying profitability.

### Build

- Add `scripts/check_qadam_learning_and_backtest_gap_closure.py`.
- Write
  `data/runtime/qadam_learning_and_backtest_gap_closure_certification.json`.
- Validate every PLBG stage, artifact hash, schema, provider state, safety flag,
  and acceptance criterion.
- Add negative probes for fixture promotion, secret leakage, timestamp leakage,
  outcome leakage, direct prediction-market writes, duplicated source quorum,
  fake exact STOCK Act amounts, stale legacy counts, silent strategy mutation,
  paper-calendar advancement, proof credit, and broker writes.
- Register stage status in
  `data/runtime/qadam_learning_backtest_gap_closure_status.json`.
- Append implementation evidence to
  `docs/qadam-learning-backtest-gap-closure-implementation-log.md`.

### Certification Levels

| Level | Meaning |
| --- | --- |
| `structurally_ready` | Contracts, safety gates, and provider plans pass |
| `provider_complete_with_classified_gaps` | Every provider lane is acquired, proxy-approved, forward-only, or terminally unavailable |
| `empirical_backtest_complete` | Every eligible lane was scored, labelled, and tested under the frozen protocol |
| `historical_edge_candidate_found` | Optional state; at least one result meets all historical promotion gates |
| `forward_validation_required` | A historical candidate exists but has not earned real forward evidence |
| `complete_no_edge_found` | The full eligible test completed honestly and no result survived |

The checker must pass in either `historical_edge_candidate_found` or
`complete_no_edge_found` when all evidence and safety requirements are met.
It must never fabricate an edge to reach a passing state.

## 8. Implementation Sequence And Dependencies

The recommended sequence is:

1. PLBG-0 freezes truth and safety.
2. PLBG-1 and PLBG-2 reconcile past learning.
3. PLBG-3 certifies provider access and limits.
4. PLBG-4, PLBG-5, PLBG-6, and PLBG-7 run as independent resumable provider
   lanes.
5. PLBG-8 closes or classifies the remaining universe.
6. PLBG-9 rebuilds point-in-time evidence.
7. PLBG-10 freezes the new feature registry and score tape.
8. PLBG-11 runs the statistical backtest.
9. PLBG-12 re-evaluates old lessons against the new evidence.
10. PLBG-13 creates proposals and begins real forward observation.
11. PLBG-14 refreshes read-only visibility.
12. PLBG-15 certifies the result.

PLBG-4 through PLBG-7 may run in parallel after PLBG-3, but PLBG-9 must not
start its final build until every focus lane has reached a terminal checkpoint.

### 8.1 Modular Check Matrix

Each stage must have one executable checker and must update the shared dynamic
status artifact. A later stage may not infer success from file existence alone.

| Stage | Required checker |
| --- | --- |
| PLBG-0 | `scripts/check_qadam_learning_backtest_baseline.py` |
| PLBG-1 | `scripts/check_qadam_legacy_learning_inventory.py` |
| PLBG-2 | `scripts/check_qadam_learning_contract_reconciliation.py` |
| PLBG-3 | `scripts/check_qadam_focus_provider_readiness.py` |
| PLBG-4 | `scripts/check_qadam_stock_act_transaction_history.py` |
| PLBG-5 | `scripts/check_qadam_kalshi_historical_identity.py` |
| PLBG-6 | `scripts/check_qadam_polymarket_historical_identity.py` |
| PLBG-7 | `scripts/check_qadam_unusual_whales_historical_features.py` |
| PLBG-8 | `scripts/check_qadam_full_universe_gap_closure.py` |
| PLBG-9 | `scripts/check_qadam_point_in_time_evidence.py` with V2 coverage probes |
| PLBG-10 | `scripts/check_qadam_pattern_score_tape.py` with V4 feature coverage probes |
| PLBG-11 | `scripts/check_qadam_statistical_backtest.py` with V4 experiment and ablation probes |
| PLBG-12 | `scripts/check_qadam_past_learning_reassessment.py` |
| PLBG-13 | `scripts/check_qadam_forward_learning_loop.py` |
| PLBG-14 | Existing dashboard and Telegram suites plus focus-provider visibility probes |
| PLBG-15 | `scripts/check_qadam_learning_and_backtest_gap_closure.py` |

Every stage update must record:

- stage ID and schema version;
- started, checkpointed, paused, failed, and completed timestamps;
- input artifact and dataset hashes;
- output artifact hashes;
- checker command and exit status;
- real provider, fixture, or classified-unavailable evidence state;
- operator action, if any;
- next permitted stage;
- complete authority flags.

## 9. Laptop Runtime Design

The implementation must remain practical on the M5 laptop with 24 GB RAM and 1
TB storage.

### Runtime Rules

- Stream provider pages and partitions; do not load the full lake into memory.
- Keep one bounded writer per provider and use atomic checkpoint replacement.
- Partition by provider, source, instrument or contract, and date.
- Resume after sleep, restart, rate limiting, network loss, or process failure.
- Make every write idempotent by logical record identity and checksum.
- Use bounded worker counts and provider-specific rate limiters.
- Pause safely when an operator action or purchase is required.
- Keep immutable raw evidence separate from normalized and derived evidence.
- Reuse completed partitions only when dataset and parser hashes match.
- Publish heartbeat, throughput, error, disk, request, cost, and estimated
  completion summaries.
- Refuse to continue if disk, API-call, monetary, or corruption limits are
  breached.

### Suggested Execution Classes

| Class | Work |
| --- | --- |
| Fast checks | Schemas, hashes, manifests, safety probes |
| Provider capture | Network-bound, rate-limited, resumable |
| Parsing | CPU-bound, bounded by document partition |
| Alignment | Streaming joins by time and instrument |
| Score tape | Partitioned deterministic feature calculation |
| Backtest | Parallel by registered experiment with capped workers |
| Quantum review | Shortlisted matched experiments only, never every raw row |

## 10. Testing Strategy

Every stage must include unit, integration, replay, idempotency, and negative
safety tests where applicable.

### Mandatory Test Families

- schema validation
- deterministic ID and hash generation
- interrupted-resume equivalence
- duplicate logical write denial
- provider pagination and rate-limit handling
- timezone and market-calendar handling
- point-in-time availability enforcement
- future-field denial
- current-revision leakage denial
- outcome and settlement leakage denial
- contract and token side mapping
- filing amendment and duplicate handling
- historical symbol validity
- source-independence clustering
- score-before-label separation
- realistic transaction-cost application
- untouched-holdout isolation
- false-discovery accounting
- negative-control rejection
- strategy and source ablation
- no-candidate, no-order, no-broker-write, and no-proof-credit probes
- active paper epoch non-interference
- dashboard public-safety and anti-slop checks

## 11. Operator Actions

The implementation should automate technical work but pause for explicit
operator action when required.

Potential operator actions are:

- rotate and securely install any exposed provider credential;
- approve current private-research terms and retention treatment;
- request an official Unusual Whales historical export;
- approve a provider purchase within a recorded cost ceiling;
- approve use of a proxy and its basis-risk limit;
- decide whether unavailable direct prediction-market instruments remain
  research context only;
- review a research improvement proposal before it becomes an applied research
  version.

The implementation must provide an exact reason, provider, requested action,
cost estimate, and consequence when it pauses. It must not ask for credentials
to be pasted into chat or tracked files.

## 12. Risks And Mitigations

| Risk | Mitigation |
| --- | --- |
| Old daily briefs contaminate current evidence | Quarantine first; migrate only point-in-time-eligible observations |
| Repeated old hypotheses appear stronger than they are | Deduplicate and use frequency only for test priority |
| STOCK Act transaction dates create lookahead | Score from public filing availability, with a transaction-date leakage control |
| Amount ranges become fake exact notionals | Preserve intervals and run lower/midpoint/upper sensitivity tests |
| Kalshi or Polymarket resolution leaks into features | Separate feature and label planes; enforce public resolution availability |
| Equivalent prediction markets inflate independence | Build event and condition clusters across venues |
| Unusual Whales single call is mistaken for history | Require eligible row coverage and all five ablations |
| Fixed current universe creates survivorship bias | Add historical membership where possible and report residual limitation |
| More hypotheses create false positives | Pre-registration, one attempt ledger, and false-discovery correction |
| Provider data volume overwhelms laptop | Streaming partitions, capped workers, disk and cost ceilings |
| Backtest work interferes with clean paper epoch | Separate process lock, read-only paper observation, and non-interference tests |
| Dashboard overstates completeness | Separate acquisition, scoreability, test, and validation counts |

## 13. Final Acceptance Criteria

The plan is fully implemented only when all of the following are true:

1. The original 516 past-learning snapshots are inventoried, hashed, and
   preserved without mutation.
2. Every past-learning record is deduplicated and assigned a provenance and
   current-contract reconciliation state.
3. Legacy 37-source, 21-instrument, and non-canonical edge counts cannot enter
   current runtime decisions.
4. Every eligible migrated observation existed before its tested outcome.
5. Kalshi contract identity, lifecycle, pricing, and resolution coverage are
   complete or explicitly classified.
6. Polymarket event, condition, token, pricing, liquidity, and resolution
   coverage are complete or explicitly classified.
7. STOCK Act filing metadata is separated from parsed transaction details, and
   all scores use public filing availability.
8. Unusual Whales contains real eligible provider rows and all required
   ablations, or it is honestly certified forward-only or unavailable.
9. Every one of the 41 sources and 19 instruments has an acquired, approved
   proxy, forward-only, or terminally unavailable state.
10. Acquired-but-not-scored sources are explicitly visible and either made
    scoreable or given a typed exclusion reason.
11. All source-price score inputs have provider, timestamp, availability, and
    parser lineage.
12. Leakage violations are zero.
13. Every missing forward window has a typed reason.
14. The historical score tape is immutable, deterministic, and written before
    labels.
15. All five core strategy families and the strategy-agnostic discovery lane
    are tested where evidence is sufficient.
16. Kalshi, Polymarket, STOCK Act, and Unusual Whales standalone, combined,
    ablation, and negative-control experiments are completed or explicitly
    classified insufficient.
17. Costs, spread, slippage, liquidity, proxy basis risk, dependence, regime,
    concentration, survivorship, and false-discovery effects are reported.
18. The untouched holdout remains isolated from feature and threshold design.
19. Every historical result is classified as validated candidate, rejected,
    unstable, overfit, cost-sensitive, concentrated, or insufficient.
20. Past lessons are reclassified against fresh evidence without rewriting
    their original history.
21. Any proposed improvement remains versioned, reversible, and
    human-reviewed before research application.
22. No historical or shadow result creates a candidate, order, broker write,
    proof credit, live-capital authority, or paper-calendar progress.
23. The active clean paper epoch remains unchanged by the historical workflow.
24. Dashboard and Telegram summaries are current, plain-English, deduplicated,
    public-safe, and read-only.
25. `scripts/check_qadam_learning_and_backtest_gap_closure.py` passes with either
    an honest edge-candidate state or an honest no-edge-found state.

## 14. What Success Looks Like

After implementation, Qadam can truthfully say:

> Qadam preserved its earlier observations as research memory, reconciled them
> to the current source and instrument universe, expanded provider-backed
> historical evidence, and retested every eligible relationship under a frozen
> point-in-time protocol. Kalshi, Polymarket, STOCK Act, and Unusual Whales were
> each measured separately and incrementally. Unavailable history remained
> explicitly classified. Any surviving result is a historical research
> candidate that still requires real forward validation; no result was promoted
> merely to make the system trade.

That is the evidence standard required before past learning can become genuine
self-improvement.
