# Qadam Quantum Edge Three-Layer UX Implementation Plan

Date: 2026-07-13
Status: Implementation in progress; Stage 5 documentation alignment completed
Route: `/dashboard/?module=patterns&view=nonlinear`
Scope: Public read-only Quantum Edge dashboard experience

## 1. Executive Decision

Rebuild the Quantum Edge page around one plain-English introduction and exactly
three primary questions:

1. **The answer:** Has a market-level quantum edge been proven?
2. **The evidence:** What was run, compared, and independently verified?
3. **The consequence:** Did the result change a validated strategy or paper
   decision?

The page will use one canonical public projection and one page renderer. It
will no longer read as three separately appended Wave F, Wave G, and Wave H
reports.

The page introduction remains visible at all times. `The answer` is expanded
by default. `The evidence` and `The consequence` are collapsed by default.
Each primary section can be expanded or collapsed independently, so users may
compare sections without another section closing automatically.

All existing scientific, hardware, provenance, lifecycle, and downstream
information remains available. Progressive disclosure changes the hierarchy;
it does not delete the audit trail.

## 2. User Outcome

A non-technical, non-financial user should be able to understand the page in
under ten seconds and answer these questions correctly:

- Qadam has **not** yet proven a market-level quantum edge.
- Qadam has shown that the engineering and experiment machinery works.
- A fair untouched market-data comparison and an authorized IBM hardware result
  do not yet exist.
- No validated strategy or governed paper decision has changed because of
  quantum evidence.
- A classical method matching or beating the quantum method would be a useful
  scientific result, not a system failure.

A technical user must still be able to inspect the full proof ladder,
experiment ledger, matched baseline, hardware record, certification checks,
data and circuit provenance, and downstream attribution.

## 3. Verified Current Baseline

The current page is assembled by multiple independent frontend owners:

- `landing-page-repo/dashboard.js` supplies the base nonlinear-review view.
- `landing-page-repo/quantum-edge-wave-f.js` replaces that view with the core
  Quantum Edge proof page.
- `landing-page-repo/quantum-edge-wave-g.js` appends the recurring hybrid-loop
  and downstream-route material.
- `landing-page-repo/quantum-edge-wave-h.js` appends the crude-oil certification
  and engineering-versus-market-proof material.
- `landing-page-repo/auth.js` loads all three Wave asset pairs independently.

This produces one technically complete page with several competing reading
systems:

- the six-step Quantum Edge proof ladder;
- the eight-step recurring hybrid lifecycle;
- the five public proof-state definitions;
- the engineering check score;
- the market-proof score;
- the crude-oil pilot ledger;
- the guarded downstream route.

The content is valuable, but the presentation makes the user assemble the
mental model themselves. The Wave-specific DOM mutation observers also make
order, rerendering, and disclosure-state preservation unnecessarily fragile.

The current public conclusion must remain truthful throughout this work:

- the engineering control has been reproduced;
- local quantum simulation is not IBM hardware execution;
- provider access is configured and the readiness probe has recovered, which
  satisfies one of six market-proof prerequisites;
- provider access is not a provider job or result: IBM hardware has not been run
  and no provider execution call or hardware result exists;
- a prepared manifest is not a submitted experiment;
- a synthetic fixture is not market evidence;
- no fair untouched market comparison has established a winner;
- no validated strategy or paper decision is attributable to quantum evidence;
- the current public state is `unproven` / `not measurable`.

No mutable count such as `11/11`, `1/6`, or `0` may be hardcoded into permanent
page copy. Counts and the identity of passed checks must come from the current
canonical public artifact.

## 4. Non-Negotiable Product Principles

### 4.1 One page owner

One generated public view model and one renderer own the final Quantum Edge
page. Wave F, G, and H remain valid evidence producers and historical contracts,
but they must not independently append competing top-level page sections.

### 4.2 Essential truth remains visible

The current verdict, proof state, engineering state, market-proof state, and
downstream impact must be readable without hovering over a tooltip. Tooltips
explain terms; they do not carry the only copy that tells the truth.

### 4.3 Complexity must earn its place

Quantum is a specialist branch, not a required decoration on every pattern.
The page must explain that simpler classical analysis is preferred whenever it
explains the evidence equally well.

### 4.4 Engineering success is not market proof

The visual hierarchy must keep these separate:

- **Engineering mechanism:** does the test rig, data separation, simulation,
  reproducibility, safety, and lineage machinery work?
- **Market-proof prerequisites:** is there enough independent market evidence
  to establish incremental predictive and economic value?

Until the underlying scientific contract changes, use `Market-proof
prerequisites` rather than a visually celebratory `Market proof passed` label.
Provider readiness is a prerequisite, not empirical predictive proof.

### 4.5 The page remains read-only

Nothing on this page may:

- submit or authorize a Q-CTRL or IBM job;
- create, promote, mutate, or approve a pattern or strategy;
- create a trade candidate;
- size a position or approve risk;
- approve execution;
- create a PaperOps handoff or paper order;
- write to Alpaca or any broker;
- award proof credit;
- send a Telegram message or accept a Telegram command;
- create live-capital authority.

