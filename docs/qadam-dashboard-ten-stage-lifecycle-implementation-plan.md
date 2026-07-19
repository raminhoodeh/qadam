# Qadam Dashboard 10-Stage Lifecycle Implementation Plan

Status: implemented, locally certified, deployed, and production-verified on 2026-07-12

Scope: the public Qadam dashboard and the dashboard-safe runtime contracts that
explain how each dashboard module participates in Qadam's end-to-end operating
lifecycle.

This plan preserves the current 13 dashboard routes, sidebar structure, paper-only
boundaries, and read-only public interface. It adds one consistent 10-stage
lifecycle timeline to every module and removes system-level explanations that
would become repetitive after that timeline exists.

## 1. Product Outcome

Every dashboard page must answer four questions without requiring the reader to
understand Qadam's internal names:

1. Where does this page sit in Qadam's operating lifecycle?
2. What enters this stage, and what does it produce?
3. What is Qadam doing at this stage now?
4. Where does an item go next if it advances?

The page-level answer must be visible before the detailed module content. A new
reader should be able to identify the page's role, previous handoff, and next
handoff in less than 10 seconds.

The canonical lifecycle is:

`Observe -> Qualify Evidence -> Discover Patterns -> Form Strategies -> Validate Edge -> Filter Tradeability -> Govern Decision -> Execute and Monitor -> Learn -> Improve and Re-enter`

## 2. Non-Negotiable Constraints

- Preserve all 13 current routes and their sidebar order.
- Do not merge or remove a route as part of this work.
- Do not turn the 10-stage lifecycle into a new navigation hierarchy.
- Do not imply that the entire system has one global current stage. Different
  patterns, hypotheses, orders, and lessons can occupy different stages at the
  same time.
- Distinguish a page's structural relationship to a stage from the aggregate
  runtime state of work at that stage.
- Keep the dashboard read-only. The lifecycle component must not create research
  goals, candidates, approvals, orders, broker writes, live-capital authority, or
  proof credit.
- Preserve paper-only execution and the guarded PaperOps route.
- Keep internal names subordinate to plain-English explanations.
- Keep every status traceable to a runtime artifact. The browser must not infer
  operational health from missing data.
- If runtime state is stale or unavailable, show that honestly while retaining
  the static explanation of where the module belongs.
- Do not remove unique module evidence merely to make the interface shorter.
  Remove repeated orientation copy, repeated flow maps, and duplicate handoff
  panels only.

## 3. Canonical 10-Stage Lifecycle

| Stage | Public Label | Key Question | Core Sub-Stages | Primary Output |
| --- | --- | --- | --- | --- |
| 1 | Observe the World | What changed in the world or the markets? | Ingest sources; check freshness; classify trust; record observations | Fresh, provenance-linked observations |
| 2 | Qualify the Evidence | Is the information reliable, timely, and relevant to a watched market? | Normalize evidence; align timestamps; map sources to instruments; test quorum and paperability | Qualified source-price evidence packet |
| 3 | Discover Patterns | Is there a repeatable relationship worth investigating? | Engineer features; scan linear relationships; retrieve analogs; review nonlinear interactions; rank or reject findings | Ranked research pattern |
| 4 | Form Strategy Hypotheses | How could this pattern become a disciplined trading approach? | Map to an existing strategy; propose a new strategy family when needed; define lineage, instruments, invalidation, and risk concept | Research-backed strategy hypothesis |
| 5 | Validate the Edge | Did the idea work repeatedly after costs, risk, and out-of-sample checks? | Historical backtest; walk-forward validation; shadow observation; estimate expectancy and drawdown; classify evidence | Validated, rejected, or still-observing edge record |
| 6 | Filter Tradeability | Is the otherwise interesting idea practical to trade now? | Build Akber context; test catalyst and confirmation; apply practical vetoes; assess timing, liquidity, risk/reward, and invalidation | Akber pass, hold, or veto with explanation |
| 7 | Govern the Decision | Is this setup allowed into the guarded paper route? | Apply risk budget; check exposure, drawdown, source quorum, duplicates, idempotency, Q-CTRL state, and route safety | One Router state and, only when clean, a PaperOps handoff |
| 8 | Execute and Monitor | What happened to the paper order and position? | Submit through guarded Alpaca Paper; reconcile broker state; track accepted, filled, open, closed, or cancelled lifecycle | Unambiguous paper-order and position state |
| 9 | Learn From the Outcome | What did the trade, hold, veto, or research event teach Qadam? | Attribute outcome; write postmortem; test proof eligibility; separate market result from system defect | Supported lesson with complete lineage |
| 10 | Improve and Re-enter | Should Qadam change future behavior because of that lesson? | Propose change; test historically; observe forward; review; apply a versioned change; return to observation | Approved versioned improvement or rejected proposal |

Stage 5 and Stage 10 must remain visibly distinct:

- Stage 5 evaluates whether a strategy has a repeatable, tradeable edge.
- Stage 10 evaluates whether Qadam should change future behavior because of
  accumulated evidence and outcomes.

## 4. Page Relationship Model

Every route receives one of four relationship labels:

- `Primary stage`: this page owns the main public explanation and evidence for
  that stage.
- `Supports stage`: this page contributes evidence to a stage but does not own
  the final decision.
- `Outcome mirror`: this page shows consequences produced by a stage rather than
  performing that stage.
- `Cross-cutting`: this page spans or monitors multiple stages and must not be
  assigned a false primary stage.

The visual component must show both dimensions separately:

1. `Page relationship`: stable product architecture, such as "Primary stage 3."
2. `Runtime state`: fresh operational state, such as "2 findings under review" or
   "waiting for forward evidence."

Do not use `aria-current` or "you are here" language for a runtime item. It may be
used only to indicate the stage or stages explained by the current page.

## 5. Route-to-Stage Map

| Route | Page | Primary Relationship | Supporting Relationship | Page-Specific Meaning |
| --- | --- | --- | --- | --- |
| `system/team` | Qadam Team | Cross-cutting across stages 1-10 | None | Shows which member of the hybrid team contributes at each lifecycle stage |
| `fund/portfolio` | Portfolio | Stage 8 outcome mirror | Supports stage 9 | Shows the current financial consequence of guarded paper execution and the evidence later reviewed |
| `fund/timeline` | Timeline | Stage 8 chronology | Supports stage 9 | Shows the ordered history of paper orders, fills, closes, holds, and learning handoffs |
| `observe/sources` | Data Sources | Primary stage 1 | Supports stage 2 | Shows what Qadam watches and whether each source is fresh, trusted, and usable |
| `observe/universe` | Trading Universe | Primary stage 2 | Supports stage 1 | Shows which markets and instruments evidence may be mapped to and whether they are paperable |
| `patterns/findings` | Pattern Discovery | Primary stage 3 | Supports stage 5 | Shows ranked source-price relationships and what evidence each still needs |
| `patterns/nonlinear` | Quantum Review | Primary stage 3 specialist review | Supports stage 5 | Shows whether nonlinear or quantum-assisted review adds useful evidence beyond the classical baseline |
| `decide/strategies` | Trading Strategies | Primary stages 4 and 5 | Supports stage 6 | Shows how patterns become strategy hypotheses and how those hypotheses earn or fail edge evidence |
| `decide/decision` | Decision Room | Primary stages 6 and 7 | Supports stage 8 | Shows Akber's tradeability verdict, portfolio governance, Router state, and PaperOps boundary |
| `trade/orders` | Order Monitor | Primary stage 8 | Supports stage 9 | Shows the guarded paper-order lifecycle and the next lifecycle action |
| `learn/outcomes` | Results and Lessons | Primary stage 9 | Supports stage 10 | Shows what happened, why it happened, and which lessons are supported by evidence |
| `learn/improvements` | Tests and Improvements | Primary stage 10 | Returns to stage 1 | Shows proposed, tested, reviewed, applied, and rejected changes before the next observation cycle |
| `system/overview` | System Overview | Cross-cutting health view across stages 1-10 | None | Shows freshness, blockers, throughput, and defects for every lifecycle stage |

This map is canonical. The frontend must consume it from a dashboard-safe
contract rather than maintain an independent hardcoded interpretation.

## 6. Shared Lifecycle Component

Add one shared component to every visible module. The preferred page order is:

1. Existing module title and concise purpose.
2. Module relationship sentence.
3. The 10-stage lifecycle timeline.
4. A concise runtime summary for the stage or stages relevant to the page.
5. The module's unique evidence and controls.

Example relationship block:

```text
PRIMARY STAGE 3 OF 10
Discover Patterns
This page shows relationships Qadam has detected. It also supplies evidence to
Stage 5, where the possible edge is tested.
```

The timeline must contain exactly 10 ordered nodes. Each node shows:

- Stage number.
- Short stage label.
- Page relationship style: primary, supporting, outcome mirror, cross-cutting,
  or unrelated.
- Aggregate runtime state, when fresh state is available.
- A tooltip or tap disclosure.
- A link to the stage's primary dashboard destination when one exists.

The component must not present the lifecycle as a progress bar that fills once.
Qadam is a continuous multi-item system. Use a lifecycle rail or connected map,
not completion percentages.

### 6.1 Visual State Vocabulary

Use separate visual channels for architecture and runtime:

- Filled crimson border or marker: primary stage explained by this page.
- Crimson outline: supporting stage for this page.
- Neutral outcome marker: outcome mirror.
- Continuous top rule or multi-stage brace: cross-cutting page.
- Small status dot and plain text: runtime state.
- Muted node: structurally unrelated to the page, but still navigable.

Do not use red automatically to mean failure. Qadam's crimson is a navigation and
identity color. Operational failure states require an icon, a label, and a
plain-English reason rather than color alone.

