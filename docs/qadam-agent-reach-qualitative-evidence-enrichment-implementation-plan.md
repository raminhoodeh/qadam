# Qadam Selective Agent Reach Qualitative Evidence Enrichment Implementation Plan

Status: proposed implementation plan

Date: 2026-08-15

Supersedes for future implementation scope:
`docs/qadam-agent-reach-source-enrichment-2026-06-15.md`

Primary objective: give Qadam more timely, explainable and testable qualitative
evidence so it can discover more distinct patterns, resolve more directional
research questions, and evaluate more legitimate paper-trade opportunities
without weakening portfolio, execution or broker safeguards.

Cross-system objective: give every productive Qadam lane explicit authority to
advance the evidence it can legitimately produce into one canonical
tradeability envelope. Eliminate schema-induced dead ends so complete,
current, low-risk hypotheses can reach the validated-strategy or discovery-micro
paper lane without manual repair. This is a conversion objective, not a trade
quota or permission for research components to submit orders.

## 1. Executive Decision

Qadam should use Agent Reach selectively as a discovery and retrieval capability,
not install it wholesale as a privileged component of the trading system.

Agent Reach must not become a new data source in its own right. It is a transport
and capability router. Qadam must preserve and score the underlying origin:

| Retrieved item | Credited origin | Permitted role |
|---|---|---|
| Official company earnings call | Corporate primary source | Context and catalyst evidence after verification |
| SEC filing reached through web search | SEC EDGAR | Regulated primary evidence |
| Reuters article reached through a reader | Reuters | Independent secondary corroboration |
| Official YouTube briefing | Verified issuing institution | Primary briefing evidence with transcript-quality label |
| Reddit discussion | Reddit narrative context | Attention and disagreement context only |
| X post from an unverified account | X narrative context | Discovery only until corroborated |
| GitHub release from an official project | Verified project repository | Technology-release evidence after identity verification |

The preferred implementation is a Qadam-native, sandboxed evidence worker that
uses only audited and pinned Agent Reach channel backends. Qadam must not run
`agent-reach install --system`, accept automatic upstream changes, read the main
browser profile, or expose broker and model credentials to the worker.

This programme is intended to improve the supply of usable evidence. It must not
manufacture trade frequency. Increased activity is valid only when it comes from
more fresh directional triggers, better evidence coverage, and fewer schema
mismatches between acquired evidence and Qadam's gates.

Two subordinate lanes are added to the programme:

| Lane | Purpose | Boundary |
|---|---|---|
| Functional specialist challenge | Examine the same evidence independently through business-quality, catalyst, macro-regime, market-reaction and adversarial lenses before Strategy Lead synthesis. | Model agreement is not source agreement. The specialists cannot create facts, quorum, expected returns, risk approval or orders. |
| Prediction Market Intelligence V2 | Convert Kalshi and Polymarket contracts into normalized belief, logical-consistency, liquidity-quality and cross-asset research evidence. | Read-only research initially. Direct prediction-market execution remains unavailable; only a separately qualified listed Alpaca Paper proxy may reach the existing guarded route. |

The attached inactive n8n workflow, `Ai Hedge Fund viral copy.json`, is a design
reference only. Qadam should adopt its useful parallel-review pattern but must
not import its celebrity personas, hardcoded TSLA path, same-model voting,
free-form allocation estimates, short price window or Telegram-first workflow.

## 2. Why This Work Is Needed

Qadam already has broad source and market coverage, but several important forms
of decision-relevant information are weak or absent:

- Management language from earnings calls and public briefings.
- Statements about demand, backlog, capacity, delivery constraints and margins.
- Changes in guidance or confidence relative to prior management statements.
- Qualitative information that is public but not encoded in structured filings.
- Narrative disagreement between official evidence, independent reporting,
  prediction markets and social attention.
- Timely event-to-market mappings that turn qualitative information into a
  directional question with an explicit horizon.

The conversation with Akber exposed a concrete example. A chief executive may
say that demand cannot be fulfilled until a future date. The market may then
fall, volume may contract and implied volatility may stagnate. A useful system
must preserve the original statement, determine when it became available, map
it to affected issuers and sector proxies, compare the market reaction, and test
whether similar divergences historically preceded a tradeable move.

Agent Reach can help discover and retrieve that information. It cannot decide
whether the information is true, independent, predictive or tradeable. Those
jobs remain with Qadam's evidence, pattern, strategy, Akber, risk and execution
layers.

## 3. Current Codebase Baseline

The implementation must start from the current code rather than recreate an
older architecture.

### 3.1 Existing Agent Reach Surface

`orchestrator/agent_reach_bridge.py` currently:

- maps 13 Agent Reach channel capabilities;
- labels selected channels as supplemental research context;
- exposes only capability metadata, not fetched provider evidence;
- forbids source-quorum credit, signal authority, candidate creation, orders,
  broker writes, cookies, browser control, quantum jobs and live capital;
- disables Agent Reach installation and live backend probes;
- writes `data/runtime/agent_reach_bridge.json`.

`scripts/check_agent_reach_bridge.py` validates the metadata bridge and its
authority boundary. It does not validate real document retrieval, transcript
quality, provenance, point-in-time safety or downstream pattern use.

### 3.2 Existing Downstream Surfaces

The implementation must extend, not replace:

- `orchestrator/qadam_evidence_contracts.py` for typed evidence completeness;
- `orchestrator/evidence_packet_normalization.py` for safe evidence packets;
- `orchestrator/qadam_temporal_graph_contracts.py` and the temporal graph store;
- `orchestrator/qadam_graph_pattern_discovery.py` for ranked research patterns;
- `orchestrator/qadam_strategy_translation.py` for directional resolution;
- `orchestrator/qadam_strategy_foundry_v4.py` for core-family refinement and
  emerging pattern-sourced strategies;
- `orchestrator/qadam_akber_evidence_fit.py` for evidence-adapted filter inputs;
- the active-discovery and discovery-micro paper policy already present in the
  current branch;
- the canonical Router and PaperOps path for guarded Alpaca Paper submission.

### 3.3 Source Count Contract Drift

The current universal matrix reports 41 source interfaces, while the legacy
`world_monitor/source_registry.py` and Agent Reach checker still use a canonical
count of 35. This programme must resolve the meaning, not force one number over
the other.

Every public and runtime contract must distinguish:

- `source_interface_count` - configured adapters or observable interfaces;
- `canonical_origin_count` - distinct evidence origins represented;
- `supplemental_transport_count` - discovery or retrieval transports;
- `quorum_eligible_origin_count` - origins currently eligible for a candidate;
- `fresh_provider_backed_origin_count` - origins with a current real observation.

Agent Reach transports must never increase `canonical_origin_count` merely by
retrieving another origin's content.

## 4. Target Operator Outcome

After implementation, Qadam should autonomously:

1. Watch approved official and public qualitative sources relevant to its 19
   watched instruments.
2. Retrieve new documents and transcripts without accessing Qadam secrets or
   authenticated personal browser sessions.
3. Preserve what was said, who said it, where it appeared and when the market
   could first have known it.
4. Extract structured claims while preserving exact supporting spans and model
   uncertainty.
5. Challenge claims against prior statements, filings, market prices, volume,
   options context, prediction markets and independent reporting.
6. Build source-claim-entity-instrument relationships in the temporal evidence
   graph.
7. Search historical and forward outcomes for repeatable source-price patterns.
8. Refine an existing core strategy or form an emerging strategy when evidence
   survives the required tests.
9. Populate Akber's context and catalyst stages with evidence Qadam can actually
   collect.
10. Continue to obtain execution, spread, expected-return and portfolio-risk
    evidence from their proper market and risk providers.
11. Route only qualified bounded setups to the existing guarded paper path.
12. Explain on the dashboard and Telegram what new evidence changed, rather
    than reporting scraping volume.
13. Publish a capability manifest for every lane that states which Context,
    Catalyst, Confirmation, Risk, Execution and learning fields it may fill.
14. Compile compatible same-generation lane contributions into one typed
    tradeability envelope with one candidate identity and one downstream owner.
15. Automatically create current-market, cost, shadow and risk evidence when a
    lane produces an active directional trigger, rather than waiting for an
    unrelated scheduled job.
16. Permit every complete setup to receive a deterministic Akber and Router
    disposition during the same market session, with no artificial one-trade-
    per-day ceiling.

The desired practical effect is more evidence-backed decisions and fewer holds
caused by missing context, catalyst or direction. It is not a guaranteed number
of trades per day.

## 5. Non-Negotiable Boundaries

### 5.1 Security

- Do not run `agent-reach install --system`.
- Do not allow Agent Reach to modify Codex, MCP, shell, browser or Qadam config.
- Do not pass the worker the Alpaca, Telegram, IBM, Q-CTRL, Gemini, Unusual
  Whales, Kalshi or Polymarket environment.
- Do not read the user's primary Chrome profile, cookies, keychain or home
  directory.
- Do not install from mutable `main`; pin an audited commit and dependency set.
- Do not enable automatic Agent Reach or backend updates.
- Do not execute commands supplied by retrieved documents.
- Do not write fetched content into Git-trackable paths.
- Do not store video or audio when captions or text are sufficient.

### 5.2 Evidence

- Agent Reach is a transport, not an evidence origin.
- Model-generated summaries are not primary evidence.
- Search-result snippets are discovery records, not facts.
- Social attention cannot establish a corporate or geopolitical fact.
- Reposts and articles derived from one original statement are one independence
  cluster, not several corroborating sources.
- Missing publication or availability time must be explicit.
- Historical data must never be rewritten with a later revision as though it
  were known earlier.
- Unsupported archives must be classified honestly as unavailable or
  forward-only.

### 5.3 Trading Authority

- A retrieved document cannot create a trade candidate directly.
- A transcript-extraction model cannot approve risk or execution.
- A high narrative or research score is not a probability of profit.
- Qualitative evidence may satisfy only the evidence roles permitted by its
  trust tier.
- Spread, liquidity, current price, expected return, invalidation and portfolio
  exposure must come from the appropriate market and risk systems.
- All orders remain paper-only and must use the guarded Alpaca Paper route.
- No live-capital path is created or changed by this programme.
- No trade quota may force a setup through Akber, Router or PaperOps.
- Every lane receives only the authority appropriate to its role: observe,
  qualify evidence, rank a pattern, nominate a strategy, challenge or block, or
  nominate a paper review.
- Research lanes never receive broker-write authority. Portfolio risk and
  Router remain the only governance authorities, and PaperOps remains the only
  paper-order submitter.
- A negative-control, adversarial or quantum lane may downgrade or block a
  claim when its declared test fails; it may not promote a strategy by itself.
- A productive lane must not be blocked merely because a downstream consumer
  expects an equivalent field under a different name or nesting shape.

### 5.4 Product Surface

- Preserve the current dashboard routes, sidebar order, 10-stage lifecycle and
  existing page structure.
- Enrich existing modules instead of replacing their UX with an older bundle.
- Telegram remains explanatory, deduplicated and command-disabled.
- Raw copyrighted text, cookies, private URLs and local paths must not appear on
  public dashboard or Telegram surfaces.

## 6. Architecture Decision

### 6.1 Component Model

