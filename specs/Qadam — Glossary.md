# Qadam — Glossary

<aside>
📖

Every vocabulary term used in the [Qadam Specifications v3](../Qadam%20Specifications%20v3%203566fe2ecf37800abef8c5c717cc6656.md) — alphabetically ordered, with a plain-language definition, the *if X → Y* shorthand where applicable, and the section where the full spec lives.

</aside>

---

# A

**Architect Agent** *(The System Watcher)*

*Plain language:* The system's immune system coordinator. A lightweight, always-on monitoring process that watches for model drift, data degradation, performance decay, and regime shifts. It can trigger bounded autonomous actions (like feed failover) but cannot change the Manifested Strategy or lift kill-switches on its own — those require Ramin's approval.

*If X → Y:* If Entropy Level exceeds the critical threshold → Global Kill-Switch fires automatically AND Crisis Manifestation is queued for Ramin review.

`→ §8.1`

**Attention Ceiling**

*Plain language:* The maximum number of concurrent data streams Gemma 4 can triage before its classification accuracy starts to drift. Measured during Gemma's self-audit. If Neural Engine load exceeds 90%, the Architect Agent throttles stream count to stay below this ceiling.

`→ §5.1`

**Alignment Score**

*Plain language:* The gap between what Qadam predicted would happen (the true probability estimate) and what actually happened. Tracked per catalyst class. A widening Alignment Score means the probability engine is drifting from reality — which triggers a Reflective Manifestation.

`→ §9.2.3`

---

# B

**Bayesian Weight Updating** *(Success Attribution Score)*

*Plain language:* After every closed trade, each contributing component (Gemma, Gemini, Quantum, Regime Engine, Volume Agent) receives a fractional credit score based on whether its output contributed to the correct outcome. The Orchestrator applies these scores to shift component weights — making the system trust more heavily whichever component has been most accurate for each catalyst type.

*If X → Y:* No single trade moves any weight by more than the configured maximum delta — the system cannot be whipsawed by one lucky or unlucky outcome.

`→ §8.3.2`

**The Biological Model** *(Autonomous Resilience)*

*Plain language:* The self-healing design philosophy: a living system doesn't shut down when one organ fails — it reroutes, compensates, and signals for repair. In Qadam, this means automatic data-source failover, Cognitive Conflict resolution, and Circuit Breaker triggers, all without waiting for Ramin.

`→ §8.2`

**Black-Scholes Gap** *(BS Gap)*

*Plain language:* The mathematical difference between what the options market implies is going to happen (the implied probability distribution extracted from the options chain via Black-Scholes) and what Qadam estimates is actually going to happen (the true probability distribution from Gemini + Quantum). This gap is the trade. The wider the gap, the better the expected value of the recommended option structure.

*If X → Y:* If `bs_gap.tail_mass_diff` ≥ 15 percentage points → the signal passes Layer 2 of the 6-Step Filter.

`→ §4.3, §6.3`

---

# C

**Catalyst-Correct Rate**

*Plain language:* The percentage of closed trades where the underlying catalyst actually played out as Qadam predicted — regardless of whether the trade made money. A correct catalyst with a losing trade = execution problem. An incorrect catalyst with a winning trade = lucky. Tracked separately from P&L.

`→ §9.2.1`

**Circuit Breaker** *(The Sanity Gate)*

*Plain language:* A hard stop that fires when the system detects it is making systematic errors. Examples: 3 consecutive False Positive catalysts trigger a Strategy Kill-Switch; portfolio drawdown crossing 20% triggers the Global Kill-Switch. The system pauses before any more capital is risked.

`→ §8.2.3`

**Cognitive Conflict**

*Plain language:* When Gemma 4 (triage) and Gemini 3.1 Pro (research) produce conflicting sentiment classifications on the same instrument — e.g. Gemma says Bullish, Gemini says Bearish — by more than 30%. The instrument is flagged `conflict-pending` and no new signals are proposed on it until the Quantum Engine adjudicates at the next weekly batch.

`→ §4.1, §8.2.1`

**Cognitive Drift Rate**