## 5. Target Page Architecture

### 5.1 Always-visible page context

Keep these elements outside the three disclosures:

1. The shared ten-stage lifecycle strip and page-fit explanation.
2. `Quantum Research` eyebrow.
3. `Quantum Edge` page title.
4. The new purpose paragraph.
5. The red `Read more +` disclosure and its optional guidance.
6. A concise current-conclusion line, for example:
   `Current conclusion: Unproven — market advantage not measurable yet.`
7. The three primary section summaries.
8. One final authority/freshness boundary at the bottom of the page.

### 5.2 The three primary sections

| Section | Default | Collapsed summary | Content moved inside |
| --- | --- | --- | --- |
| **01 — The answer** | Expanded | `Has a market-level quantum edge been proven?` plus the current verdict and named proof state | Current proof state, short plain-English conclusion, six-stage proof ladder, engineering-versus-market-proof summary, immediate blockers, and next proof required |
| **02 — The evidence** | Collapsed | `What was run, compared, and independently verified?` plus current engineering and market-proof counts | Strongest evidence, originating-pattern link, experiment gallery, matched classical comparison, negative evidence, hardware authenticity, pilot facts, run ledger, certification checks, latest unattended-cycle facts, and provenance |
| **03 — The consequence** | Collapsed | `Did this change a strategy or paper decision?` plus current strategy and paper-attribution counts | Strategy influence, paper-outcome lineage, recurring hybrid lifecycle, guarded downstream route, integration counts, next destination, and read-only daily explanation preview |

### 5.3 Content de-duplication rules

- The introduction explains why Quantum Edge exists.
- `Read more` explains the six questions and possible scientific outcomes.
- `The answer` shows the **current state** of those questions.
- `The evidence` proves why that answer is honest.
- `The consequence` shows whether anything changed downstream.
- The five public proof-state definitions move into a nested `What these
  verdicts mean` disclosure in `The evidence`.
- Full certification checklists move into a nested `View certification checks`
  disclosure.
- Dataset hashes, circuit identifiers, receipts, and evaluation hashes move
  into a nested `View hardware and provenance` disclosure.
- Latest unattended-cycle facts move into a nested `View operational evidence`
  disclosure.
- The Telegram explanation becomes a nested supporting disclosure under `The
  consequence`; it is not a fourth primary page section.
- Repeated authority paragraphs are replaced by one concise local limitation
  where needed and one final page boundary.

## 6. Exact Header And Guidance Copy Contract

### 6.1 Purpose paragraph

Replace:

> Did quantum computation add useful information beyond Qadam's strongest
> matched classical method?

With this exact paragraph:

> Not every pattern needs quantum analysis. It is used when a relationship
> might involve complicated interactions, sequencing, regimes or path
> dependence that simpler analysis could miss. Quantum Edge is Qadam’s
> independent proof room for deciding whether a nonlinear or quantum-assisted
> method genuinely contributes something that the best conventional method
> missed.

Place the red text control `Read more +` directly after the paragraph. It must
look like a secondary disclosure control, not an error, destructive action, or
primary trading call to action.

### 6.2 Expanded guidance

When `Read more +` is selected, reveal:

> If you're wondering what this page is trying to establish... It asks six
> progressively harder questions:

- Can Qadam access the required technology?
- Was an actual hardware experiment executed?
- Can the result be reproduced?
- Did it beat the strongest fair classical comparison?
- Did that advantage survive completely untouched market data?
- Did it ultimately improve a governed paper decision?

Then show:

> A quantum method can therefore:

- Strengthen the evidence.
- Agree with the classical result.
- Lose to the classical method.
- Weaken the original pattern.
- Remain unmeasurable because evidence is missing.

End with:

> Note: “Classical preferred” is a perfectly successful scientific outcome:
> Qadam learns that the simpler method is sufficient.

When expanded, change the control label to `Read less −`. Selecting it collapses
the guidance again.

## 7. Interaction Specification

### 7.1 Introductory disclosure

- Use a real `<button type="button">` with `aria-expanded` and `aria-controls`.
- Keep a stable controlled-region ID across status refreshes.
- `Read more +` and `Read less −` must be accessible names, not decorative
  pseudo-element text.
- Preserve the state across an in-page data rerender.
- Do not permanently persist it across browser sessions.
- Return focus to the button if the region is collapsed while focus is inside.
- Do not animate height unless the animation respects `prefers-reduced-motion`.

### 7.2 Primary disclosures

- Use three semantic `<details>/<summary>` disclosures or an equivalent fully
  accessible disclosure implementation.
- Default state on a fresh visit:
  - `The answer`: open;
  - `The evidence`: closed;
  - `The consequence`: closed.
- Allow more than one section to remain open at the same time.
- Make the full summary row clickable and show an explicit chevron or plus/minus
  state.
- Give each summary a section number, title, question, current status, and short
  count summary.