### 6.2 Runtime State Vocabulary

The backend may expose only these public-safe aggregate states:

- `active`: fresh work exists at this stage.
- `waiting_for_evidence`: work exists but cannot advance yet.
- `blocked`: a named safety or evidence requirement prevents advancement.
- `idle`: no current item requires this stage.
- `degraded`: the stage can be described, but one or more required components are
  not healthy.
- `unavailable`: current state cannot be established from fresh artifacts.

Every state must include `generated_at`, `freshness`, `summary`, and optional
`blockers`. The browser must not convert a missing record into `idle`.

## 7. Tooltip And Disclosure Specification

Every stage node must have a tooltip on pointer hover and keyboard focus. Touch
devices must receive the same information through a tap disclosure. No content
may be hover-only.

Each tooltip contains:

1. Stage number and public label.
2. Plain-English description of what Qadam does here.
3. The key question this stage answers.
4. Two to five sub-stages.
5. Inputs received from the previous stage.
6. Output handed to the next stage.
7. Team members involved.
8. Current aggregate state, freshness, and blocker when available.
9. Why the current module is primary, supporting, an outcome mirror, or
   cross-cutting for this stage.
10. A "View this stage" link when a primary destination exists.

Keep the initially visible tooltip concise. Detailed inputs, outputs, and actors
may sit behind "More detail" inside the disclosure, but must remain keyboard and
touch accessible.

### 7.1 Interaction Requirements

- Use an anchor when the entire stage node navigates to a route.
- Use a button only when the node opens information without navigation.
- Support `Tab`, `Shift+Tab`, `Enter`, `Space`, and `Escape`.
- Keep only one tooltip or disclosure open at a time.
- Return focus to the stage node when a disclosure closes.
- Use `aria-describedby` for transient tooltip content.
- Use `aria-expanded` and `aria-controls` for persistent disclosures.
- Keep tooltips inside the viewport and prevent clipping by cards or the sidebar.
- Do not make tooltip text the only place where the current module's stage is
  stated. The relationship sentence must remain visible.

## 8. Responsive Layout

### Desktop

- Prefer a 10-node horizontal lifecycle rail when the content width supports it.
- At narrower desktop widths, switch to a connected 5-by-2 grid rather than
  shrinking labels below readable size.
- Keep short labels visible without interaction.

### Tablet

- Use a 5-by-2 or 2-by-5 connected layout.
- Keep the current page's primary nodes in the first visible row where practical.
- Keep tooltip positioning viewport-safe.

### Mobile

- Show a persistent summary such as `Stage 3 of 10: Discover Patterns` above the
  rail.
- Use a horizontally scrollable rail with snap points or a compact expandable
  lifecycle map.
- Automatically bring the primary stage into view without stealing focus.
- Preserve all 10 stages and do not replace the rail with only previous/next
  buttons.
- Prevent horizontal page overflow.

### Motion And Print

- Respect `prefers-reduced-motion`.
- Use motion only to clarify opening, focus, and stage transitions.
- In print or no-script fallbacks, show all stage names and the page relationship
  without requiring a tooltip.

## 9. Content Ownership And De-Duplication Rules

The shared lifecycle component becomes the single owner of:

- The overall 10-stage explanation.
- Where the current module sits.
- Generic previous-stage and next-stage handoffs.
- Stage-level questions, inputs, outputs, actors, and sub-stages.
- Generic "how Qadam works" prose.
- Navigation between lifecycle destinations.

Each module remains the owner of:

- Its unique records, evidence, metrics, and timestamps.
- Its local sub-lifecycle, such as Akber's filters or the paper-order lifecycle.
- Per-record next actions and blockers.
- Module-specific safety and authority boundaries.
- Technical diagnostics needed to understand degraded state.
- Detailed qualitative explanations specific to the page.

The implementation must remove the old global
`renderQsaseJourneyNavigation(...)` component after the 10-stage timeline is
available on every route. The dashboard footer remains.

## 10. Per-Module Consolidation Plan

### 10.1 Qadam Team

Keep:

- Expandable Python COO, Local Research Analyst, Frontier Strategy Lead, and Head
  of Quant cards.
- Qualitative descriptions, current focus, responsibilities, and boundaries.
- The explanation of Qadam's self-aware use of cognition, latency, and data
  quality.

Remove or merge:

- Any separate whole-system flow map that repeats all lifecycle stages.
- Repeated handoff prose between team members when the same actor handoff is
  available in stage tooltips.

New treatment:

- Label the page `Cross-cutting across all 10 stages`.
- Each stage tooltip lists the participating team members.
- A role card may show small stage chips to indicate responsibility, but must not
  repeat the full lifecycle description.

### 10.2 Portfolio

Keep:

- Portfolio value line graph, cash, exposure, realized and unrealized P&L,
  drawdown, current holdings, strategy lineage, and invalidation.

Remove or merge:

- Generic prose that restates the complete intelligence-to-trade flow.
- Repeated explanations of what the rest of the dashboard contains.

New treatment:

- Label the page `Stage 8 outcome mirror` and `Supports stage 9`.
- Explain that portfolio values are consequences of guarded paper execution, not
  evidence that upstream research is currently healthy.

### 10.3 Timeline

Keep:

- Full trading chronology, order and fill states, holds, closes, P&L, lineage,
  postmortem state, and paper proof ledger state.

Remove or merge:

- Generic previous/next page navigation.
- Repeated "what happens next" prose when the record already has a next action
  and the lifecycle rail explains the stage handoff.

New treatment:

- Label the page `Stage 8 chronology` and `Supports stage 9`.
- Keep per-record next action because it is item-specific rather than generic.

### 10.4 Data Sources

Keep:

- Expandable source categories and granular APIs.
- Freshness, trust, outage, provenance, and source-quorum contribution.
- Read-only source authority boundary.

Remove or merge:

- A second complete end-to-end Qadam flow.
- Any source-to-market diagram that duplicates the same full diagram on Trading
  Universe.

New treatment:

- Label the page `Primary stage 1` and `Supports stage 2`.
- Retain one compact local handoff: `Fresh source observation -> qualified
  evidence`, with a link to Trading Universe.

### 10.5 Trading Universe

Keep:

- Market categories, individual instruments, core and secondary instruments,
  paperability, liquidity context, availability, and strategy mappings.

Remove or merge:

- A duplicate full source-network map.
- Generic strategy and execution explanations already covered by later stages.

New treatment:

- Label the page `Primary stage 2` and `Supports stage 1`.
- Show the local handoff from qualified source evidence to an affected market or
  instrument.
- If a shared source-to-market component remains, render a source perspective on
  Data Sources and a market perspective here rather than identical copies.

### 10.6 Pattern Discovery

Keep:

- Qualitative findings summary, ranked pattern cards, research score, source-to-
  price relationship, evidence, affected market, confirmation, blocker, and next
  action.
- Per-pattern lifecycle state and rejected findings.

Remove or merge:

- Any page-level generic pipeline that repeats the 10 stages.
- A generic "where this advances" panel if it contains no pattern-specific state.

New treatment:

- Label the page `Primary stage 3` and `Supports stage 5`.
- Every finding retains a specific destination such as `Needs more history`,
  `Sent to Quantum Review`, `Sent to strategy formation`, or `Rejected`.

### 10.7 Quantum Review

Keep:

- Classical baseline, nonlinear relationship, quantum backend or classical
  fallback label, incremental usefulness, ambiguity, verdict, and evidence gap.

Remove or merge:

- Generic mission-control prose about where quantum sits in Qadam.
- Repeated definitions of all surrounding stages.

New treatment:

- Label the page `Stage 3 specialist review` and `Supports stage 5`.
- Explain that Quantum Review tests whether nonlinear analysis adds useful
  evidence; it does not approve a trade.

### 10.8 Trading Strategies

Keep:

- Existing and emerging strategy families, qualitative explanations, source
  inputs, core and secondary instruments, invalidation, evidence requirements,
  confidence class, and self-refinement details.

Remove or merge:

- A broad Strategy Admission Path that repeats stages 3 through 7.
- Generic Pattern Discovery and Akber descriptions already owned by their pages.

New treatment:

- Label the page `Primary stages 4 and 5` and `Supports stage 6`.
- Replace the broad path with a focused local sub-flow:
  `Pattern evidence -> strategy hypothesis -> historical validation -> forward
  shadow evidence -> edge classification`.
- Make clear that Qadam can form an emerging strategy outside the known core
  strategies, but no strategy advances without evidence.

### 10.9 Decision Room

Keep:

- Akber's local filter stages, pass/hold/veto reason, practical confirmation,
  current portfolio state, risk budget, candidate state, Router state, prior
  reviews, Q-CTRL state, and PaperOps boundary.

Remove or merge:

- The generic Decision Room introduction when it repeats stages 6 and 7.
- A separate generic decision-flow strip that restates the lifecycle timeline.

New treatment:

- Label the page `Primary stages 6 and 7` and `Supports stage 8`.
- Keep Akber's detailed local sub-flow because it explains decisions inside stage
  6 rather than duplicating the global lifecycle.
- Show one current final Router answer per setup.

### 10.10 Order Monitor

Keep:

- Guarded Alpaca Paper route state, submitted, accepted, filled, open, cancelled,
  rejected, and closed order states; broker reconciliation; stale-order policy;
  position lifecycle; and route safety.

Remove or merge:

- A separate generic Learning Handoff panel when it only says that closed records
  move to learning.
- Previous/next route navigation.

New treatment:

- Label the page `Primary stage 8` and `Supports stage 9`.
- Keep the local order sub-flow:
  `Submitted -> accepted -> filled -> open -> closed/cancelled`.
- Reduce learning handoff to an item-specific state, count, or link where useful.