```mermaid
flowchart LR
    A["Approved origin registry"] --> B["Sandboxed reach worker"]
    B --> C["Immutable retrieval envelope"]
    C --> D["Provenance and security gate"]
    D --> E["Local structured claim extraction"]
    E --> F["Frontier-model challenge"]
    F --> G["Temporal evidence graph"]
    G --> H["Historical and forward feature builder"]
    H --> I["Pattern Recognition"]
    I --> J["Core strategy refinement or emerging strategy"]
    J --> K["Akber's 6-Stage Filter"]
    K --> L["Portfolio risk and Router"]
    L --> M["Guarded Alpaca Paper"]
```

### 6.2 Sandboxed Reach Worker

Create a small sidecar process with one responsibility: retrieve approved public
content and emit schema-valid envelopes into a bounded spool directory.

Preferred isolation:

| Control | Required implementation |
|---|---|
| Process identity | Dedicated unprivileged worker or container |
| Environment | `env -i` style allowlist with no Qadam secrets |
| Filesystem | Read-only worker code, write-only spool and bounded cache |
| Network | Domain allowlist derived from approved origin registry |
| Commands | Explicit binary and argument allowlist |
| Updates | Disabled; version changes require review and re-certification |
| Output | JSON envelopes only; no arbitrary files or shell instructions |
| Resource limits | Time, response size, concurrency, disk and memory ceilings |
| Failure | Per-channel circuit breaker; never a global trading bypass |

The worker may use audited implementations equivalent to the selected Agent
Reach channels. It does not need to import the complete Agent Reach runtime.

### 6.3 Initial Channel Set

Launch only with zero-auth, high-value channels:

| Channel | Initial state | Qadam purpose |
|---|---|---|
| Official web pages | Enabled by allowlist | Investor relations, regulators, public briefings |
| RSS/Atom | Enabled by allowlist | Fast official announcements and trusted journalism |
| YouTube captions | Enabled for verified channels | Earnings calls, briefings and interviews |
| GitHub public releases | Narrow allowlist | AI infrastructure and semiconductor release context |
| Semantic web search | Discovery only | Find candidate original sources; no factual credit |
| Reddit | Existing Qadam narrative proxy first | Attention context only |
| X/Twitter | Disabled initially | Later isolated-account review only |
| Facebook/Instagram | Disabled | No initial investment case justifies session risk |
| LinkedIn | Disabled | Slow signal; revisit after core evidence pipeline works |
| Regional social/video | Disabled | Activate only for a preregistered strategy need |

### 6.4 Transport Versus Origin

Every record must include both:

- `retrieval_transport` such as `rss`, `jina_reader`, `yt_dlp_captions` or
  `github_cli`;
- `evidence_origin` such as `company_ir`, `sec_edgar`, `eia`, `reuters`,
  `verified_company_youtube` or `reddit_narrative`.

Trust, independence and quorum are calculated from `evidence_origin`, never from
`retrieval_transport`.

## 7. Priority Evidence Programmes

### 7.1 Earnings-Call Guidance And Supply Constraints

This is the highest-priority programme because it addresses the information gap
identified by Akber.

Extract and compare:

- revenue and margin guidance direction;
- backlog and order-book changes;
- capacity sold-out or delivery-delay language;
- demand that cannot be fulfilled;
- customer concentration and cancellation language;
- capex, inventory and lead-time changes;
- management confidence and uncertainty;
- changes from the same speaker's prior call;
- statements omitted from the formal filing;
- market reaction, volume, implied volatility and later return path.

Initial issuer coverage should be derived from the 19-instrument universe:

- direct issuers: NVDA and LMT;
- semiconductor constituents for SMH, SOXX and QQQ;
- defence constituents for ITA, XAR and PPA;
- energy producers and service companies relevant to XLE, USO and BNO;
- precious-metal producers relevant to SIL and SLV;
- market-moving issuers and macro institutions relevant to SPY and GLD.

Constituent membership must be point-in-time where historical tests use it.

### 7.2 Management-Evidence Versus Price-Reaction Divergence

Research question:

> When verified operating evidence remains constructive but price, volume and
> implied volatility weaken or stagnate, does the divergence precede a bounded
> reversal or continuation in the affected issuer or sector proxy?

This is a testable translation of the qualitative setup Akber described. It must
not be installed as a strategy before historical and forward testing.

### 7.3 Post-Earnings Announcement Drift

Use transcript evidence to enrich, not replace, the existing PEAD research
candidate:

- actual versus timestamp-valid consensus surprise;
- before-open versus after-close announcement timing;
- immediate market reaction;
- guidance and management-claim direction;
- agreement or disagreement between numerical surprise and qualitative claims;
- long-only and long-short variants;
- 1, 3, 5, 20 and 60 trading-day outcomes.

### 7.4 Narrative Diffusion And Disagreement

Measure how an original claim propagates without treating repetition as source
independence:

- first official publication;
- independent reporting latency;
- cross-platform attention velocity;
- consensus versus disagreement;
- prediction-market probability movement;
- options-flow confirmation or rejection;
- price reaction before and after narrative saturation.

### 7.5 Technology And Supply-Chain Change

Use official GitHub releases and technical briefings only for a narrow,
preregistered semiconductor and AI-infrastructure watchlist. Commit count and
social excitement alone are not investment evidence. Useful features include
release significance, deprecation, production availability, security incidents
and changes linked to identifiable public issuers or suppliers.

### 7.6 Prediction Market Intelligence V2

This lane completes Qadam's existing prediction-market research rather than
creating another source count or execution venue. It must treat a quoted event
price as a market state whose meaning depends on contract semantics, liquidity,
participant structure and time to resolution.

The lane has four evidence layers:

1. **Belief state:** probability, log-odds, belief volatility, jump intensity,
   scheduled-news surprise and cross-event co-jumps.
2. **Logical state:** mutually exclusive, exhaustive, conditional and equivalent
   contract relationships, with deterministic constraint validation.
3. **Market-quality state:** quoted and effective spread, depth, price impact,
   activity, concentration, resiliency, time to resolution and shock regime.
4. **Cross-asset state:** point-in-time mapping from the event and belief change
   to Qadam's watched instruments and approved paper proxies.

Polymarket activity must be decomposed into exchange-equivalent turnover, net
inflow and gross activity. Share minting, burning and conversion cannot be
counted naively as ordinary trading volume. Kalshi and Polymarket contracts may
be compared only when event identity, outcome space, settlement rule, cutoff,
currency and resolution authority are compatible.

The first three preregistered programmes are:

| Programme | Frozen question | Initial use |
|---|---|---|
| Belief Jump Lead-Lag | Do liquidity-qualified log-odds jumps precede repricing in a mapped listed instrument after costs? | Refine Prediction Market Geopolitical Dislocation or another existing family when the mechanism fits. |
| Cross-Venue Belief Disagreement | Does a compatible Kalshi-Polymarket probability gap predict convergence or a listed-market repricing, conditional on spread, depth and time to resolution? | Research pattern first; listed-proxy paper expression only after validation. |
| Logical Constraint Dislocation | Do deterministic probability-constraint violations persist after executable depth, fees, latency and settlement risk? | Simulation and research only until a separately governed prediction-market paper route exists. |

The paper registry must preserve research status honestly:

- `Toward Black-Scholes for Prediction Markets` is a methodological candidate;
  its synthetic variance-forecast result is not an edge.
- `Unravelling the Probabilistic Forest` is an empirical method reference;
  its LLM-proposed dependencies require deterministic truth-table or constraint
  validation.
- `What Happens When Institutional Liquidity Enters Prediction Markets?` is a
  `withdrawn_method_reference`; its measurement checklist may be used, but its
  synthetic results provide no strategy evidence.
- `The Anatomy of a Blockchain Prediction Market` is an empirical measurement
  reference for transaction decomposition, disagreement and liquidity regimes;
  its single-event estimates are not universal parameters.

## 8. Evidence Trust And Promotion Model

### 8.1 Trust Tiers

| Tier | Definition | Candidate role |
|---|---|---|
| A | Regulated filing, official statistic, verified company or government statement | May satisfy context or catalyst after identity and freshness checks |
| B | Independent reputable reporting with a traceable original source | May corroborate Tier A or support a distinct fact |
| C | Verified expert, executive or official social account | Discovery or contextual support; promotion requires identity and claim checks |
| D | Forums, aggregate sentiment and unverified social content | Narrative, attention and disagreement only |
| E | Search snippets, generated summaries or unattributed text | Discovery only; no candidate evidence |

### 8.2 Promotion States

```text
discovered
-> retrieved
-> security_checked
-> origin_verified
-> claim_extracted
-> independently_challenged
-> evidence_qualified
-> feature_eligible
-> historically_tested
-> forward_observed
```

Each transition must have a durable receipt and a typed reason. No stage may be
inferred from a later stage's existence.

### 8.3 Independence Rules

- One earnings call is one origin cluster regardless of how many sites quote it.
- An official filing and an earnings call can be distinct evidence only when
  they contain independently available claims.
- Two articles copying the same wire story are one secondary cluster.
- Five Reddit posts linking the same article are one narrative propagation
  event, not five facts.
- Model agreement is not source agreement.
- Qadam must expose the independence-cluster count beside raw source count.

## 9. Canonical Data Contracts

### 9.1 Retrieval Envelope

Create `qadam_external_document.v1` with at least:

| Field group | Required fields |
|---|---|
| Identity | `document_id`, canonical URL, origin domain, origin type, transport |
| Time | event time, publication time, first-seen time, retrieval time, availability time, timezone, confidence |
| Integrity | raw hash, normalized-text hash, parser version, retrieval version |
| Content | media type, language, transcript provenance, bounded supporting text |
| Origin | publisher, verified channel/account ID, issuer or institution identity |
| Rights | terms-review state, retention class, redistribution class, expiry |
| Safety | prompt-injection state, quarantine state, secret scan, PII classification |
| Authority | all trade, risk, broker, proof and live-capital fields false |

### 9.2 Claim Envelope

Create `qadam_qualitative_claim.v1` with:

- `claim_id` and `document_id`;
- atomic claim type;
- subject, predicate and object;
- speaker identity and role;
- affected entity, product, geography and time period;
- direction and magnitude when explicitly stated;
- direct supporting span offsets;
- extraction model and confidence;
- source trust separate from extraction confidence;
- novelty versus prior claims;
- contradiction and corroboration links;
- strategy-family and instrument hypotheses;
- explicit falsifier;
- model-review state;
- independence cluster;
- no trading authority.

### 9.3 Feature Envelope

Create `qadam_qualitative_feature.v1` with:

- feature identity and preregistered recipe version;
- claim and origin lineage;
- feature family;
- numeric value and transformation;
- availability time;
- affected instrument and horizon;
- missingness and staleness;
- forward-label maturity time;
- historical, shadow or live classification;
- negative-control label;
- no strategy or order authority.

### 9.4 Required Claim Types

The first schema must support:

- demand strengthening or weakening;
- capacity constraint or expansion;
- backlog increase or decrease;
- delivery-date extension or improvement;
- guidance raise, maintain, cut or withdraw;
- margin expansion or compression;
- capex increase or decrease;
- inventory build or drawdown;
- regulatory approval or restriction;
- supply disruption or normalization;
- management confidence or uncertainty change;
- explicit contradiction of a prior statement.

