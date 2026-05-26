# Qadam Dashboard D11A Information Diet Audit

Date: 2026-05-26

## Scope

D11A audits the current `/dashboard/` information load before any UI deletion or
layout rewrite. The goal is to decide what the dashboard should keep, collapse,
move, or remove so D11B and later stages can simplify the interface without
losing operational truth.

No runtime authority changes are allowed in D11A. This stage is documentation
and control only.

## Goal

The simplified dashboard should have fewer primary views, fewer sub-sections,
fewer cards, and less repeated safety/status text. It should explain only what a
founding Fund Manager needs to know first, while preserving detailed audit data
inside Operations.

Target primary views after D11:

1. Overview
2. Trades
3. Evidence
4. Reasoning
5. Operations

The current `Executive / Terminal` density switcher is obsolete because the
segmented view model already controls density by routing users into the right
view.

## Current Static Shell Inventory

| Current surface | Current view | D11 fate | Destination | Reason |
| --- | --- | --- | --- | --- |
| Hero and mode stack | Global | Collapse into summary | Global safety strip | Keeps account/mode/freshness, removes density switcher and phase-first copy. |
| `Executive / Terminal` density toggle | Global | Delete from UI | None | Obsolete and adds a false choice. |
| Status/Safety hover | Global | Keep only as short tooltip | Global safety strip | Must become a compact explainer, not onboarding text. |
| `mission-control` | Overview | Keep primary | Overview | Becomes the only first-read operating summary. |
| Overview status rail | Overview | Collapse into summary | Overview current state | Keep mode, paper account, demo window, action needed. |
| Overview hero metrics | Overview | Collapse into summary | Overview current state | Keep only the single operating sentence plus 3 to 5 facts. |
| Overview lifecycle strip | Overview | Keep primary | Overview trade funnel mini-map | This is the clearest current user-facing concept. |
| Overview system panel | Overview | Collapse into summary | Overview mini system map | Keep compact node flow only. |
| Overview next links | Overview | Keep primary | Overview | Keep as next-action routing. |
| `strategy-manifestation` | Reasoning | Collapse into summary | Reasoning strategy research | Move phase/audit detail to Operations. |
| `system-map` | Operations | Keep secondary | Operations full system map | Keep expanded map, but never first-screen. |
| Fund model cards | Operations/System map | Collapse into summary | Overview mini-map and Operations full map | Useful metaphor, currently duplicated with system map. |
| Snapshot banner | Operations/System map | Move to Operations | Operations runtime health | Snapshot source is technical context. |
| Operations workspace inside system map | Operations | Keep secondary | Operations | Preserve diagnostics, but remove duplicate safety rail. |
| Operations role spine | Operations | Collapse into full map | Operations full map | Role cards duplicate fund model cards and map nodes. |
| Operations full map | Operations | Keep secondary | Operations full map | Audit-useful and matches user guide intent. |
| Static six-lane system flow diagram | Operations | Collapse into full map | Operations full map | Use one shared map model, not static plus dynamic maps. |
| `review-sequence` | Overview | Delete from UI | None | The primary nav already explains the review sequence. |
| `watching` | Sources | Keep primary, rename | Evidence | Source health becomes Evidence, grouped by source type. |
| Sources workspace head | Sources | Collapse into summary | Evidence summary | Keep quorum/freshness, remove workspace jargon. |
| Source reliability grid | Sources | Keep primary | Evidence | Keep grouped health states. |
| Supplemental source cards | Sources | Collapse into details | Evidence details | Keep Yahoo/Preference context, not primary cards. |
| Source-to-setup links | Sources | Keep primary only when active | Evidence | Useful only when there is an active setup/candidate. |
| Pipeline group cards | Sources | Collapse into grouped rows | Evidence | Use groups instead of large card grids. |
| Detailed watched-source registry | Sources | Move to Operations | Operations source diagnostics | Too dense for primary Evidence view. |
| `cognition` | Reasoning | Keep primary, simplify | Reasoning | Becomes the single place for thesis, evidence, blockers, and quant state. |
| Reasoning workspace head | Reasoning | Keep primary | Reasoning | Good top-level framing. |
| Reasoning boundary card | Reasoning | Collapse into tooltip/global safety | Reasoning tooltip | Repeats safety state already shown elsewhere. |
| Reasoning lane grid | Reasoning | Collapse into summary | Reasoning | Keep fewer lane summaries. |
| Legacy cognition fallback card | Reasoning | Delete from UI | None | Obsolete after dynamic Reasoning workspace. |
| `worldview` | Reasoning | Delete as separate panel | Reasoning prior section | Already says it is merged into Reasoning. |
| Private Edge summary strip | Reasoning | Collapse into tooltip | Reasoning prior section | Prior/evidence boundary belongs inside Reasoning. |
| `forbidden` | Operations | Collapse into global safety strip | Global safety plus Operations counters | Hard blocks should not be a standalone user view. |
| Forbidden action list | Operations | Move to Operations | Operations safety counters | Keep for audit, not as a card wall. |
| `communications` | Governance | Move to Operations | Operations communications/governance | Notify-only status is audit/governance detail. |
| Telegram summary strip | Governance | Collapse into Operations row | Operations communications | Keep delivery failures only if actionable. |
| `trade-layer` | Trades | Keep primary | Trades | Core operating view. |
| Trade route strip | Trades | Keep primary | Trades funnel | This should become the single canonical trade funnel. |
| Trades workspace | Trades | Keep primary, simplify | Trades | Keep lifecycle, candidates, blockers, paper account. |
| Phase 5 drill section | Trades | Move to Operations | Operations phase/audit detail | Implementation proof, not daily trade state. |
| Phase 5 certification section | Trades | Move to Operations | Operations phase/audit detail | Audit-only. |
| Phase 5 to Phase 6 handoff section | Trades | Move to Operations | Operations phase/audit detail | Audit-only. |
| Phase 6 learning loop section | Trades | Move to Operations | Operations learning diagnostics | Not primary trade funnel. |
| Phase 6 certification section | Trades | Move to Operations | Operations phase/audit detail | Audit-only. |
| Phase 7 demo proof section | Trades | Collapse into summary | Trades and Operations | Keep proof state in Trades; move counters/audit to Operations. |
| Signal Review UI section | Trades | Collapse into trade blockers | Trades blockers | Keep only active review/action state. |
| Risk Agent policy router | Trades | Collapse into trade blockers | Trades blockers | Keep reason, not every counter. |
| Execution Policy and kill switches | Trades | Collapse into trade blockers | Trades blockers and Operations safety | Avoid separate implementation section. |
| Disabled staged paper-order contract | Trades | Collapse into trade blockers | Trades blockers | Keep if it explains why no paper order. |
| Read-only broker reconciliation | Trades | Move to Operations unless active | Operations broker diagnostics | Primary user only needs whether broker submit is ready. |
| Dry-run paper-submit receipt | Trades | Move to Operations unless active | Operations broker diagnostics | Audit-only until there is a submitted paper order. |
| TradingView alert source | Trades | Move to Evidence | Evidence market/technical inputs | It is an evidence source, not a trade section. |
| Trade state ladder | Trades | Delete from UI | None | Duplicates the lifecycle funnel. |
| Observed signals | Trades | Keep primary if non-empty | Trades funnel detail | Hide empty walls. |
| Candidates | Trades | Keep primary if non-empty | Trades funnel detail | Candidate is central when present. |
| Blocked trades | Trades | Keep primary if non-empty | Trades blockers | Show only meaningful blockers. |
| Paper lifecycle states | Trades | Keep primary if non-empty | Trades paper state | Collapse into paper account/lifecycle view. |
| `money` | Performance | Merge | Trades paper account | Remove Performance as primary nav view. |
| Performance workspace | Performance | Merge | Trades paper account, Operations audit | Paper outcome belongs with Trades; proof/audit details in Operations. |
| Paper account live board | Performance | Keep primary | Trades paper account | Important, but should appear once. |
| Paper equity chart | Performance | Keep primary | Trades paper account | Useful once there is live history. |
| Money panel brief | Performance | Delete from UI | None | Duplicates paper account summary. |
| Paper mirror state | Performance | Move to Operations | Operations broker/account diagnostics | Technical mirror details. |
| Maturity benchmark | Performance | Collapse into summary | Trades paper account | Keep only proof/maturity headline. |
| Open positions | Performance | Keep primary if non-empty | Trades paper account | Useful in Trades. |
| Closed trades | Performance | Keep primary if non-empty | Trades paper account | Useful in Trades. |
| Mirrored paper orders | Performance | Keep primary if non-empty | Trades paper account | Useful in Trades. |
| Equity snapshot log | Performance | Move to Operations | Operations account diagnostics | Too granular for primary. |
| `process-console` | Operations | Keep secondary | Operations runtime health | Useful but audit-only. |
| Process panel brief | Operations | Delete from UI | None | Duplicates runtime event list. |
| Console feed | Operations | Keep secondary | Operations runtime health | Keep concise event list. |
| `governance` | Governance | Move and collapse | Operations governance | Remove Governance as primary view. |
| Governance workspace | Governance | Keep secondary | Operations governance | Comments/approvals are operational controls unless active. |
| Governance comment targets | Governance | Keep secondary | Operations governance | Keep form, but not first-level nav. |
| Governance form and comment list | Governance | Keep secondary | Operations governance | Keep for founding-manager feedback. |

