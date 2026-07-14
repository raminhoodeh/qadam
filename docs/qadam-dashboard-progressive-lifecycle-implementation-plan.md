# Qadam Dashboard Progressive 10-Stage Lifecycle Implementation Plan

Status: Implemented, verified, and deployed to production.

Date: 2026-07-13

## 1. Objective

Redesign the shared 10-stage lifecycle as a progressive-disclosure component:

- Every dashboard route keeps exactly one canonical 10-stage lifecycle.
- The default state becomes a quiet orientation rail rather than a large
  explanatory panel.
- Hover, keyboard focus, or an explicit touch action reveals the complete page
  context and existing stage-level detail.
- The stage or stages owned by the current page remain immediately visible.
- Page position and current runtime activity remain separate concepts.
- The protected 13-route navigation, route aliases, module order, quantum-edge
  surfaces, and paper-only authority boundaries do not change.

This is a presentation and comprehension improvement. It must not change the
canonical lifecycle, infer one global current stage, alter route ownership, or
create any operational authority.

## 2. Interpretation Of The Requested Experience

### 2.1 Compact State: The Default

When the lifecycle is not being hovered, focused, or deliberately expanded,
the user sees only:

1. The title `10-Stage Lifecycle`.
2. Ten short rectangular stage cells.
3. The stage number and short stage name inside each cell.
4. Strong highlighting for the current page's primary stage or stages.
5. Softer highlighting for supporting or outcome relationships where needed.

The compact state must not show:

- the technical relationship heading, such as `Stage 8 outcome mirror;
  supports stage 9`;
- the page-position explanation;
- source provenance or refresh copy;
- per-stage runtime status text;
- the concurrency disclaimer;
- any duplicate whole-system explanatory prose.

Runtime state remains available in the expanded stage detail, but the compact
rail is first and foremost a map of where the page belongs.

### 2.2 Expanded State: The Full Explanation

On pointer hover or keyboard focus within the component, reveal the full card.
On touch devices, provide an explicit expand/collapse control with equivalent
behavior.

The expanded state must:

- use the heading `WHERE THIS PAGE SITS IN THE OVERALL FLOW`;
- replace the technical relationship heading with page-specific qualitative
  language;
- explain what the user is looking at, what came before it, and what happens
  next;
- retain the ten-stage rail and all existing stage tooltips/disclosures;
- retain stage inputs, outputs, team, blocker, freshness, safety boundary, and
  destination details;
- retain provenance-backed runtime state without presenting it as the page's
  structural position;
- remove the sentence beginning `Qadam can have different research ideas...`
  completely.

The technical relationship values (`primary`, `supporting`, `outcome_mirror`,
and `cross_cutting`) remain in the machine-readable contract and DOM data
attributes. They should no longer be used as the main visible heading.

## 3. Visual Hierarchy

### 3.1 Compact Card

The compact card should be approximately half the current height:

- a small institutional title row;
- a ten-cell rail beneath it;
- stage cells with a horizontal number/name arrangement;
- no status line under each stage name;
- no large display heading;
- no descriptive footer.

The cells should change from tall square-like cards to short rectangles. The
target desktop height is approximately 3.25 to 3.75rem rather than the current
6.4rem. The rail may remain five columns by two rows at normal desktop widths
and ten columns at wide widths. Mobile should retain a horizontally scrollable
ten-stage rail with compact touch targets.

The current implementation has a specific density defect that must be fixed,
not merely hidden by the collapsed state. At some laptop and content-panel
widths, each stage receives a `6.4rem` minimum height, `0.75rem` padding, three
stacked text rows, and a five-column grid. The result is a set of oversized,
square-like tiles with large areas of unused space. The expanded state must not
bring this oversized treatment back.

Use shared density tokens rather than route-specific overrides:

| Property | Compact target |
| --- | --- |
| Cell minimum height | 44px accessibility floor; approximately 52-60px visual target |
| Vertical padding | Approximately 0.4-0.5rem |
| Horizontal padding | Approximately 0.55-0.7rem |
| Number/name gap | Approximately 0.35-0.5rem |
| Stage status line | Hidden in compact cells; retained in expanded detail |
| Label wrapping | Maximum two visual lines without clipping the accessible name |
| Row gap | Approximately 0.35-0.45rem |

The number and short stage name should form one compact information unit rather
than three vertically separated rows. Prefer a horizontal number/name layout
when the cell is wide enough and a tightly stacked two-line layout when it is
not. Do not use empty space to equalize the cell to the height of the old card.