### 10.11 Results And Lessons

Keep:

- Outcome and research-event records, attribution, postmortems, supported lessons,
  system-defect classification, missed opportunities, and proof eligibility.

Remove or merge:

- The current repeated six-part operating-flow overview.
- The current full eight-step learning-loop overview.
- Generic "return to observation" prose already expressed by stage 10.

New treatment:

- Label the page `Primary stage 9` and `Supports stage 10`.
- Replace both global maps with one compact local sub-flow:
  `Outcome or research event -> attribution -> supported lesson`.
- Keep a direct handoff link to Tests and Improvements.

### 10.12 Tests And Improvements

Keep:

- Improvement proposals, historical test results, forward observations, review
  state, applied versions, rejected proposals, and Stage 1 handoff state.

Remove or merge:

- The duplicated six-part operating-flow overview.
- The duplicated full eight-step learning-loop overview.

New treatment:

- Label the page `Primary stage 10` and `Returns to stage 1`.
- Keep one local sub-flow:
  `Proposed improvement -> historical test -> forward observation -> review ->
  applied version -> next Observe cycle`.
- State explicitly that proposals cannot silently mutate authority or execution
  settings.

### 10.13 System Overview

Keep:

- One infrastructure verdict, a separate expected operating-mode explanation,
  deduplicated root incidents, and public-safe evidence covering connections,
  automations, freshness, downstream flow impact, recoveries, and technical
  diagnostics.

Remove or merge:

- A separate End-to-End Operating Flow that duplicates the lifecycle rail.
- Generic route-navigation cards already handled by stage destinations.

New treatment:

- Label the page `Monitors all 10 stages`.
- Keep the shared lifecycle component unchanged as the global navigation and
  explanation layer.
- Lead with one infrastructure-health verdict and distinguish deliberate
  research or paper-trading restrictions from actual operating failures.
- Keep deduplicated root incidents visible, with their impact, evidence owner,
  and next diagnostic step.
- Place the stage-health matrix inside the collapsed `Effect on Qadam's Flow`
  disclosure so it remains available without repeating the lifecycle rail on
  the default page.
- Collapse infrastructure, scheduled-work, freshness, typed-event, and
  technical-evidence sections by default.

## 11. Canonical Runtime Contracts

Create one backend-owned lifecycle definition and one dashboard-safe aggregate.
Suggested implementation files:

- `orchestrator/qadam_end_to_end_lifecycle.py`
- `orchestrator/qadam_dashboard_lifecycle_view_model.py`
- `data/runtime/qadam_end_to_end_lifecycle.json`
- `data/runtime/qadam_dashboard_route_stage_map.json`
- `data/runtime/qadam_lifecycle_dashboard_summary.json`
- `scripts/check_qadam_end_to_end_lifecycle.py`
- `scripts/check_dashboard_ten_stage_lifecycle.js`
- `tests/test_qadam_end_to_end_lifecycle.py`

The static contract should be version controlled in code. Runtime JSON is a
generated projection, not a second source of truth.

### 11.1 Lifecycle Contract Shape

```json
{
  "contract_version": "qadam_end_to_end_lifecycle_v1",
  "generated_at": "ISO-8601",
  "stages": [
    {
      "stage_id": "discover_patterns",
      "number": 3,
      "label": "Discover Patterns",
      "short_label": "Patterns",
      "plain_english": "Qadam looks for relationships that repeat across sources and prices.",
      "key_question": "Is there a repeatable relationship worth investigating?",
      "sub_stages": [],
      "inputs": [],
      "outputs": [],
      "primary_routes": ["patterns/findings", "patterns/nonlinear"],
      "supporting_routes": ["decide/strategies"],
      "actors": [],
      "safety_boundary": "Research evidence only"
    }
  ],
  "route_contexts": {
    "patterns/findings": {
      "relationship": "primary",
      "primary_stage_ids": ["discover_patterns"],
      "supporting_stage_ids": ["validate_edge"],
      "cross_cutting": false,
      "module_relationship": "This page owns ranked pattern findings and supplies evidence to edge validation.",
      "entry_from": ["qualify_evidence"],
      "hands_off_to": ["form_strategy_hypotheses", "validate_edge"]
    }
  }
}
```

### 11.2 Runtime Aggregate Shape

```json
{
  "contract_version": "qadam_lifecycle_dashboard_summary_v1",
  "generated_at": "ISO-8601",
  "freshness": "fresh",
  "stage_states": {
    "discover_patterns": {
      "state": "active",
      "summary": "3 ranked findings are under research review.",
      "item_count": 3,
      "blockers": [],
      "source_artifacts": [],
      "source_generated_at": "ISO-8601"
    }
  },
  "authority": {
    "dashboard_read_only": true,
    "live_capital_enabled": false,
    "can_create_orders": false,
    "can_grant_proof_credit": false
  }
}
```

## 12. Runtime Aggregation By Stage