## Dynamic Renderer Inventory

| Renderer/model | Current issue | D11 fate |
| --- | --- | --- |
| `buildOverviewModel` / `renderOverviewFirstScreen` | Strong foundation but still repeats paper account, safety, proof, and lifecycle facts. | Keep and simplify to four Overview panels. |
| `buildTradesModel` / `renderTradeLifecycleWorkspace` | Good lifecycle model, then followed by too many implementation sections. | Keep funnel and records; collapse downstream module sections. |
| `buildSourcesModel` / `renderSourcesWorkspace` | Too many source cards and detailed source rows. | Rename to Evidence and group by evidence class. |
| `buildReasoningModel` / `renderReasoningWorkspace` | Correctly separates prior/evidence, but still too verbose. | Keep as Reasoning backbone; remove old Cognition/Private Edge duplication. |
| `buildPerformanceModel` / `renderPerformanceWorkspace` | Duplicates Trades and Money. | Merge into Trades and Operations. |
| `buildSystemConnectivityModel` | Correct shared system map model. | Keep as source for Overview mini-map and Operations full map only. |
| `buildOperationsModel` / `renderOperationsWorkspace` | Right destination for detail, but currently duplicates safety/source/map state. | Keep, but restructure as the only audit/diagnostic location. |
| `buildGovernanceModel` / `renderGovernanceWorkspace` | Useful but not worth a primary nav view. | Move under Operations governance. |
| `renderFundModel` | Duplicates system map role cards. | Collapse into Overview/Operations copy. |
| `renderFlowMap` | Renders Operations workspace into the System Map shell. | Keep one Operations full map, remove static duplicate map. |
| `renderWatching` | Renders source summaries plus detailed registry. | Evidence should show grouped health first; registry moves to Operations. |
| `renderCognition` | Renders new Reasoning plus legacy cognition stacks. | Remove legacy stacks after Reasoning covers them. |
| `renderWorldview` | Explicitly says merged into Reasoning but still renders a panel. | Delete separate panel. |
| `renderForbidden` | Repeats global hard safety. | Replace with global safety strip and Operations counters. |
| `renderCommunications` | Separate panel for notify-only rail. | Move into Operations governance/communications. |
| `renderTrades` | Contains lifecycle plus many phase/audit sections. | Keep lifecycle/candidates/blockers; move phase modules to Operations. |
| `renderCapital` | Renders Performance plus paper account detail. | Move account summary/chart into Trades; diagnostics into Operations. |
| `renderFundManagerNotes` | Useful governance form/list. | Move into Operations governance. |
| `renderConsole` | Useful event feed. | Keep in Operations runtime health. |

