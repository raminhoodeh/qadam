# Qadam Resource Registry

Primary source document: `specs/qadam-general-context.md`. Additional architecture references are linked in individual entries.

This registry is separate from the World Monitor API/source registry. World Monitor is the live 5-pipeline ingress layer for machine-readable data feeds. This document tracks the broader Qadam build resources: strategy wisdom, reference products, open-source stacks, research papers, analytical frameworks, and implementation ideas that should guide architecture and product decisions.

## How To Use This Registry

- Treat resources as evidence, inspiration, or implementation references, not automatic truth.
- Promote a resource into the build only after it maps to a specific Qadam module, test, or risk control.
- Keep live data/API feeds in `docs/api-source-inventory.md`.
- Keep non-live references, product benchmarks, papers, and open-source projects here.

## Strategy Wisdom And Guardrails

Purpose: encode the operating discipline that keeps Qadam from becoming a hype-driven trading bot.

Key principles from `qadam-general-context.md`:

- Edge beats excitement.
- Process beats prediction.
- Behavior beats optimization.
- Transparency beats trust.
- Robustness beats backtest beauty.
- AI is leverage, not authority.
- Avoid guru gravity.
- Read, backtest, implement.
- Paper trade until it actually works.
- Backtest results must be treated as weaker than live/paper-forward evidence.

Foundation implication:

- The Event Log, trade journal, postmortems, and Signal Review must capture assumptions, evidence, costs, slippage, invalidation, and outcome.
- The cockpit should make `no trade` a first-class outcome.
- Every strategy promotion requires out-of-sample or paper-forward evidence.

## Signal And Intelligence Benchmarks

These are products or public examples Qadam should study for signal presentation, data scope, or positioning.

| Resource | Role In Qadam |
| --- | --- |
| unusualwhales.com | Benchmark for unusual options flow and market-moving activity presentation. |
| glint.trade | Comparable signal/intelligence UX benchmark. |
| One Shot Algo v2 | Competitor positioning and signal packaging reference. |
| QuantMap Report | Reference for how professional quants communicate signals. |
| WallStreetQuants firm list | Competitive landscape and institutional positioning reference. |
| Dumb Money Hunter | Trader/setup reference to monitor, not a source of truth. |
| Maven Trading | Community/trader infrastructure reference. |
| LiquidityEdge / MIG indicator | Volume/orderflow confirmation concept for catalyst-driven setups. |
| Hermes + XGBoost + unusualwhales stack | Candidate v1 architecture pattern for options-mispricing modelling. |

Foundation implication:

- Add a future `benchmark_registry` table or document so Qadam can record which external products informed each UI or signal design choice.

## AI Architecture And Proofs Of Concept

These resources guide Qadam's agent architecture, swarm simulation, and continuous improvement loops.

| Resource | Role In Qadam |
| --- | --- |
| MiroFish NBA bet | Blueprint for swarm-derived probability vs prediction-market pricing gap. |
| MiroFish graph RAG + personas | Blueprint for knowledge graph plus agent-persona simulations. |
| Synthetic market simulation | Reference for simulated market participant reactions. |
| AI orderflow trader with Claude | Reference for LLM interaction with market/orderflow data. |
| WeaveMind / Weft | Candidate orchestration reference for typed agent workflows. |
| Markov regime engine | Reference for regime-aware gating before signals fire. |
| Google TimesFM | Candidate time-series forecasting model for research/testing. |
| Karpathy AutoResearch / nanochat | Reference pattern for postmortem agents and experiment loops. |
| Anthropic financial-services | Reference pattern for named financial workflow agents, reusable skill bundles, MCP connector grants, managed-agent cookbooks, validation scripts, and secret-scan discipline. |
| AutoHedge | Reference pattern for separating director/research, quant validation, risk management, and execution roles. Qadam should use the role separation pattern, not import autonomous execution behavior. |
| Vibe-trading / agentic trading workflow repos | Reference pattern for research-goal driven workflows, broker/tool connectors, and shadow backtests. Qadam should convert this into explicit Research Goal records before any trade candidate exists. |
| Fincept Terminal | Reference pattern for financial-terminal taxonomy, broad connector maps, portfolio analytics, and market-context UX. Treat code and license as restricted until reviewed; use architecture lessons only. |
| LibreChat | Reference pattern for multi-model operator chat, MCP configuration UX, tool visibility, and multi-user operator workflows. Qadam should keep commands read-only and structured-record backed. |
| Cloudflare Agents / durable inbox patterns | Reference pattern for durable agent state, alert workflows, human-in-the-loop approvals, retries, and acknowledgements. Qadam should keep canonical state local while using the workflow pattern for cockpit and Telegram visibility. |
| Sam120204/Stock_Trading_Reddit | Reference pattern for no-key Reddit-like aggregate retail attention through ApeWisdom, ticker mention/rank deltas, sentiment/correlation feature ideas, and later Reddit OAuth enrichment. Qadam should implement a native `Reddit Narrative Proxy` and avoid importing PRAW/raw Reddit scraping for the first release. |

