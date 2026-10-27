# WallStreetBets Research Context

Added 27 October 2026 through the existing `reddit` source owner. The 41-entry
source catalogue, trading universe, paper-only route and risk limits are unchanged.

## What It Collects

The public `r/wallstreetbets/new/.rss?limit=25` feed provides a bounded sample of
submission titles, canonical IDs/URLs and explicit publication/update timestamps.
The existing source worker checks it no more often than every 30 minutes. It does
not crawl comments, user profiles, post bodies, images, account screenshots or
options-position tables. This is not exhaustive subreddit coverage.

Explicit cashtags, parenthesized tickers, reviewed bare instrument tickers and a
small company-name map identify issuer-specific leads. Ambiguous generic words
such as DD, YOLO and FED do not become symbols. Unmapped issuers remain research
leads; they do not expand the tradable universe. Generic daily threads are not
issuer observations.

Title hints distinguish options speculation, earnings discussion, analysis claims
and gain/loss claims. These are not verified holdings, measured sentiment, expected
returns, short-share recommendations or evidence of an attention spike. Public
ticker counts describe unique titles in the current 25-post sample only, not all
mentions, comments, users, engagement, market demand or a representative poll.

## How Qadam Uses It

Posts enter durable first-seen receipts and existing issuer/family research joins.
The role `unverified_retail_discussion_secondary` appears in relevant pattern and
canonical strategy-decision packets. Intel discussion may provide semiconductor
ETF context but is not an automatic directional claim about a competing issuer.
Original publication and first-seen availability are separate, so repeated polling
cannot create a new event or backdate historical evidence.

WallStreetBets, the congressional-discussion subfeed and ApeWisdom share one parent
Reddit source. Their overlap is explicitly possible; they cannot manufacture
independent source quorum. The combined event envelope is capped at 25: up to
seven congressional leads, eight WallStreetBets leads and the remaining aggregate
attention observations. Unavailable subfeeds leave healthy variants operational.

The new role is not eligible for the economic-catalyst extractor. Context cannot
create orders, approve risk, increase scores or size, replace fresh broker/quote
evidence, or bypass a valid entry trigger. Existing forward-only controls and
cost-aware outcome evaluation still govern any future claim of useful edge.

## Operations and Verification

Both subreddit adapters share `orchestrator/research/reddit_feed.py`, rather than
independent copies of transport/safety logic. Only reviewed communities can be
fetched. Each request is limited to eight seconds and 512 KiB; redirects are not
followed, unsafe XML is rejected, future clocks are excluded and IDs are deduped.
Independent community caches preserve their own cadence and provider cooldowns.
HTTP 401/403 backs off six hours, 429 respects Retry-After with at least an hour,
and other transport failures retry on the normal cadence. No access-denial bypass,
new credential, paid provider or scheduler is introduced.

The existing owner writes `qadam_reddit_wallstreetbets_feed_state.json`. A missing
initial state makes Reddit due for its existing bounded worker, not a new job or
forced global refresh. Summary health is retained in source-collection coverage,
the source-capability registry and `reddit_narrative_proxy.wallstreetbets` in the
signed public cockpit payload. `not_polled`, access failures and unmeasured
sentiment remain explicit rather than being replaced with fixtures.

Verification covers both adapters, invalid provenance/XML/clocks, permission and
rate-limit backoff, separate caches, partial outages, balanced event budgets,
first-seen durability, sector joins, economic-catalyst exclusion and unchanged
strategy-decision/risk behavior. A live bounded read returned HTTP 200 with 25
posts, five issuer-tagged titles and six ticker/title associations. Collection is
not evidence that trading on those discussions is profitable.

Before commercial/live-capital use or redistribution, review
[Reddit's applicable terms](https://redditinc.com/policies/data-api-terms) and any
licensing requirements. Public accessibility is not a license to scrape unrelated
content, bypass access controls or train models.
