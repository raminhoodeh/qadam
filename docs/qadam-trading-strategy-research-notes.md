# Qadam Trading Strategy Research Notes

Date: 2026-05-25

Source: rough transcript notes from `/Users/raminhoodeh/Downloads/trading strategy notes.md`.

## Purpose

These notes are useful to Qadam as a research-intake packet, not as approved
trading strategy authority.

They contain four strategy themes that can be converted into Qadam hypothesis
packets, backtest requirements, data-source requirements, risk-sizing tests, and
Phase 7 paper-candidate experiments:

1. Opening range breakout with volatility-targeted sizing.
2. Post-earnings announcement drift.
3. Simple trend-following / Turtle-style breakout baseline.
4. Order-flow volume-delta dislocation.

None of these notes should create a trade by themselves. They should enter the
Qadam system through Strategy Lead review, Signal Integrity, Risk Agent,
Execution Policy, and PaperOps gates.

## Runtime Integration

The notes are now represented in Qadam as a structured strategy-research intake:

- `orchestrator/strategy_research_intake.py` converts the notes into four
  research candidates and a challenge-only decision context.
- `scripts/check_strategy_research_intake.py` validates the intake and rejects
  probes that try to turn the notes into trade, execution, broker, or live
  authority.
- Strategy Lead receives the intake as read-only challenge context during the
  Phase 2 shadow cycle.
- The Phase 4 candidate strategy universe annotates each relevant Qadam strategy
  family with matching research candidates and review questions.
- PaperOps readiness checks that this context is present before full paper
  operation.

## How This Helps Qadam

The useful parts are not the influencer claims or the transcript narrative. The
useful parts are the repeatable research habits:

- Start from a documented market anomaly or simple rule.
- Separate entry, exit, and position sizing.
- Test each added filter independently.
- Reject filters that do not improve both halves of the sample.
- Use risk-adjusted metrics, not just headline profit.
- Check long/short asymmetry instead of assuming symmetry.
- Prefer simple, inspectable rules before adding complexity.
- Treat position sizing as a first-class strategy component.
- Require out-of-sample validation before paper trading.

For Qadam, these become implementation requirements:

- a candidate strategy registry
- a hypothesis packet for each strategy idea
- source and data-quality requirements
- minimum sample-size requirements
- in-sample / out-of-sample separation
- paper-only execution rules
- postmortem and learning-loop hooks
- dashboard visibility for why a setup was accepted or rejected

## Strategy Candidate 1: Opening Range Breakout

### Core Idea

The first part of the trading day may reveal a persistent buyer/seller
imbalance. If price breaks out after the opening range is defined, that
imbalance may continue during the session.

The notes connect this idea to the market intraday momentum literature, where
the first half-hour return is reported to predict later same-day returns.

### Base Rules From Notes

- Instrument in example: Nasdaq futures / ENQ.
- Session: New York regular session.
- Opening range: first 30 minutes.
- Entry: long when a 5-minute candle closes above the opening range high.
- Stop: below the opening range low.
- Target: 1R.
- Time exit: close position by 3:00 p.m. New York time.
- Frequency: one trade per day.
- Direction: long-only in the tested version.
- Original optional filter: positive volume delta threshold on breakout candle.

### Research Findings From Notes

- Delta confirmation looked intuitive but did not reliably improve the edge.
- Removing the delta filter made the strategy simpler and likely more robust.
- Fixed one-contract sizing ignored volatility differences between narrow and
  wide opening ranges.
- Volatility-targeted sizing improved risk-adjusted performance in both halves
  of the tested sample.

### Qadam Use

This is useful as an intraday paper-candidate template for liquid US market
proxies, for example QQQ, SPY, SMH, SOXX, XLE, USO, SLV, or other paper-tradable
ETF proxies aligned with Qadam's first trading universe.

It should not be treated as proof that Qadam has an edge in crude oil, silver,
defence, semiconductors, or prediction markets until those instruments are
tested directly.

### Qadam Validation Requirements

- Confirm exact instrument universe.
- Translate futures rules into Alpaca-paper tradable symbols where needed.
- Include commissions, slippage, spread, and partial-fill assumptions.
- Re-run with and without the delta filter.
- Re-run with fixed sizing and volatility-targeted sizing.
- Split sample into at least two periods.
- Test pre-2020 and post-2020 regimes separately.
- Log no-trade days and failed breakouts.
- Require Signal Integrity to verify that the rule is not just bull-market beta.