## Duplicate Concept Audit

| Concept repeated today | Current repeated locations | D11 owner | D11 rule |
| --- | --- | --- | --- |
| Paper/demo mode | Hero, Overview, Operations safety rail, Money, Performance, Forbidden, tooltips | Global safety strip | Show once globally, reference only when directly relevant. |
| Live capital disabled | Hero, Overview, System Map, Forbidden, Trades, Performance, Money, Governance, Operations | Global safety strip and Operations counters | One global badge, raw counters in Operations only. |
| Broker writes blocked / no UI-to-broker path | Hero tooltip, Operations, Forbidden, Trades, Performance, Money, Governance | Global safety strip and Operations counters | One global badge, detailed counters in Operations. |
| Read-only dashboard | Hero tooltip, Overview, Operations, Reasoning, Trades, Performance, Governance, Process Console | Global safety strip | Stop repeating full boundary paragraphs in every panel. |
| Q-CTRL / quantum state | Reasoning quant annotation, Operations, PaperOps status, Overview safety/action | Reasoning summary plus Operations diagnostics | Plain state in Reasoning; provider counters in Operations. |
| Phase 5 / Phase 6 / Phase 7 proof machinery | Trades, Performance, Operations, Governance, Overview | Trades summary plus Operations audit | User sees proof state once; phase detail goes to Operations. |
| Paper account balance/P&L | Overview, Performance, Money, Trades lifecycle records | Trades paper account plus Overview one-line summary | Full account only in Trades. |
| Source health | Overview, Sources, Operations feed clusters, System Map, status banner | Evidence plus Overview one-line summary | Detailed registry moves to Operations. |
| System map | Overview mini-map, System Map static lanes, Operations workspace, fund model cards | Overview mini-map and Operations full map | Only two map placements. |
| Reasoning and private priors | Reasoning, Cognition legacy stacks, Private Edge | Reasoning | Private Edge is a subsection, not a panel. |
| Governance/comms | Governance panel, Communications panel, Signal Review governance actions | Operations governance | Surface in Overview only when action is needed. |
| `blocked` state | Almost every panel | Status language system | Split into safety block, missing setup, waiting for evidence, and fault. |