The lifecycle should use its own available width, not only the browser viewport,
to choose a grid. Prefer a CSS container query or equivalent component-width
measurement so the sidebar and content frame cannot unexpectedly force large
five-column tiles:

- use ten columns when the lifecycle component can keep every short label
  readable;
- use five compact columns by two rows at intermediate component widths;
- use a single horizontally scrollable rail on narrow screens;
- never use two wide columns that turn compact stages back into large cards.

The compact rail should have a bounded visual footprint. At wide desktop widths,
one row should remain close to a single 60px band. At intermediate widths, two
rows should remain close to 120px including the inter-row gap. Content must not
stretch either row beyond what its number and short label require.

### 3.2 Relationship Highlighting

Relationship styling must remain honest:

| Page relationship | Compact treatment |
| --- | --- |
| Primary | Strong brand highlight on the owned stage or stages |
| Supporting | Light outline or tint, visibly secondary to primary |
| Outcome mirror | Distinct information tint on the stage whose result is shown |
| Cross-cutting | Equal restrained treatment across all ten stages; no false primary stage |
| Unrelated | Neutral low-emphasis cell |

Current runtime state must not override the page-position highlight. A blocked
or degraded runtime state may appear as a small accessible marker only if it
does not compete with the structural relationship. Full runtime wording belongs
in expanded stage detail.

### 3.3 Expansion Motion

Keep the compact title and rail anchored while the qualitative panel expands
below or above them. This avoids a pointer-leave loop and prevents the page from
jumping before the user can read it.

Use a short opacity/height transition. Disable the transition under
`prefers-reduced-motion`. Expansion must not move the sidebar, replace the page,
or obscure the module's primary content.

Expansion reveals the qualitative context around the rail; it must not resize
the ten stage rectangles. Cell dimensions, padding, label treatment, and grid
breakpoints remain identical in compact and expanded states.

## 4. Route-Specific Qualitative Copy

Add a dedicated `flow_position_description` to every route context. The current
technical `relationship_label` remains available for validation and provenance
but is not rendered as the prominent heading.

| Route | Highlight | Expanded qualitative description |
| --- | --- | --- |
| Qadam Team | All stages, cross-cutting | Meet the hybrid team that carries evidence from observation through testing, paper execution, and learning. Each member contributes at different points rather than owning one isolated step. |
| Portfolio | Stage 8 outcome; Stage 9 support | You are looking at the financial result of Qadam's guarded paper-trading decisions. Portfolio value and positions are consequences of execution and become evidence for later learning. |
| Timeline | Stage 8 outcome; Stage 9 support | You are following what happened after an idea entered the guarded paper route. Each order and position event is recorded in sequence so the result can be reviewed honestly. |
| Data Sources | Stage 1 primary; Stage 2 support | This is where Qadam begins: watching the world and markets, checking source freshness, and recording observations worth examining. |
| Trading Universe | Stage 2 primary; Stage 1 support | This is where trustworthy observations are connected to the markets and instruments Qadam is allowed to study. |
| Pattern Recognition | Stage 3 primary; Stage 5 support | This is where Qadam searches for repeatable relationships across evidence and prices, then records what each finding still needs before it can be treated as an edge. |
| Quantum Edge | Stage 3 specialist; Stage 5 support | This is a specialist review inside pattern discovery. It asks whether nonlinear or quantum-assisted analysis adds useful evidence beyond matched classical methods. |
| Trading Strategies | Stages 4 and 5 primary; Stage 6 support | This is where supported patterns become testable strategy ideas and those ideas are challenged to show a repeatable, tradeable edge. |
| Decision Room | Stages 6 and 7 primary; Stage 8 support | This is where an evidence-backed idea is checked for practical tradeability, portfolio risk, and permission before it can reach paper execution. |
| Order Monitor | Stage 8 primary; Stage 9 support | This is where an approved paper setup becomes an order or position and is followed through submission, fill, monitoring, closure, and handoff to learning. |
| Results & Lessons | Stage 9 primary; Stage 10 support | This is where Qadam compares what it expected with what actually happened and records only lessons supported by the evidence. |
| Tests & Improvements | Stage 10 primary; Stage 1 support | This is where supported lessons become proposed changes, are tested and reviewed, and are either rejected or returned to the next observation cycle. |
| System Overview | All stages, cross-cutting | This is the operating view across all ten stages. It shows freshness, activity, blockers, and defects without pretending Qadam is in only one place at a time. |

Copy may be refined for rhythm during implementation, but its meaning and route
ownership must not change. Each route must have unique copy; no generic fallback
may appear while canonical route context is available.