### 9.5 Prediction Contract Envelope

Create `qadam_prediction_contract.v1` with:

- venue, event, market, condition and outcome-token identity;
- canonical question and normalized event ontology;
- mutually exclusive, exhaustive, conditional and equivalent relationships;
- open, close, expiry and resolution times;
- first-known contract definition and every later revision;
- resolution source, settlement rule, dispute state and ambiguity label;
- price, bid, ask, depth, volume and trade availability timestamps;
- Polymarket mint, burn, conversion and exchange-trade classification;
- Kalshi and Polymarket compatibility state;
- direct venue paperability and approved listed-proxy mapping;
- origin, transport, parser, terms and hash lineage;
- no source-quorum, strategy, risk, execution or proof authority.

### 9.6 Prediction Belief And Consistency Envelope

Create `qadam_prediction_belief_state.v1` with:

- contract identity and decision-time timestamp;
- probability and bounded log-odds;
- filtered belief volatility and jump state;
- spread, depth, price impact, activity and concentration features;
- exchange-equivalent turnover, net inflow and gross activity separately;
- liquidity and shock-regime classification;
- linked-contract constraint, residual and deterministic validation receipt;
- cross-venue compatibility, agreement and disagreement;
- mapped listed instrument, economic mechanism and horizon;
- missingness, staleness, cost and settlement-risk fields;
- research, historical, forward-shadow or decision-time classification;
- no direct trade or order authority.

## 10. Model And Team Responsibilities

### 10.1 Python COO

- Own schedules, retrieval policy, hashes, atomic writes and deduplication.
- Verify origin identity and timestamp rules deterministically.
- Enforce source, storage, cost and authority boundaries.
- Create no claim or strategy through free-form reasoning.
- Preserve the only guarded path into PaperOps.

### 10.2 Local Research Analyst

- Run text normalization, chunking, entity extraction and candidate claim
  extraction locally.
- Produce schema-valid JSON only.
- Mark uncertainty and preserve supporting spans.
- Never infer missing numbers or publication times.
- Never see broker credentials.

### 10.3 Frontier Strategy Lead

- Challenge the candidate claim and proposed economic mechanism.
- Identify alternative explanations and already-priced information.
- Compare the claim with prior calls, filings and independent evidence.
- Suggest testable market mappings, horizons and falsifiers.
- Produce research proposals, not execution approval.

#### 10.3.1 Functional Specialist Challenge Matrix

The Strategy Lead should receive five blinded, schema-constrained challenge
records rather than a free-form committee transcript:

| Perspective | Required question |
|---|---|
| Business quality | Does the operating evidence support durable economics, or is the apparent signal financially weak? |
| Catalyst | What changed now, when did it become public, and why could it matter inside the declared horizon? |
| Macro regime | Which rates, liquidity, commodity, policy or correlation regime strengthens or invalidates the mechanism? |
| Market reaction | Do price, volatility, volume, flow, prediction-market and execution conditions confirm or contradict the thesis? |
| Adversarial skeptic | What alternative explanation, prior failure, crowding, leakage or already-priced information could make the setup false? |

Each perspective uses the same immutable evidence packet, cannot see the other
answers during first-pass inference, and returns evidence IDs, direction,
horizon, mechanism, counterargument, falsifier and uncertainty. Python validates
and aggregates fields deterministically. The Strategy Lead explains disagreement
but cannot turn model consensus into factual corroboration.

### 10.4 Head Of Quant

- Receive structured feature matrices only after provenance checks.
- Compare linear, nonlinear and quantum-assisted methods on identical samples.
- Test whether interactions add out-of-sample value after costs.
- Never turn novelty or model complexity into strategy admission by itself.

### 10.5 Human Fund Manager

- Approve new origin classes, authenticated channels and risk-envelope changes.
- Review terms or licensing decisions that cannot be automated safely.
- Review material changes to the source promotion policy.
- Need not approve every bounded paper hypothesis inside an already frozen and
  certified paper policy.

## 11. Historical And Forward Research Protocol

### 11.1 Historical Acquisition

Historical backfill should prioritize:

- official investor-relations transcript and presentation archives;
- SEC 8-K earnings releases and exhibits;
- verified official YouTube captions when publication history is available;
- issuer newsrooms and RSS archives;
- selected independent reporting where retention permits;
- historical prediction-market, options-flow and price context already held by
  Qadam;
- official Kalshi market, trade, candlestick, lifecycle and settlement history;
- official Polymarket Gamma, CLOB and Polygon settlement history with market,
  condition and token identity preserved;
- order-book or trade snapshots sufficient to measure spread, depth, price
  impact and executable size without reconstructing unavailable liquidity.

Every unavailable source must be classified as:

- `available_provider_backed`;
- `available_primary_archive`;
- `forward_only`;
- `pre_inception`;
- `terms_restricted`;
- `authentication_required_not_approved`;
- `provider_gap`;
- `excluded_low_value`.

### 11.2 Point-In-Time Alignment

- Use the first time the content was publicly available, not the date discussed.
- Respect before-open, during-session and after-close earnings timing.
- Enter historical tests only on the first tradeable bar after availability.
- Preserve transcript corrections as later versions.
- Keep preliminary captions distinct from final transcripts.
- Do not use current ETF constituents in an old historical period without a
  point-in-time membership record.

### 11.3 Outcome Windows

Build outcomes for the horizon appropriate to each recipe:

- intraday reaction when reliable intraday data exists;
- close-to-close 1, 3 and 5-day outcomes;
- 20 and 60-day drift outcomes;
- maximum favourable and adverse excursion;
- benchmark-relative return;
- sector-relative return;
- spread, slippage and proxy-basis assumptions;
- volume, volatility and options-flow changes.

### 11.4 Statistical Discipline

- Preregister feature recipes and horizons before opening holdout data.
- Use walk-forward splits and untouched holdouts.
- Apply false-discovery controls across claim types, instruments and horizons.
- Include shuffled-text, shifted-time and wrong-instrument negative controls.
- Compare against price-only, sector-beta, seasonal and simple trend baselines.
- Report sample size and independent-event count separately.
- Reject results dominated by one issuer, one quarter or one market regime.
- Require a matched classical baseline for every quantum-assisted result.

## 12. Pattern And Strategy Integration

### 12.1 New Pattern Families

The Pattern Recognition engine should be able to rank:

- management claim to price lag;
- guidance-reaction divergence;
- language change versus prior call;
- cross-issuer sector contagion;
- supply-chain constraint propagation;
- official evidence versus prediction-market disagreement;
- official evidence versus options-flow confirmation;
- narrative acceleration after an original event;
- source disagreement and later resolution;
- regime-conditioned claim effectiveness.

### 12.2 Pattern Record Requirements

Each pattern must show:

- the research question;
- originating claims and independence clusters;
- affected market and paperable proxy;
- first and latest observations;
- research score and its components;
- historical sample and holdout state;
- what would confirm it;
- what would invalidate it;
- current blocker;
- next destination in the 10-stage lifecycle.

### 12.3 Core Strategy Refinement

Qualified patterns may propose changes to:

- Crude Oil Energy Security Disruption;
- Defence Repricing Geopolitical Watch;
- Prediction Market Geopolitical Dislocation;
- Semiconductor Policy Options Asymmetry;
- Silver Macro Liquidity Stress.

Examples include adding a management-capacity feature to the semiconductor
family or an official-producer guidance feature to the energy family.

### 12.4 Emerging Strategy Formation

A pattern outside the core five may form an emerging strategy only when it has:

- a distinct economic mechanism;
- a stable source recipe;
- an actionable direction rule;
- an instrument or approved paper proxy;
- a declared horizon;
- historical or bounded discovery-micro evidence permitted by policy;
- explicit invalidation;
- a cost and risk concept;
- no unresolved negative-control failure.

Agent Reach retrieval success alone can never satisfy these requirements.

### 12.5 Prediction-Market Strategy Translation

Prediction Market Intelligence V2 first enriches the existing **Prediction
Market Geopolitical Dislocation** family. A result may instead refine another
core family when the event has a direct, preregistered mechanism to oil,
defence, semiconductors, silver or the broad market.

Only a mechanism that remains distinct after testing may form an emerging
pattern-sourced strategy. The initial candidate names are:

- Event Belief Jump Repricing;
- Cross-Venue Belief Divergence;
- Logical Constraint Dislocation.

These are research labels, not admitted strategies. Promotion requires correct
event identity, point-in-time history, liquidity-qualified observations,
untouched holdout performance, net-of-cost expectancy, forward evidence,
negative-control survival and a paperable expression. Logical arbitrage may not
be expressed through an unrelated Alpaca symbol merely because no direct venue
route exists.

## 13. Akber Evidence-Fit Integration

The programme must reduce schema mismatch between evidence Qadam can collect and
evidence Akber can evaluate.

### 13.1 Context

Permitted qualitative inputs:

- verified actor and affected market;
- current regime and existing strategy family;
- independent source clusters;
- prior comparable claims and outcomes.

### 13.2 Catalyst

Permitted qualitative inputs:

- a genuinely new official statement;
- material change from prior guidance;
- fresh contradiction or confirmation;
- known publication time and expiry;
- documented relevance to the instrument.

### 13.3 Confirmation

Qualitative evidence may propose what needs confirmation, but market systems
must supply:

- current price reaction;
- volume and flow;
- volatility and pricing-gap evidence;
- prediction-market movement where relevant;
- nonlinear or quantum review state.

### 13.4 Risk

Historical analogues may supply an expectancy distribution and invalidation
concept. The risk engine must independently set size, loss limit, concentration
and portfolio compatibility.

### 13.5 Execution

Agent Reach supplies nothing authoritative here. Current provider-backed spread,
liquidity, tradability and guarded Alpaca Paper route state remain mandatory.

### 13.6 Postmortem Learning

Every accepted, held or rejected qualitative setup must preserve:

- the expected outcome written before maturation;
- which claim and feature affected the decision;
- whether Akber passed, held or vetoed it;
- the realized path and counterfactual no-order result;
- whether the qualitative evidence improved the decision versus a price-only
  baseline.

### 13.7 Prediction-Market Evidence Roles

- Contract semantics, linked-event state and external world evidence may fill
  **Context**.
- A fresh, liquidity-qualified belief jump or constraint break may fill
  **Catalyst**.
- Cross-venue agreement, depth, spread, price impact and mapped listed-market
  response may contribute to **Confirmation**.
- Historical analogues may propose expectancy and invalidation, but cannot
  replace the canonical risk calculation.
- Prediction-market liquidity cannot stand in for current Alpaca proxy spread,
  liquidity or route checks.
- One underlying event represented on two venues is not automatically two
  independent causal sources.

## 13A. All-Lane Authority And Trade-Conversion Architecture

The current failure class is not solved by giving every component the ability
to trade. It is solved by giving every lane explicit **stage authority**, making
its evidence consumable by the next stage, and reserving governance and broker
authority for the existing deterministic owners.

### 13A.1 Authority Tiers