### Current Verdict

Good research candidate. Not approved. Best immediate use is as a PaperOps
backtest candidate and a Strategy Lead challenge packet.

## Strategy Candidate 2: Post-Earnings Announcement Drift

### Core Idea

Post-earnings announcement drift is the tendency for stocks to continue moving
in the direction of an earnings surprise after the announcement.

If a company beats expectations and price reacts positively, the drift may
continue upward. If a company misses and price reacts negatively, the drift may
continue downward. The notes emphasize that the long side may be cleaner than
the short side in modern large-cap equities.

### Academic Anchors To Verify

The transcript references the main PEAD literature. Names should be verified
before formal citation, but the intended anchors appear to be:

- Ball and Brown, 1968.
- Bernard and Thomas, 1989.
- Livnat and Mendenhall, 2006.
- A broad review of PEAD research around 2021.

### Base Rules From Notes

- Universe tested in notes: 20 large US stocks across sectors.
- Period: January 2018 to April 2026.
- Events: 658 earnings events.
- Required data:
  - announcement date
  - announcement timing flag: before market open or after market close
  - actual EPS
  - consensus EPS estimate
  - price reaction
- Surprise: actual EPS minus consensus EPS.
- Concordant long: positive surprise and positive price reaction.
- Concordant short: negative surprise and negative price reaction.
- No trade when surprise and reaction disagree.
- Entry: after the reaction window has completed.
- Exit: time-based, around 60 trading days.
- Basic version: no stop loss and no take profit.
- Position sizing: fixed percentage of capital per position.

### Research Findings From Notes

- The first pass produced a positive risk-adjusted result.
- Removing the concordant price-reaction filter increased return but also
  increased drawdown.
- Adding a 5 percent surprise threshold did not clearly improve risk-adjusted
  results.
- Combining concordance and surprise threshold degraded the strategy.
- Short legs were repeatedly negative in the tested large-cap sample.
- Long-only concordant PEAD was the cleanest tested configuration.

### Qadam Use

This is probably the most directly useful strategy idea in the notes because it
maps cleanly into Qadam's research pipeline:

- evidence event: earnings announcement
- fundamental surprise: actual versus consensus
- market reaction: post-announcement price move
- signal direction: long-only or long/short
- holding period: 60 trading days
- risk sizing: fixed percent or volatility-adjusted percent
- postmortem: compare drift expectation against realized path

It is especially relevant to semiconductors, defence, energy equities, miners,
and ETF components inside Qadam's first trading universe.

### Qadam Validation Requirements

- Choose a clean earnings data provider.
- Store announcement timing and avoid lookahead bias.
- Verify consensus estimate timestamps.
- Use adjusted prices and corporate-action handling.
- Test large-cap, mid-cap, and small-cap baskets separately.
- Compare long-only versus long/short.
- Compare concordance filter versus no concordance filter.
- Compare surprise thresholds.
- Add liquidity and borrow constraints for any short tests.
- Require a paper-mode portfolio exposure cap.

### Current Verdict

Strong research candidate. Best suited for a Qadam Strategy Candidate Registry
entry and a Phase 7 paper backtest track once reliable earnings data exists.

## Strategy Candidate 3: Simple Trend-Following Baseline

### Core Idea

Simple trend-following systems can work because they cut losers quickly and let
winners run. The note uses the Turtle-style breakout idea as an example of why
simple systems are often better research starting points than complex systems.

### Base Rules From Notes

- Trend filter: 200-period moving average.
- Long bias: price above the 200-period moving average.
- Short bias: price below the 200-period moving average.
- Entry: breakout of the previous 40 bars high or low.
- Stop: 2x ATR.
- Sizing: 2 percent account risk per trade.
- Example instrument: Nasdaq futures on a 60-minute chart.

### Qadam Use

This should be treated as a benchmark strategy, not as a unique edge.

It is useful because Qadam needs simple controls:

- Does a proposed complex strategy beat a basic trend-following baseline?
- Is the edge coming from the signal or from the market's broad trend?
- Does adding complexity improve drawdown, return, or stability?
- Does the strategy fail on instruments where it should not apply?

### Qadam Validation Requirements

