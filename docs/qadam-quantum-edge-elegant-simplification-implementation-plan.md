# Qadam Quantum Edge Elegant Simplification Implementation Plan

Date: 2026-07-15

Status: Approved implementation specification. No frontend or runtime behavior
is changed by this document alone.

Route: `/dashboard/?module=patterns&view=nonlinear`

Scope: Simplify the public, read-only Quantum Edge page while preserving the
complete scientific record, the hybrid classical-quantum loop, the current
10-stage dashboard lifecycle, and all paper-only authority boundaries.

## 1. Executive Decision

Quantum Edge is one of Qadam's defining product surfaces. It should communicate
the system's most ambitious claim without reading like a PhD appendix.

The page will be rebuilt around one concise scientific narrative:

1. **Experiment & Evidence** - What was tested, compared and verified?
2. **Strategy & Paper Impact** - Did the result improve a strategy or paper
   decision?
3. **Quantum Edge Verdict** - Has a genuine market-level quantum advantage been
   proven?

The detailed evidence remains preserved, but it leaves the primary reading
flow. A non-technical visitor should understand the page in under ten seconds.
An expert should still be able to inspect the complete technical record through
one clearly labelled secondary surface. The three primary rows provide the
overview and are collapsed by default; opening a row reveals one flat,
plain-language explanation rather than another hierarchy of accordions.

The main page must make the comparison understandable. It must not use the
amount of technical detail as a substitute for proof.

## 2. Relationship To Existing Qadam Contracts

This plan refines presentation only. It does not replace or weaken the existing
research, evidence, validation, or authority contracts.

- `docs/qadam-quantum-edge-hybrid-loop-implementation-plan.md` remains the
  evidence-production, matched-lane, hardware, validation, and governance
  contract.
- `docs/qadam-quantum-edge-three-layer-ux-implementation-plan.md` remains the
  detailed public evidence and audit-trail reference.
- `docs/qadam-pattern-discovery-quantum-review-implementation-plan.md` remains
  the historical Pattern Recognition and Quantum Review implementation record.
- `docs/qadam-operator-ready-edge-engine-implementation-plan.md` remains the
  canonical path from evidence through validation, Strategy Foundry, Akber,
  forward shadow, risk, Router, and guarded PaperOps.
- The 13-route dashboard information architecture and shared 10-stage
  lifecycle remain protected.

Where this plan conflicts with an older Quantum Edge presentation order, this
plan controls the primary page hierarchy. It does not change scientific
semantics or source artifacts.

## 3. Current Truth That Must Survive The Redesign

The current canonical public projection reports:

- public proof state: `unproven`;
- scientific verdict: `not_measurable`;
- engineering checks: `11/11` passed;
- market-proof prerequisites: `1/6` passed;
- Q-CTRL and the configured IBM instance are accessible;
- eligible IBM devices have been discovered;
- no IBM hardware experiment has been authorized, submitted, completed, or
  verified;
- the current bounded hardware manifest records 6 qubits, 100 circuits, 256
  shots per circuit, and 25,600 total shots;
- no fair empirical matched classical-versus-quantum comparison exists on
  untouched market evidence;
- no validated strategy has changed because of quantum evidence;
- no paper decision or paper outcome is attributable to quantum evidence.

These values describe the current artifact, not permanent page copy. Every
mutable value must be read from the canonical public projection at render time.
The implementation must display different truthful states when the underlying
artifact changes.

## 4. Product Goals

### 4.1 Ten-second comprehension

A visitor should understand all of the following without opening a disclosure:

- Qadam compares classical and quantum-assisted methods on the same frozen
  evidence.
- The experimental machinery works locally.
- provider readiness is not hardware execution;
- hardware execution is not a market edge;
- no market-level quantum advantage has been proven yet;
- no strategy or paper decision has changed because of unvalidated quantum
  evidence.

The collapsed row summaries and header conclusion must carry this ten-second
story. Tooltips, expanded rows, and the technical record may add explanation,
but they must not contain the only statement of an important truth.

### 4.2 Scientific honesty

The page must make these distinctions visually and verbally explicit:

- local simulation versus IBM hardware execution;
- engineering reproducibility versus market proof;
- provider access versus a completed provider job;
- a prepared manifest versus a submitted experiment;
- a synthetic or known-answer fixture versus untouched market evidence;
- a quantum-originated research pattern versus a validated edge;
- a validated edge versus a strategy;
- a strategy versus an approved paper decision.

### 4.3 Elegant depth

The main reading flow contains exactly three collapsed overview rows. Each row
opens into one flat primary section, with no nested primary accordions.
Technical depth is available through one full-width inline `View technical
evidence` disclosure at the bottom rather than many nested accordions, a side
drawer, a separate page, or appended Wave reports.

### 4.4 Institutional trust

An unproven or classically dominated result is a valid scientific result. The
page should show Qadam refusing to promote weak evidence, not apologize for the
absence of a positive quantum claim.

## 5. Non-Goals

This work must not:

- alter Pattern Recognition scoring or discovery;
- submit, schedule, authorize, or poll a Q-CTRL or IBM hardware job;
- hardcode a backend such as `ibm_kyoto` without a current completed provider
  record naming it;
- change a strategy, strategy weight, threshold, risk policy, or authority;
- create a candidate, validated edge, strategy hypothesis, risk approval,
  PaperOps handoff, order, broker write, proof credit, or live-capital path;
