# Capability-led economic event optimization

## Objective and scope

Focus existing research capacity on semiconductor issuer disclosures and oil
supply/demand changes. Turn cited changes into testable interpretations in the
existing paper decision path, rather than treating relevance scores or financial
word counts as expected returns. Other strategy families remain available.

This release does not claim a validated edge, change portfolio budgets, introduce
a new execution owner, submit demonstration trades, or enable live capital.

## Operating changes

- `economic-changes.1` extracts a metric, issuer, exact supporting span, reported
  change, conditional/negated state and economic mechanism.
- Explicit same-statement `from X to Y` comparisons retain values and compatible
  units. They are reported-prior comparisons, not analyst-consensus surprises.
- Revenue, demand, margin and guidance changes are interpreted separately from
  capex, capacity and inventory. More investment is not automatically bullish.
- Negated or unchanged economic claims cannot fall through to a keyword buy.
- Commodity supply restoration and supply loss have opposite interpretations;
  oil demand has a separate channel. Gas and refining do not automatically become
  crude-supply shocks. Reported events are not independently verified physical losses.
- A named issuer's cash-flow claim is not assigned to its competitors. Sector
  proxies and unattributed issuer claims need the existing current price/volume
  confirmation before a bounded discovery direction is resolved.
- Optional economic features do not become another global gate. Missing model,
  transcript or economic-comparison data does not veto an otherwise valid setup.
- Research scheduling prioritizes obtainable semiconductor and energy evidence,
  before ranking secondary programmes by coverage and the latest research score.

## SEC content boundary

The rotating submissions collector can fetch one primary HTML filing accepted
within the preceding 72 hours. It uses the declared SEC User-Agent and a derived,
whitelisted `www.sec.gov/Archives/edgar/data/` URL. Redirects, arbitrary links,
attachments and unsupported filenames are not followed. Collection is capped at
eight seconds, two megabytes and eight cited sentences per document.

The existing control-plane database retains at most 32 cache rows. Successes and
failures have a minimum 24-hour cache/cooldown; provider Retry-After is respected.
The raw provider envelope archives selected quotes, document hash and URL, not an
unbounded local filing corpus. SEC metadata remains available if optional content
access fails, but its role remains `issuer_filing_metadata`, not document analysis.

SEC policies and API references:
- https://www.sec.gov/search-filings/edgar-application-programming-interfaces
- https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data

## Learning and compatibility

Economic features retain the source receipt and immutable first-seen availability
in the existing cross-source packet. Decision-time copies are included in the
existing forward-shadow hash. The economic policy version is included in the two
families' strategy definitions; old strategy outcomes cannot certify this policy.

Prospective component studies compare an economic-context policy with the frozen
price-only baseline on the same instrument, horizon, unit notional and modeled
costs. The study requires registration before decision time and real subsequent
provider-backed outcomes. Missing comparators remain unavailable, not zero-return
controls. Both losses and zero improvements are retained. This is a policy
comparison, not a causal source-removal/retraining experiment or actual portfolio P&L.
Existing source/abstention studies keep their original immutable payload shape.

No source receives extra quorum credit, score weight, confidence-as-probability or
position size from the new features. Quantum stays a challenger, not an assumed
advantage. Unknown subscription costs remain unknown rather than zero.

## Verification and limitations

Regression tests cover numeric comparisons, negation, conflicting metrics,
issuer/proxy attribution, supply versus demand, first-seen deduplication, SEC
filename security, content limits, cache/cooldown behavior and prospective matched
outcomes. Run the full suite offline in the isolated worktree, then verify the
committed operator, owned source/decision/shadow refreshes, broker reconciliation
and signed public snapshot on deployment.

This is a bounded deterministic extractor, not general financial language
understanding. It does not supply earnings-call entitlements, consensus forecasts,
historical filing-text diffs, options pricing or verified regional power exposure.
Those require separate point-in-time data and experiments. Better interpretations
may improve decisions, but only enough independent forward outcomes after costs
can establish whether they add trading value. Trade count and profit are not
acceptance criteria for a maintenance deployment.