- Run across Qadam's candidate instruments.
- Compare against buy-and-hold or ETF exposure.
- Compare across timeframes.
- Check whether results are dominated by a few large winners.
- Track long and short legs separately.
- Treat it as a control model inside Strategy Lead review.

### Current Verdict

Useful as a baseline/control. Not sufficient as a Qadam strategy by itself.

## Strategy Candidate 4: Volume-Delta Dislocation

### Core Idea

Volume delta measures the net imbalance between aggressive buying and aggressive
selling. A dislocation between price direction and volume delta can imply
exhaustion or reversal pressure.

### Base Rules From Notes

Example long setup:

- Instrument: Nasdaq futures / ENQ.
- Timeframe: 1-hour chart.
- Price above previous session high.
- Last hour candle closes negative.
- Volume delta for that hour is positive.
- Delta threshold: at least 500.
- Exit: fixed take profit, fixed stop loss, or end-of-day close.

### Qadam Use

This is useful as a future microstructure feature, but it is not immediately
ready for current Qadam PaperOps unless Qadam has reliable bid/ask or futures
order-flow data.

It could eventually help:

- confirm intraday breakout quality
- identify exhaustion near key levels
- improve entry timing
- explain why an otherwise valid setup failed
- provide a Head-of-Quant feature for ambiguity scoring

### Qadam Validation Requirements

- Confirm whether Qadam has a valid order-flow data source.
- Define exactly how delta is calculated.
- Avoid mixing TradingView, MultiCharts, and broker-specific delta semantics.
- Test thresholds out of sample.
- Check whether threshold values transfer across instruments.
- Include exchange fees, slippage, and spread.
- Avoid using it as a required input until data quality is verified.

### Current Verdict

Interesting future feature. Not current PaperOps-critical unless Qadam adds an
order-flow data provider.

## Cross-Strategy Rules For Qadam

Every candidate derived from these notes should be converted into this standard
Qadam packet:

### 1. Hypothesis

What market behavior should persist, and why?

### 2. Instrument Scope

Which symbols, sectors, commodities, ETFs, futures, or event markets does this
apply to?

### 3. Required Data

What source data is needed, and is it available to Qadam right now?

### 4. Entry Rule

What exact observable event creates a candidate setup?

### 5. Exit Rule

What exact observable event closes the trade?

### 6. Position Sizing

How is exposure scaled, capped, and de-risked?

### 7. Validation Design

What is the in-sample period, out-of-sample period, and no-lookahead policy?

### 8. Risk And Failure Modes

What regime breaks the idea?

### 9. PaperOps Readiness

Can this be tested in Alpaca paper with the current venue, data, and guardrails?

### 10. Learning Loop

How will postmortems decide whether to keep, modify, or reject the strategy?

## Recommended Qadam Prioritization

1. PEAD long-only concordant strategy.
   - Best fit for Qadam's evidence-based, event-driven process.
   - Needs reliable earnings data before PaperOps.

2. Opening range breakout with volatility-targeted sizing.
   - Good intraday template.
   - Needs careful instrument translation from futures to Alpaca-paper symbols.

3. Simple trend-following baseline.
   - Useful benchmark for Strategy Lead and Head of Quant.
   - Should be used to challenge more complex systems.

4. Volume-delta dislocation.
   - Potentially useful later.
   - Blocked until Qadam has reliable order-flow data.

## Immediate Implementation Ideas

- Add these four ideas to a Strategy Candidate Registry.
- Build a PEAD data-requirements checklist.
- Add an ORB backtest scaffold for QQQ, SMH, SOXX, XLE, USO, and SLV.
- Add a baseline trend-following benchmark for every candidate instrument.
- Add a rule that no new filter is accepted unless it improves risk-adjusted
  performance in multiple periods.
- Add dashboard visibility for strategy-candidate status:
  - idea captured
  - data missing
  - backtest running
  - failed validation
  - paper candidate
  - paper active
  - rejected after postmortem

## Bottom Line

The notes are valuable because they show the kind of institutional research
process Qadam should automate:

raw idea -> academic or empirical anchor -> explicit rule -> clean data ->
backtest -> split-sample validation -> risk sizing -> paper trade -> postmortem.

They are not trade instructions. They are strategy raw material for Qadam's
research, validation, and paper-trading pipeline.