- Preserve manual open/closed state during status refreshes using
  `sessionStorage` with a versioned key such as
  `qadam.quantumEdgeThreeLayer.open.v1`.
- Do not use permanent `localStorage`; a later visit should begin with the
  essential answer visible even if the evidence section was previously open.
- Support deep links such as `#quantum-answer`, `#quantum-evidence`, and
  `#quantum-consequence`. A deep link opens the matching `<details>`, scrolls it
  into view, and focuses its interactive `<summary>` rather than adding focus to
  a non-interactive container.
- If a section collapses while focus is inside it, return focus to that
  section's summary.

### 7.3 Nested disclosure depth

Allow no more than one supporting disclosure level inside a primary section.
The permitted nested disclosures are:

- `What these verdicts mean`;
- `View experiment details`;
- `View certification checks`;
- `View hardware and provenance`;
- `View operational evidence`;
- `View the research-to-paper lifecycle`;
- `View daily explanation preview`.

This limit prevents progressive disclosure from becoming a maze of disclosures
inside disclosures.

## 8. Tooltip And Plain-Language Help Plan

### 8.1 Tooltip design contract

- Use neutral grey help buttons. Red remains reserved for the `Read more` link,
  navigation emphasis, and intentional Qadam brand accents.
- Use a visible `i` or `?` inside a minimum 44 by 44 pixel target.
- Give every trigger a descriptive accessible name, such as
  `Explain market-proof prerequisites`.
- Repeated triggers must have stable unique IDs and contextual accessible names,
  such as `Explain engineering control: Local finite-shot simulation`.
- Implement one button-controlled, non-interactive help-popover pattern rather
  than mixing incompatible tooltip and disclosure behaviors. Connect the button
  and panel with `aria-controls` and `aria-describedby`; keep `aria-expanded`
  synchronized with the panel's `hidden` state.
- The help panel may use `role="tooltip"`, but it contains no focusable content.
- Open on mouse hover and keyboard focus.
- Clicking, tapping, Enter, or Space toggles and pins the help for touch and
  keyboard users.
- `Escape`, outside click/tap, or a second trigger selection closes it.
- Focus remains on the trigger.
- An unpinned tooltip remains visible while the pointer is over either the
  trigger or the tooltip, then closes only after the pointer leaves both. It
  must remain visible long enough to read and remain dismissible with Escape.
- Tooltips must flip or reposition to stay within 16 pixels of the viewport.
- Do not place an interactive tooltip button inside a native `<summary>`.
  Put it beside the relevant metric inside the expanded section.
- Tooltips may not contain links or controls. Longer interactive help must use
  an inline disclosure or named popover instead.
- Each tooltip should explain one idea in roughly 25 to 55 words.
- Essential status always remains visible outside the tooltip.

### 8.2 Tooltip placement and copy matrix

| Placement | Plain-language help |
| --- | --- |
| `Current proof state: Unproven` | **A market-level quantum edge has not been proven.** Qadam has shown that its testing process works, but it has not shown that a quantum-assisted method improves predictions on real untouched market evidence. |
| `Strongest evidence so far` and every `Engineering control` badge | **This is a known-answer synthetic test.** Qadam deliberately used data containing a relationship it already knew was there, then checked whether the classical and local quantum methods could recover it. Passing shows that the test machinery works; it does not prove a market edge. |
| `Local quantum simulation` | **This ran on a simulator, not IBM quantum hardware.** It demonstrates that the software path and circuit logic can be reproduced, but it does not establish quantum-hardware performance or market advantage. |
| `Engineering mechanism` score | **These checks test the experimental machinery.** They cover frozen inputs, reproducibility, lineage, safety, and authority isolation. A complete engineering score certifies the test rig, not predictive or investment performance. |
| Shared help beside the engineering and market-proof cards | **Read these scores together.** The engineering score says whether the experimental test rig works. The market-proof score says whether the investment claim has evidence. It is like proving an engine works on a test bench without yet proving that it wins races. |
| `Market-proof prerequisites` score | **These checks test what is still required before Qadam may claim market value.** The current tooltip should name the checks that actually passed and those still missing. Provider access alone is not an IBM experiment or a market advantage. |
| `Provider configured` or `IBM instance accessible` | **Access is not execution.** This confirms that Qadam can reach the configured provider path. It does not mean a quantum circuit was run or that a result exists. |
| `IBM hardware executed`, `Hardware job submitted`, `Hardware result completed`, and the Fire Opal/IBM ledger row | **The current record shows that no IBM hardware experiment was authorized, submitted, completed, or verified.** A prepared circuit manifest and a local simulation are not hardware execution. This current-state wording must change when the artifact changes. |
| `Untouched-data advantage`, `Market evidence`, and `Eligible holdout windows` | **An untouched holdout is market history kept completely out of discovery and tuning, then opened only for the final test.** Without eligible untouched evidence, Qadam cannot fairly measure whether either method generalizes to unseen markets. |
| `Classical baseline beaten` and the matched-baseline comparison | **No winner exists until both methods are tested on the same unseen evidence.** If the fair comparison has not run, the result is not measurable; it is neither a quantum loss nor a classical win. |
| `Classical preferred` proof state | **This is a useful scientific result.** It means the simpler conventional method explains the evidence just as well as, or better than, the more complicated method. Qadam should prefer the simpler method. |
| `Classified windows` versus `Eligible holdout windows` | **Classified windows have been inspected and categorized. Eligible holdout windows also satisfy the stricter point-in-time, completeness, and independence rules required for a fair final test.** A large classified count does not imply usable holdout evidence. |
| `Provider-history rows` and `Completed provider partitions` | **Provider-history rows are raw time-stamped records received from a data provider. Completed partitions are validated, coherent groups that are ready for point-in-time testing.** Raw rows in incomplete or failing partitions cannot create eligible holdout evidence by themselves. |
| `Strategy influence` count | **No strategy may change because of quantum evidence until the contribution passes independent market validation.** A simulator, synthetic fixture, provider connection, or prepared hardware manifest cannot influence a governed strategy. |
| `Paper outcome lineage` and `Paper decision improved` | **This count changes only after validated evidence affects a governed paper decision and the resulting paper outcome is recorded.** A zero means no paper decision or result can currently be traced to validated quantum evidence. |