*Plain language:* The rolling 30-day percentage of signals where Gemma and Gemini disagreed. A system health indicator. If it exceeds 40%, the Architect Agent triggers a Reflective Manifestation and suspends `high_conviction` tier signals until the audit is complete.

`→ §9.2.3`

**Cognitive Heatmap**

*Plain language:* Gemini 3.1 Pro's self-assessment of where its reasoning is strong vs. weak — a confidence matrix across 12 geopolitical regions and 8 sector categories. Used by the Architect Agent to weight Gemini's outputs by domain. A signal from a low-confidence domain requires a higher evidence bar before queuing for Quantum.

`→ §4.2, §5.1`

**The Cockpit** *(Web Cockpit)*

*Plain language:* The single-operator control surface. A Next.js web app (single-tenant, one user) where Ramin reviews signals, monitors positions, operates kill-switches, and reads postmortems. Read-heavy, control-light. Contains 8 pages: Dashboard, Signal Review, Trade Journal, Strategies, Postmortems, Intelligence Feed, System Health, Settings.

`→ §11`

**The Conjuring Phase** *(Phase 1)*

*Plain language:* The pre-trading audit phase. Before a single dollar is risked, the system audits its own cognitive architecture, hardware constraints, and data environment, then uses those findings to generate the Manifested Strategy. Named for the idea that the strategy is not hard-coded by Ramin — it emerges from the system's honest self-assessment.

`→ §5`

**Crisis Manifestation**

*Plain language:* An emergency full re-run of Phase 1, triggered by the Architect Agent when the Entropy Level exceeds the critical threshold. Ramin must approve it before it runs. The system stops proposing new signals during a Crisis Manifestation.

`→ §5.4`

**Cross-Dataset Pattern Cluster** *(Quantum-Confirmed Pattern)*

*Plain language:* A statistically significant co-occurrence of signals across two or more of the five data pipelines — e.g. a thermal anomaly in a port region + unusual options flow on a shipping stock + a politician trade — that classical correlation matrices miss. Identified by the Quantum Engine's weekly Job 1. Elevated to a Quantum-Confirmed Pattern when confidence > 0.7 and ≥ 3 historical precedents exist in the Knowledge Graph.

`→ §4.3`

---

# E

**The Energy of Instability** *(Geopolitical & Conflict Pipeline)*

*Plain language:* The vocabulary name for Pipeline A — the conflict and geopolitical data feeds (ACLED, UCDP, GDELT, Oref). Called this because armed conflict, political violence, and regional instability are forms of energy that eventually manifest as market price moves.

`→ §3.2`

**Entropy Level**

*Plain language:* The Architect Agent's composite health metric for the entire system. Combines: Gemma/Gemini Cognitive Conflict rate, data feed degradation count, strategy drawdown proximity to caps, and regime transition frequency. High entropy = the system is under stress. If it crosses the critical threshold, the Global Kill-Switch fires automatically.

`→ §8.1`

**Epistemic Accretion**

*Plain language:* The compounding of knowledge (alpha) over time, not just capital. Every resolved catalyst — whether it was traded or not — is stored permanently in the Knowledge Graph with its full context and outcome. Over months and years, Qadam doesn't just reason from first principles; it recognises patterns it has seen before and adjusts probability priors accordingly. The Knowledge Graph is never purged.

*If X → Y:* If the Knowledge Graph contains ≥ 20 prior instances of catalyst cluster X resolving in direction Y with > 80% frequency → the Risk Agent is authorised to increase position sizing up to the per-trade cap for that cluster.

`→ §1.5, §8.4`

**The Execution Rail** *(Layer B — Orchestration Layer)*

*Plain language:* Layer B of the two-layer architecture. The autonomous system that receives signals from Layer A only after the Approval Policy Router assigns a valid approval state, sizes positions using Kelly Criterion, places orders through broker adapters, monitors open positions, and closes them when exit rules trigger. In test mode, qualifying signals auto-approve so the proof remains clean; in live mode, Ramin approves signals only when the configured policy requires it. Ramin's standing role is strategy approval, approval-policy configuration, kill-switch control, and outcome review — not emotional management of individual trades.

`→ §7`

---

# G

**The Gatekeeper** *(Risk Agent)*

