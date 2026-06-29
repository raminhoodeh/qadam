# Qadam Reddit Narrative Proxy Implementation Plan

Date: 2026-06-29

Reference repo: `Sam120204/Stock_Trading_Reddit`

Purpose: close Qadam's current Reddit API gap without waiting for Reddit OAuth approval by wiring a public aggregate retail-attention layer into Qadam's Social/Narrative pipeline. This is a read-only narrative-pressure source, not an execution venue and not proof by itself.

## 1. Decision

Use the `Stock_Trading_Reddit` repo as a reference implementation, not as imported runtime code.

The usable first-release pattern is the ApeWisdom aggregate path:

- `https://apewisdom.io/api/v1.0/filter/all-stocks/page/{page}`
- `https://apewisdom.io/api/v1.0/filter/all-crypto/page/{page}`
- `https://apewisdom.io/api/v1.0/filter/4chan/page/{page}`

The repo also contains PRAW/raw Reddit collection, sentiment modelling, MongoDB storage, Streamlit UI, and Random Forest ideas. Those are useful later, but they do not solve the immediate no-Reddit-key condition because they require Reddit credentials or web scraping risk. Qadam should not import those paths for the first release.

## 2. How This Fills The Reddit Gap

Current gap: Reddit OAuth credentials are unavailable, so Qadam cannot call `oauth.reddit.com`.

Replacement bridge: `Reddit Narrative Proxy`, powered by ApeWisdom-style aggregate data. It observes retail/forum attention without raw post access.

This changes the source posture:

- `Reddit API`: still optional and pending approval.
- `Reddit Narrative Proxy`: active no-key aggregate bridge.
- Source count: no automatic new source 36. It fills the existing Reddit social/narrative slot as a variant until Reddit OAuth arrives.
- Authority: read-only only; cannot create trades, approve risk, submit orders, or satisfy source quorum by itself.

## 3. Qadam Role

This layer answers:

- Which tickers are suddenly being discussed by retail forums?
- Is a ticker reaching narrative saturation, meaning Qadam's edge may already be crowded?
- Is social attention confirming, contradicting, or arriving late relative to price, volume, Options/Alpaca, Yahoo Finance, OddsPipe, and news evidence?
- Are prediction-market themes becoming visible in retail equity or crypto discussion before or after market odds move?

It is not a buy/sell predictor. It is an attention and crowding sensor.

## 4. Data Contract

Create normalized observations with this shape:

```json
{
  "source_key": "reddit_narrative_proxy",
  "source_variant": "apewisdom_public_aggregate",
  "pipeline": "social",
  "event_type": "social_signal",
  "collected_at": "ISO-8601",
  "asset_type": "equity | crypto | forum_cross_asset",
  "ticker": "NVDA",
  "name": "NVIDIA",
  "rank": 1,
  "rank_24h_ago": 8,
  "mentions": 1258,
  "mentions_24h_ago": 442,
  "upvotes": 3890,
  "mention_change_abs": 816,
  "mention_change_pct": 184.6,
  "attention_velocity": 0.74,
  "crowding_risk": "low | medium | high",
  "qadam_use": "confirmation | contradiction | saturation_warning | anomaly",
  "trust_score_seed": 0.46,
  "authority": "read_only_context_only"
}
```

## 5. Integration Phases

### RNP-0 Reference Review And Guardrails

Objective: record the reference repo safely.

Tasks:

- Add `Stock_Trading_Reddit` to the Resource Registry as a social/narrative reference.
- Record that the repo is MIT licensed, but Qadam is not importing code wholesale.
- Mark PRAW, raw Reddit scraping, MongoDB, and Streamlit components as deferred.
- Mark the ApeWisdom aggregate client pattern as the only first-release implementation target.

Acceptance:

- Docs say clearly that this is a no-key aggregate bridge, not full Reddit API replacement.
- No Reddit credentials are required.
- No raw Reddit scraping is introduced.

### RNP-1 ApeWisdom Adapter Skeleton

Objective: create a Qadam-native adapter, not a pasted repo module.

Target files:

- `orchestrator/adapters.py` or a dedicated `orchestrator/social_narrative_proxy.py`
- `scripts/check_reddit_narrative_proxy.py`
- `data/runtime/reddit_narrative_proxy_validation.json`

Adapter behavior:

- Fetch `all-stocks`, `all-crypto`, and optionally `4chan` aggregate pages.
- Support sample mode and live mode.
- Rate-limit and timeout all calls.
- Archive raw payloads locally using Qadam's raw payload contract.
- Normalize into `social_signal` observations.
- Fail closed as `degraded` if ApeWisdom is unavailable.

Acceptance:

- Sample mode passes without network.
- Live mode can fetch at least one page when internet is available.
- No secrets are printed or required.
- Output contains rank, mentions, rank delta, mention delta, upvotes, and source variant.

### RNP-2 Trust Score And Source Registry Posture

Objective: make the source visible without overstating its reliability.

Tasks:

- Add `reddit_narrative_proxy` as the active variant for the existing Reddit source slot.
- Keep `reddit_oauth` as pending optional upgrade.
- Seed trust score around `0.42-0.50`, below direct exchange/broker/macro data.
- Add a stricter source contribution rule: this layer can support or challenge a setup but cannot originate a paper trade alone.

Acceptance:

- `scripts/check_phase1_live_source_hardening.py` reports Reddit gap as covered by proxy or optional-pending OAuth, not trade-blocking.
- Dashboard data-source section shows "Reddit Narrative Proxy via ApeWisdom" separately from "Reddit OAuth pending".
- Source quorum policy refuses to count this as a high-trust primary source.

### RNP-3 Market And Prediction-Market Joins

Objective: connect retail attention to Qadam's existing market context.

Join targets:

- Alpaca paper/account universe for current watchlist and holdings.
- Yahoo Finance/yfinance for price, volume, options-chain, and sector context.
- OddsPipe for normalized Polymarket/Kalshi themes where possible.
- SEC/Capitol Trades for company and politician-trading context.
- RSS/GDELT for news-confirmation timing.

Derived features:

- `attention_vs_price_gap`
- `attention_vs_volume_gap`
- `retail_arrival_lag`
- `crowding_risk`
- `late_consensus_warning`
- `prediction_market_theme_overlap`

Acceptance:

- At least one research packet can say: "retail attention is rising, but price/volume/prediction-market context does or does not confirm it."
- The layer can downgrade a setup when retail attention is already euphoric and price has already moved.
- The layer can upgrade review urgency when retail attention jumps before price/news confirmation.

### RNP-4 Local Research Analyst Use

Objective: feed the local LLM structured observations, not raw noisy text.

Tasks:

- Add Research Analyst packet template: `retail_attention_packet`.
- Give Gemma only the normalized top movers, deltas, and corroborating market context.
- Ask for compression only:
  - What changed?
  - Which assets/themes need Strategy Lead review?
  - Is this early attention, late attention, or manipulation/crowding risk?

Acceptance:

- Local LLM output remains non-executable.
- No raw Reddit post text is required.
- If LM Studio is offline, deterministic fallback still produces basic summary packets.

### RNP-5 Strategy Lead And Akber Filter Integration

Objective: make the social proxy useful to Qadam's trade reasoning.

Strategy Lead uses:

- Compare retail narrative pressure with Qadam worldview hypotheses.
- Identify second-order AI infrastructure names gaining/losing attention.
- Test whether attention supports Akber's catalyst, timing, and market-structure checks.
- Flag crowding, pump risk, and "edge already gone" conditions.

Akber 6-stage filter use:

- Stage 1 Catalyst: social attention can help confirm that a catalyst has entered retail consciousness.
- Stage 2 Sector/Theme: attention can reveal crowding in AI infrastructure, defence, crude, silver, semiconductors.
- Stage 3 Macro/News Context: must be corroborated by RSS/GDELT/FRED/SEC/physical sources.
- Stage 4 Technical: must be confirmed by price/volume/TradingView/Yahoo/Alpaca.
- Stage 5 Risk: euphoric retail attention raises slippage and reversal risk.
- Stage 6 Execution: never execution-authorizing by itself.

Acceptance:

- Strategy packets explicitly label the proxy as `social_narrative_context`.
- It can modify confidence or urgency, but not bypass Signal Integrity or Risk Agent.

### RNP-6 Dashboard UX

Objective: make the Reddit gap visibly resolved in plain English.

Dashboard changes:

- Data Sources: show `Reddit Narrative Proxy - connected through ApeWisdom aggregate data`.
- Reddit OAuth: show `optional upgrade pending`.
- Mission Snapshot: mention "retail/forum attention is available through aggregate public data."
- Strategy section: show how retail attention affects crowding and edge-decay checks.
- Do not show this as a broken source.

Acceptance:

- A user can see that Qadam has social-retail attention coverage even without a Reddit API key.
- The dashboard still makes clear this is aggregate data, not full Reddit post/comment ingestion.

### RNP-7 PaperOps Safety Gate

Objective: let the proxy inform paper trading without becoming a trigger.

Rules:

- Cannot create a trade candidate alone.
- Cannot satisfy minimum source quorum alone.
- Cannot approve risk, sizing, order staging, or broker submission.
- Can add:
  - `social_confirmation`
  - `social_contradiction`
  - `crowding_warning`
  - `late_consensus_warning`
  - `retail_attention_anomaly`

Acceptance:

- `scripts/check_signal_integrity_gate.py` or equivalent rejects any candidate whose only support is `reddit_narrative_proxy`.
- A candidate with market/physical/macro evidence can use this proxy as a secondary confidence modifier.

### RNP-8 Later Reddit OAuth Upgrade

Objective: preserve a clean upgrade path if Reddit grants access.

Tasks:

- Keep the existing Reddit OAuth credential placeholders.
- Add a second variant: `reddit_oauth_raw_posts`.
- Compare OAuth-derived raw-post sentiment against ApeWisdom aggregate attention.
- Use OAuth only for narrow subreddits and watchlists.
- Keep rate limits and policy compliance explicit.

Acceptance:

- OAuth becomes an enrichment path, not a forced rewrite.
- ApeWisdom remains fallback if OAuth is unavailable or rate-limited.

## 6. First Implementation Slice

Implement in this order:

1. Add Resource Registry and API docs entries.
2. Build `orchestrator/social_narrative_proxy.py` with sample payloads.
3. Add `scripts/check_reddit_narrative_proxy.py`.
4. Add source-hardening visibility so Reddit is `covered_by_proxy` rather than `missing_credentials` for first-release operations.
5. Add cockpit status fields and dashboard copy.
6. Add Phase 2 Research Analyst packet generation.
7. Add Signal Integrity rule: secondary signal only.
8. Add live-mode fetch behind timeout/rate budget.

## 7. Acceptance Gates

Minimum acceptance before this counts as implemented:

- `check_reddit_narrative_proxy.py` sample mode passes.
- Live mode fetches ApeWisdom when network is available.
- Dashboard stops showing Reddit as a failed connection.
- `api-specs.md` explains that Reddit OAuth is optional while the proxy is active.
- `qadam-master-implementation-plan.md` points to this plan.
- Signal Integrity refuses proxy-only trade candidates.
- No new execution authority exists.

## 8. Risks And Controls

| Risk | Control |
| --- | --- |
| ApeWisdom unavailable | Degrade explicitly; do not block PaperOps. |
| Aggregate data lacks raw-post provenance | Keep trust score modest and secondary-only. |
| Retail attention causes hype chasing | Treat high attention after price movement as crowding risk. |
| 4Chan data is noisier/manipulable | Lower trust score and require stronger corroboration. |
| Accidentally reintroducing Reddit scraping | First-release adapter uses only aggregate public endpoints. |
| Confusing proxy with Reddit OAuth | Dashboard labels both separately. |

## 9. Done State

Qadam has filled the practical Reddit data gap when:

- It can observe retail ticker attention through a no-key aggregate source.
- It can compare retail attention against price, volume, news, prediction markets, and Qadam's strategy universe.
- It can use that context to challenge or support paper-trade review.
- It no longer treats missing Reddit OAuth as a trade-blocking or silent source gap.
- It still preserves the upgrade path to official Reddit OAuth later.