## Current Primary View Audit

| Current view | D11 fate | Reason |
| --- | --- | --- |
| Overview | Keep | Must become the simple first screen. |
| Trades | Keep | Core paper-trade lifecycle workspace. |
| Sources | Rename to Evidence | Sources are useful only as evidence quality. |
| Reasoning | Keep | Core explanation of why Qadam cares. |
| Performance | Remove as primary view | Merge paper account/proof performance into Trades and Operations. |
| Operations | Keep | Only place for machinery, raw counters, phase codes, audit logs. |
| Governance | Remove as primary view | Move comments, approvals, Telegram, and review packs into Operations unless active action is needed. |

## D11 Simplification Targets

| Area | Current problem | D11 target |
| --- | --- | --- |
| Primary nav | 7 views plus obsolete density toggle | 5 views, no density toggle. |
| Overview | Multiple cards plus repeated safety and performance facts | Max 4 major panels. |
| Trades | Lifecycle plus many phase/audit sections | Funnel, candidates, blockers, paper account. |
| Evidence | Source card grid and detailed registry | Evidence groups with expandable details. |
| Reasoning | New workspace plus old cognition/private-edge stacks | One narrative: thesis, evidence, blockers, research, quant. |
| Operations | Useful but mixed with duplicated system map/safety/source content | One audit destination for map, runtime, safety counters, phase details, governance. |
| Tooltips | Long explainers carry onboarding work | Three short fields: What this is, Why it matters, What to watch. |

## D11B Handoff Decisions

D11B should implement the new navigation contract:

- Remove `Executive / Terminal`.
- Replace current views with `Overview`, `Trades`, `Evidence`, `Reasoning`,
  and `Operations`.
- Redirect legacy hashes:
  - `#sources` to `#evidence`
  - `#performance` and `#money` to `#trades`
  - `#governance` and `#communications` to `#operations`
  - `#system-map`, `#process-console`, and `#forbidden` to `#operations`
  - `#worldview` and `#strategy-manifestation` to `#reasoning`
- Preserve deep links where useful by scrolling to the related section after
  the new view activates.

## Non-Negotiable Retention

The simplification must not hide or weaken:

- paper/demo mode
- live capital disabled state
- broker write and Alpaca POST counters
- Q-CTRL provider-call state
- source freshness and degradation
- candidate-is-not-order boundary
- paper-order submitted/open/closed/postmortem distinction
- proof credit and maturity separation
- Event Log/runtime auditability
- founding-manager governance notes

The rule is relocation, not deletion, for audit-critical data.

## D11A Acceptance

- Every current static dashboard section has a D11 fate.
- Every major dynamic renderer/model has a D11 fate.
- Duplicate concepts have a single future owner.
- The obsolete density switcher is explicitly marked for deletion.
- The next stage is D11B - New Navigation Contract.