*Plain language:* The deterministic code layer that sits between every approved signal and the broker. Every order must pass a 7-point pre-trade gate checklist. Hard position-size caps are enforced. The Risk Agent cannot be bypassed by any other component.

`→ §7.3`

---

# H

**High-Correlation Cluster**

*Plain language:* A catalyst type that has accumulated ≥ 20 resolved instances in the Knowledge Graph with > 80% resolution in the thesis direction. When a catalyst achieves this status, the Risk Agent is authorised to increase per-trade sizing up to the hard cap for signals of that type (the Kelly fraction ceiling is raised, not the hard cap itself).

*If X → Y:* If the cluster's win rate decays below 70% over the following 20 trades → the cluster is demoted; sizing returns to standard Kelly.

`→ §8.4.2`

---

# I

**The Ingress** *(World Monitor Data Pipelines)*

*Plain language:* The sensory layer of Qadam. Five specialised pipelines (Conflict, Physical/OSINT, Economic/Macro, Market Microstructure, Social/Narrative) stream raw data from 35 sources into the Python Orchestrator, which normalises everything into a unified event schema before any model touches it.

`→ §3`

---

# J

**Joint Cognitive Profile**

*Plain language:* The structured output of the Triple-Mirror Audit. A document that records each component's processing strengths, hardware constraints, confidence boundaries, and recommended domain weightings. Used by the Architect Agent and the Orchestrator to weight each component's outputs going forward.

`→ §5.1`

---

# K

**Knowledge Graph**

*Plain language:* The permanent vector database (ChromaDB) that stores every resolved catalyst Qadam has ever detected — with full context (physical signals, market signals, swarm output, regime state, actual outcome, lead time). It is never purged. Gemini queries it before every swarm simulation; the Quantum Engine reads it during weekly Pattern Recognition. It is Qadam's most irreplaceable long-term asset.

`→ §8.4.1`

---

# L

**Layer A — Intelligence Engine**

*Plain language:* The cognitive and mathematical stack. Ingests alternative data, reasons over it, runs quantum pattern recognition, and surfaces high-conviction signals with full evidence trails. It never places a trade. It figures out what to trade and why.

`→ §1.1, §2`

**Layer B — Orchestration Layer**

*Plain language:* The autonomous execution stack. Receives signals from Layer A only after the Approval Policy Router assigns a valid approval state, executes trades within hard risk guardrails, manages positions, and runs the 90-day demo proof. In test mode, Qadam auto-approves qualifying signals and Ramin observes/holds kill-switches; in live mode, Ramin approves signals only when the configured approval policy requires it.

`→ §1.1, §7`

---

# M

**The Manifested Strategy** *(Manifested Strategy Document)*

*Plain language:* The concrete, human-readable trading ruleset that the system generates for itself at the end of Phase 1, based on its own audit of what it can actually do and which data it can actually trust. Not hard-coded by Ramin — it emerges from the RBI methodology. Ramin must approve it in writing before Phase 2 starts.

`→ §5.3`

**Mathematical Veracity Baseline**

*Plain language:* The Quantum Engine's self-assessment of what its current hardware allocation can reliably do vs. what should fall back to classical. Established during the Quantum Engine's self-audit in Phase 1. Defines the Q_threshold and the recommended circuit complexity limits.

`→ §5.1`

---

# N

**The Nervous System** *(Python Orchestrator)*

*Plain language:* The connective tissue of the entire system. Has no intelligence of its own — coordinates all inter-component calls, enforces Trust Score throttles, manages the Event Log, schedules the Quantum batch job, and applies Bayesian weight updates. Deliberately "dumb": it follows rules, it does not reason.

`→ §4.4`

**The Noise Gate** *(Gemma 4 — Triage)*

*Plain language:* The first line of cognitive defence. Gemma 4 runs 24/7 on the M5 Neural Engine, monitoring all high-velocity feeds. Its job is binary: pass an anomaly up the stack to Gemini, or discard it. It does not reason; it triages.

`→ §4.1`

---

# O

**The Oracle** *(Quantum Engine)*