| Tier | Authority | Permitted result |
|---|---|---|
| A0 | Observe | Retrieve or record a timestamped observation with no evidence credit. |
| A1 | Qualify evidence | Contribute typed evidence to declared Akber roles with provenance, freshness and independence. |
| A2 | Pattern judgment | Rank, strengthen, weaken, reject or challenge a relationship. |
| A3 | Strategy nomination | Propose a core-family refinement or emerging strategy with mechanism, direction, horizon and invalidation. |
| A4 | Paper-review nomination | Nominate a complete setup to the validated-strategy or discovery-micro Router review. This is not approval. |
| A5 | Governance | Set size, exposure compatibility and one Router disposition. Owned only by portfolio risk and Router. |
| A6 | Paper execution | Submit and reconcile through guarded Alpaca Paper. Owned only by PaperOps. |

No research or model lane may hold A5 or A6. An A4 nomination must still pass
Akber, current portfolio risk, duplicate exposure, drawdown, idempotency, route
freshness and PaperOps checks.

### 13A.2 Complete Lane Capability Matrix

| Lane | Maximum authority | What it may contribute | What it needs to advance |
|---|---|---|---|
| Strategy-informed discovery | A4 | Core-family mapping, current trigger, direction, horizon and strategy lineage | A complete tradeability envelope, current confirmation, positive net expectancy, invalidation and paperable proxy |
| Strategy-agnostic discovery | A4 | Distinct relationship and emerging-strategy nomination | Preregistered mechanism, non-duplicate identity, instrument mapping, current trigger and Foundry acceptance |
| Classical recognition | A3 | Linear, analogue, state, regime and conventional nonlinear evidence | Point-in-time samples, declared baseline, holdout, costs, stability and negative controls |
| Quantum-assisted challenger | A2 | Incremental nonlinear challenge, downgrade or measured uplift | Identical evidence, labels, folds and costs versus the strongest matched classical method |
| Validated-strategy paper lane | A4 | Validated paper-review nomination | Promoted edge, complete lineage, forward evidence and current tradeability state |
| Discovery-micro paper lane | A4 | Bounded experimental paper-review nomination | Active trigger, direction, live market confirmation, positive current expectancy after costs, invalidation, decision-time shadow, spread/liquidity and risk proposal |
| Negative-control search | A2 block-only | False-discovery warning, downgrade or rejection | The same frozen recipe under shuffled, shifted, placebo or wrong-instrument evidence |
| Kalshi-only research | A2 | Venue-specific belief and catalyst evidence | Correct contract identity, point-in-time probability, liquidity and mapped-market mechanism |
| Polymarket-only research | A2 | Venue-specific belief, activity and catalyst evidence | Correct condition/token identity, transaction decomposition, liquidity and mapped-market mechanism |
| Prediction-market consensus | A3 | Cross-venue corroboration and strategy nomination | Semantically compatible contracts, independent venue state, executable quality and mature mapped outcomes |
| Prediction-market disagreement | A3 | Divergence pattern and strategy nomination | Compatible settlement semantics, gap persistence, depth, costs, direction rule and mapped paper expression |
| Prediction-to-market lead-lag | A3 | Belief-jump to listed-market strategy proposal | Frozen lag, instrument, horizon, baseline, costs, holdout and current trigger |
| Direct prediction instruments | A2 research-only | Contract-level simulation and logical-dislocation evidence | A separately governed paper route, lifecycle, settlement, liquidity and execution controls; unavailable in this release |
| STOCK Act filing events | A3 | Policy or ownership catalyst and sector strategy proposal | Official availability time, issuer mapping, non-leaking event date, direction and independent market confirmation |
| Prediction-market x STOCK Act interaction | A3 | Cross-source interaction and strategy proposal | Independent origins, preregistered interaction, sufficient sample, holdout and mapped instrument |
| Unusual Whales confirmation | A2 | Options-flow, volume and market-reaction Confirmation | Provider-backed decision-time observation, symbol mapping, freshness and no historical claim when only forward data exists |
| Forward shadow | A4 readiness input | Decision-time no-order snapshot, counterfactual and matured outcome | Frozen setup identity, timestamp, expiry and real elapsed market time |
| Agent Reach qualitative evidence | A2 | Verified Context, Catalyst and falsifiable qualitative features | Approved origin, supporting span, availability time, trust tier and independence cluster |
| Functional specialist challenge | A2 | Structured support, disagreement, falsifier and downgrade | Same immutable evidence packet, blinded first pass and schema-valid challenge records |
| Prediction Market Intelligence V2 | A3 | Contract graph, belief jump, consistency, liquidity and cross-asset strategy evidence | Contract compatibility, deterministic graph validation, costs, holdout, forward evidence and listed-paper expression |
| Emerging Power Scarcity and Congestion sleeve | A4 | Pattern-sourced strategy and current scarcity/congestion trigger | Provider-backed grid/weather/power evidence, mapped listed proxy, current confirmation, expectancy and risk state |
| Authenticated social research | A1 discovery-only | Narrative attention, disagreement and original-source leads | Separate approval, terms review, isolated credentials and corroboration; deferred by default |

Each configured strategy sleeve also needs a registered evidence-fit and trigger
profile so the generic strategy-informed lane does not collapse six different
economic mechanisms into one checklist:

| Strategy sleeve | Default profile | Current paper expression requirement |
|---|---|---|
| Crude Oil Energy Security Disruption | Event catalyst | A fresh disruption trigger, energy repricing confirmation and a qualified `USO`, `BNO` or `XLE` expression; `CL=F` may remain research context. |
| Defence Geopolitical Repricing | Event catalyst | A fresh escalation, procurement or policy trigger with confirmation in `ITA`, `XAR`, `LMT` or `PPA`. |
| Prediction Market Geopolitical Dislocation | Prediction market | Compatible event semantics, belief or disagreement trigger, listed-market mechanism and a separately qualified Alpaca Paper proxy. |
| Semiconductor Policy Asymmetry | Qualitative management or policy catalyst | Fresh policy, capacity, guidance or supply evidence with confirmation in `SMH`, `SOXX`, `NVDA` or `QQQ`. |
| Silver Macro Liquidity Stress | Regime state | Persistent liquidity, rates or stress state with current confirmation in `SLV` or `SIL`; `SI=F`, `GLD` and `SPY` may remain context. |
| Power Scarcity and Congestion | Regime state | Provider-backed grid, weather and price stress mapped to an approved `CEG`, `VST`, `NRG`, `TLN`, `XLU`, `GRID` or `UNG` proxy with basis-risk controls. |

### 13A.3 Canonical Lane Contracts

Extend `orchestrator/qadam_tradeability_capabilities.py` with
`qadam_lane_capability.v1` for the static authority and evidence-role contract
of each lane. Required fields include:

- lane identity, owner, version and status;
- allowed authority tier and prohibited authority tiers;
- allowed evidence roles and field paths;
- required provider classes, freshness rules and independence rules;
- valid instruments, strategy families, horizons and evidence profiles;
- permitted positive, hold, downgrade, veto and expiry outcomes;
- required downstream owner and canonical artifact;
- paperability and route constraints;
- negative-control requirements.

Extend `orchestrator/qadam_evidence_contracts.py` with
`qadam_lane_contribution.v1` for each runtime contribution. Required fields
include:

- lane, generation, evidence packet, research goal and candidate identity;
- source, claim, pattern, strategy and instrument lineage;
- current trigger, direction, horizon and expiry;
- Context, Catalyst and Confirmation contributions with provenance;
- historical and current expectancy references;
- invalidation and reward-to-risk proposal;
- price, volatility, spread, liquidity and execution references where allowed;
- decision-time shadow reference;
- support, missing, adverse, stale and contradiction states;
- content hash, producer version and atomic completion receipt;
- authority tier and all broker, order, proof and live-capital flags false.

Extend the existing canonical `orchestrator/qadam_tradeability_pipeline.py`
producer so one deterministic compiler consumes all compatible contributions
for one candidate and generation into a versioned `TradeabilityEnvelope`.
Producers may not write competing hypothesis or Akber shapes. Equivalent
evidence must be normalized through generated accessors rather than copied into
parallel JSON contracts.

### 13A.4 Trigger-To-Decision Fast Path

When any A3-capable lane produces an active directional trigger during a
tradeable session, the operator must run this dependency chain immediately:

```text
lane contribution
-> evidence and independence validation
-> current price, volatility, spread and liquidity snapshot
-> current cost and expectancy calculation
-> decision-time shadow snapshot
-> strategy and invalidation compilation
-> Akber profile evaluation
-> portfolio-risk proposal
-> single Router disposition
-> guarded PaperOps handoff when accepted
```

The chain must use one generation ID and immutable input hashes. A later refresh
cannot silently combine yesterday's strategy template with today's market
snapshot. If the market is closed, the setup is queued with an expiry and is
revalidated at the next permitted session rather than discarded or submitted
with fabricated execution evidence.

### 13A.5 Evidence-Fit Profiles

Akber and the compiler must request evidence according to the strategy's actual
mechanism:

- event-catalyst profiles prioritize event identity, novelty, affected market,
  current repricing and expiry;
- regime-state profiles prioritize persistent macro or market state, current
  technical confirmation and regime invalidation;
- flow-confirmation profiles use Unusual Whales or equivalent flow only as
  current confirmation, not as a causal trigger by itself;
- prediction-market profiles distinguish belief, contract logic, venue
  liquidity and listed-proxy execution;
- qualitative-management profiles use official claims as Context or Catalyst
  and require separate current market confirmation;
- validated-edge profiles preserve the full historical and forward standard;
- discovery-micro profiles permit bounded paper evidence without claiming an
  edge, while retaining current expectancy, invalidation, execution and
  portfolio controls.

A lane must never be asked for a field it cannot legitimately produce. The
capability registry must route that field to the correct market, risk, shadow or
execution provider instead of recording a permanent generic hold.

### 13A.6 Trade-Frequency Objective

The operational objective is to remove **artificial inactivity**:

- scan every enabled strategy and emerging sleeve on every eligible market
  cycle;
- evaluate every fresh active trigger before its expiry;
- allow multiple distinct qualified setups on the same day;
- preserve candidate identity, exposure and idempotency so repeated evidence
  cannot create duplicate orders;
- route under-evidenced but complete setups through discovery-micro rather than
  requiring validated-edge status;
- classify every non-progression as missing evidence, adverse evidence, stale
  evidence, inactive trigger, duplicate exposure, portfolio risk or code defect;
- automatically repair only safe data refresh and contract-shape defects;
- measure opportunity conversion by lane and investigate any productive lane
  that remains at zero downstream evaluations during eligible market time.

There is no forced minimum order count. Success means Qadam evaluates and routes
all legitimately complete opportunities quickly, not that it manufactures one
trade each day regardless of evidence.

### 13A.7 Golden-Journey And Reachability Proof

Every lane needs a disk-backed test using its real producer and consumer
contracts:

1. Positive evidence reaches the maximum permitted authority tier.
2. Missing evidence produces a typed hold naming the correct owner.
3. Adverse evidence produces a veto or downgrade.
4. Stale evidence expires and refreshes without contaminating generations.
5. Inactive triggers do not create candidates.
6. Duplicate exposure and idempotency prevent repeated submission.
7. An A4 setup reaches a broker-disabled PaperOps canary with complete lineage.
8. No lane can call a broker, mutate risk authority or create proof credit.

