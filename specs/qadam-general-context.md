# Qadam

<aside>
🎯

**Qadam** is a trading recommendations platform to be built using a generative AI coder. The goal is not to capture 100x returns — it's to **capture margin** through high-conviction, catalyst-driven opportunities surfaced logically by AI.

</aside>

<aside>
🌓

**Updated product framing:** Qadam is a **dual-layer system** — autonomous underneath, transparent and advisory on top.

- **Autonomous engine:** Qadam monitors the world, detects catalysts, models probability gaps, paper/live trades under strict guardrails, logs every decision, and learns through postmortems.
- **Internal intelligence platform:** Ramin and a close circle can log into [**qadam.trade**](http://qadam.trade) to see what Qadam is watching, what recommendations it is producing, why those recommendations exist, what evidence supports them, and how the autonomous engine would act.
- **Responsibility boundary:** Qadam does not need to begin as a broker-connected autopilot for users. The responsible v1 is: *watch the autonomous system, understand its reasoning, and decide for yourself whether to trade.*
</aside>

# 0. At a Glance

<aside>
📍

**Build status:** Pre-build — Research & architecture phase

**Owner:** Ramin Hoodeh — built and operated by Ramin; trading thesis and philosophy sourced from Akber Ali / DELTAROYALE

**Core bet:** AI can surface high-conviction, catalyst-driven opportunities beyond what any manual process can find alone — systematically, at scale, and with explainable evidence

**What this doc is:** A living blueprint for building Qadam using a generative AI coder. Vision, philosophy, architecture, data strategy, and build resources — all in one place.

</aside>

<aside>
🚫

**What Qadam is NOT**

- Not a low-latency, speed-based HFT system — that's an entirely different game with different infrastructure
- Not a copy-trading app — wallet, politician, or insider-style trades are **signals / conviction multipliers**, not instructions to blindly mirror
- Not a general stock screener — the edge is *catalyst detection before consensus*, not filtering on standard metrics
- Not a financial advisor — Akber is aware of the grey area; this is intelligence infrastructure, not formal recommendations
- Not built around lagging indicators (earnings reports, jobs data) — Qadam uses leading signals
- Not a black-box bot — every signal must be explainable: catalyst source, evidence trail, probability estimate, pricing gap, invalidation condition, and risk. If Qadam cannot explain a trade, it should not make it.
- Not a frequency machine — the weekly proof cadence exists to prove the system, not to generate volume. Rare high-conviction opportunities are the actual goal.
</aside>

<aside>
🏆

**North Star:** Qadam proves itself at a steady **2 autonomous proof trades per week** in its test account, so performance is trackable without forcing overtrading. That proof cadence does **not** replace rare high-conviction opportunities — it creates the evidence base that lets Qadam recognise them when they appear.

- **Weekly proof cadence:** 2 autonomous test-account trades per week, fully logged with thesis, evidence, risk, entry, exit, and postmortem.
- **Rare high-conviction cadence:** 4–6 exceptional catalyst-driven opportunities per year, each with a probability estimate, catalyst evidence trail, options pricing gap analysis, and clear invalidation logic.
- **Internal product success:** Ramin and a close circle can log into [qadam.trade](http://qadam.trade), understand what Qadam would do and why, and make their own trading decision with better context than they had before.
</aside>

<aside>
⚙️

**Autonomy, approval, and risk policy**

- **Scope for now:** Qadam is an internal tool for Ramin and a close circle — not a public community product.
- **Test account:** Qadam trades autonomously with no human approval. Ramin may observe signal cards and operate kill-switches, but he does not approve, reject, defer, modify, close, or adjust individual proof trades; the point is to prove whether the system can act under its own rules.
- **Live account:** Human approval is configurable. A live deployment can run with approval **on**, **off**, or conditional by variables such as position size, conviction tier, instrument, drawdown state, or whether the trade exceeds a predefined threshold.
- **Risk cap principle:** Standard defined-risk options trades are capped at **2%** of bankroll; only rare high-conviction / high-correlation setups can expand toward a **5% absolute maximum**. Prediction-market trades stay capped at **1%**.
- **Human-in-the-loop channel:** Telegram is the primary action channel. Email is only a delivery-failure fallback if Telegram cannot send after retries.
- **Quantum role:** The Quantum Oracle is queried at least once per week and is reserved mainly for rare high-conviction candidates, ambiguity checks, and non-linear pattern discovery. It is a probabilistic conviction layer — not a real-time trading brain and not a standalone reason to trade.
</aside>

---

# 1. Project Vision

Money doesn't always equal value. Some people get rich by creating, building, and solving problems. Others get rich by timing, access, and betting on collapse or rise. **Qadam is built for the second category — but with a systematic, AI-powered edge.**

- The strategy is **dynamic and asset-class agnostic** — identifying companies that will *benefit* from something else (e.g. a company winning a government contract)
- **Not** a low-latency, speed-based system — that's a different game entirely
- Akber's original approach commits capital **2–3 times a year** — only the truly highest-conviction opportunities. The question is whether Qadam can surface more of these opportunities systematically, without lowering the conviction bar
- Qadam has two cadences: a steady **2 proof trades per week** in the autonomous test account, and rarer **high-conviction opportunities** when the catalyst, mispricing, evidence trail, and risk/reward all line up. The weekly cadence proves the machine; the rare cadence preserves judgment.

<aside>
💎

**The Rare Edge Doctrine — quality beats frequency, always.**

Genuine edge is rare. Most markets are efficient most of the time. Qadam's target window is narrow: the gap between what the physical world has already signalled and what the options market has not yet priced in.

- Never trade to fill a calendar. If there is no genuine catalyst with a verified mispricing, the right trade is no trade.
- The 2-proof-trades-per-week cadence is a discipline mechanism — it creates a consistent sample for review, not a quota to hit regardless of quality.
- Rare high-conviction signals (4–6 per year) represent the system at its best. Forcing trades degrades the signal record and corrupts the Knowledge Graph.
- **Process beats prediction. Edge beats excitement. Quality of thesis beats quantity of trades.**
</aside>

- TradingView's strong buy/sell signals and analyst views are a **reference point, not the edge**
- Getting into formal recommendations is a **grey area** — if someone acts on advice and it fails, there could be liability. Akber is aware of this
- Getting into formal recommendations is a **grey area** — especially for a public product. For now, Qadam should be treated as internal intelligence infrastructure for Ramin and a close circle, not a mass-market advisory community.

---

# 2. The Trading Philosophy Behind Qadam

*Akber Ali is the source of the trading thesis and philosophy that Qadam is built on. Ramin Hoodeh builds, operates, and owns the system. The framework below is Akber's intellectual contribution — the "why" behind every signal type, filter, and operating principle in the spec.*

**Akber Ali** — Founder & CEO of **DELTAROYALE**

> *DELTAROYALE gives investors access to intelligence once reserved for institutions. We use catalyst detection and probability modelling to reveal market moves before they become consensus, turning uncertainty into calculated opportunities.*
> 

Akber wants to prove himself wrong that this doesn't work — but if it does, there's a clear case for making real money. The immediate version of Qadam is not a public community marketplace; it is an internal intelligence and autonomy system for Ramin / Akber and a close circle. Any future market-making, community, or public recommendation layer should be treated as a separate, later product surface with its own legal and risk constraints.

---

# 3. Core Trading Philosophy

## Akber's 6-Step Filter for a Trade

*Akber's original framework — with notes on how Qadam operationalises each step.*

1. **Low volatility** — suggests above-average probability of *future* volatility
    
    *→ Qadam scan layer: screen for historically suppressed implied volatility (IV) relative to a ticker's own baseline and sector peers. Flag when IV percentile is below the 20th percentile while a known catalyst window is approaching — this is the entry queue.*
    
2. **Options distribution check** — do the options show a normal distribution in the presence of a bi-modal event? If so, options are mispriced
    
    *→ Qadam pricing layer: compare the options chain's implied probability distribution against Qadam's estimated true probability. A near-normal distribution ahead of a binary event (FDA ruling, contract announcement, geopolitical flashpoint) signals mispricing — this is where the edge lives. Black-Scholes is the benchmark; the gap is the trade.*
    
3. **Catalyst identification** — is there a catalyst that will break the normal distribution?
    
    *→ Qadam signal layer: the core function. Cross-reference news feeds, OSINT data (satellite, AIS, GPS anomalies), Telegram/Reddit/X sentiment, SEC filings, and earnings calendars to surface catalysts before they reach consensus. If MiroFish-style swarm simulation agrees the catalyst is real and not yet priced, confidence increases.*
    
4. **Technical setups**
    
    *→ Qadam confirmation layer: once a catalyst + mispriced options combo is identified, run Citadel-style technical checks — trend direction (daily/weekly), key support/resistance, MA crossovers, RSI, MACD, Fibonacci levels — to find optimal entry zones and risk-to-reward ratios. This is the gating step before a signal fires.*
    
5. **On-balance volume**
    
    *→ Qadam volume intelligence: OBV is used to confirm whether smart money is already accumulating before a move. Unusual OBV divergence (price flat, volume rising) is a secondary confirmation signal layered on top of the catalyst thesis.*
    
6. **Gut**
    
    *→ Akber's final judgment remains part of the philosophy, but Qadam operationalises it carefully. In the test account, gut does not approve or block individual proof trades after Layers 1–5 pass; the system must prove itself cleanly. In live or advisory mode, gut belongs at strategy approval, approval-policy configuration, and human review when the configured policy requires it. The platform's job is to make that judgment evidence-rich rather than impulsive.*
    

## Options & Market-Making Angle

- The **Black-Scholes probability model** prices options based on the likelihood of events. All institutional investment managers use this
- Akber wants to **price options as a market maker** — but also supply them to community members who believe in a company's upside
- In a frenzy market, when a stock spikes, people rush to buy options. The play is to be on **both sides** — buyer and seller

---

# 4. Alternative Data by Trading Philosophy

Different trading philosophies leverage **alternative data** (non-traditional sources like satellite imagery or social sentiment) to find **alpha** — the edge that allows outperformance.

| **Trading Philosophy** | **Key Data Sources** | **Strategic Benefit** |
| --- | --- | --- |
| **Global Macro** | GDELT, ACLED, BIS/WTO Indicators | Anticipate shifts in national economies, interest rates, or currency values by monitoring civil unrest and diplomatic sentiment before they hit mainstream headlines. |
| **Event-Driven** | NASA FIRMS, Telegram, RSS Feeds | Capitalise on corporate or geopolitical shocks (e.g. a refinery explosion or sudden border closure) with visual/ground-level proof minutes before a press release. |
| **Commodity / Supply Chain** | AIS (Maritime), ADS-B (Air), NASA FIRMS | "Physical-to-paper" trading. Track tankers or fire anomalies near mines to predict supply shortages and hedge/speculate on commodity prices. |
| **ESG & Impact Investing** | ACLED, UNHCR, NASA FIRMS | Objective, real-time proof of a company's or country's environmental impact (fires/deforestation) and social stability (protests/refugee flows) for ESG scoring. |
| **Quantitative (Systematic)** | All (via API integration) | Feed unstructured data streams into ML models to identify non-linear correlations — e.g. how a spike in specific Telegram keywords correlates to a 2% drop in a specific tech stock. |
| **Risk Arbitrage / Management** | Internet Outages, Cyber Feeds, Threat Maps | Assess risk of a merger failing or a portfolio company being hit by infrastructure failure or cyberattacks, enabling faster position hedging. |

### How Alternative Data Shifts Decision-Making

Most traditional traders rely on **lagging indicators** (quarterly earnings, government jobs reports). Alternative data provides **leading indicators**:

- **From reactive to proactive** — instead of waiting for a news report that a port is closed, a trader sees AIS data showing a real-time traffic jam of vessels
- **Verification** — if a rumour starts on social media about a factory fire, the trader can instantly cross-reference NASA FIRMS to confirm whether a thermal anomaly actually exists at that coordinate

### What Qadam Will Actually Use in v1

Of the categories above, Qadam's first build will prioritise:

- **Event-Driven feeds** (NASA FIRMS, Telegram, RSS) — most directly aligned with Akber's catalyst-detection philosophy
- **OSINT / Geopolitical signals** (AIS maritime, GPS jamming, satellite imagery) — for detecting pre-market knowledge gaps that produce genuine options mispricing
- **Sentiment & social intelligence** (Twitter/X, Reddit) — for swarm-based probability calibration via the MiroFish-style prediction layer
- **Options flow data** ([unusualwhales.com](http://unusualwhales.com)-style feeds) — to confirm mispricing before any signal fires

Global Macro, ESG, and Commodity/Supply Chain data are in scope for future phases once the core catalyst → mispricing → signal pipeline is validated.

---

# 5. Architecture & Feature Ideas

## 5-Agent Trading Bot Pipeline

1. **Scan Agent** — Filters 300+ active markets for liquidity, volume, time-to-resolution, unusual price moves, and wide spreads
2. **Research Agents** *(parallel)* — Scrape Twitter, Reddit, RSS feeds; run sentiment analysis; compare narrative vs. market odds
3. **Prediction Agent** — Uses XGBoost + LLM to calibrate true probability vs. market price. Fires only above a confidence threshold
4. **Risk Agent** — Calculates position size using edge + bankroll (Kelly criterion). Blocks or places the trade, then monitors until settlement
5. **Postmortem Agents** *(x5, post-loss)* — Run analysis after every loss, identify what went wrong, save findings, and update the system

## Insider Wallet Detection

- Subscribe to a Polymarket websocket
- Flag buys over $1,000 that score over 65 on a custom "unusual buys" metric
- Track wallet age, trade size, market category (e.g. all military-related markets for a specific country)
- Treat flagged wallet trades as **strong signals / conviction multipliers**, not blind copy instructions. A copied-looking trade can increase confidence only when it agrees with Qadam's own catalyst, pricing-gap, liquidity, and risk checks.
- **Polymarket CLI / Claude Code variant:** treat the new Polymarket CLI as an experimentation rail for agent-assisted prediction-market research. Claude can list markets, inspect order books, inspect history, propose exact order commands, and execute only through guarded wrappers.
- **Real-world proof point to study:** the reported **ilovecircle** bot made ~$2.2M in two months on Polymarket with a 74% win rate by combining cross-niche arbitrage, news/on-chain/whale-flow analysis, and API execution. Qadam should study the pattern, not worship the claim: public wallet, reasoning trace, P&L history, drawdown, sample size, and survivorship bias all need review.
- **Qadam rule:** bot P&L screenshots or public wallets are architecture evidence, not validation. A prediction-market bot becomes relevant to Qadam only if the signal path is explainable, replayable, capped, and auditable.

## Quantum Oracle Layer

- Query the Quantum Oracle at least **once per week** as part of the high-conviction review cycle.
- Use Quantum for **rare, higher-conviction candidates** where non-linear cross-dataset pattern recognition, ambiguity scoring, and options-structure optimisation matter.
- Do **not** require Quantum for every weekly proof trade; those can be handled by the classical scan → research → risk → execution loop.
- Treat Quantum output as probabilistic evidence: it can upgrade, downgrade, or hold a signal, but it cannot originate a trade by itself.

## Swarm Intelligence for Prediction

- Feed seed material (news article, world event) → graph RAG builds knowledge graph → spawn N agent personas → simulate reactions → report agent summarises output
- **MiroFish approach**: compare swarm-derived probability vs. Polymarket pricing → trade when gap exceeds Kelly criterion threshold
- **Synthetic market simulation**: 100 bots of different archetypes (gamblers, quants, panic sellers, value investors) react to news and each other

## Build Principles & Lessons from Other Builders

*Hard-won lessons from other retail builders attempting the same thing. These are not just references — they are now embedded as architectural constraints in Qadam's spec (§1.0.9 and §5.3). Each principle below has a corresponding design decision in the system.*

- **AI agent for research, not decisions.** The most stable retail builds use a deterministic quant/ML core for execution and reserve the AI agent for asset-specific research. "Throw an AI at it and hope" is not robust — Qadam needs measurable performance across regimes so we can identify where the model works, where it breaks, and recalibrate.
- **Multi-layer bot ecosystem.** A single bot is fragile. Better pattern: 3–4 specialised bots that feed each other (signal, validation, risk, execution) — same shape as Qadam's 5-agent pipeline. Each layer is independently testable.
- **Data first, profit later.** Building a profitable bot is a waiting game on collecting data. Train on 3–8 years of historical API data; crypto, forex, and equities each need their own training regime — don't reuse the same model across asset classes.
- **Paper trade until it actually works.** Never put live money behind a paper-trading loss. Run on paper for weeks, run periodic strategy audits, then go live with very small amounts (paper ≠ real, ever), then scale gradually.
- **Backtest ≠ live.** Backtests routinely overstate performance. Real-world signal confirmation → execution latency, especially in volatile/war regimes, can blow drawdowns past anything backtests showed. Build guardrails (max drawdown, regime kill-switches, position-size caps) before going live.
- **Dynamic edge detection.** First-pass bots are usually too risk-averse and miss trades. Tune the edge threshold dynamically rather than hard-coding it.
- **Chain cheap models in parallel + RL.** Run parallel forecasting using the lowest-cost model adequate for each job, then use reinforcement learning to learn which paths work and exploit them. Avoids burning compute on one expensive model that may not be the right tool.
- **Specialised knowledge is the moat, not the AI.** You need both AI coding ability and a coherent, technically-grounded trading strategy you actually understand. Most funds underperform the index — building this is genuinely hard, and influencer claims of "AI auto-profits" almost never include position size or live trade evidence.
- **Hedge funds will always out-simulate retail.** They run thousands of simulations per second; we can't match that on raw throughput. The retail edge has to come from niche signals, alternative data, and catalyst detection — not brute-force compute. A Citadel engineer's blunt summary: on liquid public markets, AI-quant on the retail side does not work — that game belongs to Citadel, Renaissance, and the other compute-rich funds. **This is exactly why Qadam targets catalyst detection, OSINT, and prediction-market mispricing — markets where alternative data and reasoning beat raw simulation count.**
- **"AI that buys its own compute and runs itself forever" is a fantasy.** Documented retail experiment: $200 wallet, 3 years of Coinglass crypto signals, Karpathy's AutoResearch loop, agent able to buy its own compute — paper trading lost, live trading lost. The autonomy framing is seductive but the underlying signal has to actually be profitable first; self-funding compute is the last 5% of the build, not the first.
- **Most "AI hedge fund magic" GitHub repos are useless.** Treat them as inspiration only; expect to build the real system ourselves.
- **Read → Backtest → Implement (RBI).** Skip any of these and the bot loses. Build the discipline into the workflow.
- **AI is the tool, you are the pilot.** Ground the build in the maths of optimisation and control; AI helps with API plumbing and boilerplate, not strategy design.
- **Reference the institutional benchmark.** BlackRock's Aladdin (Asset, Liability, Debt and Derivative Investment Network) started as an in-house risk-management platform on a single workstation in the late 1980s and is now the "hidden OS of global finance" — managing ~$25T+ with agentic AI layers (Aladdin Copilot, Asimov equity research, Thematic Robot, Auto Commentary). State Street runs State Street Alpha (front-to-back, neural-net anomaly detection, Charles River). Vanguard launched Expert Insights (April 2026) for advisor-facing AI portfolio analysis. Qadam isn't competing with Aladdin — but the architecture (single risk/data spine + bolted-on AI layers) is the right shape to copy.

---

# 6. Resources & References

*Every link below is here because it's directly useful to building or informing Qadam. Organised by function.*

## 🧠 Strategy Wisdom & Guardrails

*Distilled from the cleaned finance/trading notes. These are not just references — they are operating principles Qadam should absorb into its product logic, research layer, signal-quality rules, and risk review.*

### Master filters to embed in Qadam

- **Edge beats excitement:** A boring repeatable edge is more valuable than a dramatic story.
- **Process beats prediction:** Define rules, risk, data, and review loops before acting.
- **Behavior beats optimization:** A perfect strategy the trader cannot follow is worse than a good strategy they can execute.
- **Transparency beats trust:** Prefer systems with visible logic, trade logs, live results, and auditability.
- **Robustness beats backtest beauty:** Test across regimes, costs, slippage, and unseen data.
- **AI is leverage, not authority:** Use AI to research, structure, automate, and challenge thinking — not to outsource judgment.
- **Avoid guru gravity:** Strip every claim down to evidence, incentives, risk, and repeatability.

### Qadam-relevant research cards

- **High-growth stock quality**
    - **Core wisdom:** Reduce growth-stock analysis to a few durable business-quality signals instead of drowning in narrative.
    - **Key signals:** Revenue growth above 20% over many quarters; gross margins expanding over time; free cash flow turning positive as the company scales.
    - **Useful threshold:** By roughly $500M in annual revenue, a quality growth company should have a credible path to positive free cash flow.
    - **Qadam relevance:** Useful as a fundamental quality filter after a catalyst candidate is surfaced.
    - **Avoid:** A single blowout quarter, declining gross margins, or a founder/product story that distracts from weak economics.
    - **Source:** [Instagram](https://www.instagram.com/p/DIHkl3xNpT8/)
- **Dollar-cost averaging vs lump-sum investing**
    - **Core wisdom:** Lump-sum investing often wins mathematically because markets rise over time, but DCA can win behaviorally because it helps people stay invested.
    - **Key insight:** A strategy that is slightly less optimal but easier to stick with may outperform a theoretically superior strategy that causes panic selling.
    - **Qadam relevance:** Community-facing recommendations should account for investor behavior, not just theoretical return.
    - **Avoid:** Treating historical average returns as useful if the user cannot emotionally tolerate drawdowns.
    - **Source:** [YouTube](https://www.youtube.com/watch?v=9bZkp7q19f0)
- **200-week moving average discipline**
    - **Core wisdom:** Simple long-term signals can work only if paired with rare discipline during market fear.
    - **Key signal:** High-quality companies or broad-market ETFs touching long-term support such as the 200-week SMA during major selloffs.
    - **Qadam relevance:** Potential long-term confirmation layer for high-quality names during crash/capitulation regimes.
    - **Avoid:** Assuming every touch is automatically safe; quality, valuation, and macro context still matter.
    - **Source:** [Instagram](https://www.instagram.com/p/DXOue-TFvzx/)
- **AI-assisted stock analysis**
    - **Core wisdom:** AI can speed up institutional-style analysis, but it does not remove the need for data quality, assumptions, and judgment.
    - **Useful workflows:** Stock screening, DCF valuation, portfolio risk review, earnings breakdown, portfolio construction, technical analysis, dividend analysis, competitive landscape, quant pattern search, and macro impact assessment.
    - **Best prompt pattern:** Assign a specific analyst role, define the task, request tables, require assumptions, include bull/base/bear cases, and ask for risks that could break the thesis.
    - **Qadam relevance:** Maps directly to Qadam's analyst-agent output layer.
    - **Avoid:** Treating AI output as truth without checking source data, calculations, and assumptions.
    - **Source:** [Instagram](https://www.instagram.com/p/DXGptJMj8Yj/)
- **Small statistical edges**
    - **Core wisdom:** Quant success often comes from applying tiny edges repeatedly across many uncorrelated opportunities, not from being right all the time.
    - **Key idea:** A modest win rate can be profitable if expectancy is positive, position sizing is controlled, and opportunities repeat at scale.
    - **Useful metrics:** Expected value, Sharpe ratio, drawdown, volatility, correlation, turnover, and net returns after fees.
    - **Qadam relevance:** Every signal should be scored by expectancy, not by confidence language alone.
    - **Avoid:** High-conviction single bets disguised as quant strategy.
    - **Source:** [Instagram](https://www.instagram.com/p/DXrvIoJDub4/)
- **Renaissance-style quant research**
    - **Core wisdom:** Treat markets as noisy stochastic systems where no single model is trusted alone.
    - **Workflow:** Research signal → engineer features → simulate → test robustness → control correlation → integrate only if it adds independent value.
    - **Key idea:** Price, volume, spread, and order book behavior often reflect information faster than manually reading every news item.
    - **Qadam relevance:** Qadam should separate signal discovery, feature engineering, simulation, validation, and risk control into independently testable layers.
    - **Avoid:** Overweighting a single story, indicator, or model.
    - **Source:** [Instagram](https://www.instagram.com/reel/DUKGyURDLo4/)
- **Momentum strategy structure**
    - **Core wisdom:** A simple systematic strategy needs clearly defined inputs, scoring, and testing.
    - **Example signal:** Positive 14-day price change; volume above 20-day average; price near the upper part of a longer-term range.
    - **Example score:** Momentum × volume surge × relative strength.
    - **Qadam relevance:** Useful as a secondary confirmation score after a catalyst has been detected.
    - **Avoid:** Deploying because it “looks good” without out-of-sample tests and transaction-cost assumptions.
    - **Source:** [Instagram](https://www.instagram.com/reel/DVrml9qgbeA/)
- **Gold quant agent architecture**
    - **Core wisdom:** A useful trading agent is not just a model; it is a loop of data, backtests, signals, logging, feedback, and continuous review.
    - **System components:** Historical data, strategy scripts, ML model, backtest engine, trade log database, performance metrics, and alert channel.
    - **Key metrics:** Win rate, risk/reward, returns, drawdown, and model accuracy by regime.
    - **Qadam relevance:** Strong reference shape for Qadam's Scan → Predict → Risk → Postmortem loop.
    - **Avoid:** Optimizing for accuracy alone; a lower win rate can still work if risk/reward and expectancy are strong.
    - **Source:** [Instagram](https://www.instagram.com/reel/DT-rdimDamA/)
- **Reinforcement learning for trading**
    - **Core wisdom:** RL trading systems need carefully designed environments, reward functions, evaluation sets, and realistic constraints.
    - **Useful components:** Train/evaluation split, transaction costs, portfolio constraints, max loss limits, reward scheme, action scheme, and repeatable evaluation.
    - **Key risk:** A model can learn the quirks of the training environment instead of a durable market edge.
    - **Qadam relevance:** RL can help optimize thresholds and routing, but should not be trusted as a black-box signal generator in v1.
    - **Avoid:** Judging an RL strategy from a single equity curve.
    - **Source:** [Instagram](https://www.instagram.com/p/DXWmkYKko8N/)
- **Multi-agent trading research**
    - **Core wisdom:** A defensible investment view can be produced by separating analysis roles and forcing disagreement before a decision.
    - **Agent roles:** Fundamentals analyst, sentiment analyst, news analyst, technical analyst, bull researcher, bear researcher, trader, risk manager, and portfolio manager.
    - **Key value:** Transparency. Every decision can be traced through reports, debate, risk review, and final approval.
    - **Qadam relevance:** Maps directly to Qadam's multi-agent architecture; especially useful for explainable signal reports.
    - **Avoid:** Letting one LLM produce a confident buy/sell answer without adversarial review.
    - **Source:** [YouTube](https://www.youtube.com/watch?v=9FoEsXNGLwI)
- **Verified strategy marketplaces**
    - **Core wisdom:** Trading automation is less dangerous when performance is verified, trades are visible, source logic can be inspected, and allocation remains under user control.
    - **Useful checks:** Third-party trade verification, live track record, source code access, backtest reproducibility, custom allocation, and ability to pause.
    - **Qadam relevance:** Qadam's signal output should include evidence trails and verification, not just recommendations.
    - **Avoid:** Blindly handing over capital to a black-box bot.
    - **Source:** [Instagram](https://www.instagram.com/reel/DWrm-3qicPE/)
- **Trading bots**
    - **Core wisdom:** “Trading bot” is not automatically good or bad; the quality depends on transparency, control, verification, and risk design.
    - **Good signs:** Real-time verified performance, clear rules, visible drawdowns, allocation control, and manual override.
    - **Bad signs:** Guaranteed returns, hidden logic, demo-account screenshots, vague guru claims, or no live results.
    - **Qadam relevance:** Qadam should position itself as intelligence infrastructure with human override, not as a magic auto-profit bot.
    - **Source:** [Instagram](https://www.instagram.com/reel/DU54QMZEbTd/)
- **Overnight range breakout**
    - **Core wisdom:** A simple price-range rule can be testable if the entry, stop, exit, market, and session are precisely defined.
    - **Example rules:** Define a session range; enter on breakout; set stop as a fraction of the range; exit at a fixed time if stop is not hit.
    - **Qadam relevance:** Good example of converting vague trading content into a precise, testable rule.
    - **Avoid:** Believing a long backtest without checking optimization, survivorship, and execution assumptions.
    - **Source:** [Instagram](https://www.instagram.com/reel/DWYRW2DAnN4/)
- **Open range breakout / break-and-retest**
    - **Core wisdom:** Many discretionary setups can be simplified into structure: define range, wait for breakout, wait for retest, require rejection, then manage risk.
    - **Example setup:** First 15-minute candle at New York open; trade the break and retest on a lower timeframe; stop below/above the invalidation point; target a predefined risk/reward.
    - **Key caution:** One profitable trade proves nothing. Evaluate across hundreds or thousands of trades.
    - **Qadam relevance:** Useful template for how Qadam should express technical confirmation rules.
    - **Sources:** [Instagram](https://www.instagram.com/reel/DXl9G5XDkZN/) | [Instagram](https://www.instagram.com/reel/DVjNrWbFerC/)
- **Insider buying as a signal**
    - **Core wisdom:** Insider purchases can be useful because they may indicate conviction from people close to the business, but they need filtering.
    - **Useful filters:** Size of purchase, buyer identity, market cap, historical behavior, clustering, filing delay, and whether the purchase is meaningful relative to wealth/compensation.
    - **Qadam relevance:** Potential event-driven signal source, but must be filtered for context and timing.
    - **Avoid:** Assuming every insider buy predicts a rally.
    - **Source:** [Instagram](https://www.instagram.com/reel/DXiUf-okgUB/)
- **Copying politician or famous-investor trades**
    - **Core wisdom:** Public trade disclosures can generate ideas, but reporting delays and context gaps make blind copying risky.
    - **Useful filters:** Disclosure delay, position size, sector theme, related legislation or macro events, and whether the trade still makes sense at current price.
    - **Qadam relevance:** Useful as delayed thematic research, not as a direct execution signal.
    - **Avoid:** Treating delayed public filings as real-time alpha.
    - **Source:** [YouTube](https://www.youtube.com/watch?v=3eD61_wBtQ4)
- **Polymarket / wallet-copying claims**
    - **Core wisdom:** Copying “profitable wallets” sounds attractive but can hide major risks around timing, liquidity, selection bias, and undisclosed losses.
    - **Key questions:** Is performance net of losses and fees? Are copied trades still available at the same price? How many wallets failed and were omitted? Is liquidity deep enough?
    - **Qadam relevance:** Directly relevant to insider-wallet detection; Qadam must account for execution lag, liquidity, and survivorship bias.
    - **Avoid:** “Free money” framing.
    - **Source:** [Instagram](https://www.instagram.com/reel/DW-m1yRAlAv/)
- **Out-of-sample testing**
    - **Core wisdom:** A strategy is not validated because it worked on the data used to build it.
    - **Required tests:** In-sample, out-of-sample, walk-forward, parameter sensitivity, transaction costs, slippage, regime splits, and live paper trading.
    - **Qadam relevance:** Minimum standard before any model or strategy becomes a live signal.
    - **Avoid:** Tweaking until the backtest looks great.
    - **Source:** [Instagram](https://www.instagram.com/reel/DUSGv54DsBC/)
- **Regime classification**
    - **Core wisdom:** Strategies behave differently in bull, bear, sideways, high-volatility, low-volatility, trend, and shock regimes.
    - **Useful tests:** Regime-based backtests, Monte Carlo simulations, drawdown analysis, stress tests, and hidden Markov model classification.
    - **Key insight:** Optimizing for one recent regime often creates fragility in the next regime.
    - **Qadam relevance:** Signals should be gated by market regime before firing.
    - **Avoid:** Buying or deploying an algorithm based only on attractive backtested returns.
    - **Source:** [Instagram](https://www.instagram.com/reel/DVMukN2kWNk/)
- **Live results vs backtests**
    - **Core wisdom:** Live performance is more valuable than polished historical performance because it includes real frictions and uncertainty.
    - **Ask for:** Timestamped live trades, broker statements where possible, max drawdown, open losses, full trade distribution, and performance after costs.
    - **Qadam relevance:** Qadam should keep a permanent live signal log and compare signal outcomes against its original thesis.
    - **Avoid:** Screenshots, cherry-picked trades, or equity curves without trade logs.
    - **Source:** [Instagram](https://www.instagram.com/reel/DVMukN2kWNk/)
- **Professional performance metrics**
    - **Core wisdom:** Do not judge a strategy by one day, one trade, or one payout screenshot.
    - **Use instead:** Expectancy, Sharpe, Sortino, max drawdown, recovery factor, profit factor, exposure, tail risk, and performance across market regimes.
    - **Qadam relevance:** These should be first-class fields in the signal evaluation dashboard.
    - **Avoid:** Win rate obsession and risk/reward claims without sample size.
    - **Source:** [Instagram](https://www.instagram.com/reel/DVjNrWbFerC/)
- **Claude + TradingView automation**
    - **Core wisdom:** AI can become an operator of trading tools, not just an advisor, when connected through browser or MCP-style control layers.
    - **Possible workflow:** Switch symbols, load charts, write Pine Script, fix compile errors, add indicators, backtest, capture screenshots, set alerts, and scan markets.
    - **Key limitation:** This is custom integration, not a native guarantee from Claude or TradingView.
    - **Qadam relevance:** Useful for research automation and technical-analysis workflow acceleration.
    - **Avoid:** Letting automation place trades without guardrails, review, and kill switches.
    - **Sources:** [Instagram](https://www.instagram.com/reel/DWz0sbcFKVE/) | [Instagram](https://www.instagram.com/reel/DWpIKZ-htUT/)
- **TradingView skill from educational content**
    - **Core wisdom:** Turning expert content into an AI skill can help structure analysis, but it does not magically create trading mastery.
    - **Useful version:** Extract repeatable rules, define invalidation, encode checklist, test historically, then review failures.
    - **Qadam relevance:** Useful pattern for converting Akber's trading logic into agent-readable operating procedures.
    - **Bad version:** Feed transcripts into AI and assume it will make you “the greatest trader alive.”
    - **Source:** [Instagram](https://www.instagram.com/reel/DXmtuVRjc_1/)
- **Alert-based trading workflow**
    - **Core wisdom:** A trader can reduce screen time by turning setups into alerts, but alerts are only useful if the underlying setup is tested and rules-based.
    - **Good design:** Clear trigger, chart screenshot, symbol, timeframe, setup type, invalidation level, and risk plan.
    - **Qadam relevance:** Signal notifications should include enough context for fast human review.
    - **Avoid:** Replacing impulsive chart-watching with impulsive alert-following.
    - **Source:** [Instagram](https://www.instagram.com/reel/DXrlH1hDcjk/)
- **Backtest-by-prompt tools**
    - **Core wisdom:** Natural-language backtesting tools can lower the barrier to testing ideas, but the user still needs to understand assumptions.
    - **Check:** Generated code, timeframe, data source, fees, slippage, survivorship, repainting, and optimization.
    - **Qadam relevance:** Good prototyping interface, but generated strategies must go through Qadam's validation pipeline.
    - **Avoid:** Trusting generated strategy code because the tool made it quickly.
    - **Source:** [Instagram](https://www.instagram.com/reel/DWRrBsENsBJ/)
- **Knowledge arbitrage**
    - **Core wisdom:** Some investors win by noticing behavior, culture, and real-world shifts before they are fully priced into markets.
    - **AI use case:** Track news, portfolio holdings, cultural signals, macro events, and second-order effects automatically.
    - **Example pattern:** A change in natural gas prices might affect fertilizer companies before most people connect the dots.
    - **Qadam relevance:** This is close to Qadam's core thesis: identify secondary beneficiaries of emerging catalysts before consensus.
    - **Avoid:** Confusing interesting news with investable edge.
    - **Source:** [Instagram](https://www.instagram.com/reel/DWonhksgi0S/)
- **GDELT global news data**
    - **Core wisdom:** Global news tone can be quantified and monitored as a macro-awareness signal.
    - **Useful features:** Huge multilingual news archive, frequent updates, emotional tone dimensions, event classification, and Google BigQuery access.
    - **Potential applications:** Macro sentiment, geopolitical risk, commodity narratives, sector narrative shifts, and early-warning dashboards.
    - **Qadam relevance:** Strong candidate for Qadam's global macro / geopolitical signal layer.
    - **Limitations:** Media bias, noisy tone scores, uneven coverage, and need for cleaning or financial NLP refinement.
    - **Source:** [Instagram](https://www.instagram.com/reel/DW1T7zmslre/)
- **Emotional durability**
    - **Core wisdom:** A technically valid strategy fails if the trader cannot execute it during fear, boredom, greed, or drawdown.
    - **Key idea:** The ability to remain okay after losses is a trading edge because it prevents revenge trading and identity-driven decisions.
    - **Qadam relevance:** Qadam's UI should reduce emotional decision-making by showing evidence, risk, invalidation, and outcome tracking.
    - **Avoid:** Trying to prove self-worth through market outcomes.
    - **Source:** [Instagram](https://www.instagram.com/reel/DUwzvvFk0_H/)
- **Discipline vs quitting**
    - **Core wisdom:** Many traders do not hate trading; they hate the undisciplined version of themselves that appears while trading.
    - **Failure patterns:** Chasing, forcing, doubting, revenge clicking, breaking rules, and using “one last trade” logic.
    - **Qadam relevance:** Signals should include a clear no-trade / invalidation rule so users do not improvise under stress.
    - **Useful response:** Reduce size, define rules, journal violations, and stop trading when emotional state breaks process.
    - **Source:** [Instagram](https://www.instagram.com/reel/DXbB8XjCSRs/)
- **Ego vs profit**
    - **Core wisdom:** The goal is not to be clever, different, or “right”; the goal is to control risk and make money.
    - **Better mindset:** Move with observable market flow, volume, order flow, and risk parameters.
    - **Qadam relevance:** Qadam should reward evidence quality and risk-adjusted outcomes, not dramatic contrarian narratives.
    - **Avoid:** Identity-based trading, conspiracy narratives, and complexity that does not improve expectancy.
    - **Source:** [Instagram](https://www.instagram.com/reel/DVdlTS4iIv8/)

<aside>
🧘

**Cockpit design implication — emotional durability is a product requirement, not a soft skill.**

The three cards above (Emotional Durability, Discipline vs Quitting, Ego vs Profit) directly constrain how Qadam's signal presentation layer must behave.

- Every signal card must show evidence, risk, and invalidation condition — reducing the cognitive load and anxiety that triggers impulsive overrides.
- The weekly proof cadence (2 trades) is a discipline mechanism: a consistent sample for review, not a quota that forces sub-par trades.
- The Regret Metric in the spec tracks rejected signals for 30 days so impulse-rejections can be honestly evaluated — without ego and without pressure.
- If Ramin is feeling the urge to force a trade or reverse a decision, that is information. Log it in the weekly review; do not act on it.
</aside>

### Red-flag checklist for Qadam

- **Core wisdom:** Most bad finance content uses certainty, urgency, lifestyle, or secrecy to bypass careful thinking.
- **Red flags to detect or exclude:**
    - “Free money”
    - “Infinite money glitch”
    - “Guaranteed”
    - One-trade proof
    - No drawdown shown
    - No live results
    - No costs or slippage
    - Demo-account screenshots
    - Hidden logic
    - No sample size
    - High-pressure community or course funnel
    - “Comment a word and I’ll send it”
- **Best response:** Convert the claim into a testable hypothesis, then demand data.

### Minimum evidence before trusting a Qadam signal

- **Clear rules**
- **Full trade log**
- **Out-of-sample results**
- **Live or paper-forward results**
- **Drawdown statistics**
- **Transaction-cost assumptions**
- **Regime analysis**
- **Parameter sensitivity**
- **Risk per trade**
- **Failure conditions**
- **Kill switch**
- **Position-sizing rule**
- **Execution guardrails** — any agent-accessible CLI/API path must enforce max order size, market whitelist, total exposure cap, dry-run mode, and human approval policy in code, not only in the prompt.
- **Secret hygiene** — API keys and wallet credentials live in environment variables or a secret store, never in scripts, prompt files, or copied terminal commands.
- **Read-only-first proof** — before any live prediction-market execution, the agent must run in read-only scan/report mode long enough to prove useful probability estimates without touching capital.

### Best reusable validation question

- **Question:** Does this have positive expectancy across many trades, regimes, and real execution conditions?
- **Use this for:** Bots, indicators, AI agents, gurus, backtests, copy trading, catalyst signals, options mispricing, prediction-market trades, and discretionary setups.

## 🔍 Signal & Intelligence Sources

*Platforms that surface the kind of signals Qadam's data layer should replicate or connect to.*

- [**unusualwhales.com**](http://unusualwhales.com) — Surfaces unusual options activity that predicts market moves before headlines. The closest existing product to Qadam's signal layer — study it closely
- [**glint.trade**](http://glint.trade) — Comparable signal/intelligence platform; useful for UX and signal presentation benchmarking
- [**One Shot Algo v2**](https://oneshotalgo.com/) — Existing AI trading signals product; understand its positioning to identify what Qadam should differentiate from
- [**QuantMap Report**](https://report.quantmap.app/) *(Ivan Patriki, Carson Hein, Biggun — Substack)* — How professional quants frame and communicate signals to an audience; useful for Qadam's output format
- [**WallStreetQuants — Quant Firm Tier List**](https://www.thewallstreetquants.com/firm-list) — Reference for understanding the competitive landscape of systematic trading firms Qadam is positioning against
- [**Dumb Money Hunter (YouTube)**](https://www.youtube.com/@dumbmoneyhunter?app=desktop) — Trader to study; commentary and setups worth tracking for signal/positioning ideas
- [**Maven Trading**](https://maventrading.com/) — Prop/trader platform to evaluate as a reference point for community-facing trader infrastructure
- **Hermes + XGBoost + unusualwhales (0DTE gamma play)** — Reported retail stack: feed Hermes signals plus the unusualwhales API into an XGBoost model to trade 0DTE options around gamma levels. Bookmap orderflow can be layered in for richer features but the data cost scales fast. **Use for: a concrete v1 model architecture for Qadam's options-mispricing layer.**
- [**LiquidityEdge / MIG indicator**](https://www.instagram.com/reel/DVhAYnZiNIg/) — Orderflow-inspired, Bookmap-style TradingView indicator that highlights reaction zones where volume confirms price. Demo'd with a 96% account return using a 1:4 R:R, 5% entry buffer, and 15% stop-loss buffer at the base. **Use for: visual confirmation layer when Qadam surfaces a catalyst-driven setup — does volume actually support the level the signal is firing at?**
- [**Zulz Trades — Premium Discord**](https://linktr.ee/zulztrades) — Premium trader Discord; potentially relevant community to study for signal delivery, engagement format, and pricing model

## 🤖 AI Architecture & Proof of Concepts

*Validated real-world implementations to draw on when building Qadam's prediction engine.*

- [**MiroFish — $1.49M NBA bet**](https://www.instagram.com/reel/DV9v4URD4j4/) — 4,096 agents trained on 3 years of NBA data; consensus piped into a transformer trained on 16,000+ predictions; gap vs. Polymarket pricing traded using Kelly criterion. **Direct blueprint for Qadam's swarm prediction layer**
- [**MiroFish — Knowledge graph + agent personas**](https://www.instagram.com/reel/DV9X3RpD401/) — Upload any document, build a knowledge graph, activate hundreds of agents with unique personalities to simulate reactions in real time. Use cases include crisis testing, trading signals, and prediction market betting
- [**MiroFish — Built in 10 days, fully open source**](https://www.instagram.com/reel/DWHb7a7DJLZ/) — Uses graph RAG + OASIS engine. Free 3-hour multi-agent architecture lecture series available. **Start here when building the swarm component**
- [**Synthetic market simulation — 100 AI bots**](https://www.instagram.com/reel/DWRCs-2DSXL/) — 100 bots of different archetypes (gamblers, quants, panic sellers, value investors) provisioned with $1M, reading news, arguing, and driving a simulated price. Gamblers beat the quants. Built on Chinese swarm intelligence
- [**AI orderflow trader — Week 4 with Claude**](https://www.instagram.com/reel/DWwaw5ksMRK/) — Live proof-of-concept of Claude trading from orderflow/footprint chart data. Relevant to how Qadam's LLM interacts with market data
- [**WeaveMind / Weft**](https://weavemind.ai/) — Autonomous builder for AI systems, powered by a new language (Weft) designed for AI to write. LLM calls, databases, browser agents, cron jobs, and human-in-the-loop are first-class primitives — maps almost 1:1 to Qadam's 5-agent pipeline (Scan → Research → Predict → Risk → Postmortem). Compiles to a typed visual graph + native Rust binary. **Candidate orchestration layer for Qadam's catalyst → mispricing → review → signal pipeline.**
- [**Markov regime engine —](https://www.instagram.com/reel/DW8OywrkpP9/) [edgebuildit.com](http://edgebuildit.com)** — Quant-built observable Markov engine that classifies the live market into four structural regimes (calm trend, volatile trend, chop, risk-off) by weighting volatility, trend strength, drawdown pressure, correlation stress, and shock intensity. Builds a rolling transition matrix (P(next state | current state)) with hysteresis, minimum-persistence windows, and majority bias to suppress noise; risk-off is gated on verified stress indicators. Visualised as a phase-space projection with regime attractors and vector fields. Free at [edgebuildit.com](http://edgebuildit.com). **Use for: regime-aware gating in Qadam — only fire catalyst signals when the current regime supports the thesis (e.g. suppress chop-state trades, require volatile-trend confirmation for breakout plays).**
- **Google TimesFM** — Decoder-only time-series foundation model from Google Research. Trained on 100B+ real-world data points; predicts market prices, sales trends, and crypto volatility in zero-shot mode. Open source (Apache). **Candidate model for Qadam's prediction layer.**
    - [Instagram overview](https://www.instagram.com/p/DWorz9sjsa_/)
    - [GitHub — google-research/timesfm](https://github.com/google-research/timesfm)
    - [Google Research blog — A decoder-only foundation model for time-series forecasting](https://research.google/blog/a-decoder-only-foundation-model-for-time-series-forecasting/)
    - [Google Cloud — TimesFM in BigQuery and AlloyDB](https://cloud.google.com/blog/products/data-analytics/timesfm-models-in-bigquery-and-alloydb)
    - [Medium — Exploring TimesFM: the foundation model that understands the language of time](https://codemaker2016.medium.com/exploring-timesfm-the-foundation-model-that-understands-the-language-of-time-57486ebca761)
- [**Full architecture research page**](https://www.notion.so/3366fe2ecf3780a38aadc20e323b6988?pvs=21) — Deep-dive on MiroFish, OASIS, Polymarket, Polyrouter, XGBoost, the 5-agent pipeline, insider wallet detection, swarm intelligence, and the 9 Wall Street Claude prompts

## 📊 Prediction Market Strategies

*Proven trading strategies that validate Qadam's recommendation logic and can be used as feature blueprints.*

- [**Insider wallet copy-trading — Israeli arrest case**](https://www.instagram.com/reel/DUrQ187EvI4/) — Find wallets with high win rates on niche topic clusters. Polymarket API + websocket; flag buys >$1K with >65 unusual-buys score; copy within seconds. Real enforcement precedent confirms the strategy works
- [**Polymarket insider wallet bot — 3-second alerts**](https://www.instagram.com/reel/DVrjxRqEjvk/) — All Polymarket trades are public on-chain. Bot alerts within 3 seconds when a top-8 insider wallet moves
- [**Six wallets profit ~$1M betting US strikes Iran**](https://www.instagram.com/reel/DVYyPx0jGQt/) — Accounts activated shortly before first explosions. Validates geopolitical catalyst detection as a real edge
- [**Automated limit-order bot: $7.4K → $210K in 4 months**](https://www.instagram.com/reel/DWEfIS9jRgI/) — Fully automated; 75 limit orders/hour on near-certain Bitcoin outcomes at 99¢. Blueprint for Qadam's automated execution layer
- [**AI agent copy-trades Polymarket: $900 → $7,200 in one day**](https://www.instagram.com/reel/DVz9YnlDUWF/) — Agent identified the best trader on Polymarket and mirrored their positions
- [**Polyrouter MCP for Claude**](https://www.instagram.com/reel/DTfU311EvFu/) — MCP server giving Claude direct access to Polymarket and Kalshi with configurable trading credentials via Polyrouter key. **Practical integration point for Qadam's Claude-powered layer**
- [**Polymarket latency-arbitrage bot — live test**](https://www.instagram.com/reel/DW5Mksyj75g/) — $500 live account, 4–5 opportunities/day, 5–10 trades each. Captures full orderbook depth, up/down odds, and the latency delta between the operator's Chainlink feed and Polymarket's Chainlink feed across market regimes. Author skipped backtesting because historical data isn't deep enough for latency arb (but is acceptable for stat arb). **Use for: Qadam's execution-layer pattern — live data collection over backtesting when the edge is microstructure, not signal.**
- [**Cielo.finance](http://Cielo.finance) [wallet copy-trading](https://www.instagram.com/reel/DWUZuaVDekm/)** — Pick any profitable on-chain wallet on [cielo.finance](http://cielo.finance), hit "track", connect Telegram, and the Cielo bot pushes notifications + one-tap buys. **Use for: lightweight prototype of Qadam's insider-wallet detection layer — validate the copy-trade workflow before building the custom websocket+scoring stack described in Section 5.**

## 🌍 Geopolitical & OSINT Intelligence

*Methods for detecting the kind of catalysts Akber's strategy is built around — events that break normal distribution before the market prices them in.*

- [**OSINT / Operation Epic Fury reconstruction**](https://www.youtube.com/watch?v=0p8o7AeHDzg) — Weekend-built browser app. AI agent swarm captured OSINT signals during Iran strikes across satellite flyovers, flights, GPS jamming, maritime data, internet blackouts, and no-fly zones — all on a 4D globe with a minute-by-minute scrubber. **Blueprint for Qadam's geopolitical monitoring and catalyst detection layer**
- [**Geopolitical risk and trading data**](https://www.youtube.com/watch?v=A-n8E9w3i5M) — How geopolitical risk data feeds into trading decisions; context for designing Qadam's risk signal inputs
- [**Spy Satellite Simulator in a browser**](https://www.spatialintelligence.ai/p/i-built-a-spy-satellite-simulator) — Spatial intelligence applied in a browser app; relevant to satellite data integration and OSINT visualisation
- [**jsfinancials reel 1**](https://www.instagram.com/reel/DWqjFVzDkVx/) / [**reel 2**](https://www.instagram.com/reel/DWo4CeNGs5N/) — Financial content creator; signals/setups framing reference
- [**rick l Quantamentals**](https://www.instagram.com/reel/DVjb_xTCNJJ/) — Bridges quantitative analysis and retail audiences; useful for how Qadam communicates output

## 🛠️ APIs & Technical Infrastructure

*Tools to use when building and integrating the platform.*

- [**RapidAPI Hub**](https://rapidapi.com/hub) — API marketplace; starting point for financial data feeds, sentiment APIs, and news integrations
- [**Coinglass**](https://www.coinglass.com/) — Crypto derivatives data API (funding rates, open interest, liquidations, long/short ratios) with multi-year history. **Use for: candidate data feed if/when Qadam extends into crypto-derivatives catalyst detection. Note: 3-year Coinglass history alone wasn't enough to make a naive autonomous bot profitable — treat it as one input among many, not a standalone edge.**
- [**Karpathy's AutoResearch / nanochat**](https://github.com/karpathy) — Self-experimentation loop pattern (agent designs, runs, and evaluates its own experiments). **Use for: Qadam's Postmortem agents and continuous-improvement loop — the right shape for the "learn from every loss" layer, even though using it as a full autonomous trader has been shown to fail.**
- **Execution venues — [Hyperliquid](https://hyperliquid.xyz) & [Alpaca](https://alpaca.markets)** — Most-cited retail execution stack from other builders. Hyperliquid for on-chain perps, Alpaca for US equities/options API. **Use for: Qadam's execution layer — start with Alpaca for equities/options paper trading, Hyperliquid for any crypto-perps experimentation.**
- [**traderalice/openalice**](https://github.com/traderalice/openalice) — Community-shared open trading bot codebase; worth reading as another reference implementation alongside the Polymarket repos.
- [**Wispr Flow**](https://ref.wisprflow.ai/beehiiv-dev/?utm_campaign=ZC52Z6UIS8&utm_source=beehiiv&utm_term=dev_primary2&_bhiiv=opp_cb737871-db8f-4bfc-8838-1eb3fc2c0dcf_6e77d35f&bhcl_id=88686c81-2fe5-4c44-a454-b6b68f8700c8_eab34e97-fcf2-4656-ac75-dd887bb5526d_977930cc-106b-48ed-b33b-2fb6bb89e0cb) — Voice-first coding workflow for Cursor/Warp prompts, bug reports, acceptance tests, PR descriptions, and file/variable tagging. **Use for: speeding up Qadam build/debug loops when working with a generative AI coder; especially useful for preserving exact filenames, variables, and inline code while verbally describing issues.**
- [**Discord trading bot group**](https://discord.com/channels/1471338915867660433/1471339906851672137) — Active community to observe how trading bots are being deployed and iterated on in practice
- [**9 Wall Street analyst prompts reference**](https://www.instagram.com/p/DVX7iuxj08h/) — Source post for the Goldman, Morgan Stanley, Bridgewater, JPMorgan, BlackRock, Citadel, Harvard, Bain, and Renaissance prompts in Section 5

### Polymarket open-source stack

*Five GitHub repos surfaced by [@](https://www.instagram.com/p/DWx-cSPGV1i/)[Parasmadan.In](http://Parasmadan.In) that map directly to Qadam's prediction-market layer — connection, agents, MCP, and live data.*

- [**Polymarket CLI**](https://github.com/Polymarket/polymarket-cli) — Agent-friendly terminal interface for browsing markets, checking order books, getting price/history data, and placing orders. **Use for: the quickest Qadam prediction-market prototype path — Claude Code can run read-only market scans first, then propose exact commands such as `polymarket markets list`, `polymarket markets book <id>`, and guarded order wrappers once the safety layer exists.**
- [**pmxt-dev/pmxt**](https://github.com/pmxt-dev/pmxt) — Unified trading API (a "CCXT for prediction markets"). Connect to Polymarket, Kalshi, and Limitless through one consistent interface in <10 lines of code; auto-migrates Dome API codebases via `npx dome-to-pmxt`. Python/JS, MIT. **Use for: Qadam's exchange-abstraction layer so the signal engine can route to any prediction market.**
- [**Polymarket/agents**](https://github.com/Polymarket/agents) — Polymarket's official framework for autonomous AI trading agents (LLMs + RAG + superforecasting + live news retrieval via vector search). Modular — swap any LLM without rewriting core logic; full CLI to go live in one session. Python, MIT. **Use for: reference implementation for Qadam's Research → Prediction agents.**
- [**PrefectHQ/fastmcp**](https://github.com/PrefectHQ/fastmcp) — De facto MCP server framework (powers ~70% of MCP servers). Decorate a Python function with `@mcp.tool` to expose it; supports filesystem, OpenAPI, and proxy providers; OAuth/JWT built in. Python, MIT. **Use for: wrapping every Qadam data source (AIS, FIRMS, Polymarket, options flow) as MCP tools that Claude/agents can call directly.**
- [**caiovicentino/polymarket-mcp-server**](https://github.com/caiovicentino/polymarket-mcp-server) — 45-tool MCP server connecting Claude Desktop to live Polymarket trading. Demo mode (no wallet), hard limits on order size/exposure, real-time WebSocket monitoring. Python, MIT. **Use for: safe sandbox for Claude-driven Polymarket execution before Qadam goes live with capital.**
- [**txbabaxyz/polyrec**](https://github.com/txbabaxyz/polyrec) — Real-time terminal dashboard fusing Chainlink, Binance, and the Polymarket orderbook for BTC markets. 70+ technical indicators + orderbook depth in one view; auto-CSV logging; built-in backtests for balance replication and impulse fade. Python, MIT. **Use for: data-collection blueprint for Qadam's signal layer and a starting point for backtesting infrastructure.**

## 📐 Analytical Frameworks

*9 Claude prompts that replicate institutional analyst thinking — to be embedded into Qadam's analysis output layer. Each maps to a specific role in the pipeline.*

1. **Goldman Sachs Stock Screener** — Top 10 stocks, P/E vs sector, revenue growth, debt-to-equity, dividend yield, moat rating, bull/bear 12-month targets, risk rating, entry zones
    
    *→ Use for: initial opportunity scoring and building the candidate list before the catalyst filter runs*
    
2. **Morgan Stanley DCF Valuation** — 5-year revenue projection, FCF, WACC, terminal value (exit multiple + perpetuity), sensitivity table, undervalued/overvalued verdict
    
    *→ Use for: fundamental anchor when sizing a position — is this stock genuinely undervalued before the catalyst hits?*
    
3. **Bridgewater Risk Assessment** — Correlation analysis, sector concentration, geo/currency risk, recession stress test, hedging strategies
    
    *→ Use for: portfolio-level risk check before Akber commits capital — does this trade concentrate risk in a way that's already exposed?*
    
4. **JPMorgan Earnings Analyzer** — Beat/miss history, consensus estimates, options implied move, historical price reactions, bull/bear case
    
    *→ Use for: validating catalyst timing — especially when the catalyst is an earnings event or FDA/contract window*
    
5. **BlackRock Portfolio Builder** — Asset allocation, ETF picks, core vs satellite, expected return/drawdown, rebalancing rules, DCA plan
    
    *→ Use for: community-facing portfolio recommendations layer (future phase)*
    
6. **Citadel Technical Analysis** — Trend direction (daily/weekly/monthly), support/resistance, MA crossovers, RSI/MACD/Bollinger, chart patterns, Fibonacci levels, risk-to-reward
    
    *→ Use for: Step 4 of Akber's filter — finding the entry zone after the catalyst and mispricing are confirmed*
    
7. **Harvard Endowment Dividend Strategy** — 15–20 dividend picks, safety scores, payout ratio, DRIP compounding, tax implications
    
    *→ Use for: income-focused community recommendations (future phase)*
    
8. **Bain Competitive Analysis** — Top 5–7 competitors, market share trends, moat analysis, SWOT, single best pick with catalysts
    
    *→ Use for: company-specific moat analysis before government contract or sector-beneficiary plays*
    
9. **Renaissance Technologies Pattern Finder** — Seasonal patterns, day-of-week effects, insider filing patterns, short interest, unusual options activity
    
    *→ Use for: secondary confirmation — does historical pattern data support the catalyst thesis?*
    

## 🎨 Product & Positioning References

*For building the front-end and understanding how to market Qadam.*

- [**motionsites.ai**](http://motionsites.ai) — Bottom templates are the design reference for Qadam's landing page
- [**Qadam intro video**](https://www.youtube.com/watch?v=uOC9vLRipsg) — Original vision video; re-watch before starting build to stay aligned with the founding intent
- [**Vaughan Fawcett — AI Hedge Fund content**](https://www.instagram.com/reel/DWjoQgMjfgd/) — How AI-driven investment advice is being marketed to retail. Reference for Qadam's tone and positioning
- [**Instagram post reference**](https://www.instagram.com/p/DVPKIEzEkhp/) — Visual/branding reference
- [**antpalkin X post**](https://x.com/antpalkin/status/2041517093670052193) — Additional market intelligence reference
- Raw Trading Notes (unprocessed)
    
    **Source:** [One-candle daily system](https://www.instagram.com/reel/DVtoIBUjkwh/)
    At 9:30 AM EST, the first 5-minute candle forms. Mark its high and low. Drop to the 1-minute chart and wait for a fair value gap to break through one of those levels. Enter on the next candle. Stop at the first candle that closed outside the range. Target: fixed 2:1 R:R. Same setup, every day.
    
    **Source:** [13-year-old NQ micro trade](https://www.instagram.com/reel/DT6gMyWjhmJ/)
    Trade based on London/NY session high, fair value gap respected, break of structure confirmed on 5-minute chart. Scaled out at TP1, moved stop to a lower high with liquidity present.
    
    **Source:** [530% gain trader](https://www.instagram.com/reel/DWAa3y-E_jw/)
    Rules-based system. Less than 5 minutes/week. Key principle: the more you complicate trading, the more you lose. Verify results with broker statements, not highlight reels.
    
    **Source:** [Weekly→daily 3-candle entry](https://www.instagram.com/reel/DUytVrFkzPz/)
    Set bias on the weekly: price up = look to buy, price down = look to sell. Drop to the daily and find a 3-candle sequence — big candle / small body with long wick / big candle. For longs, scan down-left for a "bottom" pattern; for shorts, scan up-left for a "top". Mark the long-wick candle from low-wick to high-wick. Entry = top of that range; stop = bottom of that range with breathing room. Wait for price to tap in.
    
    **Source:** [15-min Opening Range Breakout — optimised](https://www.instagram.com/reel/DU-404PCkXe/)
    15-min ORB coded in PineScript and parameter-swept (timeframe, opening-range duration, entry confirmation, SL/TP size & placement) using a free Chrome extension instead of manual backtesting. Reported best variant: 62% win rate over 2 years, clean equity curve, 300% outperformance vs NASDAQ. Replication TODO: rebuild the PineScript template and run the optimiser ourselves before trusting the numbers.
    
    **Source:** [LiquidityEdge 1:4 RR setup](https://www.instagram.com/reel/DVhAYnZiNIg/)
    96% account return using a 1:4 risk-to-reward, 5% buffer on zone entry, 15% buffer on stop loss at the base. Edge comes from entering at volume-confirmed reaction zones (Bookmap-style orderflow), not impulse.
    

# **Prediction Market Papers**

## **1. Toward Black-Scholes for Prediction Markets**

Treats probabilities like tradable assets with their own volatility.

[https://arxiv.org/html/2510.15205v2](https://arxiv.org/html/2510.15205v2?utm_source=chatgpt.com)

## **2. Unravelling the Probabilistic Forest: Arbitrage in Prediction Markets**

Shows how arbitrage emerges across complex, linked prediction events.

[https://arxiv.org/abs/2508.03474](https://arxiv.org/abs/2508.03474?utm_source=chatgpt.com)

## **3. What Happens When Institutional Liquidity Enters Prediction Markets?**

Explores how these markets change when serious capital enters.

[https://arxiv.org/html/2604.10005](https://arxiv.org/html/2604.10005?utm_source=chatgpt.com)

## **4. The Anatomy of Polymarket**

Analyzes millions of trades to reveal how these markets actually function.

[https://arxiv.org/html/2603.03136v1](https://arxiv.org/html/2603.03136v1?utm_source=chatgpt.com)

[Qadam Specifications v3](Qadam/Qadam%20Specifications%20v3%203566fe2ecf37800abef8c5c717cc6656.md)

[Archive](Qadam/Archive%203566fe2ecf378007ad09d73864bdd8c8.md)