### 8.3 Stateful tooltip rule

Definition text may remain stable, but current claims must be generated from the
public view model. For example, the market-proof tooltip must enumerate the
currently passed prerequisite from the artifact instead of permanently saying
that provider access is the only passed item.

The matrix above describes the expected rendering for the current
`unproven` / `not_measurable` snapshot. The view model must select state-specific
variants for provisional, validated, classical-preferred, decayed,
hardware-completed, eligible-holdout, and nonzero downstream states. Tests must
cover every supported state rather than only today's snapshot.

Preserve raw audit terminology while mapping it to humane public wording. At a
minimum:

```text
classically_dominated -> Classical preferred
```

The raw value remains in the sanitized provenance record. The visible label and
tooltip use `Classical preferred` and explain why preferring the simpler method
is a useful scientific outcome.

The implementation must distinguish:

- `not_run`;
- `not_measurable`;
- `waiting_for_evidence`;
- `blocked`;
- `failed`;
- `classical_preferred`;
- `validated`;
- `decayed`.

A test that has not run must never be described as failed.

## 9. Canonical Public View-Model Contract

### 9.1 New projection

Add one read-only aggregator, for example:

```text
orchestrator/qadam_quantum_edge_page_view_model.py
```

It consumes the existing public-safe Wave F, G, and H artifacts. It does not
run research, call a provider, submit hardware, create a strategy, or touch a
broker.

Export:

```text
data/runtime/qadam_quantum_edge_page.json
landing-page-repo/status/quantum-edge-page.json
```

Suggested schema:

```json
{
  "artifact_type": "qadam_quantum_edge_three_layer_page",
  "schema_version": "qadam.QuantumEdgeThreeLayerPage.v1",
  "generated_at": "...",
  "content_hash": "...",
  "copy_version": "quantum-edge-three-layer-v1",
  "source_artifacts": [],
  "freshness": {},
  "page_explainer": {},
  "answer": {
    "proof_state": "unproven",
    "scientific_verdict": "not_measurable",
    "plain_english_summary": "...",
    "proof_ladder": {},
    "engineering_checks": {},
    "market_proof_prerequisites": {},
    "current_blockers": [],
    "next_required_evidence": []
  },
  "evidence": {
    "strongest_evidence": {},
    "experiments": [],
    "matched_classical_comparison": {},
    "negative_evidence": [],
    "hardware_authenticity": {},
    "pilot": {},
    "certification": {},
    "operational_evidence": {},
    "provenance": {}
  },
  "consequence": {
    "strategy_influence": {},
    "paper_outcome_lineage": {},
    "hybrid_lifecycle": [],
    "guarded_route": {},
    "daily_explanation_preview": {}
  },
  "plain_english_help": {},
  "authority": {}
}
```

### 9.2 Source responsibility

| Existing source | Canonical responsibility in the new projection |
| --- | --- |
| Wave F public view | Proof ladder, strongest evidence, experiments, matched comparison, negative evidence, hardware authenticity, originating-pattern route, and provenance |
| Wave G hybrid loop | Recurring lifecycle, safe-cycle facts, downstream route, integration counts, paper attribution, and daily explanation preview |
| Wave H crude-oil certification | Current public proof state, engineering and market-proof counts, pilot manifest, run ledger, certification check detail, hardware authorization state, and next evidence required |

### 9.3 Conflict and freshness policy

- Record every source artifact's schema version, `generated_at`, and content hash.
- Do not silently choose between two artifacts that make incompatible claims
  about the same fact.
- The unified projection gives Wave H responsibility for the current public
  proof state and the engineering-versus-market-proof denominators.