Module fixtures alone do not satisfy this requirement. Certification must run
the scheduled producer chain against immutable on-disk artifacts and verify the
actual consumer access paths.

## 14. Autonomous Operating Schedule

| Job | Suggested cadence | Purpose |
|---|---|---|
| Official RSS and newsroom polling | Every 5 to 15 minutes | Detect new primary events |
| Official event-calendar refresh | Daily and weekly look-ahead | Prepare expected calls and briefings |
| Caption/transcript retrieval | Every 15 minutes around known events | Obtain qualitative evidence quickly |
| Discovery search | Hourly with strict query budget | Find missing original sources |
| Claim extraction | On new document | Produce structured local candidates |
| Strategy Lead challenge | Material claims only | Prevent narrative overreach |
| Market confirmation refresh | During market hours | Resolve price, volume and volatility context |
| Outcome maturation | After each declared horizon | Produce forward labels |
| Incremental backtest | When new labels mature | Update evidence without rerunning everything |
| Full challenger backtest | Weekly | Check stability and false discovery |
| Strategy governance review | Monthly or material change | Admit or retire strategy versions |
| Telegram brief | Material change only | Explain new evidence and decisions |
| Prediction contract graph refresh | Every 5 to 15 minutes for active mapped events | Maintain event identity, logical links and lifecycle state |
| Prediction belief-state refresh | During active venue hours and around known shocks | Update log-odds, jumps, market quality and cross-venue state |
| Prediction-market constraint scan | On each compatible state refresh | Detect deterministic inconsistencies after costs and depth |
| Lane contribution compilation | On every atomic lane completion | Build one same-generation tradeability envelope from compatible evidence |
| Active-trigger fast path | Immediately during eligible market sessions | Refresh market, expectancy, shadow, Akber, risk and Router state before trigger expiry |
| Closed-market revalidation | At the next permitted session open | Recheck queued setups using current execution evidence |
| Lane conversion diagnosis | Every market cycle and daily summary | Identify evidence, trigger, contract or code-defect reasons for non-progression |
| Broker-disabled reachability canary | At startup, after release and daily | Prove complete A4 envelopes can reach the PaperOps boundary without submitting an order |

No job should send a message merely because it ran.

## 15. Storage And Resource Policy

Qadam previously experienced severe disk pressure. This programme must be
bounded from its first release.

- Store research data under ignored `data/research/` paths.
- Refuse to run if any raw path is Git-trackable.
- Never download video when captions are available.
- Delete temporary HTML and media after normalized, hashed evidence is written.
- Compress immutable text and metadata partitions.
- Use a 10 GB initial hard ceiling for the entire qualitative evidence lane.
- Pause acquisition at 80 percent of the lane budget.
- Maintain per-origin, per-day and per-document response limits.
- Record bytes fetched, retained and deleted in every run.
- Keep a manifest so cleanup never deletes an artifact referenced by a
  validated test or audit record.
- Add a dry-run retention and cleanup command.

## 16. Phased Implementation

## AR-0 - Baseline, Ownership And Contract Reconciliation

### Objective

Freeze the current system and establish exactly what Agent Reach may extend.

### Build

- Inventory current Agent Reach bridge, source interfaces and runtime artifacts.
- Reconcile the 41-source universal matrix with the 35-source legacy registry.
- Add explicit transport, origin, trust and quorum count fields.
- Record current context, catalyst and direction-missing rates entering Akber.
- Record current pattern, strategy, shadow and paper-decision throughput.
- Register artifact owners and prohibit duplicate producers.
- Mark the June Agent Reach note as historical, not the active specification.

### Artifacts

- `data/runtime/qadam_agent_reach_baseline.json`
- `data/runtime/qadam_source_count_contract.json`
- `data/runtime/qadam_qualitative_evidence_gap_map.json`
- `config/qadam_runtime_artifact_ownership.json` updates

### Checks

- `scripts/check_qadam_agent_reach_baseline.py`
- `scripts/check_qadam_source_count_contract.py`

### Acceptance

- Every count has one definition and one owner.
- Agent Reach does not change canonical source counts.
- Current downstream blockers are measured from real artifacts.
- Existing dashboard and PaperOps behavior remain unchanged.

## AR-1 - Supply-Chain Audit And Sandboxed Worker

### Objective

Create a narrow retrieval runtime that cannot compromise Qadam or the operator's
machine.

### Build

- Pin the reviewed Agent Reach commit and record its hash.
- Create an SBOM and dependency license manifest.
- Pin every directly executed backend and dependency with hashes.
- Implement the isolated worker and filtered environment.
- Add command, domain, size, time, concurrency and disk allowlists.
- Disable system install, browser sessions, cookies, auto-update and config
  mutation in code and tests.
- Make worker output pass through one JSON spool contract.

### Artifacts

- `config/qadam_agent_reach_lock.json`
- `config/qadam_agent_reach_command_policy.json`
- `data/runtime/qadam_agent_reach_supply_chain_audit.json`
- `data/runtime/qadam_agent_reach_sandbox_status.json`

### Checks

- `scripts/check_qadam_agent_reach_supply_chain.py`
- `scripts/check_qadam_agent_reach_sandbox.py`

### Acceptance

- The worker cannot read a seeded fake Alpaca or model secret.
- Attempts to access browser cookies, home directories or arbitrary commands
  fail closed.
- An upstream version change fails certification until reviewed.
- A malicious retrieved page cannot cause command execution.

## AR-2 - Origin Registry, Terms And Trust Policy

### Objective

Define what Qadam may retrieve and how each underlying origin may be used.

### Build

- Create an approved origin registry tied to strategy families and instruments.
- Record domain, feed URL, verified channel ID, origin class and identity method.
- Record terms, retention, attribution, redistribution and historical-use state.
- Define trust tiers and independence-cluster rules.
- Separate discovery transport from credited origin.
- Add source promotion and demotion receipts.
- Require human review for authenticated or terms-ambiguous channels.

### Artifacts

- `config/qadam_external_origin_registry.json`
- `config/qadam_external_evidence_trust_policy.json`
- `data/runtime/qadam_external_origin_terms_matrix.json`
- `data/runtime/qadam_external_origin_promotion_ledger.jsonl`

### Checks

- `scripts/check_qadam_external_origin_registry.py`
- `scripts/check_qadam_external_origin_terms.py`

### Acceptance

- Every enabled URL maps to an approved origin and use class.
- Search, Jina, RSS, YouTube and GitHub are represented as transports.
- No social origin can satisfy factual quorum by itself.
- Terms-unknown origins are discovery-only.

## AR-3 - Official Web, RSS, YouTube And GitHub Acquisition

### Objective

Acquire fresh, high-value qualitative evidence from the approved zero-auth
channel set.

### Build

- Poll official feeds with ETag and Last-Modified support.
- Discover and retrieve official documents from allowlisted sites.
- Retrieve captions from verified official YouTube channels.
- Retrieve narrow official GitHub release metadata.
- Add bounded pagination, rate limits, retries and per-channel circuit breakers.
- Canonicalize URLs and deduplicate content by hash and origin identity.
- Write immutable retrieval envelopes atomically.
- Do not retain video or unnecessary page assets.

### Artifacts

- `data/runtime/qadam_external_acquisition_status.json`
- `data/runtime/qadam_external_channel_health.json`
- `data/runtime/qadam_external_document_manifest.jsonl`
- ignored `data/research/qadam_external_evidence/raw/`

### Checks

- `scripts/check_qadam_external_acquisition.py`
- `scripts/check_qadam_external_retrieval_idempotency.py`

### Acceptance

- Repeated polling creates no duplicate logical documents.
- Interrupted runs resume without corrupting manifests.
- Official publication and first-seen times are preserved.
- No authenticated session is used.
- Channel failure does not stop unrelated Qadam services.

## AR-4 - Provenance, Security And Point-In-Time Evidence Lake

### Objective

Convert retrieved content into durable, auditable evidence suitable for research.

### Build

- Implement the external document, claim and feature schemas.
- Add content and normalized-text hashing.
- Add origin verification and publication-time confidence.
- Detect prompt injection, secrets, hidden text and suspicious redirects.
- Quarantine unsafe or ambiguous documents.
- Preserve revision chains without mutating prior versions.
- Write public-safe summaries separately from internal research content.

### Artifacts

- `data/runtime/qadam_external_documents.jsonl`
- `data/runtime/qadam_external_evidence_security_audit.json`
- `data/runtime/qadam_external_evidence_provenance_audit.json`
- ignored `data/research/qadam_external_evidence/normalized/`

### Checks

- `scripts/check_qadam_external_evidence_contracts.py`
- `scripts/check_qadam_external_evidence_provenance.py`
- `scripts/check_qadam_external_evidence_security.py`

### Acceptance

- Every research-eligible document has origin, availability time and hashes.
- Quarantined text cannot reach a model or pattern feature.
- Public artifacts contain no raw copyrighted transcript, secret or local path.
- Revised documents remain point-in-time reproducible.

## AR-5 - Structured Claim Extraction And Model Challenge

### Objective

Turn text into falsifiable structured claims without allowing model prose to
become evidence.

### Build

- Add deterministic document segmentation and speaker attribution.
- Use the local model for schema-constrained candidate extraction.
- Preserve supporting span offsets for every extracted claim.
- Calculate extraction confidence separately from source trust.
- Compare new claims with prior claims from the same issuer and speaker.
- Use the frontier model to challenge mechanism, novelty and alternatives.
- Reject unsupported, ambiguous or purely promotional claims.
- Add model-version and prompt-version receipts.

### Artifacts

- `data/runtime/qadam_qualitative_claims.jsonl`
- `data/runtime/qadam_qualitative_claim_rejections.jsonl`
- `data/runtime/qadam_qualitative_claim_challenges.jsonl`
- `data/runtime/qadam_qualitative_claim_summary.json`

### Checks

- `scripts/check_qadam_qualitative_claim_extraction.py`
- `scripts/check_qadam_qualitative_claim_grounding.py`

### Acceptance

- Every accepted claim traces to a real supporting span.
- A model cannot invent a timestamp, speaker, magnitude or direction.
- Contradictory claims are linked rather than silently overwritten.
- Fixture documents with prompt injection cannot alter model instructions.

## AR-6 - Entity, Instrument And Temporal Evidence Graph

### Objective

Connect claims to companies, products, suppliers, strategies, instruments and
outcomes so Qadam gains a reusable relationship graph rather than a pile of
summaries.

### Build

- Add document, claim, speaker, entity, product, geography and event nodes.
- Add asserts, mentions, corroborates, contradicts, affects, depends-on and
  precedes edges.
- Map entities to the 19 instruments and point-in-time ETF constituents.
- Cluster derivative coverage around the original source.
- Preserve observed, inferred and governed graph layers.
- Prevent inferred edges from receiving observed-evidence authority.

### Artifacts

- `data/runtime/qadam_qualitative_graph_summary.json`
- `data/runtime/qadam_qualitative_entity_mappings.jsonl`
- `data/runtime/qadam_qualitative_instrument_mappings.jsonl`
- temporal graph records in the existing canonical graph store

