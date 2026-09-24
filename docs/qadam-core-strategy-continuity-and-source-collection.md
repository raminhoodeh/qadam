# Core Strategy Continuity and Source Collection

## Operating Contract

The five existing core families remain the operating taxonomy. Power research
and other emerging relationships remain separate. A core family is not proof
of an edge and a research score is not a probability of profit.

Current observations can create bounded paper hypotheses using the existing
Strategy Foundry and canonical decision path. They do not need completed
historical or forward validation before entering discovery-micro review.
Validated strategies still need the historical evidence contract. Missing
direction, unusable market observations, malformed strategy mappings or
authority violations remain blockers. No new execution owner is introduced.

The existing discovery budget, stop/target construction, holding-period exits,
portfolio limits, reconciliation, duplicate prevention and paper-only mandate
are unchanged. This release does not increase position sizes or promise trades.

## Stable Rules and Learning

The strategy source recipe is the configured source universe, not whichever
subset happened to be fresh on a polling cycle. Actual fresh sources and their
provenance remain attached to each observation. A change in source freshness,
score or observation ID therefore does not reset the strategy version.

The frozen definition now includes the admission rules, score model and
direction-confirmation thresholds, as well as entry, exit, risk, direction,
instrument and horizon. Changes to rules generate a different version.
Existing registered definitions and outcomes are never rewritten or backdated.
This release necessarily begins new cohorts for the revised definition.

The existing immutable ledger and matched-forward evaluator continue to compare
each registered version against SPY after modeled costs and no trade, using
independent events. A fresh signal can proceed before the comparison matures.
Approved, matching forward estimates can feed the same version without changing
its risk envelope. Changed rules remain separate challengers, not silent edits
to an incumbent or manufactured evidence of improvement.

`qadam_core_strategy_status.json` shows all five families even when none has a
current signal: observed scores, resolved directions, eligible hypotheses,
versions, specific blockers and source coverage. It is a read model, not trading
authority. Existing dashboard layout is unchanged.

## Source Collection

The catalog is not 41 independent API collectors. It contains provider adapters,
aliases, derived records, local bridges and deliberately disabled integrations.
Existing enabled collectors retain their provider cadence and bounded run budget.
No paid subscription or disabled provider is enabled by this release.

The scheduler persists last attempt, last success, failure class, consecutive
failures, next attempt and next action per adapter. Transient failures retry
with bounded backoff rather than waiting for a weekly publication cadence.
Authentication, endpoint and entitlement errors are distinguished from network
failures and do not cause rapid retries. Successful empty responses remain empty;
they do not become trading evidence. Failed reads do not advance last success.

`qadam_source_collection_coverage.json` accounts for every catalog entry. The
existing source capability registry also includes collection status alongside
provider freshness and evidence eligibility. It explicitly identifies missing
adapters, disabled sources, derived aliases and external collectors. HTTP status
codes are retained without writing credential-bearing exception URLs.

The BIS collector now uses a bounded US policy-rate series query and parses SDMX
observations. UN Comtrade uses the complete commodity API route, its configured
subscription header, and bounded US import queries for crude oil, integrated
circuits and arms over the last two completed years. Numeric values and reference
periods are retained; neither reference periods nor API response generation times
are misrepresented as historical publication timestamps. These are contextual
observations, not automatically tradeable events.

AISStream now uses its WebSocket subscription protocol, not an HTTP GET against
a streaming endpoint. Captures are limited to 25 position reports in a bounded
time window around Hormuz and Suez. Control frames are excluded from evidence;
credentials are sent only in the subscription and are not archived. This is
sampled regional shipping context, not complete global vessel coverage.

Provider contracts: [BIS API](https://stats.bis.org/api-doc/v1/),
[UN Comtrade API](https://uncomtrade.org/docs/un-comtrade-api/) and
[AISStream protocol](https://aisstream.io/documentation).

The existing source inbox, correction receipts, bounded ingestion queue and
provider archives retain data for both research and strategy development. A
collection success does not imply an independent directional signal, and a
healthy service process does not imply every external provider is available.

## Acceptance

- Refreshing observations preserves strategy versions but not signal identities.
- Changing rules or the source universe creates a new version.
- Complete micro-paper signals can reach the compiler without historical validation.
- Bad mappings, unresolved direction, controls and authority defects still block.
- The validated lane cannot use missing or corrupt historical evidence.
- Failed slow-cadence sources retry; authentication and rate limits back off.
- Every source has a truthful collection disposition, including unavailable ones.
- Source and strategy artifacts are owned by their existing runtime services.
- Verify real provider results and the running committed build before claiming deployment.

External credentials, entitlements, unsupported provider contracts and elapsed
market observations cannot be replaced by code or a green health label.

## Release Verification Snapshot

On 24 September 2026 the guarded, non-submitting integration pass completed
source ingestion, pattern scoring, strategy research and canonical tradeability
with four successful service receipts and no failures. A subsequent scoped
provider capture returned two BIS observations and six UN Comtrade records;
AISStream confirmed its subscription but returned no positions in that capture.
Ten research goals were created by the scoped refresh. These are collection
receipts, not ten profitable signals or trade submissions.

The catalog coverage snapshot at 13:53 UTC reported 22 successfully polled
entries, including empty and internal-derived responses. Three aliases and
three externally owned collectors must not be counted as additional successful
API reads. The two deliberately disabled integrations and three unselected
provider candidates were retained as such. Remaining access, endpoint, local
bridge and rate-limit failures stay visible with their recovery schedules.
This snapshot does not certify every source as operational or evidence-ready.