- Wave F's six-stage ladder remains an evidence progression, not a competing
  headline score.
- Determine semantic coherence through declared dependency content hashes and a
  shared evidence/cycle identity, not timestamp proximity. Wave G or H may be
  newer than Wave F only when it declares the exact upstream hash or evidence
  identity it consumed.
- If the existing producers do not export sufficient dependency lineage, add it
  before aggregation. Do not invent an arbitrary time tolerance as a substitute
  for lineage.
- Use timestamps only to report freshness after semantic coherence has passed.
- Reject internally contradictory check records. For example, `passed=true`
  cannot coexist with `waiting`, `not certified`, or equivalent negative
  explanatory text for the same condition. Repair the upstream Wave record or
  fail closed; never render a contradictory numerator.
- If source dependencies, epochs, or states conflict, fail closed to
  `source_truth_conflict` and show an unproven/unavailable summary.
- Never average, infer, or promote a result to resolve a conflict.
- Reject secret-like values, raw provider responses, circuit payloads, tokens,
  credentials, private broker details, and authority-changing fields.
- Generate runtime and static-site mirrors from the same content-addressed
  payload and verify matching hashes.

## 10. Frontend Architecture

### 10.1 Single renderer

Add one page owner, for example:

```text
landing-page-repo/quantum-edge-page.js
landing-page-repo/quantum-edge-page.css
```

The renderer:

- activates only on `module=patterns&view=nonlinear`;
- performs one Quantum Edge-specific read-only status fetch in addition to the
  dashboard shell's normal status request;
- renders exactly one `data-quantum-edge-page` root;
- preserves the shared lifecycle strip;
- owns the intro, three disclosures, tooltips, nested disclosures, and boundary;
- is content-hash and rerender idempotent;
- preserves disclosure state during data refresh;
- never contains provider, order, broker, risk, approval, or send endpoints;
- fails back to a truthful minimal base view if the enhanced projection is
  unavailable.

### 10.2 Legacy Wave migration

- Keep Wave F available for Pattern Recognition and Trading Strategies.
- Make the cutover atomic in one tested bundle: Wave F skips nonlinear ownership
  unconditionally, Wave G/H frontend loaders are removed or disabled, and the
  new renderer plus truthful base fallback become the only nonlinear owners.
- Do not use runtime detection of whether the new renderer has loaded; async
  loader timing and MutationObservers must not decide page ownership.
- Keep their generated artifacts, backend checks, and legacy frontend assets as
  rollback evidence for one release.
- Remove the old independent MutationObservers from the final nonlinear route.
- Update the base `dashboard.js` fallback to use the same purpose copy and a
  minimal three-section truth hierarchy, so enhancement failure does not expose
  a contradictory page.

### 10.3 Visual system

- Use full-width section rows and bodies.
- Use red for the requested `Read more` control, active navigation, and small
  brand accents.
- Use neutral grey for help icons and technical metadata.
- Use purple only to identify quantum methods, not to imply success.
- Use green only for genuinely passed conditions.
- Use amber or grey for waiting, incomplete, blocked, and not-measurable states.
- Pair status with text and iconography; never communicate status through color
  alone.
- Use consistent spacing, border weight, status chips, summary typography, and
  chevrons across all three sections.
- Stack all content into one column below tablet width.
- Make metric pairs two columns on wide screens and one column on mobile.
- Keep every control at least 44 pixels tall or provide a 44-pixel hit area.
- Avoid horizontal proof ladders on narrow screens; convert them to a vertical
  stepper.
- Avoid celebratory styling while the result remains unproven.

## 11. Multi-Stage Implementation Plan

### Stage 0 — Baseline And Truth Freeze

Objective: preserve the current evidence and deployment truth before changing
the presentation.

Work:

- Capture current desktop, tablet, and mobile DOM/screenshots.
- Record the current production deployment URL and both public aliases.
- Record Wave F/G/H schema versions, generated times, and content hashes.
- Audit every current certification item for semantic consistency, including
  agreement between boolean `passed`, lifecycle status, and explanatory text.
- Map every existing visible block to `The answer`, `The evidence`, or `The
  consequence`.
- Identify dirty and user-owned files in both the root and nested static-site
  worktrees.
- Freeze the current authority, secret-safety, and no-promotion assertions.
- Define the source precedence and conflict rules from section 9.
- Add characterization assertions for the current route before refactoring.

Exit gate:

- A signed content map accounts for every current block.
- The current deployment can be restored by URL.
- Current truth and zero-authority assertions are reproducible.
- No page, runtime, provider, strategy, order, or broker state changed.

### Stage 1 — Unified Read-Only Page Projection

Objective: create one deterministic public page model without changing any
research or trading behavior.

Work:

- Add `orchestrator/qadam_quantum_edge_page_view_model.py`.
- Validate and combine the existing Wave F/G/H public artifacts.
- Export runtime and static-site mirrors with identical content hashes.
- Run the aggregator only after the prerequisite Wave F, G, and H runtime
  exports complete. The aggregator reads canonical runtime artifacts first,
  then writes the runtime projection and site mirror from one payload.