- remove negative, inconclusive, classically preferred, decayed, or failed
  experiment records from the underlying archive;
- remove the shared 10-stage lifecycle component;
- modify the Pattern Recognition page or its recent interaction work;
- create a separate competing quantum lifecycle.

## 6. Target Information Architecture

### 6.1 Shared lifecycle context

The existing compact 10-stage lifecycle remains at the top of the dashboard
content area. Its route relationship, expanded context, tooltips, stage count,
and responsive behavior must remain unchanged.

### 6.2 Header block: The setup

Render the existing compact header block directly below the shared lifecycle.
The following three strings are immutable for this implementation and must be
preserved character-for-character:

- eyebrow: `Quantum Benchmark Framework`;
- title: `Quantum Edge`;
- subtitle:

  > Not every pattern needs quantum analysis. It is used when a relationship
  > might involve complicated interactions, sequencing, regimes or path
  > dependence that simpler analysis could miss. Quantum Edge is Qadam’s
  > independent proof room for deciding whether a nonlinear or quantum-assisted
  > method genuinely contributes something that the best conventional method
  > missed. The framework presents the experiment record first, then any
  > strategy and paper impact, and closes with the formal market-level verdict.

The eyebrow, title, and subtitle are content-locked acceptance criteria, not
suggested copy. The title and subtitle must also retain exact visual parity with
the Pattern Recognition page title and subtitle: at the current desktop root
size this is `2.5rem / 1.05` (40px / 42px) for the title and `1rem / 1.65`
(16px / 26.4px) for the subtitle. Responsive sizing must use the same shared
breakpoints and tokens as Pattern Recognition rather than a Quantum-only scale.

Keep the small, non-celebratory `Current conclusion` card right-aligned beside
the header copy. Its labels and values are dynamic. For the current projection
it reads `Unproven — Not measurable yet`. The card provides the answer
immediately; the later Verdict row explains why. The existing expandable
introductory guidance may continue to explain that `Classical preferred` is a
successful scientific outcome, but it must not rewrite or displace the locked
subtitle.

Do not put the full proof ladder, engineering checklist, hardware ledger, or
authority disclaimer in the header.

### 6.2.1 Primary-row disclosure contract

Immediately after the header, render exactly three full-width overview rows in
this order:

1. `Experiment & Evidence` — `What was tested, compared and verified?`
2. `Strategy & Paper Impact` — `Did the result improve a strategy or paper
   decision?`
3. `Quantum Edge Verdict` — `Has a genuine market-level quantum advantage been
   proven?`

All three rows are collapsed on initial load and every time the user leaves and
re-enters the Quantum Edge route. A row may remain open during a data-only
refresh while the user stays on the route. Each collapsed row includes one
meaningful, dynamically generated summary sentence, so the three-row overview
communicates the evidence state, downstream consequence, and verdict before any
row is opened. Opening one row does not automatically open or close another.

Expanded primary content is flat. It may use labelled facts, lists, or a
side-by-side comparison, but it must not contain nested accordions, nested
`details` elements, or another reveal hierarchy. Deep links may explicitly open
their requested primary row; they are the only exception to the default-closed
entry state.

### 6.3 Section 01: Experiment & Evidence

Collapsed-row eyebrow: `Experiment & Evidence`

Collapsed-row title: `What was tested, compared and verified?`

Current-state summary example:

> The experimental loop reproduced locally; provider access is ready, IBM
> hardware has not run, and no fair untouched market comparison is available.

This section uses one cohesive comparison component with four flat parts. The
primary experience is status-led, not count-led.

#### A. Shared frozen evidence bar

State whether both lanes received the same point-in-time frozen evidence and
whether an eligible untouched holdout exists. An originating pattern or pilot
label may appear when it helps orient the reader. Do not show source,
instrument, variable, snapshot, or row totals in the primary section; those
counts belong in `View technical evidence`.

#### B. Classical lane

Show:

- lane label: `Classical benchmark`;
- a concise plain-language method summary;
- whether its result is reproducible;
- whether it has an eligible untouched comparison result.

Method inventories, tuning records, negative-control tables, and benchmark
counts remain in the technical record.

#### C. Quantum lane

Show:

- lane label: `Quantum-assisted method`;
- execution mode: local simulator, IBM hardware, or unavailable;
- provider readiness separately from execution;
- hardware execution state;
- exact backend name only after a canonical completed hardware record exports
  it;
- current reproducibility state.

Qubit, circuit, shot, job, and device totals remain in technical evidence. They
are not primary proof and must not dominate the comparison.

Use purple only to identify the quantum lane. Purple must not imply that the
lane passed, won, or produced market value.

#### D. Matched comparison outcome

Join both lanes in one bottom result strip:

- `No fair market-data winner yet` when no eligible untouched comparison
  exists;
- `Classical preferred` when the classical lane matches or beats the quantum
  lane under the governed comparison;
- `Quantum contribution provisional` when untouched evidence is positive but
  complete proof is missing;
- `Quantum contribution validated` only when the canonical proof contract
  permits that label.

When prior evidence no longer meets freshness or stability requirements, show
`Evidence no longer current` as a separate freshness warning; do not turn it
into a matched-comparison outcome.

Below the comparison, render only three compact facts:

- shared basis, for example `Same frozen evidence`;
- execution truth, for example `Local simulator reproduced; hardware not run`;
- comparison truth, for example `Untouched comparison unavailable`.