## 5. Data Contract Changes

Extend each canonical route context with:

```json
{
  "flow_position_description": "Plain-English description unique to this route.",
  "compact_label": "10-Stage Lifecycle",
  "expanded_label": "Where this page sits in the overall flow"
}
```

Keep these existing fields unchanged:

- `relationship`;
- `primary_stage_ids`;
- `supporting_stage_ids`;
- `outcome_stage_ids`;
- `cross_cutting`;
- `entry_from`;
- `hands_off_to`;
- `relationship_label`;
- runtime stage state and provenance.

Validation must fail if any of the 13 routes lacks a qualitative description,
if two routes accidentally share identical descriptions, or if a cross-cutting
page receives a false primary stage.

The frontend fallback contract must contain the same route-specific copy so a
temporary status outage does not reduce the component to generic text.

## 6. Frontend Component Refactor

Refactor `renderQadamLifecycleTimeline` into three conceptual layers while
retaining one `[data-qadam-lifecycle]` root per route:

1. Compact summary: title, expand affordance, and ten-stage rail.
2. Expanded page context: renamed heading, qualitative route description,
   provenance, and entry/handoff explanation.
3. Stage detail: the existing ten stage-specific tooltips/disclosures.

Recommended semantic structure:

```html
<section data-qadam-lifecycle>
  <header data-lifecycle-compact-summary>...</header>
  <ol data-lifecycle-track>...</ol>
  <section data-lifecycle-page-context hidden>...</section>
</section>
```

The exact DOM may differ if accessibility testing requires it. The following
contracts are mandatory:

- the compact summary is always visible;
- the expanded context has a stable ID;
- the touch/keyboard toggle exposes `aria-expanded` and `aria-controls`;
- stage buttons keep their existing stage-detail controls;
- opening page context does not automatically open a stage tooltip;
- opening a stage tooltip does not collapse page context;
- Escape closes the most recently opened disclosure first;
- only one stage detail remains open at a time.

## 7. Interaction Model

### Desktop Pointer

- Resting state: compact summary and rail only.
- Hover anywhere within the lifecycle root: reveal page context.
- Hover a stage rectangle: retain the existing stage-specific preview.
- Moving away: collapse page context unless keyboard focus or a pinned touch
  state remains inside.

### Keyboard

- Tab reaches the lifecycle expand control and each stage control.
- Focusing within the component reveals page context.
- Enter or Space pins/unpins the expanded context.
- Escape closes stage detail first, then the page context.
- Focus indicators remain visible and do not depend on color alone.

### Touch

- No hover assumptions.
- Tapping the compact title/expand control reveals or hides page context.
- Tapping a stage opens its existing fixed-sheet stage detail.
- The compact rail remains horizontally scrollable.
- The expanded context must not cover the active stage trigger.

### Print

Print the compact ten-stage rail and the qualitative page-position description.
Hide interactive stage tooltips and controls. This preserves meaning when hover
and touch are unavailable.

## 8. Responsive Behavior

### Wide Desktop

- Ten short rectangles in one row where space permits.
- Expanded qualitative copy uses the existing page width without becoming a
  full-width wall of text.

### Desktop And Tablet

- Five rectangles per row where ten would become illegible.
- Expanded context stacks cleanly beneath the rail.

### Mobile

- One horizontal rail of ten compact rectangles.
- Each rectangle remains at least 44px tall but avoids padding beyond the space
  required for a readable number/name.
- Expanded page context becomes an in-flow panel, not a hover tooltip.
- Stage details may retain their fixed mobile sheet behavior.

No breakpoint may hide a stage, duplicate the lifecycle, or require horizontal
scrolling for the whole page.

## 9. Copy And Anti-Slop Rules

- Use the exact expanded label `WHERE THIS PAGE SITS IN THE OVERALL FLOW`.
- Use the exact compact title `10-Stage Lifecycle`.
- Remove the concurrency disclaimer completely.
- Do not expose phrases such as `Primary stage`, `supports stage`, `outcome
  mirror`, or `cross-cutting` as the prominent user-facing heading.
- Do not repeat a page's hero description word-for-word.
- Do not explain all ten stages again in paragraph form.
- Keep one qualitative page-position description and one stage-level detail
  source.
- Preserve technical relationship labels only for validation, accessibility
  context where useful, and diagnostics.

## 10. Testing And Acceptance

Extend the canonical lifecycle tests rather than creating an unrelated visual
test suite.

### Structural Checks