### Checks

- `scripts/check_qadam_qualitative_temporal_graph.py`
- `scripts/check_qadam_qualitative_instrument_mapping.py`

### Acceptance

- Every feature traces through claim, document and origin nodes.
- Same-origin repetition does not inflate independence.
- Historical mappings use point-in-time constituents when required.
- Unmapped claims remain research backlog and cannot reach strategy formation.

## AR-7 - Historical Qualitative Backfill And Forward Labels

### Objective

Build enough point-in-time observations to test whether qualitative features
precede market outcomes.

### Build

- Acquire approved official archives by issuer and date partition.
- Record unsupported and forward-only histories explicitly.
- Align events to the first tradeable price observation.
- Generate return, drawdown, volatility, volume and options-context labels.
- Preserve historical and forward-observation namespaces separately.
- Make jobs resumable, idempotent and disk-bounded.
- Add coverage and missing-window classification.

### Artifacts

- `data/runtime/qadam_qualitative_history_coverage.json`
- `data/runtime/qadam_qualitative_forward_window_status.json`
- `data/runtime/qadam_qualitative_label_manifest.jsonl`
- ignored `data/research/qadam_external_evidence/features/`

### Checks

- `scripts/check_qadam_qualitative_history.py`
- `scripts/check_qadam_qualitative_point_in_time.py`
- `scripts/check_qadam_qualitative_forward_labels.py`

### Acceptance

- No label uses information unavailable at decision time.
- Every missing window has a typed reason.
- Historical replay cannot advance the 30-day paper growth trial or paper proof
  ledger.
- Restart and rerun produce identical logical records.

## AR-8 - Qualitative Pattern Lab And Challenger Backtests

### Objective

Test the priority evidence programmes against fair baselines and negative
controls.

### Build

- Implement preregistered management-guidance, divergence, PEAD, narrative and
  supply-chain feature recipes.
- Run linear event studies and lag tests.
- Run state-matrix, interaction and nonlinear models only with sufficient data.
- Run matched quantum review only after classical baselines exist.
- Add walk-forward, untouched holdout, costs and false-discovery controls.
- Record rejected patterns as reusable negative knowledge.
- Rank patterns by evidence quality, repeatability, net effect and actionability.

### Artifacts

- `data/runtime/qadam_qualitative_pattern_candidates.jsonl`
- `data/runtime/qadam_qualitative_pattern_rejections.jsonl`
- `data/runtime/qadam_qualitative_backtest_summary.json`
- `data/runtime/qadam_qualitative_quantum_review.json`

### Checks

- `scripts/check_qadam_qualitative_pattern_lab.py`
- `scripts/check_qadam_qualitative_negative_controls.py`
- `scripts/check_qadam_qualitative_quantum_comparison.py`

### Acceptance

- Every candidate beats its declared baseline on the metric it claims to
  improve.
- Negative controls do not promote.
- Quantum output reports incremental value versus the matched classical model.
- No backtest result creates a paper order or proof credit.

## AR-9 - Pattern Score, Direction And Strategy Foundry Bridge

### Objective

Make accepted qualitative patterns usable by current Pattern Recognition and
Strategy Foundry contracts.

### Build

- Add qualitative features to Pattern Score V3 without changing score meaning.
- Preserve source recipe, independence clusters and feature availability.
- Produce one current direction or an explicit unresolved state.
- Map qualified patterns to a core-family refinement or emerging strategy.
- Preserve Research Goal, pattern, strategy-version and candidate identity.
- Deduplicate repeated documents and previously considered setups.
- Reject weak hypotheses before Akber.

### Artifacts

- `data/runtime/qadam_qualitative_pattern_score_bridge.json`
- `data/runtime/qadam_qualitative_direction_resolutions.jsonl`
- `data/runtime/qadam_qualitative_strategy_impacts.jsonl`
- existing canonical strategy artifacts updated by their current owners

### Checks

- `scripts/check_qadam_qualitative_pattern_bridge.py`
- `scripts/check_qadam_qualitative_strategy_bridge.py`

### Acceptance

- A source document cannot skip Pattern Recognition.
- Every actionable direction has fresh evidence IDs and an expiry.
- Existing core families are refined rather than duplicated.
- New mechanisms appear as emerging strategies, not a sixth core family by
  default.

## AR-10 - Akber Evidence Fit And Bounded Paper Experiment Eligibility

### Objective

Allow genuinely usable qualitative evidence to fill the Akber fields it can
support while preserving market, risk and execution requirements.

### Build

- Translate Tier A and B evidence into typed Context and Catalyst inputs.
- Translate historical analogues into expectancy and invalidation proposals.
- Require current market providers for Confirmation and Execution fields.
- Add stale, low-trust, derivative-source and contradiction hold reasons.
- Add explicit distinction between missing evidence and adverse evidence.
- Connect eligible strategy versions to the current discovery-micro policy.
- Preserve current risk caps, duplicate-exposure checks and guarded paper route.

### Artifacts

- `data/runtime/qadam_qualitative_akber_inputs.jsonl`
- `data/runtime/qadam_qualitative_akber_explanations.jsonl`
- `data/runtime/qadam_qualitative_paper_eligibility.json`

### Checks

- `scripts/check_qadam_qualitative_akber_bridge.py`
- existing Akber, Router, risk and PaperOps checkers

### Acceptance

- Accepted qualitative evidence reduces only legitimate Context or Catalyst
  missingness.
- No qualitative record fabricates spread, liquidity or expected return.
- Missing evidence produces a hold; adverse evidence produces a veto.
- A clean bounded paper setup can reach the existing Router without manual data
  reformatting.
- No bypass, exception sleeve or direct broker call exists.

## AR-11 - Autonomous Scheduling, Self-Healing And Resource Control

### Objective

Run the enrichment lane unattended without destabilizing Qadam.

### Build

- Add jobs to the current operator service in dependency order.
- Use per-channel circuits and repair records.
- Retry only idempotent retrieval and transformation work.
- Resume interrupted queues after restart, sleep or network loss.
- Enforce disk, response, provider-call and model-call ceilings.
- Refresh downstream components only after atomic upstream completion.
- Add heartbeat, lag, throughput and next-action fields.
- Prevent a failed optional channel from blocking price, risk or PaperOps health.

### Artifacts

- `data/runtime/qadam_agent_reach_operator_status.json`
- `data/runtime/qadam_agent_reach_repair_queue.jsonl`
- `data/runtime/qadam_agent_reach_resource_state.json`
- `data/runtime/qadam_agent_reach_soak_status.json`

### Checks

- `scripts/check_qadam_agent_reach_operations.py`
- `scripts/check_qadam_agent_reach_resource_limits.py`

### Acceptance

- Seven unattended sessions complete with no corrupt artifacts.
- Simulated network loss, sleep, provider error and disk pressure recover safely.
- Optional channel failures remain isolated.
- No automatic repair installs code, changes authority or edits secrets.

## AR-12 - Dashboard And Telegram Evidence Visibility

### Objective

Explain what Qadam learned from qualitative evidence without changing the
established dashboard architecture.

### Dashboard Enrichment

| Existing module | Added information |
|---|---|
| Data Sources | Transport versus origin, trust tier, freshness, terms and health |
| Trading Universe | Relevant issuers, constituents and qualitative evidence coverage |
| Pattern Recognition | Claim-to-market evidence chain, score, status, blocker and next stage |
| Quantum Edge | Only matched nonlinear/quantum comparisons derived from structured features |
| Trading Strategies | Which evidence refined a core family or formed an emerging strategy |
| Decision Room | Which Akber fields qualitative evidence filled and what is still missing |
| Order Monitor | No new authority; show lineage only for an accepted guarded paper setup |
| Results & Lessons | Whether the qualitative feature improved or harmed the decision |
| Tests & Improvements | Proposed source, feature or threshold changes and their validation state |

### Telegram Rules

Send only when something material changes:

- a new verified claim changes a research hypothesis;
- a historical or forward outcome matures;
- a pattern strengthens, weakens or is rejected;
- a strategy is refined or newly formed;
- Akber changes state;
- a paper decision or material operational blocker occurs.

Do not report raw scrape counts as an achievement. Do not repeat unchanged next
questions. Do not publish copyrighted transcript text. Keep messages short and
specific.

### Artifacts

- `data/runtime/qadam_qualitative_dashboard_summary.json`
- `data/runtime/qadam_qualitative_communications_summary.json`
- `data/runtime/qadam_qualitative_notification_dedupe.jsonl`

### Checks

- `scripts/check_qadam_qualitative_dashboard.py`
- `scripts/check_qadam_qualitative_telegram.py`
- existing dashboard anti-slop and Telegram quality checkers

### Acceptance

- Existing routes, sidebar order, lifecycle and protected module structure are
  unchanged.
- Every displayed claim has public-safe provenance and freshness.
- The dashboard distinguishes discovered, verified, tested, strategy-relevant
  and tradeable states.
- Telegram cannot create commands, candidates, approvals, orders or proof.

## AR-13 - End-To-End Certification And Controlled Activation

### Objective

Prove that the selective enrichment lane improves Qadam's evidence competency
without creating a new security or authority path.

### Build

- Create one end-to-end certification script and artifact.
- Run positive and negative probes across every phase.
- Compare pre-implementation and post-implementation blocker distributions.
- Activate only official web, RSS, verified YouTube and narrow GitHub channels.
- Keep authenticated social channels disabled.
- Run a 20-market-day forward-observation period with frozen feature recipes.
- Review trade-decision impact after sufficient outcomes mature.

### Artifacts

- `data/runtime/qadam_agent_reach_enrichment_certification.json`
- `data/runtime/qadam_agent_reach_activation_receipt.json`
- `data/runtime/qadam_qualitative_evidence_impact_report.json`

### Checker

- `scripts/check_qadam_agent_reach_enrichment.py`

### Acceptance

Certification passes only when:

1. The pinned dependency and sandbox checks pass.
2. No browser cookie, home-directory or secret access exists.
3. Origin and transport are distinct in every record.
4. Every research-eligible document has provenance, hashes and availability time.
5. Prompt-injection and unsafe-content probes are quarantined.
6. Claims remain grounded in supporting spans.
7. Independence clustering prevents duplicate corroboration.
8. Historical alignment and leakage checks pass.
9. Pattern candidates survive declared baselines and negative controls.
10. Strategy records preserve lineage and do not create orders.
11. Akber receives only evidence appropriate to each stage.
12. Spread, liquidity, risk and execution remain provider-backed and separate.
13. Router and PaperOps remain the only paper-order path.
14. Live capital remains disabled.
15. Dashboard and Telegram remain public-safe, read-only and deduplicated.
16. Resource ceilings and cleanup checks pass.
17. Existing Qadam certification suites remain green.

## 16A. Prediction Market Intelligence V2 Cross-Phase Lane

Prediction Market Intelligence V2 is a cross-phase research lane, not a new
execution path. Its implementation must be included in the relevant AR phase
rather than delivered as a disconnected prediction-market subsystem.