Do not show `11/11`, `1/6`, compute footprints, broad platform totals, or the
full engineering checklist on the primary page. Those values remain available
in technical evidence. Specialist risk vocabulary does not appear in the
primary page.

#### E. Fair-comparison eligibility contract

The page may describe a classical-versus-quantum result as a `fair comparison`
only when the canonical artifact proves that both lanes used:

1. the same immutable point-in-time evidence manifest and eligible feature set;
2. the same prediction target, outcome definition, and forecast horizon;
3. the same chronological training, calibration, and completely untouched
   holdout windows;
4. preprocessing that uses only information available at each historical
   timestamp, with equivalent leakage controls;
5. the same predeclared evaluation metric, trading-cost assumptions, and
   statistical decision rule;
6. a governed and comparable tuning and model-selection budget frozen before
   the untouched holdout was inspected;
7. the same negative controls, multiple-testing or false-discovery controls,
   and minimum evidence requirements; and
8. reproducible provenance linking the dataset, configuration, code, seeds or
   sampling policy, and results.

The strongest eligible classical benchmark must be selected under that frozen
protocol rather than chosen after seeing the quantum result. If any required
condition is missing or contradictory, the comparison outcome is `Not
measurable`; the UI must not name either lane a winner.

### 6.4 Section 02: Strategy & Paper Impact

Collapsed-row eyebrow: `Strategy & Paper Impact`

Collapsed-row title: `Did the result improve a strategy or paper decision?`

Current-state summary example:

> No validated strategy or governed paper decision has changed because of
> quantum evidence.

This section is a flat gatekeeper component, not a nested card collection.

#### A. Central downstream status

Show one prominent result:

- `No downstream change`;
- `Strategy evidence strengthened`;
- `Validated strategy changed`;
- `Paper decision influenced`;
- or the appropriate canonical state.

For the current state, show `No strategy or paper-decision change`. Numeric
lineage counts may appear only when they add meaning and are canonically
available; a row of zero counters is not required on the primary page.

#### B. Four plain-language gates

Show one ordered, scannable progression using these reader-facing questions:

1. `Does the experiment work?` — local engineering reproducibility.
2. `Does hardware evidence exist?` — an authorized, completed, verified
   provider-backed execution, not provider access or a prepared manifest.
3. `Does the market comparison hold up?` — a fair comparison on completely
   untouched evidence under the eligibility contract in Section 6.3.E.
4. `Did it improve a strategy or paper decision?` — validated lineage into a
   governed strategy or attributable paper decision.

Each stage uses one of four public states:

- `Passed` - the canonical evidence requirement passed;
- `Waiting` - a prerequisite is missing but no failure is claimed;
- `Not run` - the experiment or check has not executed;
- `Failed` - the check ran and failed.

Do not use `Locked` when the actual meaning is `Waiting for evidence` or `Not
run`. Do not use `Completed` for local simulation if the label could be read as
completed IBM hardware execution.

The existing seven auditable lifecycle stages are not deleted. They remain in
the inline technical evidence record with their original evidence links and
granularity. The four primary gates are a deterministic reader-facing grouping
of those seven stages, not a new proof model and not an alternate source of
truth.

#### C. Boundary statement

Use one concise sentence:

> Quantum findings remain research-only until they survive a fair classical
> comparison, untouched market evidence, required hardware evidence, and the
> governed strategy and paper-decision gates.

Do not repeat the entire authority ledger in this section.

### 6.5 Section 03: Quantum Edge Verdict

Collapsed-row eyebrow: `Quantum Edge Verdict`

Collapsed-row title: `Has a genuine market-level quantum advantage been
proven?`

Current-state summary example:

> Unproven — the engineering pathway works, but market-level quantum advantage
> is not measurable yet.

This section delivers the final conclusion after the evidence and consequence
have been shown.

#### A. Ultimate status

Show the canonical proof label as the largest text in the section:

- `UNPROVEN`;
- `PROVISIONAL`;
- or `VALIDATED`.

Show the comparison outcome directly beneath it, for example:

`Not measurable yet`

`Classical preferred` is a comparison outcome, not a proof state. `Decayed` is
a freshness state, not a proof state. Display either as a clearly labelled
secondary status without overwriting the proof label. When evidence is decayed
or stale beyond contract, the current advantage claim fails closed while the
historical result remains available in technical evidence.

#### B. Three-status readout

Display exactly three concise, plain-language statuses:

1. experiment, for example `Reproduced locally`;
2. market proof, for example `Not measurable yet`;
3. downstream impact, for example `No strategy or paper-decision change`.

These statuses must be derived from the current projection. Engineering check
ratios, market-prerequisite ratios, and raw impact counters belong in technical
evidence. Missing evidence must render `Unavailable` rather than an inferred
failure, success, or zero.

#### C. Summary statement

For the current unproven state, use this semantic contract:

> Qadam's hybrid classical-quantum experimental pathway is implemented and
> reproducible locally. A genuine market-level quantum advantage remains
> unproven because no authorized IBM hardware result, untouched market
> comparison, or forward-validated strategy impact exists yet.

Do not say the pathway is `validated locally`; that phrase can be confused with
market validation. Use `implemented and reproducible locally`.

#### D. What changes the verdict

End with one dynamic next-evidence line derived from the canonical blockers,
for example:

> Next proof required: complete provider-backed evidence history, run the
> frozen classical-versus-quantum holdout comparison, and separately authorize
> the exact hardware experiment only when its prerequisites pass.

## 7. Technical Evidence Without Primary-Page Noise

The complete audit trail remains available through one secondary, full-width
inline disclosure at the bottom of the page:

`View technical evidence`

This is the only technical-evidence interaction. It expands in place beneath
the three primary rows and must not open a drawer, modal, separate route, or
fourth primary section. It is visually subordinate to the primary narrative
and closed by default on initial load and route re-entry.

The technical surface may contain:

- the six-step proof ladder;
- the complete seven-stage auditable validation record;
- engineering checks;
- market-proof prerequisite checks;
- experiment and candidate ledger;
- matched classical comparison details;
- negative and classically dominated results;
- circuit and provider provenance;
- manifest, dataset, and result hashes;
- hardware authorization and receipt state;
- recurring hybrid lifecycle;
- strategy influence and paper-outcome lineage;
- latest unattended-cycle facts;
- sanitized source-artifact references.

The technical surface must:

- be closed by default;
- preserve its open state during data refreshes;
- reset to closed when the user leaves and re-enters the route;
- use a semantic `details`/`summary` disclosure or an equivalent accessible
  button-and-region pattern;
- support keyboard toggling, visible focus, correct `aria-expanded` state when
  applicable, and a minimum 44 by 44 CSS-pixel trigger;
- change its trigger to `Hide technical evidence` while open, or provide an
  equally clear collapse affordance at the start and end of a long record;
- never expose credentials, tokens, raw provider payloads, circuit payloads, or
  private broker information;
- use the same canonical public artifact as the primary page.

The inline record may contain its own semantic headings and data tables, but it
must not reproduce the three primary rows or introduce a second verdict. Its
purpose is to show the provenance behind the primary truth, not restate that
truth with competing labels.

## 8. Canonical Public View Model

Extend `orchestrator/qadam_quantum_edge_page_view_model.py` rather than adding a
second competing page model.

The generator first normalizes mutable truth into five independent state axes.
These axes must never be compressed into a single ambiguous status:

1. **proof** - whether a market-level quantum edge is unproven, provisional,
   or validated;
2. **comparison** - whether a fair matched comparison is eligible and, if so,
   whether it is not measurable, tied, classical preferred, or quantum
   positive;
3. **execution** - local simulation, provider access, authorization,
   submission, completion, and verification as separate facts;
4. **downstream** - no change, evidence strengthened, strategy changed, or
   governed paper decision influenced; and
5. **freshness** - current, stale, decayed, unavailable, or contradictory,
   including the timestamps and artifact hashes needed to justify the label.

For example, `execution.provider_access = ready` must coexist truthfully with
`execution.hardware = not_run`; it must not promote the proof or comparison
axis. A stale or contradictory freshness axis forces a fail-closed public
render without silently rewriting historical execution facts.

The public artifact should expose a normalized projection similar to:

```json
{
  "contract_version": "quantum-edge-elegant-v1",
  "page_copy": {
    "eyebrow": "Quantum Benchmark Framework",
    "title": "Quantum Edge",
    "subtitle": "Not every pattern needs quantum analysis. It is used when a relationship might involve complicated interactions, sequencing, regimes or path dependence that simpler analysis could miss. Quantum Edge is Qadam’s independent proof room for deciding whether a nonlinear or quantum-assisted method genuinely contributes something that the best conventional method missed. The framework presents the experiment record first, then any strategy and paper impact, and closes with the formal market-level verdict."
  },
  "state_axes": {
    "proof": {"state": "unproven"},
    "comparison": {
      "state": "not_measurable",
      "fair_comparison_eligible": false,
      "eligibility_checks": []
    },
    "execution": {
      "simulation": "reproduced",
      "provider_access": "ready",
      "hardware": "not_run"
    },
    "downstream": {
      "state": "no_change",
      "strategy_count": 0,
      "paper_decision_count": 0
    },
    "freshness": {"state": "current", "as_of": "..."}
  },
  "presentation": {
    "section_order": ["evidence", "consequence", "answer"],
    "rows": [
      {"id": "evidence", "summary": "...", "fact_refs": []},
      {"id": "consequence", "summary": "...", "fact_refs": []},
      {"id": "answer", "summary": "...", "fact_refs": []}
    ],
    "four_gates": [],
    "next_required_evidence": []
  },
  "technical_record": {}
}
```

The state axes are the only mutable page truth. `presentation` supplies order,
plain-English summaries, and references to normalized facts; it must not repeat
mutable verdicts, counts, execution states, or timestamps as an independently
maintained second truth tree. Human-readable summaries are deterministically
generated from the state axes in the same generator pass and validated against
them. They are not authored or recomputed in the browser.

The existing `answer`, `evidence`, and `consequence` structures may remain for a
bounded compatibility migration, but they must be produced from the same
normalized state and checked for semantic equality. They are never a lower-
priority source that the renderer may merge with the new axes. Remove legacy
fields after all declared consumers migrate.

### 8.1 Generator and browser data authority

Generator-side authority:

1. `qadam_quantum_edge_page_view_model.py` reads the declared canonical runtime
   artifacts under their existing source contracts.
2. It validates freshness, hashes, cross-artifact identity, and contradictions
   before normalizing the five state axes.