The lifecycle view model should read, normalize, and freshness-check existing
canonical artifacts rather than create new trading logic.

| Stage | Runtime Inputs |
| --- | --- |
| 1 | Source network, provider capabilities, ingestion freshness, trust, and outage artifacts |
| 2 | Evidence-native contracts, point-in-time memory, source quorum, trading-universe paperability, and missing-evidence records |
| 3 | Pattern score tape, Pattern Discovery records, rejected patterns, nonlinear review, and quantum usefulness artifacts |
| 4 | Strategy Foundry, strategy candidates, Research Goal lineage, instrument mapping, and rejection records |
| 5 | Statistical backtests, leakage checks, walk-forward results, edge registry, historical shadow, forward shadow, and evidence class |
| 6 | Akber input context, stage decisions, historical replay, ablation evidence, and pass/hold/veto results |
| 7 | Portfolio risk, Router state, duplicate exposure, idempotency, drawdown, Q-CTRL, and PaperOps handoff artifacts |
| 8 | Alpaca paper mirror, order lifecycle poller, open positions, closes, and reconciliation artifacts |
| 9 | Outcomes, postmortems, attribution ledger, missed opportunities, system defects, and proof-boundary audit |
| 10 | Improvement pipeline, historical proposal tests, forward observation, review decisions, applied versions, and Stage 1 handoff |

If any required input is missing or stale, the aggregate must return `degraded`
or `unavailable` with the named reason. It must never fabricate an active or idle
state.

## 13. Frontend Integration

Introduce a shared renderer, for example:

```javascript
renderQadamLifecycleTimeline(activeRoute, lifecycleModel)
```

Prefer integrating it through the module shell so every route receives exactly
one instance:

```javascript
renderQsaseModulePanel(moduleId, viewId, content, activeRoute, lifecycleModel)
```

The module shell should render:

- The visible module relationship block.
- The 10-stage lifecycle component.
- The existing module content.

This avoids adding 13 independent renderer calls and prevents future pages from
omitting the lifecycle.

After all routes use the shared shell:

- Delete or stop rendering `renderQsaseJourneyNavigation(...)`.
- Replace `renderQsaseLearningLoopOverview(...)` with the two local Stage 9 and
  Stage 10 sub-flows described above.
- Remove only the duplicated page-level maps identified in Section 10.
- Keep route resolution and sidebar navigation unchanged.

The dashboard view model should embed the lifecycle definition, route context,
and runtime summary under one stable key such as `end_to_end_lifecycle`.

## 14. CSS And Design-System Work

Add lifecycle-specific tokens rather than page-specific overrides:

```css
--lifecycle-primary
--lifecycle-supporting
--lifecycle-outcome
--lifecycle-cross-cutting
--lifecycle-rail
--lifecycle-status-active
--lifecycle-status-waiting
--lifecycle-status-blocked
--lifecycle-status-degraded
```

Required component classes should cover:

- Lifecycle container and relationship summary.
- Ordered stage list and connectors.
- Primary, supporting, outcome, cross-cutting, and unrelated states.
- Runtime status marker and text.
- Tooltip, disclosure, and mobile sheet.
- Focus-visible state.
- Reduced-motion state.
- Print fallback.

Do not encode meaning through color alone. Use labels and icons. Match Qadam's
existing editorial visual language rather than introducing a generic SaaS
progress-stepper.

## 15. Implementation Phases

### Phase 0: Baseline And Duplicate Inventory

1. Record all 13 routes, current route order, page headings, page-level flow maps,
   repeated copy, and navigation components.
2. Capture desktop, tablet, and mobile screenshots before changes.
3. Add a machine-readable duplicate inventory identifying which renderer owns
   each repeated flow element.
4. Freeze protected route names, aliases, and sidebar order in a regression test.
5. Record current runtime artifact freshness and missing fields.

Exit gate: every route and duplicated flow element has an explicit keep, merge,
replace, or remove decision.

### Phase 1: Canonical Lifecycle Contract

1. Implement the 10 ordered stages and stable IDs.
2. Define public labels, questions, sub-stages, inputs, outputs, actors, safety
   boundaries, and primary routes.
3. Implement the canonical route-to-stage map for all 13 routes.
4. Add schema and semantic validation.
5. Fail if a stage number, ID, or route mapping is missing or duplicated.

Exit gate: one validated contract defines the lifecycle and every current route
has a relationship.

### Phase 2: Runtime Stage Aggregation

1. Build read-only adapters for the canonical artifacts listed in Section 12.
2. Add per-stage state, item count, freshness, blockers, and provenance.
3. Distinguish missing, stale, idle, and blocked states.
4. Add authority flags proving that the aggregate cannot mutate operational
   state.
5. Export the dashboard-safe lifecycle summary and embed it in the current public
   dashboard view model.

Exit gate: all 10 stages have provenance-backed status or an explicit unavailable
reason.

### Phase 3: Shared Timeline Component