- Define the checker so `--site-root landing-page-repo` explicitly validates or
  refreshes the deployable mirror; preflight runs this step after the Wave H
  exporter and before any frontend or deployment check.
- Add `plain_english_help` fields for state-dependent explanations.
- Fail closed on stale, missing, conflicting, or secret-bearing inputs.
- Add:
  - `scripts/check_qadam_quantum_edge_page_view_model.py`;
  - `tests/test_qadam_quantum_edge_page_view_model.py`.
- Prove determinism and idempotency.

Exit gate:

- One schema carries all three sections.
- One current conclusion is exposed.
- No duplicate or ambiguous denominator appears in the projection.
- Generation makes zero provider calls and zero downstream mutations.

### Stage 2 — Single Renderer And Fallback Migration

Objective: give the nonlinear route one DOM owner and one Quantum Edge-specific
projection fetch.

Work:

- Add `quantum-edge-page.js` and `quantum-edge-page.css`.
- Render one root from the unified projection.
- Update `auth.js` to load the new assets.
- Keep Wave F active for the other two Wave F routes.
- Disable Wave F's nonlinear-panel replacement when the new renderer is active.
- Stop Wave G/H from appending to the nonlinear panel.
- Update the base `dashboard.js` fallback.
- Preserve the existing route, navigation, and originating-pattern link.
- Prevent intermediate Wave-specific layouts and proof counts from flashing.

Exit gate:

- Exactly one Quantum Edge page root exists.
- Exactly one Quantum Edge-specific projection request serves the page, in
  addition to the dashboard shell's normal status request.
- No legacy Wave G/H block is appended.
- A failed enhanced fetch exposes the truthful fallback, not an empty page.

### Stage 3 — Header Copy And Three-Layer Progressive Disclosure

Objective: implement the requested explanation and new reading hierarchy.

Work:

- Install the exact purpose paragraph from section 6.
- Add the red `Read more +` / `Read less −` control.
- Install the exact guidance copy and bullet lists.
- Build the three full-width primary disclosures.
- Default only `The answer` to open.
- Move every current content block according to section 5.
- Add concise dynamic status summaries to collapsed section headers.
- Add only the approved nested disclosures.
- Preserve disclosure state across rerenders and support deep links.

Exit gate:

- The exact requested copy is present.
- There are exactly three top-level content disclosures.
- All existing necessary information remains reachable.
- There is no orphan fourth section or duplicated proof story.

### Stage 4 — Tooltips, Accessibility, And Responsive Behavior

Objective: make the technical evidence understandable without relying on hover
or prior financial knowledge.

Work:

- Implement the neutral shared tooltip component.
- Add every tooltip in section 8 where the corresponding metric exists.
- Bind stateful help to projection data.
- Support mouse, keyboard, touch, Escape, outside close, and viewport-aware
  placement.
- Add visible focus rings and 44-pixel targets.
- Test native summary interaction without nested interactive controls.
- Handle focus when a disclosure collapses.
- Put only the concise conclusion/status in a `role="status"` or
  `aria-live="polite"` region. Never make the entire page or accordion live.
- Preserve the currently focused control across content-hash refreshes. If a
  pinned help popover cannot be preserved, close it and return focus to its
  trigger before replacing content; never replace the root and silently drop
  focus.
- Respect reduced motion and forced colors.
- Verify mobile stacking and no horizontal overflow.
- Replace title-only feature help with accessible controls.

Exit gate:

- Every explanation is reachable by mouse, keyboard, and touch.
- The page is understandable without tooltips.
- Tooltips do not clip, cover their trigger, or toggle a parent disclosure.
- Screen-reader labels distinguish every control.

### Stage 5 — Truth, Copy, Documentation, And Regression Contracts

Objective: prevent the new hierarchy from drifting away from the scientific
and public-safety contracts.

Work:

- Add `scripts/check_dashboard_quantum_edge_page.js`.
- Update the Wave F/G/H dashboard contracts to validate their source artifacts
  without requiring their old top-level DOM blocks.
- Extend accessibility and non-homepage regression suites.
- Add checks for dynamic rather than hardcoded proof counts.
- Add checks for `not_run` versus `failed` wording.
- Add checks for simulator, hardware, provider-access, and manifest distinctions.
- Reject a check whose `passed` boolean contradicts its status or explanatory
  text; specifically cover `passed=true` paired with `waiting` or `not
  certified` language.
- Add a current-snapshot fixture that derives and verifies this explanation
  from artifact fields: `11/11 means the test rig works; 1/6 means only provider
  access has passed, while no IBM result, untouched holdout, robustness suite,
  or matched market comparison exists.` The permanent implementation must not
  hardcode those numbers.
- Test every proof-state copy variant, including the visible
  `classically_dominated -> Classical preferred` mapping and preserved raw audit
  value.