3. It writes one complete `qadam_quantum_edge_page.json` projection atomically,
   with a deterministic content hash.
4. If required inputs are missing, stale beyond contract, or contradictory, it
   emits a public-safe unavailable or contradictory state. It does not combine
   the newest value from one run with an older favorable value from another.

Browser-side authority:

1. `quantum-edge-page.js` reads only the complete canonical
   `qadam_quantum_edge_page.json` projection.
2. The browser does not read Wave F/G/H artifacts, infer a verdict, merge legacy
   structures, or calculate counts independently.
3. A projection is accepted as one atomic snapshot only after schema, contract
   version, hash, and required-state validation.
4. If that projection cannot be accepted, the browser renders a truthful
   static unavailable state containing locked explanatory copy and no mutable
   success count, provider claim, execution claim, or stale verdict.

This separation is mandatory: runtime precedence belongs to the generator;
projection precedence belongs to the browser. There is no browser-side source
fallback chain and no duplicated presentation truth.

### 8.2 No hardcoded mutable facts

The following must always be data-bound:

- source, instrument, variable, method, circuit, qubit, and shot counts;
- provider readiness;
- backend identity;
- hardware authorization, submission, completion, and verification;
- engineering and market-proof numerators and denominators;
- proof state and scientific verdict;
- fair-comparison eligibility and every eligibility check in Section 6.3.E;
- comparison outcome, execution state, downstream state, and freshness state as
  separate axes;
- strategy and paper-decision influence;
- blockers and next required evidence;
- timestamps and freshness.

## 9. Frontend Architecture

### 9.1 One DOM owner

`landing-page-repo/quantum-edge-page.js` remains the sole owner of the Quantum
Edge primary DOM. Wave F, G, and H scripts remain evidence/history contracts but
must not append independent primary sections or act as browser data sources.

### 9.2 Protected neighboring surfaces

The implementation must preserve:

- the newest compact 10-stage lifecycle;
- exactly 13 protected routes;
- the current sidebar structure;
- the current Pattern Recognition renderer, sorting, pagination, persistent
  expansion, scores, tooltips, and evidence presentation;
- Trading Strategies, Decision Room, Order Monitor, Results & Lessons, Tests &
  Improvements, Qadam Team, and System Overview;
- the stale-shell detector and release manifest;
- read-only public operation.

### 9.3 Refresh behavior

Data refreshes may update values and statuses but must not:

- replace the Quantum Edge root;
- reopen or close any primary row or the inline technical-evidence disclosure;
- reset keyboard focus;
- scroll the page unexpectedly;
- flash older Wave layouts;
- briefly display contradictory proof states.

Route exit and re-entry is not a data refresh: it intentionally resets all
three primary rows and the technical-evidence disclosure to closed. A deep link
may open only its explicitly requested row after the default reset.

## 10. Visual Design Contract

### 10.1 Layout

- Use one full-width collapsed overview row per primary question.
- Do not nest decorative cards inside section cards.
- Use a shared-evidence band, a two-lane comparison, and one joined outcome
  band in the expanded Section 01.
- Use one flat four-gate progression in the expanded Section 02.
- Use one verdict block and one three-status row in the expanded Section 03.
- Put one full-width inline technical-evidence disclosure after the three
  primary rows.
- Keep vertical spacing deliberate and materially shorter than the current
  audit-heavy page.

### 10.2 Color semantics

- Qadam red: page hierarchy, section numbering, and final blocked/unproven
  emphasis;
- institutional green: a requirement that actually passed;
- muted amber: waiting or incomplete evidence;
- Q-CTRL-inspired purple: quantum method identity only;
- charcoal and neutral gray: classical method and structural UI;
- never use purple glow, green, or celebratory treatment to imply quantum
  advantage before validation.

### 10.3 Typography

- Use the existing non-homepage design system.
- Preserve the exact Pattern Recognition title and subtitle typography parity
  defined in Section 6.2, including responsive tokens and breakpoints.
- Reserve large serif text for `Quantum Edge` and the final proof-state label.
- Keep section questions concise and readable.
- Use tabular monospaced numerals only for measured compute and proof metrics.
- Avoid uppercase paragraphs and long technical chip strings.

### 10.4 Interaction

- The three primary overview rows are visible and collapsed by default on
  initial load and route re-entry.
- Each row is independently expandable; opening it reveals one flat section
  with no nested accordions or reveal controls.
- Each closed row retains a meaningful state summary.
- Tooltips explain unfamiliar terms but never contain the only statement of
  truth.
- The full-width inline `View technical evidence` disclosure is visually
  secondary and closed by default.
- No hover-only information is required to understand the page.

## 11. Responsive And Accessibility Requirements

### 11.1 Desktop

- Within an expanded Evidence row, classical and quantum lanes display side by
  side.
- The joined comparison result is visually centered below both lanes.
- The four gates may display horizontally when every question and state remains
  readable.

### 11.2 Tablet and mobile

- Shared evidence appears first.
- Classical lane stacks before quantum lane.
- The comparison result follows both lanes.
- The four gates become a vertical ordered progression.
- The three verdict statuses stack or use a stable two-column layout without
  clipping.
- No horizontal page scrolling is permitted.

### 11.3 Accessibility

- Meet WCAG 2.2 AA color contrast.
- Use semantic headings in order.
- Represent the four gates as an ordered list with text state labels, not color
  alone.