Foundation implication:

- The foundation should reserve module slots for Research Analyst, Strategy Lead, Postmortem Agents, Regime Engine, and Swarm Simulation even before those modules execute live work.
- Add an Agent Operating System layer before deeper intelligence/execution work: named agent manifests, reusable Qadam skill bundles, explicit tool grants, validation, and secret scanning.
- Adopt the structure/safety pattern from Anthropic's reference, but keep Qadam's own local-first architecture, source registry, and paper-mode autonomy model.
- Use `docs/qadam-oss-reference-implementation-plan.md` as the control overlay for adopting external repo patterns. External code should not be copied into Qadam until license, security, broker-authority, and secret-handling review pass.

## Esoteric Edge / World-Model Corpus

Source folder: `how-the-world-works/`.

These files are not live market data. They are Qadam's private foundational worldview layer: the esoteric edge that makes the system sceptical of surface narratives and alert to hidden incentives, coordinated power, institutional self-interest, psychological control, and second-order consequences. They are useful as a contrarian world-model corpus: power-structure maps, hidden-incentive hypotheses, narrative frames, extreme scenario generation, and red-team prompts.

Operational boundary: Qadam can privately believe this corpus is directionally foundational while still requiring live-source corroboration before any claim affects signal confidence, risk, or execution.

| Resource | Role In Qadam |
| --- | --- |
| `how-the-world-really-works-v1.md` | Metaphysical and psychological-control frames; useful for narrative/sentiment modelling, not factual evidence. |
| `how-the-world-really-works-v2.md` | Institutional distrust, covert-operations, finance/media/medical controversy corpus; useful for official-vs-alternative narrative extraction. |
| `how-the-world-really-works-v3.md` | Geopolitical power hierarchy, petrodollar/BRICS flow, command-and-control models, and collapse scenarios. |
| `how-the-world-works-v4.md` | US-China Grand Bargain scenario tying stablecoins/Treasuries, AI chips, energy access, Taiwan, Iran, and financial-market opening into a tradable macro hypothesis. |

Foundation implication:

- Add a world-model/hypothesis registry that extracts claims, actors, mechanisms, observable signatures, live sources to check, and market channels.
- Treat this corpus as a private worldview prior, hypothesis generator, and red-team lens.
- Require live-source corroboration before any world-model frame can affect signal confidence.
- Show `world-model lens` provenance separately from factual evidence in the cockpit.

Detailed integration note: `docs/how-the-world-works-integration.md`.

## Prediction Market Stack

These resources map directly to Qadam's prediction-market path.

| Resource | Role In Qadam |
| --- | --- |
| Polymarket CLI | Fast read-only prototype for market discovery, order books, and price/history checks. |
| pmxt | Unified prediction-market exchange abstraction for Polymarket, Kalshi, and Limitless. |
| Polymarket agents | Reference implementation for LLM + RAG + live-news prediction-market agents. |
| fastmcp | Tool framework candidate for exposing Qadam data and market tools. |
| polymarket-mcp-server | Safe sandbox reference with demo mode, hard limits, and WebSocket monitoring. |
| polyrec | Data-collection and backtesting blueprint for Polymarket orderbook/Chainlink/futures signals. |
| Polyrouter MCP | Practical integration reference for Polymarket/Kalshi access through guarded credentials. |
| Cielo wallet tracking | Lightweight prototype reference for wallet monitoring and Telegram alerts. |

Foundation implication:

- Prediction-market adapters should begin in read-only mode.
- Any execution path must enforce max order size, market whitelist, total exposure cap, dry-run mode, and approval policy in code.

## Geopolitical And OSINT References

These resources guide Qadam's catalyst-detection UX and OSINT methodology.

| Resource | Role In Qadam |
| --- | --- |
| Operation Epic Fury reconstruction | Blueprint for geopolitical monitoring, timeline replay, and multi-source OSINT fusion. |
| Geopolitical risk and trading data | Context for converting geopolitical risk into trading inputs. |
| Spy Satellite Simulator | Reference for spatial intelligence and satellite-data visualization. |
| jsfinancials reels | Signal/setup framing reference. |
| rick l Quantamentals | Reference for explaining quantamental signals to humans. |

Foundation implication:

- The cockpit System Map should eventually support timeline replay, source layering, and catalyst provenance, not just static status cards.

## APIs And Technical Infrastructure References

These are build and integration resources beyond the 35 live World Monitor feeds.

