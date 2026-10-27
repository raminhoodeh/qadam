# Congressional-Trading Discussion Context

Implemented 27 October 2026 for private, guarded paper research.

## Purpose and Scope

Qadam reads the public `r/tradewithcongress` Atom feed as a supplemental variant
of its existing `reddit` source. It does not add another independent provider,
change the 41-entry catalogue, expand the trading universe, or change risk limits.
Existing STOCK Act coverage remains separate. A Reddit post about that same
disclosure is not independent corroboration of it.

The source can draw attention to an issuer, a potential political-information
channel, or a stale/crowded narrative. It is not verified order flow, a valuation,
an executable quote, or an established profitable strategy. Returns, screenshots,
post popularity and politician reputation do not establish predictive value.

## Collection and Provenance

- The existing `source_ingestion` owner polls one fixed HTTPS Atom endpoint.
- Each request has an eight-second timeout, a 512 KiB response limit and a
  25-post bound. Normal polling is no more frequent than every 30 minutes.
- No OAuth credentials, subscriptions, proxies, new schedulers or broker access
  are introduced. Redirects are not followed and denied access is not bypassed.
- Permission failures back off six hours; HTTP 429 respects bounded Retry-After
  with at least a one-hour delay. Other transport failures retry on normal cadence.
- Collection retains bounded title excerpts, canonical post IDs/URLs, explicit
  tickers, limited named-actor claims, dates and allowlisted reference-link URLs.
  It does not collect comment threads, author profiles, post bodies or image/OCR
  contents. A trade visible only in a screenshot is not parsed as a trade fact.
- Reference links are not fetched or authenticated as disclosures. Actor, side,
  transaction amount and ownership claims must not be represented as verified.

## Time and Interpretation

Post publication, last update, claimed transaction date, claimed filing date and
durable first-seen availability are distinct. Future/ambiguous publication clocks
are rejected. Missing years are not guessed; a filing date is not substituted for
a transaction date. Contradictory claimed dates suppress the directional claim.
Historical posts cannot be backfilled into an earlier decision or alpha backtest.

This matters because qualifying congressional transactions may be disclosed up
to 45 days after the transaction, subject to the earlier awareness deadline.
A post today can therefore discuss a much older purchase. See the official
[House PTR guidance](https://ethics.house.gov/periodic-transaction-report-calculator/).

## Decision Integration

Issuer-tagged posts become `congressional_disclosure_claim` events with explicit
unverified/untrusted labels. Generic political questions do not become issuer
observations. Existing context receipts deduplicate repeated downloads and retain
first-seen availability in the control-plane database.

Existing issuer/family joins deliver the context to pattern records and canonical
strategy-decision packets. For example, an Intel claim may inform semiconductor
ETF research through SMH/SOXX, but is not automatically a directional NVDA claim,
and does not authorize trading INTC outside the existing universe.

The role is `unverified_congressional_discussion_secondary`. It cannot be promoted
to an executable economic catalyst by the economic-change extractor. Context alone
cannot create a trade, grant quorum, approve risk, increase a score/size, bypass a
current trigger or replace fresh liquidity, invalidation and broker truth.
Existing forward evaluation requires independent outcomes, costs and comparison
with cash, SPY and price-only controls before any weight or size increase.

## Health and Operations

The existing worker owns `qadam_reddit_congress_feed_state.json`. Its summary is
published in source-collection coverage, the source-capability registry and the
public cockpit's `reddit_narrative_proxy.congressional_activity` field. This is
supplemental-feed health, not a claim that all Reddit data or all disclosed trades
are available. An inaccessible subfeed does not disable a healthy ApeWisdom feed.

A missing initial subfeed state makes only `reddit` eligible for its existing
owner's next bounded collection pass. No timestamp reset or forced global refresh
is needed. Existing watchdogs, Telegram delivery and execution ownership remain
unchanged.

Verify these existing runtime artifacts after release:

1. `qadam_reddit_congress_feed_state.json`: HTTP outcome, actual count, last
   successful collection and next allowed attempt.
2. `qadam_cross_source_context.json`: relevant Reddit receipt, original post
   publication, first-seen time, secondary role and no executable economic change.
3. `qadam_pattern_score_v3.json`: the relevant instrument's retained context packet.
4. `qadam_operator_service_status.json`: exact running build, service freshness,
   circuit/repair state and paper-only ownership.
5. `cockpit-status.json`: fresh signed publication of the supplemental-feed status.

## Verification and Limits

The isolated Python suite passed 2,139 tests, including 45 new feed/integration
cases. These cover provenance, claim ambiguity, disclosure lag, duplicate receipts,
unsafe XML/oversize responses, permission/rate-limit backoff, partial outages,
existing-owner bootstrap, sector joins and decision/risk invariance. An isolated
live request returned HTTP 200 with 25 posts, 17 containing issuer tags. This is
collection proof, not primary-disclosure or investment-performance proof.

The integration does not establish a repeatable trading edge or guarantee more
trades. Before commercial/live-capital use or broader redistribution, review
[Reddit's applicable terms](https://redditinc.com/policies/data-api-terms), licensing
and the restrictions on underlying disclosure data. Public accessibility is not
permission to bypass access controls, scrape government reports or train models.