*Plain language:* The weekly batch mathematical engine. Does not reason in language. Accesses IBM Quantum or Q-CTRL cloud processors once per week to run two jobs: (1) Pattern Recognition — identifying non-linear cross-dataset correlations classical models miss; (2) Strategy Collapse — finding the optimal option structure where the Black-Scholes model is most mispriced.

`→ §4.3`

**The Ouroboros** *(Recursive Intelligence Loop)*

*Plain language:* The snake eating its own tail. The system's outputs become its inputs. Every trade, failure, and data anomaly feeds back through the Postmortem Agent → Bayesian weight updates → Knowledge Graph → improved future signals. The loop never closes; it only tightens.

`→ §8`

---

# P

**The Paper Reality** *(Market Microstructure Pipeline)*

*Plain language:* The vocabulary name for Pipeline D — market microstructure and order flow data (UnusualWhales, Polymarket/Kalshi, Hyperliquid, Alpaca, Coinglass, Bookmap). Called this because options flow and prediction market odds reflect where institutional capital is positioning itself — the "paper" reality that often leads the physical reality.

`→ §3.2`

**Perceptual Audit** *(Data Veracity & Environment Mapping)*

*Plain language:* The second half of Phase 1. The system stress-tests all 35 data sources by running historical data through the pipeline and asking: did these signals actually precede market moves? Results populate the initial Trust Score matrix and produce the `data_environment_map.json` that Ramin reviews before approving Phase 2.

`→ §5.2`

**Postmortem Loop** *(Recursive Feedback)*

*Plain language:* The mechanism for converting closed-trade outcomes into system improvements. Every closed trade (win or loss) runs five parallel postmortem sub-agents (Catalyst, Pricing, Regime, Execution, Override). A reducer combines their outputs into a Postmortem Packet. The Packet drives Bayesian weight updates and Knowledge Graph entries.

`→ §8.3`

---

# Q

**Quantum Ambiguity Score** *(QAS)*

*Plain language:* The Quantum Engine's measure of uncertainty about a Strategy Collapse result. Formally: the standard deviation of expected value across measurement shots divided by the mean. A high QAS means the hardware is uncertain — the system's response is to hold the signal rather than fire it ("compound patience instead of capital"). Must be below Q_threshold for a signal to fire.

*Formal definition:* `QAS = σ(EV_shots) / μ(EV_shots)`

`→ §4.3`

**Quantum-Confirmed Pattern** — *see Cross-Dataset Pattern Cluster*

---

# R

**RBI Methodology** *(Read → Backtest → Implement)*

*Plain language:* The three-step process for generating the Manifested Strategy. (1) Read: Gemini reviews the Joint Cognitive Profile, Data Environment Map, and Knowledge Graph to generate candidate strategy hypotheses. (2) Backtest: the Orchestrator tests each hypothesis against historical data. (3) Implement: the top-performing hypothesis (by Expectancy, not win rate) is written as the Manifested Strategy Document.

`→ §5.3`

**The Reflector** *(Postmortem Agent)*

*Plain language:* The agent that analyses every closed trade, running five parallel sub-agents (Catalyst, Pricing, Regime, Execution, Override Analysis), then producing a structured Postmortem Packet. No closed trade is exempt — wins are analysed as rigorously as losses.

`→ §8.3.1`

**Reflective Manifestation**

*Plain language:* A scaled-down Phase 1 that runs every 30 days while the system is live. Asks: "Has the market regime shifted enough that the Manifested Strategy needs updating?" If yes, the Architect Agent proposes an update — it does not self-apply it. Ramin approves before any strategy change goes live.

*If X → Y:* If regime transition lasts > 10 trading days OR Architect Agent's Entropy Level exceeds threshold E → Reflective Manifestation is triggered early.

`→ §5.4`

**Regime Engine** *(Markov Regime Engine)*

*Plain language:* The always-on market state classifier. Classifies the market into one of four structural regimes: `calm_trend`, `volatile_trend`, `chop`, `risk_off`. Every agent in the pipeline reads the current regime. In `risk_off`, all non-defensive signal types are blocked. Transitions require a minimum persistence window to prevent whipsawing.

`→ §6.4`

---

# S

**The Sanity Gate** — *see Circuit Breaker*

**Shadow Strategy**