| Phase | Required prediction-market work |
|---|---|
| AR-0 | Inventory current Kalshi, Polymarket, price, contract-lifecycle and settlement artifacts; record provider, source, route and authority truth. |
| AR-1 | Keep venue clients inside the same bounded worker model; prohibit wallet, order-signing and authenticated execution capabilities. |
| AR-2 | Register official venue origins, APIs, retention terms, rate limits and the four-paper research-status registry. |
| AR-3 | Acquire only approved official market, trade, order-book, event, lifecycle and settlement records with cursor and rate-limit receipts. |
| AR-4 | Normalize `qadam_prediction_contract.v1` and `qadam_prediction_belief_state.v1`; preserve revisions, timestamps, transaction classes and hashes. |
| AR-5 | Map contract language to event semantics and use the functional specialist matrix to challenge economic relevance without inventing event equivalence. |
| AR-6 | Build the deterministic contract graph for mutually exclusive, exhaustive, conditional and equivalent outcomes; keep inferred links separate from verified links. |
| AR-7 | Create point-in-time belief, liquidity, logical-residual and mapped-price histories; classify unavailable depth or settlement history honestly. |
| AR-8 | Run Belief Jump Lead-Lag, Cross-Venue Belief Disagreement and Logical Constraint Dislocation against frozen baselines, costs and negative controls. |
| AR-9 | Translate only surviving evidence into the existing Prediction Market Geopolitical Dislocation family, another mechanism-compatible core family, or an emerging strategy proposal. |
| AR-10 | Fill only legitimate Akber Context, Catalyst and Confirmation fields; preserve separate listed-proxy execution and portfolio-risk checks. |
| AR-11 | Schedule contract-graph, belief-state, consistency and outcome-maturation jobs with independent circuits and bounded storage. |
| AR-12 | Explain contract meaning, belief movement, market quality, mapped instrument, test state, blocker and next action on existing dashboard and Telegram surfaces. |
| AR-13 | Certify event identity, transaction decomposition, point-in-time safety, negative controls, strategy translation and the absence of direct prediction-market execution authority. |

### 16A.1 Durable Artifacts

- `data/runtime/qadam_prediction_market_paper_registry.json`
- `data/runtime/qadam_prediction_contracts.jsonl`
- `data/runtime/qadam_prediction_contract_graph.json`
- `data/runtime/qadam_prediction_belief_states.jsonl`
- `data/runtime/qadam_prediction_market_quality.json`
- `data/runtime/qadam_prediction_market_consistency_records.jsonl`
- `data/runtime/qadam_prediction_market_cross_asset_signals.jsonl`
- `data/runtime/qadam_prediction_market_intelligence_summary.json`

Bulk venue history belongs under ignored `data/research/` partitions. Runtime
artifacts must contain only bounded, public-safe summaries and lineage.

### 16A.2 Focused Checks

- `scripts/check_qadam_prediction_contracts.py`
- `scripts/check_qadam_prediction_transaction_decomposition.py`
- `scripts/check_qadam_prediction_contract_graph.py`
- `scripts/check_qadam_prediction_belief_state.py`
- `scripts/check_qadam_prediction_negative_controls.py`
- `scripts/check_qadam_prediction_strategy_bridge.py`

### 16A.3 Lane Acceptance

The lane passes only when:

1. Every compared contract has compatible event, outcome, cutoff, resolution
   and settlement identity.
2. Polymarket exchange turnover, minting, burning and conversion are classified
   separately; naive gross activity is never labelled trading volume.
3. Every LLM-proposed logical edge is accepted or rejected by deterministic
   constraint validation.
4. The withdrawn institutional-liquidity paper contributes no empirical proof,
   parameter, edge or promotion credit.
5. All three initial programmes have frozen mechanisms, instruments, horizons,
   costs, baselines and failure conditions.
6. Any promoted relationship survives untouched holdout, costs, liquidity,
   stability and negative-control tests.
7. The same event on Kalshi and Polymarket cannot inflate source quorum or
   independence.
8. Direct prediction-market execution remains unavailable. Only a compatible,
   separately qualified listed proxy can continue through Strategy Foundry,
   Akber, portfolio risk, Router and guarded Alpaca Paper.

## 16B. All-Lane Authority And Conversion Cross-Phase Workstream

This workstream fixes every current lane without creating parallel decision
pipelines.

| Phase | Required all-lane work |
|---|---|
| AR-0 | Inventory every implemented, partial, planned, disabled and audit-only lane; record its producer, consumers, current authority, maximum intended authority and real conversion blockers. |
| AR-1 | Prove that no lane worker can access broker credentials, risk mutation, order signing or live capital. |
| AR-2 | Add lane owner, provider class, trust, freshness, independence and permitted evidence-role policy. |
| AR-3 | Ensure every evidence-producing lane can refresh its required provider inputs independently and atomically. |
| AR-4 | Extend the existing tradeability-capability and evidence-contract owners with `qadam_lane_capability.v1`, `qadam_lane_contribution.v1` and generated validation/accessor code. |
| AR-5 | Make local and frontier model outputs conform to lane contribution contracts; preserve blinded specialist disagreement. |
| AR-6 | Attach every contribution to the same temporal graph generation, candidate identity and source-independence clusters. |
| AR-7 | Make historical, current and forward-shadow evidence explicitly distinct while sharing stable lineage. |
| AR-8 | Calibrate each lane against its appropriate baseline, costs and negative controls; record which evidence requirements are empirically useful. |
| AR-9 | Extend the existing canonical tradeability pipeline to replace competing hypothesis shapes with one deterministic TradeabilityEnvelope compiler and one canonical Strategy Foundry submission. |
| AR-10 | Route evidence through mechanism-specific Akber profiles and activate the trigger-to-decision fast path for both paper evidence lanes. |
| AR-11 | Schedule lane compilation, current-market refresh, expiry, revalidation, diagnostics and reachability canaries in dependency order. |
| AR-12 | Show each lane's evidence, authority, current funnel state, blocker owner, last evaluation and next action without adding dashboard routes. |
| AR-13 | Run real-producer golden journeys, broker-disabled reachability probes, all-lane negative safety tests and conversion certification. |

### 16B.1 Durable Artifacts

- `config/qadam_lane_capability_registry.json`
- `data/runtime/qadam_lane_authority_inventory.json`
- `data/runtime/qadam_lane_contributions.jsonl`
- `data/runtime/qadam_tradeability_envelopes.jsonl` - existing canonical
  artifact; ownership must remain with `orchestrator.qadam_tradeability_pipeline`
- `data/runtime/qadam_lane_conversion_funnel.json`
- `data/runtime/qadam_lane_blocker_ownership.json`
- `data/runtime/qadam_lane_fast_path_status.json`
- `data/runtime/qadam_lane_reachability_canary.json`
- `data/runtime/qadam_all_lane_conversion_certification.json`

### 16B.2 Focused Checks

- `scripts/check_qadam_lane_capability_registry.py`
- `scripts/check_qadam_lane_contribution_contracts.py`
- `scripts/check_qadam_tradeability_envelope_compiler.py`
- `scripts/check_qadam_lane_generation_integrity.py`
- `scripts/check_qadam_lane_trigger_fast_path.py`
- `scripts/check_qadam_lane_blocker_ownership.py`
- `scripts/check_qadam_lane_golden_journeys.py`
- `scripts/check_qadam_lane_reachability.py`
- `scripts/check_qadam_all_lane_conversion.py`

### 16B.3 Conversion Acceptance

The workstream passes only when:

1. Every lane has one owner, one capability manifest and one maximum authority
   tier.
2. Every productive lane can write a schema-valid contribution using a real
   producer path.
3. One compiler produces one same-generation TradeabilityEnvelope per candidate;
   no parallel hypothesis or Akber truth remains authoritative.
4. No available evidence is reported missing because of field aliases, nesting,
   stale templates or producer-consumer version drift.
5. Every A3 active trigger receives current market, cost, shadow, Akber, risk and
   Router evaluation before expiry when providers are available.
6. Every A4 positive golden journey reaches the broker-disabled PaperOps canary.
7. Every negative, stale, inactive and duplicate golden journey stops at the
   correct deterministic boundary.
8. Both validated-strategy and discovery-micro nominations are supported without
   conflating discovery evidence with validated-edge proof.
9. Multiple distinct qualified setups can be evaluated and submitted on one day
   subject to portfolio, exposure and route controls.
10. No research lane has A5 or A6 authority, no direct broker path exists and
    live capital remains disabled.
11. Zero eligible opportunities are silently dropped. Every non-progression has
    a typed reason, responsible owner, retryability class and next action.
12. The existing canonical PaperOps wrapper consumes the accepted handoff shape
    produced by Router; a passing sidecar or projection alone is insufficient.

## 17. Deferred Authenticated Social Lane

Authenticated Reddit, X, Facebook, Instagram, LinkedIn and regional channels are
not required for initial success.

If a later preregistered hypothesis requires one of these channels, require a
separate implementation and approval package containing:

- documented investment hypothesis and expected incremental value;
- platform terms review;
- dedicated secondary account;
- isolated browser profile or provider token;
- no access to the operator's primary browser profile;
- no source-quorum authority;
- account-ban and credential-compromise response;
- separate security and value certification;
- automatic disablement if it does not add measurable information.

## 18. Measurement Framework

### 18.1 Operational Metrics

- retrieval success by origin and channel;
- event-to-retrieval latency;
- transcript availability and quality;
- duplicate and quarantine rates;
- provenance and timestamp completeness;
- disk and model-call consumption;
- circuit and repair counts;
- lane capability coverage and producer heartbeat freshness;
- lane contribution-to-envelope compilation latency;
- active-trigger fast-path completion and expiry counts;
- broker-disabled reachability-canary state;
- contract-shape, generation-mismatch and ownerless-blocker counts.

### 18.2 Research Metrics

- independent qualitative event count;
- claims mapped to instruments;
- claims with mature forward outcomes;
- directional resolution rate;
- distinct pattern count after deduplication;
- negative-control failure rate;
- patterns surviving holdout and costs;
- incremental value over price-only baselines;
- quantum incremental value over matched classical baselines;
- semantically compatible prediction-market event pairs;
- liquidity-qualified belief jumps with mature mapped-market outcomes;
- logical residuals surviving fees, depth, latency and settlement risk;
- prediction-market signals surviving holdout, costs and stability checks;
- productive lanes reaching their maximum legitimate authority tier;
- A3 triggers receiving complete current-market evaluation;
- positive and negative lane golden journeys passing on real disk artifacts.

### 18.3 Decision Metrics

- Akber Context missingness before and after;
- Akber Catalyst missingness before and after;
- setups held for direction unresolved;
- setups held for execution or risk evidence;
- qualified paper-review candidates;
- accepted, held and vetoed decisions with matured outcomes;
- paper experiments that would not have existed without new qualitative
  evidence;
- net contribution after costs and counterfactual no-order comparison;
- setups where prediction-market evidence legitimately filled Context, Catalyst
  or Confirmation;
- prediction-market-derived proposals rejected for incompatibility, weak
  liquidity, failed holdout or missing paperable expression;