| Resource | Role In Qadam |
| --- | --- |
| RapidAPI Hub | Discovery layer for niche APIs not yet in the source registry. |
| Coinglass | Candidate crypto-derivatives data source for a later crypto-perps extension. |
| Hyperliquid | Candidate crypto-perps execution venue for later experimentation. |
| PriveX Starter | Execution-adapter reference for self-hosted agents: `x-api-key` auth, delegated subaccounts, Base/COTI network selection, read-only status checks, explicit auth errors, no automatic POST retries, and live smoke tests only behind hard confirmation. Optional later perps rail; not a first-release dependency. |
| Alpaca | Primary paper/live equities and options execution API. |
| traderalice/openalice | Reference trading bot codebase to study, not inherit blindly. |
| Wispr Flow | Build workflow reference for working with generative coding tools. |
| Discord trading bot group | Community observation reference for bot iteration patterns. |
| 9 Wall Street analyst prompts | Role templates for Qadam's analysis output layer. |
| ApeWisdom aggregate endpoints | No-key public aggregate route for Reddit/4Chan stock and crypto attention. Useful for filling Qadam's Reddit API gap as a low-trust, secondary-only social narrative proxy. |

Foundation implication:

- These should be visible in the plan as candidate integrations or references, but only Alpaca and selected prediction-market tools should influence v1 execution architecture.
- PriveX Starter sharpens the execution architecture even if Qadam does not use PriveX in the first release:
  - Build a venue registry before building venue-specific code.
  - Start execution venues in `disabled` or `read_only`.
  - Check health, permissions, balances, positions, market metadata, prices, and venue limits before any order path exists.
  - Separate authentication/permission failures from transient network/API failures.
  - Scope every venue by account, subaccount, network, chain, and permission set where possible.
  - Retry only idempotent read calls; never automatically retry order-creating POST requests.
  - Require explicit confirmation flags for any live-money smoke test.
  - Keep PriveX or any crypto-perps venue `live_blocked` in the first-release £100,000 paper-account proof run unless a separate approved paper/sandbox account exists.

## Analytical Frameworks

Institutional-style analyst prompts to embed into Qadam's research and Signal Review layer.

| Framework | Qadam Use |
| --- | --- |
| Goldman Sachs Stock Screener | Candidate list and opportunity scoring before catalyst filtering. |
| Morgan Stanley DCF Valuation | Fundamental anchor for company-specific trades. |
| Bridgewater Risk Assessment | Portfolio and macro risk review. |
| JPMorgan Earnings Analyzer | Catalyst timing and implied move analysis. |
| BlackRock Portfolio Builder | Future portfolio-facing recommendations layer. |
| Citadel Technical Analysis | Step 4 of Akber's 6-Step Filter. |
| Harvard Endowment Dividend Strategy | Future income-focused analysis surface. |
| Bain Competitive Analysis | Moat and competitor analysis for company-specific catalysts. |
| Renaissance Technologies Pattern Finder | Seasonal, insider, short-interest, and historical pattern checks. |

Foundation implication:

- Signal reports should reserve fields for analyst-framework outputs even if the first version only stores placeholders.

## Product And Positioning References

These guide product tone, design, and landing-page/cockpit positioning.

| Resource | Role In Qadam |
| --- | --- |
| motionsites.ai | Landing-page visual reference. |
| Qadam intro video | Founding vision alignment reference. |
| Vaughan Fawcett AI Hedge Fund content | Retail AI-investing positioning reference. |
| Instagram visual references | Brand/style inspiration. |
| antpalkin X post | Market intelligence reference. |
| Raw trading notes | Candidate strategy hypotheses to turn into explicit test rules. |

Foundation implication:

- The landing page and cockpit should stay visually distinct: landing page sells the vision; cockpit shows system truth, health, evidence, and risk.

## Prediction Market Papers

These papers should inform pricing-gap, arbitrage, liquidity, and market-structure research.

| Paper | Qadam Use |
| --- | --- |
| Toward Black-Scholes for Prediction Markets | Probability-as-asset framing and options-style modelling. |
| Unravelling the Probabilistic Forest | Arbitrage across linked prediction events. |
| What Happens When Institutional Liquidity Enters Prediction Markets? | Market-structure and liquidity regime implications. |
| The Anatomy of Polymarket | Empirical behaviour of Polymarket trades and participants. |

Foundation implication:

- Prediction-market modelling should have a literature-backed research path, not only API experimentation.

## Immediate Corrections To The Build Plan

- Rename references to “World Monitor source registry” where they imply all Qadam resources; use “live ingress source registry” instead.
- Add this Resource Registry as a planning companion beside the API Source Inventory.
- Add a future `resources` or `references` table to track source document, type, module mapping, status, and decision notes.
- Show both “Data Sources” and “Research/Build Resources” in the cockpit System Map so the Fund Manager can distinguish live feeds from design references.