*Plain language:* A background instance of the Manifested Strategy running with slight parameter variations, testing whether a different configuration would have performed better. Runs on historical data and paper fills — never on live capital. If the shadow variant outperforms the live strategy on Expectancy over a rolling 30-day window, the Architect Agent proposes a strategy update. Ramin approves before any change goes live.

`→ §8.3.3`

**The Source of Truth** *(Physical & Logistics Pipeline)*

*Plain language:* The vocabulary name for Pipeline B — physical and logistics data (NASA FIRMS, Wingbits ADS-B, AIS Maritime, ArcGIS, Space-Track, GPS Jamming monitors, Internet Outage maps). Called this because satellite thermal anomalies, vessel diversions, and air traffic patterns reflect physical reality — often hours or days before the news narrative forms.

`→ §3.2`

**The Spine** *(Event Log)*

*Plain language:* The append-only PostgreSQL + TimescaleDB log of every event in the system: every signal state transition, every fill, every override, every kill-switch fire, every Bayesian weight change. It is the single source of truth. Any system state can be reconstructed from it. Nothing is ever deleted.

`→ §2.2`

**Strategy Collapse** *(Quantum Job 2)*

*Plain language:* The Quantum Engine's weekly optimisation job. Given a candidate catalyst packet (Gemini's true probability distribution + the options chain's implied distribution + the Manifested Strategy rules), it finds the specific option structure — strike, expiry, type — where the Black-Scholes model is most mispriced relative to Qadam's estimate. Output is the Black-Scholes Gap Report + Quantum Ambiguity Score.

`→ §4.3`

**The Strategist** *(Gemini 3.1 Pro — Swarm Engine)*

*Plain language:* Qadam's deep-reasoning layer. Where Gemma filters, Gemini understands. Runs geopolitical reasoning, constructs Catalyst Evidence Trails, and runs MiroFish-style Swarm Intelligence Simulations (100+ synthetic agent personas) to estimate probability distributions over outcomes.

`→ §4.2`

**Success Attribution Score** — *see Bayesian Weight Updating*

**Swarm Intelligence Simulation** *(MiroFish-style)*

*Plain language:* Gemini spins up 100+ synthetic agent personas (Logistics Experts, Regional Diplomats, Hedge Fund Managers, Retail Traders, Central Bankers) and has each reason independently about a flagged catalyst's likely market impact. The distribution of their responses — not a consensus — is the output. High dissent (> 60%) means the signal is downgraded to `watchlist`.

`→ §4.2`

**Synthetic Data Generation**

*Plain language:* Using winning trades to teach the triage layer to recognise the same patterns faster in future. After a strong positive outcome, Gemini analyses the triage signal and generates variations of that pattern (at different noise levels, in different geopolitical contexts) as training examples. Used to fine-tune Gemma 4 via MLX/LoRA — but only after Ramin approves, only offline, and only after validation accuracy is confirmed.

`→ §8.4.3`

**The System Watcher** — *see Architect Agent*

---

# T

**The Triage** — *see Noise Gate (Gemma 4)*

**Triple-Mirror Audit**

*Plain language:* The first half of Phase 1. Each of the three cognitive components (Gemma, Gemini, Quantum Engine) evaluates its own processing style, hardware constraints, and confidence boundaries. Outputs are `gemma_profile.json`, `gemini_profile.json`, and `quantum_profile.json`. If any component fails its accuracy floor, Phase 1 does not proceed.

`→ §5.1`

**Trust Score**

*Plain language:* A dynamic per-source credibility rating from 0.0 (ignored) to 1.0 (full weight). Calculated by backtesting: how often did a signal from this source precede an actual market move within the expected catalyst window? Updated monthly. Sources below 0.3 are quarantined from the triage layer.

*If X → Y:* Trust Score < 0.3 → source output quarantined. Stays below 0.3 for 60 days → flagged for Ramin review.

`→ §3.3`

---

# W

**World Monitor**

*Plain language:* The collective name for all five data pipelines and their 35 sources. The "senses" through which Qadam observes the physical world, financial world, and narrative world simultaneously. Each pipeline is wrapped behind a FastMCP tool interface.

`→ §3`