- Add a rendered-DOM interaction harness, for example
  `scripts/check_dashboard_quantum_edge_page_interactions.js`, that exercises
  Read more, disclosure restoration, hover/focus/tap help, Enter/Space,
  Escape/outside close, focus return, deep links, content-hash refresh, duplicate
  IDs, and viewport positioning. Static source inspection is insufficient.
- Run a dynamic accessibility scan with the project's supported browser scanner;
  if none exists, add an `axe-core`-equivalent development check. Pair it with a
  manual VoiceOver or comparable screen-reader pass.
- Align `docs/qadam-user-guide.md` and the public guide with the three-layer
  mental model.
- Replace stale hardcoded proof counts in docs with generated current state or
  non-mutable definitions.
- Update the existing Hybrid Loop plan with a pointer to this presentation plan
  only after implementation ownership is clear.

Documentation completion evidence (2026-07-14):

- `docs/qadam-user-guide.md`, the public guide, and the public whitepaper now
  explain the same `The answer`, `The evidence`, and `The consequence` model.
- `docs/qadam-quantum-edge-hybrid-loop-implementation-plan.md` now points to
  this document as the presentation-layer contract while retaining ownership of
  the underlying evidence, evaluation, and governance pipeline.
- Current-state documentation now derives the truthful distinction consistently:
  provider access is configured and recovered, 1/6 market-proof prerequisites
  are satisfied, IBM hardware has not been run, no hardware job or provider
  execution call exists, and no quantum market edge has been proven.
- Mutable proof counts remain projection data rather than permanent interface
  copy; the documentation uses current snapshot values only when explicitly
  labelling them as current-state evidence.

Exit gate:

- Existing backend evidence tests still pass.
- No public surface contains contradictory proof counts or stale wording.
- The guide and dashboard explain the same three questions.
- Zero-authority and secret-safety checks pass.

### Stage 6 — Local UX Acceptance

Objective: prove that the page works for non-technical users and expert auditors.

Work:

- Test at approximately 1440, 1024, 768, and 390 pixel widths.
- Test 200 percent browser zoom, 400 percent reflow at a 320 CSS-pixel viewport,
  increased text-spacing overrides, and tooltip reflow under those conditions.
- Exercise Read more/read less, every primary disclosure, every nested
  disclosure, and every tooltip.
- Exercise keyboard Tab, Shift+Tab, Enter, Space, and Escape.
- Exercise touch/tap behavior.
- Test route changes and the link back to Pattern Recognition.
- Refresh status data while disclosures and tooltips are open.
- Verify one root, no duplicate IDs, no console errors, and no horizontal
  overflow.
- Run a three-question comprehension check:
  1. Has a quantum edge been proven?
  2. What evidence exists and what is missing?
  3. Did anything change downstream?

Exit gate:

- A non-technical reviewer answers all three questions correctly without
  opening technical provenance.
- A technical reviewer can reach every prior evidence record.
- Desktop, tablet, mobile, keyboard, screen-reader, and touch checks pass.

### Stage 7 — Release, Deployment Verification, And Rollback Readiness

Objective: publish the exact tested page and prove that both public domains
serve it.

Work:

- Bump the new page JS/CSS cache keys in `auth.js`.
- Bump the `/auth.js?v=` key in `dashboard/index.html`.
- Extend `landing-page-repo/scripts/deploy-vercel-production.sh` to verify:
  - served `auth.js`;
  - the new Quantum Edge JS and CSS;
  - the unified public status JSON;
  - its content hash;
  - both `qadam.trade` and `www.qadam.trade`.
- Add the unified checker to `scripts/preflight_dashboard_deployment.sh`.
- Update `scripts/check_dashboard_deployment_readiness.js`,
  `scripts/check_non_homepage_deploy_discipline.js`, the static site's
  `.vercelignore` assertions, and the preflight syntax/diff file lists so the
  new JS, CSS, status artifact, checker, and tests cannot be omitted from the
  exact deployment bundle.
- Build and test from a clean exact-bundle deployment worktree.
- Stage and deploy only files owned by this release.
- Verify the live DOM, not only local source checks.
- Confirm the exact intro copy, three primary sections, default disclosure state,
  tooltips, status counts, route, asset hashes, and zero console errors.
- Record a deployment receipt and the previous production URL.

Exit gate:

- Both public domains serve the exact tested assets and status hash.
- The live DOM contains one Quantum Edge root and exactly three primary
  disclosures.
- No legacy appended section is present.
- All public-safety and accessibility checks pass after deployment.

## 12. Stage Dependencies

```text
Stage 0 truth freeze
  -> Stage 1 unified projection
  -> Stage 2 single renderer
  -> Stage 3 copy and disclosures
  -> Stage 4 tooltips and accessibility
  -> Stage 5 contracts and documentation
  -> Stage 6 local UX acceptance
  -> Stage 7 production release
```

Stages must not be skipped by directly wrapping the current Wave F/G/H DOM in
CSS accordions. That would hide the duplication without fixing ownership,
truth precedence, rerendering, or stale-count ambiguity.