- Give tooltips keyboard-accessible triggers and escape behavior.
- Implement every primary row and the inline technical record as semantic,
  labelled disclosures with correct expanded-state announcements and heading
  order.
- Maintain touch targets of at least 44 by 44 CSS pixels.
- Respect reduced motion.
- Ensure print output includes the content of all three primary sections and
  the current verdict regardless of collapsed screen state, but excludes
  interactive-only disclosure controls.

## 12. State Matrix

The renderer and tests must cover at least these combinations. Each fixture
must assert the proof, comparison, execution, downstream, and freshness axes
independently; changing one axis must not silently promote another.

| State | Required public behavior |
| --- | --- |
| Current unproven | Engineering works locally; provider ready; hardware not run; no untouched comparison; no downstream change |
| Provider degraded | No provider-readiness pass; no implication of hardware availability |
| Hardware authorized but not submitted | Prepared/authorized remains distinct from execution |
| Hardware submitted but incomplete | Pending result; no proof or strategy influence |
| Hardware completed, market proof incomplete | Hardware result visible; proof remains unproven or provisional according to the artifact |
| Classical preferred | Presented as a useful scientific conclusion; simpler method preferred |
| Quantum provisional | Positive untouched evidence visible; missing proof requirements named |
| Quantum validated | Validation label allowed only from the canonical proof state |
| Decayed | Old evidence no longer presented as current advantage |
| Artifact unavailable | Truthful unavailable fallback; no stale mutable counts or positive claim |
| Contradictory source artifacts | Fail closed to unproven/unavailable and expose a public-safe data-quality warning |
| Stale otherwise-positive artifact | Preserve historical result in technical evidence; current proof surface fails closed and names stale freshness |

## 13. Implementation Stages

### Stage 0 - Baseline And Integration Protection

1. Treat the existing original workspaces and every uncommitted change as
   protected; inspect their state but do not edit, reset, stash, rebase, or
   overwrite them.
2. Verify the known clean dashboard baseline
   `e23f0472980238525366dca51f72ce22f90dbb2b` (`Refine Quantum Edge review
   hierarchy`) and known clean core baseline
   `634fec59104471c3b420226878ceb1edea8cbe91` (`Align Quantum Edge projection
   and guidance`).
3. Create isolated clean branches/worktrees rooted exactly at those commits for
   the simplification work. Do not start blindly from a dirty checkout or
   replace these baselines merely because `origin/main` or another remote tip
   moved.
4. Fetch remotes for comparison and release planning only. If either known
   baseline is not an ancestor of the intended integration target, reconcile
   the histories explicitly in an isolated worktree and rerun all protected-
   surface checks; never silently discard either side.
5. Record current release ID, both baseline commits, JS hash, CSS hash, route
   count, lifecycle count, exact locked header copy, computed title/subtitle
   styles, and Quantum Edge source-artifact hashes.
6. Run existing lifecycle, Pattern Recognition, Wave F/G/H, authority, and
   Quantum Edge tests before editing.

Exit gate: the baseline is reproducible and no in-progress worktree is modified
or overwritten.

### Stage 1 - Canonical Presentation Projection

1. Extend the existing Quantum Edge view model with the five normalized state
   axes and presentation references in Section 8.
2. Derive shared-evidence, lane, fair-comparison eligibility, downstream,
   verdict, freshness, and technical-record structures once from canonical
   sources.
3. Add contradiction, cross-run identity, and freshness checks.
4. Preserve existing artifact fields only for a bounded compatibility period,
   generate them from the same normalized state, and assert semantic equality.
5. Add deterministic content hashing, atomic projection writes, and public-
   safety validation.
6. Make the browser consume only the generated projection and fail closed when
   it is unavailable or invalid.

Exit gate: one artifact can render the complete simplified page without reading
Wave files independently in the browser.

### Stage 2 - Header And Page Skeleton

1. Preserve the exact locked eyebrow, title, subtitle, and compact conclusion
   card in Section 6.2; do not introduce replacement header copy.
2. Preserve Pattern Recognition typography parity for the title and subtitle.
3. Render exactly three full-width primary rows in Evidence, Consequence,
   Verdict order, all collapsed by default with meaningful summaries.
4. Reset all three rows to closed on route re-entry while preserving their
   state through in-route data refreshes.
5. Remove primary-page Wave headings and competing introductions.
6. Preserve the shared lifecycle above the page content.

Exit gate: a DOM check finds one Quantum Edge root and exactly three ordered
primary sections.

### Stage 3 - Experiment & Evidence Comparison

1. Build the shared frozen-evidence band.
2. Build classical and quantum lane components.
3. Build the joined matched-comparison outcome.
4. Enforce every fair-comparison eligibility condition in Section 6.3.E.
5. Add three concise evidence statuses, not metric counters.
6. Move source/instrument totals, engineering ratios, compute footprints,
   engineering-risk pills, and raw ledgers out of the main flow.

Exit gate: the current page accurately communicates local reproducibility,
provider readiness, no hardware execution, and no fair market winner.

### Stage 4 - Strategy & Paper Impact Gatekeeper

1. Build the central downstream status.
2. Build the four plain-language gates and deterministically map the existing
   seven auditable stages into them.
3. Map internal states to `Passed`, `Waiting`, `Not run`, and `Failed`.
4. Keep the complete seven-stage record and lineage in technical evidence.
5. Add the single boundary statement.
6. Verify that absent or zero counts do not imply system failure or inactivity.