- qualified-opportunity conversion by lane and evidence profile;
- active triggers evaluated before expiry;
- setups held because of genuine missing evidence versus contract-shape defects;
- A4 nominations reaching Router and guarded PaperOps;
- distinct same-day qualified setups submitted without duplicate exposure.

### 18.4 Success Standard

The programme is successful if it creates more independent, timely and
directionally useful evidence; reduces schema-caused holds; and produces
additional qualified paper decisions with complete lineage. It must also prove
that each productive lane reaches its maximum legitimate authority tier and
that every current, complete setup receives a timely governed disposition.

It is not successful merely because:

- more URLs were fetched;
- the source count increased;
- a model produced more summaries;
- research scores increased;
- more Telegram messages were sent;
- a trade was forced;
- one paper position happened to profit.

### 18.5 Controlled Impact Targets

AR-0 must calculate the baseline before these targets are evaluated. The first
impact review occurs after at least 20 market days and 30 independent eligible
qualitative events, whichever happens later.

Lane contract, generation-integrity, golden-journey and broker-disabled
reachability targets are pre-activation requirements and do not wait for the
20-market-day impact review. Empirical edge, outcome and profitability claims
still require real matured evidence.

| Measure | Minimum controlled target |
|---|---|
| Approved scheduled-event acquisition | At least 95 percent retrieved within 60 minutes of transcript or document availability |
| Research-eligible provenance completeness | 100 percent |
| Origin versus transport classification | 100 percent |
| False independence inflation | Zero known cases |
| Logical-document duplicate rate | Below 1 percent after canonicalization |
| Mature label generation | At least 95 percent of eligible due windows, excluding typed provider gaps |
| Context/Catalyst missingness | At least 30 percent lower for setups where approved qualitative evidence is relevant |
| Direction unresolved from missing qualitative context | At least 25 percent lower for the same eligible cohort |
| Unsafe or ungrounded model claim promotion | Zero |
| Negative-control strategy promotion | Zero |
| Direct Agent Reach order or authority actions | Zero |
| Prediction contract identity and settlement completeness | 100 percent for every research-eligible comparison |
| Polymarket transaction classification | 100 percent for every retained on-chain activity record |
| Withdrawn-paper empirical evidence or promotion credit | Zero |
| Unvalidated LLM-proposed contract dependency promotion | Zero |
| Lane capability registry coverage | 100 percent of implemented, partial, planned, disabled and audit-only lanes |
| Productive-lane schema-valid contribution coverage | 100 percent |
| Available evidence reported missing due to field shape or alias drift | Zero |
| Same-generation envelope integrity | 100 percent |
| Eligible active triggers evaluated before expiry | At least 95 percent when required providers are available |
| A4 positive golden journeys reaching broker-disabled PaperOps canary | 100 percent |
| Ownerless or silently dropped eligible opportunities | Zero |
| Research-lane direct broker, risk mutation or proof actions | Zero |

Failure to hit a research target must produce a diagnosis and a proposal. It
must not cause Qadam to lower risk or execution requirements automatically.

## 18A. Proposed Code Ownership Map

The following names are recommended to keep each phase modular. Before creating
one, implementation must confirm that no newer module in the active branch
already owns the same artifact or responsibility.

| Responsibility | Proposed owner |
|---|---|
| Pinned capability and sandbox policy | `orchestrator/qadam_agent_reach_sandbox.py` |
| Origin registry and trust decisions | `orchestrator/qadam_external_origin_registry.py` |
| Zero-auth retrieval and queue | `orchestrator/qadam_external_acquisition.py` |
| Immutable document and provenance storage | `orchestrator/qadam_external_evidence_lake.py` |
| Local structured claim extraction | `orchestrator/qadam_qualitative_claim_extraction.py` |
| Frontier challenge and claim comparison | `orchestrator/qadam_qualitative_claim_challenge.py` |
| Functional specialist challenge matrix | `orchestrator/qadam_functional_specialist_challenge.py` |
| Entity and instrument graph mapping | `orchestrator/qadam_qualitative_evidence_graph.py` |
| Historical alignment and outcome labels | `orchestrator/qadam_qualitative_history.py` |
| Linear, nonlinear and quantum challenger tests | `orchestrator/qadam_qualitative_pattern_lab.py` |
| Prediction contract registry and normalization | `orchestrator/qadam_prediction_market_normalization.py` |
| Prediction contract graph and deterministic constraints | `orchestrator/qadam_prediction_contract_graph.py` |
| Prediction belief, liquidity and cross-asset research | `orchestrator/qadam_prediction_market_research.py` |
| Lane capability and authority registry | Extend existing `orchestrator/qadam_tradeability_capabilities.py` |
| Lane contribution validation and accessors | Extend existing `orchestrator/qadam_evidence_contracts.py` |
| Same-generation TradeabilityEnvelope compiler | Extend existing `orchestrator/qadam_tradeability_pipeline.py` |
| Active-trigger dependency fast path | `orchestrator/qadam_lane_trigger_fast_path.py` |
| Lane conversion funnel and blocker ownership | `orchestrator/qadam_lane_conversion.py` |
| Disk-backed golden journeys and reachability canary | `orchestrator/qadam_lane_reachability.py` |
| Pattern Score and Strategy Foundry translation | `orchestrator/qadam_qualitative_strategy_bridge.py` |
| Akber evidence-role translation | `orchestrator/qadam_qualitative_akber_bridge.py` |
| Scheduling, circuits and resource limits | `orchestrator/qadam_agent_reach_operator.py` |
| Public-safe dashboard and communication summary | `orchestrator/qadam_qualitative_visibility.py` |
| End-to-end certification | `orchestrator/qadam_agent_reach_certification.py` |
| All-lane authority and conversion certification | `orchestrator/qadam_all_lane_conversion_certification.py` |

Every module needs a corresponding focused test file under `tests/`. Existing
canonical producers remain owners of Pattern Score, Strategy Foundry, Akber,
Router, risk, PaperOps and dashboard aggregate artifacts; bridge modules submit
typed inputs to them rather than writing competing canonical outputs.

## 19. Release And Rollback

### Release Sequence

1. Merge security, lane capability, contribution and TradeabilityEnvelope
   contracts with all new channels and Router eligibility disabled.
2. Run every lane's positive, missing, adverse, stale, inactive and duplicate
   disk-backed golden journey.
3. Prove the broker-disabled reachability canary for both paper evidence lanes.
4. Enable one official RSS origin in shadow mode.
5. Enable one verified earnings-call origin.
6. Verify evidence, graph, feature and dashboard lineage.
7. Run historical and forward tests without Router eligibility.
8. Enable Pattern Recognition and the single canonical Strategy Foundry bridge.
9. Enable mechanism-specific Akber evidence-fit profiles for shadow decisions.
10. Enable the active-trigger fast path with Router and PaperOps still blocked.
11. Enable Prediction Market Intelligence V2 in read-only research mode only
   after its contract, graph and transaction-decomposition checks pass.
12. Enable bounded discovery-micro and validated-strategy PaperOps nominations
    only after all-lane conversion certification.
13. Expand issuer, origin and compatible-contract coverage gradually.

Direct Kalshi or Polymarket execution is not part of this release sequence.

### Rollback Triggers

- secret or local-path exposure;
- browser-session access;
- origin misclassification;
- duplicate-source quorum inflation;
- point-in-time leakage;
- prompt-injection escape;
- uncontrolled disk growth;
- unreviewed dependency change;
- dashboard authority drift;
- order lineage missing Agent Reach-derived evidence ancestry;
- any direct broker or live-capital path.

Rollback disables the enrichment lane and preserves the evidence ledger for
audit. It must not interrupt market-price monitoring, portfolio reconciliation
or guarded PaperOps lifecycle management.

## 20. Final Definition Of Done

The full implementation is complete only when:

1. Qadam runs a pinned, sandboxed, zero-auth qualitative retrieval worker.
2. The worker cannot access Qadam secrets, browser sessions or broker systems.
3. Official earnings calls, briefings, RSS and selected public releases are
   retrieved with origin-aware provenance.
4. Agent Reach remains a transport capability and does not inflate source
   counts or quorum.
5. Structured claims preserve supporting spans, speaker, time and uncertainty.
6. The temporal graph connects claims to entities, strategies, instruments and
   outcomes without confusing inferred edges with facts.
7. Historical and forward features are point-in-time safe and disk-bounded.
8. The priority pattern programmes have preregistered tests, baselines and
   negative controls.
9. Pattern Recognition can rank resulting relationships and explain their next
   stage.
10. Strategy Foundry can refine a core family or create an emerging strategy
    with complete lineage.
11. Akber can consume qualified Context and Catalyst evidence without demanding
    fields that the source cannot legitimately provide.
12. Current market, execution and portfolio-risk checks remain independent and
    mandatory.
13. Qualified bounded setups can reach the existing guarded Alpaca Paper route
    without manual schema repair.
14. Dashboard and Telegram communicate material evidence changes clearly while
    retaining the existing UX and authority boundaries.
15. The operator service survives restart, network failure and disk pressure.
16. The end-to-end certification passes with live capital disabled.
17. The measured result is more qualified decision opportunities, not merely
    more data or forced paper orders.
18. Prediction-market evidence is contract-compatible, liquidity-aware,
    point-in-time safe and translated through the existing strategy lifecycle.
19. Functional specialist disagreement is preserved as a challenge record and
    never misreported as independent source corroboration.
20. Every lane has one owner, capability manifest, authority tier, evidence-role
    contract and typed downstream destination.
21. One same-generation TradeabilityEnvelope compiler replaces competing
    producer and Akber shapes.
22. Every eligible active trigger receives current market, expectancy, shadow,
    Akber, risk and Router evaluation before expiry when providers are available.
23. Both paper evidence lanes pass real-producer golden journeys and the
    broker-disabled PaperOps reachability canary.
24. No setup is held because usable evidence exists under an incompatible alias,
    nesting shape, stale template or parallel artifact.
25. Multiple distinct qualified setups may proceed on one day, but no trade
    quota, research component or model can bypass portfolio or execution safety.

## 21. Recommended Implementation Order

The recommended modular sequence is:

```text
AR-0 Baseline and source-count truth
-> AR-1 Sandbox and supply chain
-> AR-2 Origin and trust policy
-> AR-3 Zero-auth acquisition
-> AR-4 Provenance and security
-> AR-5 Structured claims
-> AR-6 Temporal graph
-> AR-7 Historical and forward labels
-> AR-8 Pattern and challenger tests
-> AR-9 Strategy bridge
-> AR-10 Akber evidence fit
-> AR-11 Autonomous operations
-> AR-12 Dashboard and Telegram
-> AR-13 Certification and controlled activation
```

The Prediction Market Intelligence V2 and All-Lane Authority And Conversion
workstreams are implemented inside every applicable AR phase according to
Sections 16A and 16B. They are not postponed until after AR-13 and must not
create sidecar decision pipelines.

The highest-value first usable milestone is AR-5: Qadam can reliably capture and
challenge official management claims. The first milestone that can influence
paper-decision frequency is AR-10, after lane contracts, real-producer golden
journeys, historical or bounded discovery-micro evidence, and the separate
market, execution and risk systems are fresh. Full activation additionally
requires the all-lane conversion certification and PaperOps reachability canary.