## 13. Verification Matrix

| Concern | Required evidence |
| --- | --- |
| Exact copy | New intro and guidance strings match section 6 |
| Structure | One page root and exactly three primary disclosures |
| Defaults | Answer open; Evidence and Consequence closed |
| Preservation | Disclosure state survives content-hash rerender |
| Truth | Current proof state and counts come from the unified artifact |
| Denominators | Proof ladder, engineering checks, and market prerequisites are named distinctly |
| Hardware honesty | Provider access, simulation, prepared manifest, submission, completion, and receipt remain separate |
| Evidence honesty | Synthetic fixture, classified window, eligible holdout, and empirical result remain separate |
| Downstream honesty | Strategy, risk, PaperOps, order, and paper-outcome counts remain separate |
| Accessibility | Mouse, keyboard, touch, screen-reader labels, focus return, Escape, reduced motion, and forced colors pass |
| Responsive UX | No clipping or horizontal overflow at target widths |
| Performance | One Quantum Edge-specific projection fetch and one nonlinear-page DOM owner |
| Authority | Zero provider, strategy, risk, execution, order, broker, Telegram, proof-credit, and live-capital authority |
| Deployment | Exact assets and status hash verified on both public domains |

## 14. Suggested Verification Commands

The implementation should add or run the following focused checks:

```bash
.venv/bin/python scripts/check_qadam_quantum_edge_page_view_model.py --site-root landing-page-repo
.venv/bin/python -m pytest tests/test_qadam_quantum_edge_page_view_model.py tests/test_qadam_wave_f_public_view.py tests/test_qadam_wave_g_hybrid_loop.py tests/test_qadam_wave_h_crude_oil_certification.py
node --check landing-page-repo/quantum-edge-page.js
node scripts/check_dashboard_quantum_edge_page.js
node scripts/check_dashboard_quantum_edge_page_interactions.js
node scripts/check_dashboard_quantum_edge_wave_f.js
node scripts/check_dashboard_quantum_edge_wave_g.js
node scripts/check_dashboard_quantum_edge_wave_h.js
node scripts/check_non_homepage_accessibility.js
node scripts/check_non_homepage_regression_suite.js
node scripts/check_dashboard_deployment_readiness.js
node scripts/check_non_homepage_deploy_discipline.js
bash scripts/preflight_dashboard_deployment.sh
```

The exact regression-suite filename must be verified against the checkout at
implementation time. Do not invent or silently skip a missing check.

## 15. Rollback Strategy

- Record the current production deployment URL before aliasing a new release.
- Keep Wave F/G/H status artifacts and unreferenced legacy frontend assets for
  one release window.
- If live hash, DOM, accessibility, truth, or zero-authority verification fails,
  re-alias both public domains to the recorded prior deployment.
- After re-aliasing, verify the restored HTML, asset hashes, status hash, and
  rendered DOM on both domains. Record a rollback receipt; rollback is not
  complete merely because the alias command succeeded.
- Do not roll back or mutate runtime research evidence to repair a presentation
  regression.
- Do not redeploy the entire dirty nested working tree.
- Rebuild from the exact staged file list and rerun preflight before attempting
  another release.

## 16. Final Acceptance Criteria

The plan is complete only when all of the following are true:

- The exact new introduction is visible.
- A red `Read more +` control reveals the exact supplied guidance.
- The control becomes `Read less −` and collapses the guidance again.
- The route contains exactly three full-width, independently collapsible primary
  sections: `The answer`, `The evidence`, and `The consequence`.
- `The answer` is open on a fresh visit.
- The current conclusion remains visible and unambiguous.
- Engineering readiness and market proof are visually and semantically distinct.
- The test-bench-versus-race explanation is available beside the paired scores.
- Every requested explanation is placed beside the relevant evidence through
  visible copy or an accessible tooltip.
- `Classical preferred` is explained as a useful scientific outcome.
- Every previous necessary evidence block remains accessible.
- No Wave F/G/H page duplication remains.
- Mutable counts are generated, not hardcoded.
- The page uses one canonical public projection, one Quantum Edge-specific fetch,
  and one nonlinear-page DOM owner.
- Contradictory check booleans, statuses, or explanations fail closed before a
  proof numerator is rendered.
- Desktop, tablet, mobile, keyboard, touch, and screen-reader checks pass.
- The page remains entirely read-only and cannot change research, provider,
  strategy, risk, execution, paper-trading, broker, Telegram, proof, or capital
  state.
- The exact production assets and status hash are verified on both Qadam domains.

## 17. Definition Of Done In Plain English

The finished page should feel like a clear proof room rather than a stack of
research reports.

At a glance, the user sees the answer: **Qadam has not yet proven a market-level
quantum edge.** If they want to understand why, they open `The evidence`. If
they want to know whether anything changed in the fund, they open `The
consequence`.

The full scientific record remains available, but the user no longer has to
decode Wave F, Wave G, Wave H, several overlapping ladders, and several
different denominators before understanding the page's purpose.