1. Build the relationship summary and ordered 10-stage component.
2. Add primary, supporting, outcome, and cross-cutting treatments.
3. Add route links based on the canonical contract.
4. Integrate the component through the shared module shell.
5. Verify exactly one lifecycle component on every visible route.

Exit gate: all 13 routes render the same contract-driven component without
changing sidebar structure.

### Phase 4: Tooltips, Touch, And Accessibility

1. Implement hover/focus tooltips and tap disclosures.
2. Add keyboard support, focus return, Escape close, and one-open-at-a-time
   behavior.
3. Add viewport collision handling.
4. Add accessible names, relationships, and status text.
5. Add no-script, print, and reduced-motion fallbacks.

Exit gate: the complete stage explanation is usable by keyboard, mouse, touch,
and screen reader.

### Phase 5: Responsive And Visual Integration

1. Implement desktop, tablet, and mobile layouts.
2. Prevent page overflow and clipped tooltips.
3. Auto-reveal the page's primary stage on mobile without changing focus.
4. Align typography, spacing, rules, and state treatments with Qadam's existing
   visual language.
5. Verify long labels, blockers, and translated plain-English copy do not break
   the layout.

Exit gate: all routes pass visual checks at representative desktop, tablet, and
mobile sizes.

### Phase 6: Module-by-Module De-Duplication

1. Apply the 13 keep/remove/merge decisions in Section 10.
2. Remove the old global journey navigation.
3. Replace the two repeated learning maps with Stage 9 and Stage 10 local
   sub-flows.
4. Consolidate duplicated source-to-market explanations.
5. Simplify Pattern, Strategy, Decision, Order, and System Overview page-level
   maps without removing record-specific next actions.
6. Run anti-slop and copy repetition checks after each route group.

Exit gate: no module repeats the complete lifecycle, and every retained local
sub-flow explains unique work within a stage.

### Phase 7: Documentation And Public Language

1. Update the User Guide's route descriptions and lifecycle explanation.
2. Update the Whitepaper only where the operating lifecycle description is now
   inaccurate.
3. Add a glossary for Akber, Router, PaperOps, Q-CTRL, shadow evidence, proof
   ledger, and quantum review.
4. Ensure each internal term has a plain-English explanation at first use.
5. Keep public copy free of false authority or performance claims.

Exit gate: dashboard, User Guide, and Whitepaper describe the same lifecycle and
stage ownership.

### Phase 8: Certification And Regression

1. Run Python contract and aggregation tests.
2. Run DOM, route, accessibility, interaction, and anti-duplication checks.
3. Run dashboard anti-slop and public-safety checks.
4. Capture final visual snapshots for all routes.
5. Verify the dashboard cannot create commands, approvals, candidates, orders,
   broker writes, live-capital authority, or proof credit.
6. Write a certification artifact with pass/fail checks and explicit blockers.

Exit gate: certification passes locally with no hidden route, stale-status
misclassification, accessibility regression, or authority drift.

### Phase 9: Staged Rollout And Live Verification

1. Deploy to a preview and inspect every route.
2. Compare local and served JavaScript/CSS asset hashes.
3. Verify direct route URLs, browser back/forward, sidebar navigation, stage
   navigation, and aliases.
4. Check desktop and mobile console output for errors.
5. Run live DOM probes for one lifecycle per route and exactly 10 stages.
6. Promote only after preview checks pass.
7. Repeat served-bundle and alias verification on `qadam.trade` and
   `www.qadam.trade`.

Exit gate: the production aliases serve the certified bundle and all 13 routes
show the correct lifecycle relationship.

## 16. Test Matrix

### Python Contract Tests

- Exactly 10 stages exist.
- Stage numbers are ordered 1 through 10 with no gap or duplicate.
- Stage IDs are stable and unique.
- All 13 routes are mapped.
- Every route has a relationship type.
- Every non-cross-cutting stage has at least one primary destination.
- Stage inputs and outputs form a valid lifecycle, including Stage 10 returning
  to Stage 1.
- Runtime state includes provenance and freshness.
- Missing runtime artifacts fail closed as `degraded` or `unavailable`.
- Authority flags remain safe.

### JavaScript And DOM Tests

- Each visible module contains exactly one `[data-qadam-lifecycle]`.
- Each lifecycle contains exactly 10 ordered stage nodes.
- The active route receives the expected primary/supporting/outcome/cross-cutting
  styles.
- Every node exposes a plain-English label and tooltip/disclosure content.
- Stage links resolve to valid existing routes.
- Keyboard and Escape behavior work.
- Only one disclosure can be open.
- Mobile state reveals the relevant stage without page overflow.
- The old journey navigation is absent.
- The old global learning maps are absent after their local replacements exist.
- Hidden module panels do not expose duplicate visible lifecycle components to
  assistive technology.

### Content And Anti-Slop Tests

- No page repeats the complete 10-stage explanatory paragraph below the shared
  component.