Exit gate: users can see why quantum evidence has or has not influenced a
strategy or paper decision without reading internal route language.

### Stage 5 - Quantum Edge Verdict

1. Build the proof-state display.
2. Build the three-status readout without engineering or proof-ratio counters.
3. Generate state-specific plain-English verdict copy.
4. Generate one next-proof statement from canonical blockers.
5. Verify proof-state variants independently from `Classical preferred`
   comparison, decayed freshness, and unavailable-data variants.

Exit gate: the final conclusion is truthful, concise, and consistent with the
underlying proof state.

### Stage 6 - Technical Evidence Surface

1. Move detailed ledgers, counts, ratios, the full seven-stage record, and
   checklists into one full-width inline `View technical evidence` disclosure
   at the bottom of the page.
2. Preserve evidence lineage and negative results.
3. Keep it closed by default and route re-entry, preserve its open state during
   data refreshes, and implement accessible keyboard and expanded-state
   semantics.
4. Remove all remaining nested primary-page accordions.
5. Verify public-safe sanitization.

Exit gate: no scientific evidence is deleted, but none of it interrupts the
primary three-section narrative.

### Stage 7 - Renderer Consolidation And Refresh Stability

1. Make `quantum-edge-page.js` the sole page owner.
2. Stop Wave F/G/H scripts from appending primary DOM.
3. Prevent fallback and enhanced renderers from flashing sequentially.
4. Preserve in-route disclosure, focus, and scroll state across polling
   refreshes; reset disclosures only on route exit/re-entry.
5. Verify stale-shell behavior with a changed release manifest.

Exit gate: repeated status refreshes produce one stable page with no duplicate
sections or auto-closing UI.

### Stage 8 - Responsive, Accessibility, Print, And Reduced Motion

1. Test desktop, tablet, and phone layouts.
2. Verify keyboard-only navigation.
3. Verify screen-reader heading and status semantics.
4. Verify contrast and non-color state communication.
5. Verify print output and reduced-motion behavior.

Exit gate: all required layouts and accessibility checks pass.

### Stage 9 - Regression And Truth Tests

Add or update checks for:

- view-model schema and deterministic hash;
- exact three-section order;
- one DOM owner;
- no hardcoded mutable counts;
- no hardcoded backend identity;
- provider readiness versus hardware execution;
- simulator versus hardware truth;
- engineering versus market-proof truth;
- current `unproven` / `not_measurable` state;
- proof-state variants, `Classical preferred` comparison, decayed freshness,
  degraded-provider execution, and unavailable-data variants independently;
- no strategy or paper influence without validated evidence;
- zero authority escalation;
- no duplicate Wave sections;
- 13 protected routes and 10 lifecycle stages;
- unchanged Pattern Recognition contracts;
- responsive, accessibility, print, and reduced-motion behavior.

Exit gate: all focused and full dashboard regressions pass together.

### Stage 10 - Documentation And Deployment Discipline

1. Update the User Guide and Whitepaper only after the UI contract passes.
2. Add an implementation log with screenshots, hashes, test results, and current
   truth.
3. Create the clean dashboard integration release from the reviewed descendant
   of dashboard baseline `e23f047` and the reviewed core descendant of baseline
   `634fec59`. Reconcile a newer remote tip explicitly if required; do not
   abandon either approved baseline by switching to `origin/main` blindly.
4. Commit and push before deployment.
5. Make preflight fail closed for a dirty dashboard repository, unpushed commit,
   missing three-section contract, missing lifecycle contract, or authority
   regression.
6. Generate a release manifest with release ID, commit, route count, lifecycle
   count, JS hash, CSS hash, and Quantum Edge contract version.
7. Deploy through the existing Vercel production wrapper.
8. Verify `qadam.trade` and `www.qadam.trade` serve the committed hashes.
9. Verify all direct routes with cache-busting URLs.
10. Verify desktop and mobile rendering in a real browser.

Exit gate: both aliases serve the integrated release and no older bundle has
overwritten lifecycle, Pattern Recognition, or Quantum Edge behavior.

## 14. Required Checkers And Test Coverage

The implementation should extend the existing checks rather than create a
parallel ungoverned test suite.

Core checks:

- `scripts/check_qadam_quantum_edge_page_view_model.py`
- `scripts/check_qadam_quantum_review_dashboard.py`
- `scripts/check_qadam_quantum_discovery_evidence.py`
- `scripts/check_qadam_nonlinear_quantum_value.py`
- `scripts/check_qadam_wave_f_public_view.py`
- `scripts/check_qadam_wave_g_hybrid_loop.py`
- `scripts/check_qadam_wave_h_crude_oil_certification.py`

Frontend checks:

- `scripts/check_dashboard_quantum_edge_three_layer.js`
- `scripts/check_dashboard_quantum_edge_interactions.js`
- `scripts/check_dashboard_quantum_edge_wave_f.js`
- `scripts/check_dashboard_quantum_edge_wave_g.js`
- `scripts/check_dashboard_quantum_edge_wave_h.js`
- `scripts/check_dashboard_ten_stage_lifecycle.js`
- current Pattern Recognition frontend checks;
- current navigation, accessibility, responsive, print, and reduced-motion
  checks.

Unit and integration tests:

- `tests/test_qadam_quantum_edge_page_view_model.py`
- `tests/test_qadam_quantum_edge_page_view_model.py` state variants;
- Wave F/G/H tests;
- lifecycle and Pattern Recognition regression tests;
- browser-level tests for exact header copy and computed typography, primary-row
  order/default collapse/re-entry reset, inline technical disclosure state, and
  refresh stability.

## 15. Acceptance Criteria

The work is complete only when all of the following pass:

1. The page has exactly one Quantum Edge root.
2. The shared 10-stage lifecycle remains present and unchanged.
3. The rendered eyebrow is exactly `Quantum Benchmark Framework` and the title
   is exactly `Quantum Edge`.
4. The rendered subtitle matches the complete locked paragraph in Section 6.2
   character-for-character.
5. Computed title and subtitle typography matches Pattern Recognition at every
   shared responsive breakpoint; desktop computes to 40px / 42px and 16px /
   26.4px respectively at the current root size.
6. The top-right `Current conclusion` card remains visible beside the header on
   desktop and stacks without clipping on smaller screens.
7. The page has exactly three primary overview rows.
8. Their order is Experiment & Evidence, Strategy & Paper Impact, Quantum Edge
   Verdict, with the exact eyebrow and title copy in Section 6.2.1.
9. All three rows are collapsed on initial entry and route re-entry; deep links
   open only their requested row.
10. Every collapsed row displays a meaningful dynamic summary, so the page is
    understandable without opening a tooltip or disclosure.
11. Expanded primary rows contain no nested accordions, nested `details`, or
    additional reveal hierarchy.
12. Classical and quantum lanes visibly share one frozen evidence basis.
13. A result is called a fair comparison only when all eight eligibility
    conditions in Section 6.3.E pass; otherwise no winner is named.
14. Provider readiness cannot be mistaken for hardware execution.
15. Local simulation cannot be mistaken for IBM hardware execution.
16. Engineering success cannot be mistaken for market proof.
17. A prepared manifest cannot be mistaken for a submitted job.
18. A synthetic fixture cannot be mistaken for untouched market evidence.
19. `Classical preferred` is presented as a useful scientific result.
20. The current artifact renders `Unproven` and `Not measurable yet`.
21. Proof, comparison, execution, downstream, and freshness are independently
    represented and tested; no axis silently promotes another.
22. The primary page does not show engineering ratios, market-proof ratios,
    compute footprints, broad platform counts, or a wall of zero metrics.
23. Missing values render unavailable rather than misleading zeros or inferred
    outcomes.
24. No backend identity is shown without canonical completed-run evidence.
25. No strategy or paper-decision influence is claimed without validated
    lineage.
26. The primary consequence section shows exactly four plain-language gates;
    the complete seven-stage record remains intact in technical evidence.
27. Detailed technical evidence is accessible through exactly one full-width
    inline `View technical evidence` disclosure after the primary rows.
28. The technical disclosure is closed on initial entry and route re-entry,
    keyboard accessible, and clearly collapsible while open.
29. Data-only refreshes do not close open disclosures, reset focus, or scroll
    the page; route re-entry intentionally restores the default-closed overview.
30. The browser consumes only the complete generated projection and never
    merges Wave artifacts, legacy trees, or independently calculated facts.
31. The projection has one normalized mutable truth tree; presentation copy is
    derived from and validated against it rather than maintained as a duplicate
    truth source.
32. No Wave-specific primary section flashes or duplicates.
33. The current Pattern Recognition page remains unchanged.
34. Exactly 13 protected dashboard routes remain.
35. Every route still renders one lifecycle with 10 canonical stages.
36. The page remains read-only, paper-only, command-disabled, and unable to
    create authority or execution side effects.
37. Desktop, tablet, mobile, print, and reduced-motion checks pass.
38. The implementation is descended from and preserves the reviewed dashboard
    baseline `e23f047` and core baseline `634fec59`, with any newer integration
    reconciled explicitly.
39. The dashboard and core repositories are clean and pushed before production
    deployment.
40. Both production aliases serve JS and CSS matching the committed hashes and
    pass a real-browser verification of the locked header, collapsed rows,
    inline technical disclosure, and current truth.

## 16. Suggested Implementation Waves

To keep the work modular, execute the stages in four waves:

### Wave A - Truth And Structure

- Stage 0: Baseline And Integration Protection
- Stage 1: Canonical Presentation Projection
- Stage 2: Header And Page Skeleton

### Wave B - Primary Experience

- Stage 3: Experiment & Evidence Comparison
- Stage 4: Strategy & Paper Impact Gatekeeper
- Stage 5: Quantum Edge Verdict

### Wave C - Depth And Quality

- Stage 6: Technical Evidence Surface
- Stage 7: Renderer Consolidation And Refresh Stability
- Stage 8: Responsive, Accessibility, Print, And Reduced Motion

### Wave D - Proof And Release

- Stage 9: Regression And Truth Tests
- Stage 10: Documentation And Deployment Discipline

Each wave must finish with focused checks and a worktree review before the next
wave begins. Deployment occurs only after Wave D passes in full.

## 17. Definition Of Done

Quantum Edge is complete when it functions as Qadam's elegant public proof
room:

- the experiment is understandable;
- the classical and quantum comparison is fair and visible;
- downstream consequences are explicit;
- the verdict is honest;
- the complete audit trail remains available;
- complexity no longer dominates the primary page;
- no scientific or authority boundary has been weakened;
- and the integrated, committed release is verified on both production aliases.