1. Exactly 13 lifecycle roots render across the 13 protected routes.
2. Every root renders exactly ten canonical stage rectangles in order.
3. Every root has one compact summary and one expanded page-context region.
4. Every route has unique qualitative copy.
5. No visible lifecycle contains the removed concurrency sentence.
6. No visible prominent heading contains the old technical relationship label.
7. The exact new compact and expanded labels are present.
8. Route aliases, route order, and sidebar structure remain unchanged.
9. Compact and expanded states use the same stage-cell dimensions.
10. No compact stage cell retains the old `6.4rem` minimum height or three-row
    number/name/status layout.

### Density Checks

1. At wide component widths, the ten-stage rail renders as one compact row when
   labels remain readable.
2. At intermediate component widths, the five-by-two rail remains close to a
   120px total rail height rather than expanding into large tiles.
3. At narrow widths, all ten stages remain available through horizontal scroll
   without causing page-level overflow.
4. Every compact stage meets the 44px target floor without adding unnecessary
   vertical whitespace.
5. Long short-label cases, including `six-stage filter` and `Paper Trade`, fit
   within two visual lines without clipping or changing the accessible label.
6. Stage cells do not grow when the outer lifecycle context expands.
7. Screenshot regression is checked at 1920px, 1440px, 1280px, 768px, and 390px
   viewports, with the actual sidebar present.
8. Component-width behavior is tested independently of device pixel ratio and
   viewport width so common laptop layouts cannot reproduce the oversized
   five-card rows shown in the current dashboard.

### Relationship Checks

1. Primary pages strongly identify their owned stage or stages.
2. Portfolio and Timeline remain outcome mirrors rather than false Stage 8
   owners.
3. Qadam Team and System Overview remain cross-cutting and have no false current
   stage.
4. Runtime state stays provenance-backed and separate from page relationship.

### Interaction Checks

1. Resting desktop view shows only the compact title and stage rail.
2. Hover and focus reveal the full page context.
3. Touch toggle opens and closes page context.
4. Stage tooltips continue to work independently.
5. Escape, outside interaction, and one-open-at-a-time behavior work.
6. Reduced-motion, print, screen-reader, keyboard, and touch behavior pass.
7. Desktop, tablet, and mobile layouts have no page-level overflow.

### Regression Checks

Run all current lifecycle, navigation, Pattern Recognition, Quantum Edge,
Trading Strategies, Decision Room, Order Monitor, learning, accessibility,
Wave F, Wave G, Wave H, authority-boundary, and production deployment checks.

## 11. Deployment Sequence

This enhancement must be integrated on top of the combined Quantum Edge Wave H
and 10-stage lifecycle production baseline. It must not redeploy the older
lifecycle snapshot or overwrite Wave H.

1. Fetch the latest dashboard remote and verify the current production commit.
2. Work from a clean integration branch/worktree based on the combined baseline.
3. Implement backend copy contract, frontend renderer, interaction logic, CSS,
   and tests as one coherent change.
4. Run the complete local preflight and all checks listed above.
5. Commit and push the scoped core and dashboard changes before deployment.
6. Bump the dashboard release ID and asset cache keys.
7. Deploy the committed bundle to preview and run served-bundle checks.
8. Deploy to `qadam.trade` and `www.qadam.trade` only after preview passes.
9. Verify all 13 direct production routes with cache-busting URLs.
10. Confirm the served JavaScript and CSS hashes match the committed release.
11. Verify compact, hover/focus-expanded, touch-expanded, and stage-detail states
    in a real browser at desktop and mobile widths.
12. Write the deployment receipt and implementation log only after production
    verification passes.

No Telegram message should be sent unless a separately approved notification
gate explicitly requires it.

## 12. Definition Of Done

The redesign is complete only when:

- every route opens with a compact `10-Stage Lifecycle` rail;
- the stage cells are visibly shorter rectangles;
- stage rectangles have tight, consistent padding with no large unused areas;
- compact and expanded states preserve the same dense stage-cell geometry;
- the current page's structural stage relationship is obvious at a glance;
- hover, focus, and touch reveal the full context accessibly;
- the expanded label reads `WHERE THIS PAGE SITS IN THE OVERALL FLOW`;
- every route uses a unique qualitative description;
- no large technical relationship heading is visible;
- the concurrency disclaimer is absent;
- all stage-specific evidence and handoff detail remains available;
- cross-cutting and outcome pages remain truthful;
- the 13-route navigation and module structure are unchanged;
- Wave F, Wave G, and Wave H functionality remains intact;
- local, preview, and production served-bundle checks pass;
- both production aliases serve the same committed release.