- No pair of modules renders an identical long source-to-market or lifecycle map.
- Internal gate names have plain-English translations.
- "Current stage" is not used to describe the entire system.
- No stage description makes a performance guarantee.
- No pattern, backtest, shadow result, Akber pass, or quantum review is described
  as an order or proof credit.

### Visual Tests

- Representative 1440px, 1024px, 768px, and 390px widths.
- Long blocker copy.
- No runtime data.
- Stale runtime data.
- Multiple primary stages on Trading Strategies and Decision Room.
- Cross-cutting Team and System Overview states.
- Tooltip near all viewport edges.
- Reduced-motion and keyboard-focus states.

## 17. Acceptance Criteria

The work is complete only when all of the following are true:

1. Every one of the 13 dashboard routes shows exactly one 10-stage lifecycle.
2. Every lifecycle has exactly 10 stages in the canonical order.
3. Every module visibly states its primary, supporting, outcome, or cross-cutting
   relationship.
4. Tooltips explain what each stage does, receives, produces, and hands off.
5. Runtime status is provenance-backed, freshness-labelled, and separate from
   page relationship.
6. Qadam is not portrayed as having one global current stage.
7. Cross-cutting pages are not assigned false primary stages.
8. Previous and next lifecycle destinations are navigable without replacing the
   sidebar.
9. The old global journey navigator is removed.
10. Results and Lessons contains only its Stage 9 local learning flow.
11. Tests and Improvements contains only its Stage 10 local improvement flow.
12. Pattern, Strategy, Decision, Order, Source, Universe, Team, and System pages no
    longer repeat the complete lifecycle in page-specific prose.
13. Unique data, evidence, blockers, per-record next actions, safety boundaries,
    and local sub-flows remain intact.
14. Desktop, tablet, mobile, keyboard, touch, screen-reader, reduced-motion, and
    print behavior pass.
15. The route list, route aliases, sidebar order, and protected module structure
    do not change.
16. The dashboard remains read-only, command-disabled, paper-only, and unable to
    grant authority or proof credit.
17. Local, preview, and production served-bundle checks all pass.

## 18. Success Measures

After release, validate the design with short comprehension tasks:

- A first-time reader can name the current page's lifecycle role in under 10
  seconds.
- A reader can identify what enters and leaves the stage without opening another
  document.
- A reader can distinguish "pattern found" from "edge validated" and "tradeable
  now."
- A reader can identify where an item goes next.
- A reader can explain why Qadam may have activity in several stages at once.
- No reader needs the repeated global maps that this plan removes.

Track route-stage navigation usage, tooltip/disclosure opens, and comprehension
test results only as product analytics. Do not use interaction analytics as
trading evidence.

## 19. Risks And Mitigations

| Risk | Mitigation |
| --- | --- |
| Ten stages become visually dense | Use responsive 10-node layouts and progressive disclosure without hiding stage names |
| The rail looks like a one-time progress bar | Use lifecycle language, omit completion percentages, and show concurrent aggregate states |
| Tooltips become technical walls of text | Lead with a short plain-English answer and place detailed inputs/outputs behind disclosure |
| Runtime staleness is mistaken for inactivity | Require freshness and distinguish unavailable from idle |
| Local sub-flows duplicate the global lifecycle | Enforce the content-ownership rules and DOM anti-duplication checks |
| De-duplication removes useful evidence | Maintain a route-by-route keep/remove inventory and snapshot before changes |
| Stage 5 lacks a clear home | Make Trading Strategies explicitly own stages 4 and 5, with Pattern and Quantum Review supplying evidence |
| Cross-cutting pages imply false ownership | Use dedicated Team and System Overview treatments rather than an active stage marker |
| Navigation changes confuse existing users | Preserve route names, aliases, sidebar order, and browser history behavior |
| Frontend copy drifts from machine truth | Generate stage and route context from one canonical backend contract |
| Public UI gains accidental authority | Add negative safety probes and retain read-only authority flags in certification |

## 20. Out Of Scope

This plan does not:

- Change trading logic, pattern scoring, strategy validation, Akber thresholds,
  Router decisions, risk budgets, or PaperOps authority.
- Add new data sources or instruments.
- Change the current 13-route dashboard information architecture.
- Merge dashboard modules.
- Enable live capital, broker live endpoints, Telegram commands, or dashboard
  commands.
- Treat a lifecycle visualization as proof that an operational stage is healthy.

## 21. Definition Of Done

The dashboard is complete under this plan when every module presents the same
truthful 10-stage system map, clearly marks its own role, exposes fresh aggregate
state without implying a single global workflow position, and retains only the
local evidence and sub-flow that make that module distinct.

The resulting experience should let a new reader understand Qadam as a continuous
learning system:

`Qadam watches the world, qualifies evidence, discovers patterns, forms and tests strategies, filters tradeability, governs paper decisions, monitors outcomes, learns, and applies only reviewed improvements before observing again.`
