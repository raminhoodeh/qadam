# Source Access, Time Semantics and Research Consumption Repair

## Scope

Improve the existing paper research pipeline, not add another execution owner or
relax broker, liquidity, direction, invalidation, exposure or exit controls.
Deployment remains to the local operator and existing signed public dashboard;
"live" deployment does not enable live capital.

## Corrected Defects

- Provider timestamps are parsed and normalized, not accepted merely because a
  field contains a string. Reject date-only publication claims, ambiguous local
  clocks, invalid epochs and future observations. Normalize GDELT's compact UTC
  and AISSTREAM's Go UTC representation. CelesTrak's documented UTC epoch is an
  observation clock, not a publication clock.
- Transaction dates, economic reference periods, nested suggested contract
  matches, retrieval clocks and FRED daily reference dates cannot establish
  publication time. They remain useful forward context from durable first-seen
  availability, without historical backdating or current-catalyst credit.
- Replace the Esri hurricane demonstration layer (last observation in 2019) with
  NOAA NHC CurrentStorms. A real empty activeStorms response is a valid empty
  observation, not a fabricated signal. Preserve the old catalogue key for
  compatibility while explicitly stating the actual provider and limited scope.
- Rotate SEC submissions through NVIDIA, TSMC, Lockheed Martin and RTX instead of
  downloading Apple's filing index for every family. Match the issuer to its
  instrument or sector ETF. Filing metadata alone is not earnings-call sentiment.
- Rank economically relevant active Polymarket questions before unrelated sports
  questions. Retain indicative prices and do not claim executable quotes or
  matched-contract arbitrage.
- Rotate nine FRED factors within the existing three-request budget. Resolve the
  cadence parser bug that interpreted "6 hours or daily" as a compulsory day.
- Honor bounded provider Retry-After instructions. Configuration-file changes
  schedule an access recheck; unchanged rejected credentials do not trigger an
  aggressive retry loop. Successful sources receive one controlled time-contract
  migration pass; permission failures and rate-limit cooldowns are not bypassed.
  Migration work is due now, not sorted behind a weekly source's next nominal
  publication. This prevents newly enabled context collectors starving at boot.
- Live market-close verification exposed a separate discovery-certification
  defect: an empty active-pattern set was always a failure despite all twelve
  structural checks passing. A completed, current, count-checked scan with no
  qualifying active patterns is valid idle. Missing/stale scans remain typed
  dependency holds; incomplete accounting of real active setups still fails.

## Durable Context and Economic Joins

The existing control-plane SQLite database owns normalized source context. There
is no new runtime authority database. Cache revisions have immutable first-seen
availability, per-source current-snapshot membership and at most 12,000 retained
receipts. Actual decision and forward-shadow records retain their frozen packets
independently of research-cache retention.

Failed probes and valid empty current snapshots retire old context from current
use without erasing its history. Stable monthly values do not become new events
on every poll. Historical observations retrieved today are not historical
point-in-time alpha data.

Frozen, explicit channels:

| Channel | Evidence joins | Important limit |
| --- | --- | --- |
| Energy | Oil/shipping news and event odds, actual AIS positions, GPSJAM cells overlapping the corridor, Gulf cyclone location, oil/rates/dollar context | Vessel presence, navigation degradation or a storm does not prove lost supply |
| Semiconductors | Issuer-specific SEC metadata, chip/export-policy news, Taiwan-area physical observations, relevant market context | No claim of bullish earnings tone without transcript/content evidence |
| Defence | Relevant issuer metadata and escalation/procurement/de-escalation reporting, macro context | A conflict headline alone does not establish direction or expected return |
| Macro/metals | Rates, dollar, credit, inflation, yields, crypto leverage context and relevant market observations | Crypto funding is a separate context variable, not independent equity price confirmation |

H3 cell centers provide auditable geography for GPSJAM. USGS observations require
a frozen magnitude/location screen. Unrelated sports markets and observations
outside frozen exposure maps stay explicitly unmapped, not forced into a trade.
These geographical screens are hypotheses, not proven causal sensitivities.

Numeric factors retain units/reference periods where supplied, source receipt
citations and first availability. A 10y-minus-2y curve is derived only from both
actual same-date yield observations. Unknown units or incremental value are not
filled with invented numbers.

## Consumption and Learning

- Source ingestion alone publishes qadam_cross_source_context.json under its
  registered source_lake ownership and immutable generation contract.
- Pattern records receive instrument-matched context; its material identity
  contributes to the input-material fingerprint. Negative controls are not
  enriched. Context does not silently inflate a research score.
- The canonical compiler attaches current context to the actual executable-proxy
  draft. The Qadam-owned decision compiler rechecks availability and age and
  retains the considered context in its result. It does not turn context into a
  missing mandatory trigger, quote or approval.
- Forward-shadow decisions freeze the context and its source keys. Existing
  preregistered component studies can associate future source-context-backed
  setups with outcomes versus abstention; the existing strategy comparator
  retains its market/price-only benchmarks. This is association, not a full
  source-removal causal ablation or evidence of incremental alpha.
- Cohort observations require real time and provider-backed outcomes. No new
  source causes an automatic score/size bonus, parameter mutation or promotion.
- Existing dashboard/Telegram operating-picture consumers report current event
  coverage, forward-context coverage and unresolved access gaps separately.
  No new sender, schedule, dashboard layout or frontend authority is introduced.

## Access Limits

ACLED and X credentials remain configured locally. Earlier requests returned
HTTP 403 and HTTP 402 respectively. Missing UCDP/PatentsView tokens, Bookmap
bridge configuration and paid-alert delivery cannot be repaired by inventing
credentials. Account consent, API permissions, credit and regional restrictions
are never bypassed. Existing public alternatives can contribute under their own
identities; they are not relabelled as the unavailable vendor.

The self-healer can rerun adapters, honor cooldowns, detect changed local
configuration and refresh the complete downstream evidence path. It cannot
purchase access, accept provider terms or restore revoked entitlements.

## Verification and Release

Acceptance includes strict clock tests, first-seen/revision/restart behavior,
snapshot retirement, relevant versus irrelevant joins, negative-control
separation, source-to-decision propagation, unchanged risk sizing and
single-owner publication. Run the complete network-disabled test suite and
changed-code lint before deployment. Live probes must remain read-only and
separate from the single operator's authoritative files.

After deployment verify the exact running commit, source-ingestion completion,
context-enriched pattern records, canonical decisions, protected positions,
zero open circuits/repair requests and signed public snapshot digest parity.
Do not claim profitability or multi-session unattended reliability from these
checks. Machine-readable release evidence is retained under data/runtime.

## Primary References

- ACLED access/error semantics: https://acleddata.com/api-documentation/elements-acleds-api
- ECB data and revisions: https://data.ecb.europa.eu/help/api/data
- NOAA current feed: https://www.nhc.noaa.gov/CurrentStorms.json
- NOAA field examples: https://www.nhc.noaa.gov/productexamples/NHC_JSON_Sample.json
- NOAA JSON contract: https://www.nhc.noaa.gov/productexamples/NHC_Tropical_Cyclone_Status_JSON_File_Reference.pdf
- H3 Python cell geography: https://uber.github.io/h3-py/api_quick.html
