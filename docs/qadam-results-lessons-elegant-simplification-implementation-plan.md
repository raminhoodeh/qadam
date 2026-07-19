# Qadam Results & Lessons + Tests & Improvements Elegant Simplification Implementation Plan

Date: 2026-07-17

Status: Approved implementation specification. This document does not change
runtime behavior or the public dashboard by itself.

Routes:

- `/dashboard/?module=learn&view=outcomes`
- `/dashboard/?module=learn&view=improvements`

Scope: Replace the current dense Results & Lessons presentation with one
qualitative answer, three strict counters, two collapsed evidence repositories,
and one clear handoff to Tests & Improvements. Apply the same progressive-
disclosure discipline to Tests & Improvements, but organize that page around
what will change, what might change, what has already changed, and what was
declined. Preserve the canonical learning and improvement ledgers, attribution
and approval rules, reference-history separation, 13-route dashboard, 10-stage
lifecycle, and all paper-only authority boundaries.

## 1. Executive Decision

Results & Lessons should answer one question immediately:

> Has Qadam produced an outcome it can legitimately learn from?

The current page exposes the right evidence, but distributes the answer across
the local Stage 9 workflow, current answer, latest learning brief, five metric
tiles, chronological feed, reference history, communications detail, and page
boundary. This makes a simple attribution question feel like a database audit.

The redesigned page will use five vertical sections:

1. **Audit scope** - what this page is responsible for;
2. **Immediate answer** - a qualitative overview of the entire page state;
3. **Three counters** - the only primary quantitative summary;
4. **Evidence repositories** - exactly two collapsed detail areas;
5. **Handoff** - the route from supported lessons to governed testing.

The immediate answer is the narrative focal point. A non-technical visitor
should understand the present result, what evidence exists, what does not yet
exist, what history is excluded, and what happens next without opening a row.
The counters quantify that answer. The repositories provide optional depth.

## 2. Relationship To Existing Qadam Contracts

This plan refines the paired Results & Lessons and Tests & Improvements
presentations. It does not replace or weaken the underlying learning and
governance contracts.

- `docs/qadam-learn-improve-consolidation-implementation-plan.md` remains the
  source contract for the two-page Learn & Improve architecture.
- `docs/qadam-dashboard-ten-stage-lifecycle-implementation-plan.md` remains the
  protected 13-route and 10-stage dashboard contract.
- `docs/qadam-operator-ready-edge-engine-implementation-plan.md` remains the
  canonical evidence-to-strategy-to-paper path.
- `orchestrator/qadam_learning_cycle_view_model.py` remains the canonical
  Results & Lessons public projection builder.
- `data/runtime/qadam_learning_cycle_dashboard.json` remains the canonical
  public-safe page artifact.
- `orchestrator/qadam_improvement_pipeline_view_model.py` remains the canonical
  Tests & Improvements public projection builder.
- `data/runtime/qadam_improvement_pipeline_dashboard.json` remains the
  canonical public-safe improvement artifact.
- Tests & Improvements remains the only dashboard page that explains whether a
  supported lesson has earned the right to change Qadam.

Where this plan conflicts with older presentation details for either Learn &
Improve page, this plan controls the primary page hierarchy and visible copy.
Existing data, lineage, authority, and validation semantics remain controlling.

## 3. Current Truth That Must Survive The Redesign

At the time this plan was written, the canonical public projection reports:

- 44 attribution records in total;
- 2 learnable research or operating events;
- 0 Qadam-origin attributable paper outcomes;
- 0 proof-eligible lessons;
- 1 lesson awaiting a further test;
- 42 broker-mirror records retained as reference-only history;
- the two current learning events are one rejected research hypothesis and one
  operating release held because required evidence or approvals are incomplete;
- no reference-only broker record may become learnable or proof-eligible;
- no learning record can directly change policy, place an order, write to a
  broker, grant proof credit, or enable live capital.

These values are a current snapshot, not permanent copy. Every count and status
must be derived from the canonical artifact at render time. The implementation
must remain truthful when the system later has attributable paper outcomes,
verified lessons, no learning records, stale data, or an unavailable projection.

## 4. Product Goals

### 4.1 Immediate comprehension

Within ten seconds, a visitor should understand:

- whether Qadam has an attributable paper-trading outcome;
- whether Qadam has recorded any research or operating lessons;
- whether any lesson is verified strongly enough to count;
- why historical broker records are visible but excluded;
- that a supported lesson still cannot change Qadam until it passes Tests &
  Improvements.

### 4.2 One answer before detail

The page must lead with a two-to-four sentence qualitative answer written for a
non-technical reader. It must synthesize the page rather than repeat a status
code or narrate a single counter.

The answer must cover five semantic facts:

1. the attribution state;
2. the kind of learning evidence currently present;
3. whether verified trading lessons exist;
4. the treatment of reference-only history;
5. the next governed step.

### 4.3 Controlled information density

After the qualitative answer, the primary page may show only:

- three counters;
- two collapsed evidence repositories;
- one navigation handoff.

No additional brief card, local workflow strip, five-tile metric grid,
communications card, open chronological feed, or repeated page-level safety
paragraph may compete with that structure.

### 4.4 Honest attribution

The page must distinguish:

- a Qadam-origin paper outcome from broker-mirror history;
- a research or operating lesson from a trading-performance lesson;
- a supported lesson from a proof-eligible lesson;
- a lesson from an approved system update;
- an empty attributable track record from an inactive system.

### 4.5 Progressive disclosure

Both evidence repositories are collapsed by default. Opening either repository
must reveal useful plain-English records without introducing another nested
accordion hierarchy. User-opened repositories must remain open through
automatic data refreshes until the user closes them or leaves the route.

## 5. Non-Goals

This work must not:

- change attribution, proof eligibility, postmortem, or learning approval rules;
- turn broker-mirror records into Qadam-origin outcomes;
- call the two current learning events completed paper-trading lessons;
- call reference-only records contaminated, failed, suspicious, or invalid;
- imply that Results & Lessons approves a strategy or system update;
- create or approve an improvement proposal;
- alter the Tests & Improvements page except for the inbound handoff label;
- remove the global 10-stage lifecycle or change its stage ownership;
- introduce live-capital language, live broker routes, or broker-write controls;
- expose secrets, credentials, private prompts, raw provider payloads, or
  non-public evidence;
- hardcode the current `2 / 0 / 42` snapshot into the frontend;
- remove the complete canonical audit record from runtime artifacts or tests.

## 6. Target Information Architecture

The Results & Lessons body must render these five sections in this exact order.

### 6.1 Section One: Header Block - The Audit Scope

Keep the shared compact 10-stage lifecycle above the page body. Stage 9 may
remain visible there once as orientation. Remove repeated `Stage 9` language
from the page body.

Use this locked page copy:

- eyebrow: `Performance Attribution & Governance`;
- title: `What Qadam Learned`;
- subtitle:

  > The Learning Engine looks backward: Qadam separates its own attributable
  > outcomes from reference history, compares expectation with reality, and
  > records only lessons the evidence can support.

The title and subtitle must retain typography parity with the neighboring
dashboard page headers. Do not add a separate governing-question card or repeat
the subtitle in a second paragraph.

Directly below the subtitle, render one crimson text disclosure:

`How an outcome becomes a supported lesson +`

It is collapsed by default. Opening it reveals one concise four-step sequence:

1. **Attribute the outcome** - establish whether the event came from Qadam's
   own research and paper-decision path.
2. **Compare expectation with reality** - compare what Qadam expected with what
   actually happened.
3. **Record only the supported lesson** - refuse conclusions that incomplete
   evidence cannot justify.
4. **Send the lesson to testing** - pass the lesson to Tests & Improvements;
   do not change Qadam automatically.

Do not label this disclosure `How a trade outcome becomes an approved update`.
Results & Lessons can establish a supported lesson, but only the next page can
govern a proposed update.

### 6.2 Section Two: The Accountability Answer

Render one prominent, full-width accountability banner immediately below the
header. This is the primary narrative focal point of the page.

The banner contains:

- a short status eyebrow: `Attribution status`;
- one dynamic headline;
- one dynamic, two-to-four sentence qualitative overview;
- no raw state code, artifact name, stage number, proof-ledger terminology, or
  implementation identifier.

For the current canonical state, the headline should be:

> Waiting for the first complete Qadam paper outcome

The current-state overview should communicate this meaning:

> Qadam has recorded research and operating lessons, but it has not yet
> completed a paper trade with complete research-to-execution evidence that
> can support an official judgment of its trading decisions. Historical broker
> records are available for context only and do not count toward Qadam's track
> record. Any supported lesson must still pass testing and review before it can
> change the system.

The exact generated wording may adapt to the data, but it must remain within
the same semantic and readability contract.

#### 6.2.1 Qualitative-answer rules

The immediate answer must:

- answer the attribution question in its first sentence;
- explain the nature of current learning records without calling every record a
  trade outcome;
- state whether verified lessons exist;
- explain reference-only history in ordinary language;
- state the next governed action;
- use no more than four sentences and approximately 55 to 100 words;
- avoid repeating all three numerical counter values unless a number is needed
  to prevent ambiguity;
- avoid `idle state`, `zero track record`, `mathematical judgment`, `live
  pipeline outcome`, `proof credit`, `algorithmic proof`, `PaperOps`, and raw
  lifecycle-state language;
- never imply that the absence of an attributable outcome means Qadam is not
  scanning, researching, testing, or operating;
- never imply that a supported research lesson proves trading performance.

#### 6.2.2 Dynamic answer-state matrix

The canonical projection must select the answer from explicit dimensions, not
from a single overloaded status string.

| Condition | Headline | Required meaning |
| --- | --- | --- |
| Projection missing or stale beyond policy | `Learning status is temporarily unavailable` | The page cannot confirm a current answer; last known records remain read-only. |
| `qadam_origin_outcome_count = 0` | `Waiting for the first complete Qadam paper outcome` | Research or operating lessons may exist, but Qadam cannot yet judge its paper-trading decisions. |
| Attributable outcomes exist and `proof_eligible_count = 0` | `Paper outcomes recorded; lessons still under review` | Qadam has outcomes, but the evidence is not complete enough for a verified lesson. |
| `proof_eligible_count > 0` and lessons await testing | `Verified lessons are ready for testing` | Supported, attributable lessons exist but cannot change Qadam until the next page approves a version. |
| Verified lessons exist and none await testing | `Verified lessons recorded` | The page has completed its attribution role; update status belongs to Tests & Improvements. |

If multiple conditions apply, choose the most conservative truthful headline.
The body may explain the other dimensions.

#### 6.2.3 Visual treatment

Use a neutral institutional surface with a restrained crimson structural rule.
Do not use an emoji headline. The banner must not resemble a trading alert,
success celebration, or emergency warning. Tone color may reflect availability
or evidence state, but the text must carry the meaning.

### 6.3 Section Three: Three Strict Counters

Render exactly three compact metric boxes in one horizontal row on desktop and
one stacked column on narrow mobile screens.

| Visible label | Subtitle | Canonical binding | Current value |
| --- | --- | --- | --- |
| `What Qadam is learning` | `Learning reviews recorded` | `counts.learnable_event_count` | 2 |
| `Verified lessons` | `Complete, attributable evidence` | `counts.proof_eligible_count` | 0 |
| `Reference trade history` | `Excluded from Qadam performance` | `counts.mirror_reference_count` | 42 |

Rules:

- counts are always dynamic;
- each box contains one label, one number, and one subtitle;
- do not add secondary numbers inside a box;
- do not show attribution-record totals, record-kind totals, lessons-awaiting-
  test totals, or Qadam-origin totals in the primary metric row;
- do not use `Verified Algorithmic Proof` or `Background Account History`;
- the counter row owns quantitative summary; later sections may repeat a count
  only once in an accordion label to communicate repository size;
- a missing count renders `Not available`, never `0` by assumption.

### 6.4 Section Four: Two Evidence Repositories

Render exactly two top-level repository disclosures. Both are closed on route
entry.

#### 6.4.1 Repository A: Learning Reviews

Collapsed label:

`Learning Reviews ({learnable_event_count}) +`

Collapsed summary:

`Research, operating, and paper-outcome records Qadam is allowed to examine.`

Do not call this repository `Open Research Notes`: not every current record is
research and not every record is open.

When opened, render a flat chronological list of learnable records. Dedupe
`learnable_outcomes` and `learning_events` by stable `record_id` before
rendering.

Each record must show:

- sequence number and date;
- plain-English record type;
- concise title;
- `What happened`;
- `What Qadam can legitimately learn`;
- `Why it stopped or remains under review`;
- `What happens next`;
- a simple state label such as `Held for evidence`, `Stopped after review`,
  `Ready for testing`, or `Verified lesson`.

For the current two records, the titles should communicate:

1. `Research idea stopped before practical testing`;
2. `Research cycle held while required evidence remained incomplete`.

Do not describe both records as trades or as unvalidated trading ideas. One is a
research veto and one is an operating-readiness event.

No nested `<details>` or nested accordion is allowed inside this repository.
Technical IDs, raw component-attribution maps, authority booleans, and artifact
paths remain preserved in the canonical data and tests but do not enter the
primary public reading flow.

If more than seven learning reviews exist:

- render the newest seven initially;
- append seven more when the user chooses `View More +`;
- keep already visible rows stable during data refresh;
- announce the new visible count to assistive technology;
- do not silently collapse the repository or reset the list while the user is
  reading it.

#### 6.4.2 Repository B: Reference Broker History

Collapsed label:

`Reference Broker History ({mirror_reference_count}) +`

Collapsed summary:

`Past broker records retained for context but excluded from Qadam's official
performance and learning record.`

Do not call this repository `Quarantined Broker Mirror Archive`. The records are
not suspicious or invalid; they lack the complete Qadam decision lineage needed
for attribution.

When opened, show this note once:

> These records are retained for historical context but excluded from Qadam's
> official performance and learning record because their complete
> research-to-execution lineage is unavailable.

Render a compact, read-only chronological list. Each record may show only
public-safe fields actually present in the canonical source, such as:

- date;
- instrument, action, quantity, or outcome when exported;
- a concise `Reference only` state;
- a short explanation that no Qadam thesis is attached.

Do not invent an instrument, side, quantity, P&L, or timestamp when the source
does not export it. Prefer omitting an unavailable field over showing a dense
`not recorded` grid.

Render seven records initially and append seven at a time through `View More +`.
The repository must not render all 42 records as full-height cards on initial
open.

#### 6.4.3 Disclosure-state contract

Both repositories and the header explainer must:

- be keyboard operable;
- expose `aria-expanded` and clear accessible names;
- be collapsed on first route entry;
- stay open or closed according to the user's choice during polling and
  data-only rerenders;
- use stable keys rather than array positions;
- reset to the default collapsed state only after the user leaves and later
  re-enters the route;
- never open or close because a count, timestamp, or status refreshed;
- use the same crimson disclosure label and arrow treatment as the approved
  Data Sources and Pattern Recognition details controls.

### 6.5 Section Five: Handoff Gateway

At the absolute bottom of the Results & Lessons body, render one clear route
action:

`Continue to Tests & Improvements ->`

Supporting sentence:

`See whether a supported lesson survives testing, review, and version approval
before it can change Qadam.`

The link must use the canonical dashboard route helper for:

- module: `learn`;
- view: `improvements`.

Do not use `Proceed to System Improvement & Testing`: it does not match the
protected navigation label. Do not call the handoff an approval.

## 7. Visible Copy Translation Contract

Remove or replace the following body copy:

| Current or proposed wording | Required replacement |
| --- | --- |
| `Stage 9 looks backward` | `The Learning Engine looks backward` |
| `Inside Stage 9: turn outcomes into supported lessons` | `How an outcome becomes a supported lesson` |
| `Inside Stage 9 - Chronological learning record` | `Learning review history` |
| `Stage 9 - Outcome or research event` | Plain record type, such as `Research idea stopped` |
| `Handoff to Stage 10 - Proposed improvement` | `What happens next` |
| `Continue to Stage 10 - Improve and Re-enter` | `Continue to Tests & Improvements` |
| `Idle State (Zero Track Record)` | `Waiting for the first complete Qadam paper outcome` |
| `live pipeline outcomes` | `complete attributable paper outcomes` |
| `Verified Algorithmic Proof` | `Verified lessons` |
| `Quarantined Broker Mirror Archive` | `Reference Broker History` |
| `data contamination` | `excluded so incomplete history does not distort Qadam's performance record` |

Do not use `Empirical History` or `Verified Audit History` as the learning-list
heading while no proof-eligible trading lesson exists. Those phrases overstate
the present evidence.

## 8. Canonical View-Model Changes

Extend `orchestrator/qadam_learning_cycle_view_model.py` so the browser receives
an explicit page projection instead of reconstructing meaning from raw records.

Preserve all existing fields for backward compatibility during migration. Add
a presentation block with a versioned contract similar to:

```json
{
  "presentation_contract_version": "qadam_results_lessons.v2",
  "page_copy": {
    "eyebrow": "Performance Attribution & Governance",
    "title": "What Qadam Learned",
    "subtitle": "The Learning Engine looks backward: ..."
  },
  "immediate_answer": {
    "state": "waiting_for_attributable_paper_outcome",
    "tone": "pending",
    "eyebrow": "Attribution status",
    "headline": "Waiting for the first complete Qadam paper outcome",
    "summary": "Qadam has recorded research and operating lessons, but ...",
    "generated_from": {
      "qadam_origin_outcome_count": 0,
      "learnable_event_count": 2,
      "proof_eligible_count": 0,
      "mirror_reference_count": 42
    }
  },
  "metric_groups": [
    {
      "id": "learning_reviews",
      "label": "What Qadam is learning",
      "subtitle": "Learning reviews recorded",
      "value": 2
    }
  ],
  "repositories": {
    "learning_reviews": {
      "count": 2,
      "records": []
    },
    "reference_history": {
      "count": 42,
      "records": []
    }
  },
  "handoff": {
    "label": "Continue to Tests & Improvements",
    "module_id": "learn",
    "view_id": "improvements"
  }
}
```

### 8.1 Immediate-answer builder

Implement one deterministic backend function that:

- accepts normalized counts, freshness, and record-kind summaries;
- selects one state from the matrix in section 6.2.2;
- returns the headline and qualitative summary;
- never calls an LLM at page-render time;
- never copies the latest Telegram brief into the accountability answer;
- never treats reference records as Qadam outcomes;
- validates sentence count and required semantic dimensions;
- remains public-safe and deterministic for tests.

### 8.2 Record projection

Project each learning review into explicit display fields:

- `record_id`;
- `occurred_at`;
- `display_type`;
- `title`;
- `what_happened`;
- `supported_lesson`;
- `blocker_or_hold_reason`;
- `next_action`;
- `state`;
- `tone`.

Project each reference record into only fields backed by the source. Include a
shared repository-level exclusion explanation instead of repeating the same
compliance sentence in all 42 rows.

### 8.3 Validation rules

Extend the model validator to fail when:

- the three metric groups are missing, duplicated, or bound to the wrong count;
- reference count differs from the reference-record array;
- a reference record becomes learnable or proof-eligible;
- immediate-answer state contradicts `qadam_origin_outcome_count`;
- the answer calls an unavailable count zero;
- the handoff targets anything other than `learn/improvements`;
- the page projection permits commands, policy changes, orders, broker writes,
  proof credit, or live capital.

## 9. Frontend Renderer Changes

Refactor `renderQsaseResultsAndLessons` in
`landing-page-repo/dashboard.js` around five focused renderers:

1. `renderQsaseLearningHeader`;
2. `renderQsaseLearningAnswer`;
3. `renderQsaseLearningCounters`;
4. `renderQsaseLearningRepositories`;
5. `renderQsaseLearningHandoff`.

### 9.1 Remove from the primary page

Remove these current primary blocks from Results & Lessons:

- `renderQsaseLearningStageFlow(learning, "results")`;
- separate `Latest learning brief` card;
- five-tile `.qsase-learning-metrics` layout;
- always-open `.qsase-learning-feed`;
- separate communications disclosure;
- repeated page-boundary paragraph when the shared dashboard footer already
  communicates the read-only paper boundary;
- all visible `Stage 9` labels outside the shared lifecycle.

Do not delete their canonical source data merely because it leaves the primary
page. Communication state and detailed lineage remain available to internal
checks and runtime artifacts.

### 9.2 Repository rendering

Use native `<details>` and `<summary>` for the three disclosures: the header
explainer and the two repositories. The repository content itself must be flat;
do not nest another `<details>` per record.

Use one page-scoped interaction state object keyed by:

- `learning_scope`;
- `learning_reviews`;
- `reference_history`;
- visible review count;
- visible reference count.

Capture the state before a polling rerender and restore it after the new model
is mounted. Never use count values as element keys.

### 9.3 Defensive rendering

If the v2 presentation block is absent during rollout, render a conservative
compatibility answer from existing counts. Do not restore the legacy dense
layout. Mark missing values as unavailable, and retain read-only boundaries.

## 10. Visual Design

### 10.1 Page rhythm

Use a single vertical reading column with restrained spacing:

- compact header;
- 24px to accountability answer;
- 16px to counters;
- 24px to repositories;
- 32px to handoff.

Do not wrap each explanatory sentence in a separate card. The accountability
banner is the only prominent narrative surface.

### 10.2 Accountability banner

- full width;
- neutral white or existing pale institutional surface;
- restrained crimson left or top rule;
- no rounded marketing-card treatment;
- headline sized below the page title;
- summary constrained to a readable line length;
- state tone conveyed through a small accessible label, not a large colored
  chip wall.

### 10.3 Counter row

- three equal tracks on desktop;
- one column on mobile;
- stable minimum height;
- tabular numerals;
- no oversized hero numbers;
- labels never truncate or wrap one word per line.

### 10.4 Repository rows

Match the approved Data Sources and Pattern Recognition disclosure language:

- crimson `Expand Details`-style control treatment;
- familiar downward arrow that rotates when open;
- red or crimson structural border on open state;
- clear focus ring;
- no folder emoji in production copy;
- compact record dividers rather than nested cards.

### 10.5 Handoff

Use one professional full-width or right-aligned action row matching the
dashboard's existing next-page navigation pattern. It must look navigational,
not like a trade command or approval button.

## 11. Accessibility And Responsive Requirements

The implementation must satisfy:

- WCAG 2.2 AA contrast for text, borders, focus states, and status tones;
- keyboard operation for every disclosure, `View More +`, and handoff link;
- visible focus states;
- semantic heading order with one page `h1`;
- summaries exposed as buttons by native disclosure behavior;
- `aria-live="polite"` only for the immediate answer when refreshed, without
  announcing the entire page;
- no automatic focus movement after refresh;
- no content collapse during refresh;
- 44px minimum touch targets on mobile;
- no horizontal page scrolling at 320px, 375px, 768px, 1024px, or desktop;
- counter and record text that reflows without clipping;
- print output that shows the immediate answer and counters, then prints both
  repository headings with a concise exclusion note without dumping all 42
  technical records by default;
- reduced-motion behavior for arrows and state transitions.

## 12. Testing Strategy

### 12.1 Python view-model tests

Extend `tests/test_qadam_learning_cycle.py` to cover:

1. the current `2 / 0 / 42` state;
2. no learning events and no attributable outcomes;
3. attributable outcomes with no proof-eligible lesson;
4. at least one proof-eligible lesson awaiting testing;
5. verified lessons with no pending test;
6. stale or unavailable projection;
7. reference records remain non-learnable and non-proof-eligible;
8. immediate-answer state never contradicts counts;
9. exactly three metric groups with correct bindings;
10. exactly two repositories with correct counts;
11. all public authority booleans remain false;
12. the handoff remains `learn/improvements`.

### 12.2 Frontend contract tests

Update `scripts/check_dashboard_learn_improve_consolidation.js` and related
dashboard checks to assert:

- the locked eyebrow, title, and subtitle;
- one qualitative accountability answer;
- exactly three primary counter boxes;
- exactly two evidence repositories;
- both repositories are closed by default;
- the header explainer is closed by default;
- no visible Results & Lessons body copy contains `Stage 9`;
- no `Latest learning brief` card;
- no separate communication disclosure;
- no five-tile metrics grid;
- no always-open chronological feed;
- no nested details inside either repository;
- `View More +` reveals seven additional records;
- open state and pagination survive a data-only rerender;
- the handoff targets Tests & Improvements;
- reference history cannot be presented as Qadam performance;
- route count remains 13;
- the protected Learn & Improve two-page navigation remains intact.

### 12.3 Copy-quality tests

Add a narrow anti-slop assertion that rejects these visible phrases on the page:

- `Idle State (Zero Track Record)`;
- `Verified Algorithmic Proof`;
- `Quarantined Broker Mirror Archive`;
- `data contamination`;
- `live pipeline outcomes`;
- `proof credit`;
- `Inside Stage 9`;
- `Handoff to Stage 10`.

The test must not ban those strings from historical docs or internal artifacts;
scope it to rendered Results & Lessons HTML.

### 12.4 Browser acceptance

Verify in a real browser:

- desktop and mobile layout;
- the answer can be understood without opening a disclosure;
- initial disclosure states;
- keyboard operation;
- disclosure persistence across at least two automatic refreshes;
- incremental `View More +` behavior;
- no horizontal overflow;
- no clipped tooltips or arrows;
- correct direct-route loading;
- back and forward navigation;
- handoff to Tests & Improvements;
- print and reduced-motion modes.

## 13. Documentation Alignment

Update these documents when implementation begins:

- `docs/qadam-user-guide.md`;
- `docs/qadam-learn-improve-consolidation-implementation-plan.md` with a short
  pointer to this controlling page simplification;
- `docs/qadam-dashboard-ten-stage-lifecycle-implementation-log.md` with
  implementation evidence;
- any dashboard acceptance matrix that names the removed Stage 9 body blocks.

The User Guide should explain the page in the same five-part order and state:

- Results & Lessons decides what Qadam may legitimately conclude;
- it does not approve changes;
- broker-mirror history is context only;
- Tests & Improvements owns proposed changes and version approval.

## 14. Implementation Stages

### Stage R1: Baseline Protection

- record both repository statuses and current commits;
- preserve all unrelated dirty and untracked work;
- capture current desktop and mobile Results & Lessons screenshots;
- export the current `2 / 0 / 42` canonical snapshot;
- run the existing learning-cycle and dashboard checks before editing.

Exit criterion: the current behavior and pre-existing failures are documented.

### Stage R2: Canonical Presentation Projection

- add the v2 presentation contract;
- implement the qualitative-answer state matrix;
- add normalized learning-review display fields;
- add normalized reference-history display fields;
- retain backward-compatible source fields;
- extend validator and Python tests.

Exit criterion: the artifact supplies the complete five-section view without
frontend inference.

### Stage R3: Five-Section Renderer

- replace the current Results & Lessons body with the locked header,
  accountability answer, three counters, two repositories, and handoff;
- remove duplicated Stage 9 and learning-brief surfaces from the page;
- preserve the Tests & Improvements renderer;
- implement seven-at-a-time loading.

Exit criterion: rendered HTML contains exactly the intended primary hierarchy.

### Stage R4: Interaction Persistence

- preserve disclosure and pagination state through polling rerenders;
- reset state only on route exit and re-entry;
- add keyboard and assistive announcements;
- test stale and changing-count snapshots.

Exit criterion: user-opened content never closes itself during a refresh.

### Stage R5: Visual And Responsive Polish

- implement accountability-banner styling;
- implement the three-column counter row;
- align disclosure controls with Data Sources and Pattern Recognition;
- verify mobile, print, focus, and reduced-motion behavior.

Exit criterion: the page is calm, readable, and consistent across dashboard
modules.

### Stage R6: Regression And Documentation

- update frontend and backend acceptance checks;
- run the protected 13-route, lifecycle, navigation, accessibility, responsive,
  print, reduced-motion, authority, and deployment-preflight suites;
- update User Guide and implementation logs;
- verify no source or authority regression.

Exit criterion: the simplification passes together with the existing dashboard
and paper-only contracts.

### Stage R7: Committed Release And Production Verification

- integrate only after all checks pass;
- commit scoped core and dashboard changes without including unrelated work;
- push the dashboard release commit before deployment;
- deploy through the guarded production script;
- verify both production aliases, asset hashes, direct route, mobile rendering,
  and served copy;
- record release evidence in the deployment receipt and implementation log.

Exit criterion: production serves the committed simplified page and no older
bundle has overwritten it.

## 15. Acceptance Criteria

Implementation is complete only when all of the following pass together:

1. The page retains the protected Results & Lessons route and sidebar position.
2. The shared 10-stage lifecycle remains available at the top.
3. No `Stage 9` wording appears in the Results & Lessons body.
4. The locked eyebrow, title, and subtitle render exactly.
5. The immediate answer appears directly below the header.
6. A non-technical reader can understand attribution state, present evidence,
   exclusion of history, and next step from that answer alone.
7. The answer is deterministic, public-safe, and generated from canonical data.
8. The current state does not call Qadam idle or imply live-capital operation.
9. Exactly three primary counters render.
10. The three counters bind to learnable events, proof-eligible lessons, and
    reference-only records respectively.
11. Missing data is not silently rendered as zero.
12. Exactly two evidence repositories render.
13. Both repositories and the header explainer are collapsed on route entry.
14. User-opened disclosures remain open through automatic refresh.
15. Learning Reviews distinguishes research, operating, and paper outcomes.
16. Reference Broker History explains exclusion once, in plain English.
17. Reference records remain non-learnable and non-proof-eligible.
18. Neither repository contains nested accordions.
19. Lists initially show at most seven records.
20. `View More +` appends seven records without collapsing content.
21. The Latest Learning Brief is absent as a separate primary block.
22. Communications metadata is absent as a separate primary block.
23. The five-tile metric grid and open chronological feed are absent.
24. The only bottom action is `Continue to Tests & Improvements ->`.
25. Results & Lessons never implies that it approves an update.
26. The Tests & Improvements page and its route remain functional.
27. The dashboard remains read-only, command-disabled, paper-only, and unable
    to create approvals, trades, broker writes, proof credit, or live capital.
28. Desktop, mobile, keyboard, print, and reduced-motion checks pass.
29. All protected 13-route and 10-stage lifecycle checks pass.
30. Production aliases serve the committed release after deployment.

## 16. Final Page Reading Experience

The finished page should read naturally from top to bottom:

1. **What this page audits** - attribution and supported learning.
2. **What the answer is right now** - Qadam has learning evidence but not yet an
   attributable paper-trading performance outcome.
3. **How much evidence exists** - three clear counts.
4. **What sits behind the answer** - optional learning reviews and reference
   history.
5. **What happens next** - supported lessons move to governed testing.

The page should feel like an honest performance review, not a technical
appendix. It should make the absence of a verified trading lesson understandable
without making the system appear inactive, and it should preserve every audit
boundary without forcing a non-technical visitor to read it all.

# Part II: Tests & Improvements

## 17. Companion Page Executive Decision

Tests & Improvements should answer one downstream question immediately:

> What will actually change in Qadam?

The page must not lead with Qadam's internal six-step improvement machinery.
It must lead with the integration decision. A visitor should be able to
distinguish, without opening any row:

- improvements that are approved and scheduled to enter Qadam;
- ideas that could improve Qadam but are still being evaluated;
- changes that are already active;
- proposals that Qadam declined, retired, rolled back, or otherwise refused to
  integrate.

The organizing principle is **certainty of change**, not test chronology.

Use four public states throughout the page:

| Public state | Meaning |
| --- | --- |
| `Scheduled` | Approved, versioned, assigned to a destination, and prepared for a defined activation. |
| `Under evaluation` | Could change Qadam, but required evidence or review is incomplete. |
| `Integrated` | Approved version is active and has a recorded effective time and monitoring rule. |
| `Not proceeding` | Rejected, retired, rolled back, or otherwise closed without integration. |

Internal states such as `needs_data`, `testing`, `shadowing`,
`ready_for_review`, `inert_until_applied`, and `not_started_no_eligible_hypothesis`
may continue to govern the backend. They must be translated before reaching the
primary public page.

## 18. Current Truth That Must Survive The Redesign

At the time this companion specification was written, the canonical improvement
projection reports:

- 2 improvement proposal records in total;
- 1 proposal remains active because more evidence is needed;
- 1 earlier proposal was rejected;
- 0 proposals are ready for review;
- 0 changes are approved and scheduled for integration;
- 0 applied versions are currently exported;
- the active proposal is an operating-evidence improvement, not an approved
  trading-strategy change;
- historical testing has not started for the active proposal;
- real-time no-order observation has not started for the active proposal;
- review remains waiting for evidence;
- the current Qadam strategy and system behavior remain unchanged.

The current values are not permanent copy. All counts, records, summaries, and
integration decisions must come from the canonical improvement projection at
render time.

The current qualitative answer should communicate this meaning:

> Nothing is currently scheduled to change. Qadam is still gathering evidence
> for an operational improvement, while an earlier data-repair proposal was
> rejected. Nothing is ready for review or approved for use. Historical testing
> and real-time no-order observation must be completed before any change can be
> considered, so Qadam will continue using its current behavior.

## 19. Product Goals

### 19.1 Change-roadmap clarity

Within ten seconds, a visitor should understand:

- whether any change is definitely scheduled;
- what the scheduled change will do;
- which part of Qadam it will affect;
- when it will become active;
- what is merely under evaluation;
- what has already been integrated;
- why Qadam remains unchanged when evidence is incomplete.

### 19.2 Promises require approval evidence

The UI may use `will change`, `scheduled`, `coming next`, or `next version` only
when all required integration fields are complete. Research intent is not a
release commitment.

### 19.3 One roadmap, not three engineering consoles

Historical tests, forward observations, review, approval, versioning, and
rollback remain necessary. They should support the improvement record rather
than appear as six equal technical cards on the primary page.

### 19.4 Direct relationship to Results & Lessons

Every improvement must link back to a supported Results & Lessons record.
Results & Lessons establishes what Qadam may conclude. Tests & Improvements
decides whether that conclusion justifies a versioned change.

### 19.5 Progressive disclosure

The primary page contains:

- one concise header;
- one qualitative answer;
- one visible Next Qadam Version area;
- three counters;
- two collapsed repositories;
- one next-cycle decision.

Detailed proposal and testing records remain available only after the user asks
for them.

## 20. Non-Goals

This work must not:

- label an active or ready-for-review proposal as scheduled;
- call evidence collection completed testing;
- treat an expected benefit as a measured result;
- infer approval from a proposal state;
- create approval, assign a version, choose an activation date, or apply a
  change from the dashboard;
- mutate strategy weights, source rules, filters, risk limits, code, operations,
  policy, or broker behavior;
- turn rejected or reference-only records into active proposals;
- display hypothetical destinations as though they will change;
- remove complete testing, approval, monitoring, or rollback evidence from the
  canonical runtime artifacts;
- weaken the requirement that an applied version has approval, effective time,
  expected behavior, monitoring window, and rollback condition;
- introduce live-capital authority, broker writes, proof credit, or commands;
- hardcode the current `0 scheduled / 1 under evaluation / 0 integrated` state.

## 21. Tests & Improvements Target Information Architecture

Render the page in this order.

### 21.1 Shared lifecycle context

Keep the compact shared 10-stage lifecycle above the page body. Stage 10 may
appear there once for orientation. Remove repeated `Stage 10` language from the
body, proposal cards, test labels, and next-cycle section.

### 21.2 Header block

Use this locked visible copy:

- eyebrow: `Tests & Improvements`;
- title: `What Will Change in Qadam`;
- subtitle:

  > See which improvements are approved for integration, which are still being
  > evaluated, and which changes are already in use.

The title and subtitle must use the same typography tokens as Results & Lessons
and the neighboring dashboard pages.

Directly beneath the subtitle, render one crimson text disclosure:

`How a lesson earns the right to change Qadam +`

It is collapsed by default. Opening it reveals four plain-language gates:

1. **Define one measurable change** - connect one supported lesson to one
   specific proposed change and affected part of Qadam.
2. **Test it against historical evidence** - determine whether the change holds
   up out of sample, after realistic costs and failure controls.
3. **Observe it in real time without placing orders** - watch the proposed
   behavior forward without letting it affect the portfolio.
4. **Approve, reject, or continue testing** - only an approved, versioned change
   with monitoring and rollback rules may enter Qadam.

Do not render the existing permanent local Stage 10 workflow strip in addition
to this disclosure.

### 21.3 Immediate answer and Next Qadam Version

Render one full-width change-status banner immediately below the header.

The banner contains:

- status eyebrow: `Integration status`;
- one dynamic headline;
- one two-to-four sentence qualitative overview;
- a visible `Next Qadam Version` area directly beneath the overview.

For the current projection, the headline is:

> Nothing is currently scheduled to change

The qualitative overview must cover:

- whether anything is scheduled;
- whether an improvement is under evaluation;
- whether anything is ready for review;
- whether anything has already been integrated;
- why current behavior remains unchanged;
- the next evidence step.

It must use no more than four sentences and approximately 50 to 100 words.
It must not narrate every database count because the counter row owns the
numbers.

#### 21.3.1 Dynamic integration-answer matrix

| Condition | Headline | Required meaning |
| --- | --- | --- |
| Projection unavailable or stale beyond policy | `Improvement status is temporarily unavailable` | Do not infer that zero changes exist. Preserve last known records as read-only. |
| `scheduled_integration_count > 0` | `A new Qadam version is scheduled` | State what will change, where, and when. |
| No scheduled change and `under_evaluation_count > 0` | `Nothing is currently scheduled to change` | Explain what is still being evaluated and why it cannot advance. |
| No scheduled or active change and `integrated_count > 0` | `No further change is scheduled` | Current applied versions remain in use; no new release is queued. |
| No proposal or applied history | `No improvement proposal is currently active` | Qadam continues its current behavior until a supported lesson produces a proposal. |

Choose the most conservative truthful state when records disagree.

#### 21.3.2 Next Qadam Version empty state

When no scheduled change passes the strict scheduling contract, show:

> **No approved changes are scheduled**
>
> Qadam's next operating cycle will continue using the current version.

Do not show placeholder version numbers, hypothetical destinations, or expected
activation dates.

#### 21.3.3 Next Qadam Version scheduled-change contract

When one or more changes are genuinely scheduled, each visible change must
show:

- **What will change**;
- **Part of Qadam affected**;
- **Why it is changing**;
- **Evidence that justified it**;
- **Target version**;
- **Activation date or explicit activation condition**;
- **Monitoring window**;
- **Rollback condition**;
- **Destination page**.

Scheduled changes should be ordered by activation time, then stable proposal
ID. Do not celebrate a scheduled change as successful before monitoring has
completed.

#### 21.3.4 Strict scheduling predicate

Derive `Scheduled` only when all of the following are true:

1. approval explicitly records `approved = true`;
2. an approver and approval timestamp are recorded;
3. a non-placeholder target version is recorded;
4. the affected component or destination is recorded;
5. an effective time or governed activation condition is recorded;
6. expected behavior is recorded;
7. a monitoring window is recorded;
8. a rollback condition is recorded;
9. the record is not rejected, retired, rolled back, or already applied;
10. public authority remains read-only and command-disabled.

A proposal that is `ready_for_review` is not scheduled. A proposal marked
`approved` without the complete release record is not scheduled. Missing data
must fail closed to `Under evaluation` or `Status unavailable`.

### 21.4 Three change counters

Render exactly three compact counters:

| Visible label | Subtitle | Canonical binding | Current value |
| --- | --- | --- | --- |
| `Scheduled for integration` | `Approved future changes` | `counts.scheduled_integration_count` | 0 |
| `Still under evaluation` | `Possible future improvements` | `counts.under_evaluation_count` | 1 |
| `Already integrated` | `Approved versions now in use` | `counts.integrated_count` | 0 |

Rules:

- counts are always dynamic;
- missing counts render `Not available`, never an assumed zero;
- rejected proposals do not appear in `Still under evaluation`;
- ready-for-review proposals remain under evaluation until approved and fully
  scheduled;
- applied versions are not counted as scheduled;
- do not render provider partitions, test paths, forward observations, proposal
  totals, excluded mirror records, or validated-edge counts as first-screen
  metrics.

### 21.5 Repository A: Possible Future Improvements

Collapsed label:

`Possible Future Improvements ({under_evaluation_count}) +`

Collapsed summary:

`Changes Qadam is investigating but has not approved or scheduled.`

Both the label and summary must make uncertainty explicit.

Each collapsed proposal row shows:

- proposal title in plain English;
- affected part of Qadam;
- current public state: `Under evaluation`;
- one concise reason it is not scheduled;
- `Expand Details` with the shared crimson arrow treatment.

Opening a row reveals one flat explanation:

- **Lesson behind it** - what Results & Lessons established;
- **What could change** - the exact proposed behavior difference;
- **Part of Qadam affected** - strategy, data, filter, risk, system, code, or
  operations;
- **Why it may help** - the expected benefit, clearly labelled as an expectation;
- **Historical evidence** - not started, underway, complete, or failed;
- **Real-time observation** - not started, underway, complete, or failed;
- **Current conclusion** - continue testing, hold, or ready for review;
- **What blocks integration** - plain-language evidence gap;
- **Next action** - one concrete next step;
- **What happens until then** - current Qadam behavior remains unchanged.

Do not render six nested Stage 10 cards. Use one shallow four-gate progress row
inside the expanded record:

`Change defined -> Historical evidence -> Forward observation -> Review`

Technical partition counts, statistical paths, holdout diagnostics, quantum
incremental-value fields, artifact IDs, and raw authority maps remain preserved
in canonical artifacts and tests. They do not receive equal visual weight on
the public page.

The current active proposal must be labelled as an **operational evidence
improvement**. It must not be presented as a trading-strategy update or as being
actively tested when historical and forward tests have not started.

### 21.6 Repository B: Previous Improvement Decisions

Collapsed label:

`Previous Improvement Decisions ({decision_history_count}) +`

Collapsed summary:

`Changes Qadam integrated, rejected, retired, held closed, or rolled back.`

This repository replaces separate `Stopped or held proposals` and `Applied
version ledger` accordions.

Each record shows:

- decision date;
- proposal title;
- final public state: `Integrated` or `Not proceeding`;
- plain-English decision reason;
- whether Qadam changed;
- affected component;
- version and effective time when applied;
- monitoring result when available;
- rollback reason when applicable.

Rejected records must say `Nothing changed`. Applied records must identify the
actual version and behavior change. Rolled-back records must state what was
reverted and why.

### 21.7 Repository interaction contract

Both repositories must:

- be collapsed on route entry;
- remain in the user's chosen state through data-only refreshes;
- use stable proposal or version IDs;
- contain no nested accordion hierarchy;
- load seven records initially;
- append seven through `View More +`;
- retain already visible rows during refresh;
- never promote a record merely because it moved to the top of the list;
- match the disclosure interaction and open-border language used on Results &
  Lessons, Data Sources, and Pattern Recognition.

### 21.8 Next-cycle decision

End the page with one dynamic next-cycle section.

When nothing is scheduled or newly applied:

> **Next cycle: No change**
>
> No approved improvement exists, so Qadam will continue using its current
> strategy and system versions.

Provide one neutral navigation link:

`Return to Fund Overview ->`

When a change is scheduled, show only the actual scheduled destination:

- version;
- affected component;
- activation time or condition;
- monitoring window;
- rollback rule;
- one link to inspect the affected dashboard page.

When a version has already been integrated, state which version the current
cycle is using and whether its monitoring window remains open.

Do not render the current grid of hypothetical feedback destinations when no
change is approved.

## 22. Visible Copy Translation Contract

| Current wording | Required public replacement |
| --- | --- |
| `How Qadam Improves` | `What Will Change in Qadam` |
| `Current improvement answer` | `Integration status` |
| `Changes being tested` | `Still under evaluation` |
| `Approved and applied` | `Already integrated` |
| `Inside Stage 10 - Controlled improvement record` | `Possible Future Improvements` |
| `Stage 10.1 - Proposed improvement` | `Proposed change` |
| `Stage 10.2 - Historical test` | `Historical evidence` |
| `Stage 10.3 - Forward observation` | `Real-time observation` |
| `Supporting check - Quantum usefulness` | Omit from primary row; retain in canonical evidence |
| `Stage 10.4 - Review` | `Current conclusion` |
| `Stage 10.5 - Applied version` | `Integration decision` |
| `Stage 10.6 - Next Observe cycle` | `What happens next cycle` |
| `Cannot affect Qadam yet` | `Not scheduled` |
| `inert until applied` | `Current behavior remains unchanged` |
| `Stopped or held proposals` | `Previous Improvement Decisions` |
| `Applied version ledger` | Merge into `Previous Improvement Decisions` |
| `Return to Stage 1` | `Next-cycle decision` |

No raw internal decision state should appear without a plain-English public
translation.

## 23. Canonical Improvement View-Model Changes

Extend `orchestrator/qadam_improvement_pipeline_view_model.py` with an explicit
certainty-first presentation contract. Preserve current source fields during
migration.

Target shape:

```json
{
  "presentation_contract_version": "qadam_tests_improvements.v2",
  "page_copy": {
    "eyebrow": "Tests & Improvements",
    "title": "What Will Change in Qadam",
    "subtitle": "See which improvements are approved for integration, which are still being evaluated, and which changes are already in use."
  },
  "immediate_answer": {
    "state": "nothing_scheduled_evidence_gathering",
    "tone": "pending",
    "headline": "Nothing is currently scheduled to change",
    "summary": "Qadam is still gathering evidence for an operational improvement ..."
  },
  "counts": {
    "scheduled_integration_count": 0,
    "under_evaluation_count": 1,
    "integrated_count": 0,
    "decision_history_count": 1
  },
  "next_version": {
    "state": "no_scheduled_changes",
    "version": null,
    "scheduled_changes": []
  },
  "repositories": {
    "possible_future_improvements": {
      "count": 1,
      "records": []
    },
    "previous_decisions": {
      "count": 1,
      "records": []
    }
  },
  "next_cycle": {
    "state": "unchanged",
    "headline": "Next cycle: No change",
    "destination": {
      "module_id": "fund",
      "view_id": "portfolio"
    }
  }
}
```

### 23.1 Public-state classifier

Implement one deterministic classifier that maps canonical proposal records to:

- `scheduled`;
- `under_evaluation`;
- `integrated`;
- `not_proceeding`;
- `status_unavailable`.

The classifier must apply the strict scheduling predicate from section 21.3.4.
It must not rely on frontend string matching.

### 23.2 Scheduled-change projection

Add explicit fields:

- `proposal_id`;
- `public_state`;
- `title`;
- `what_will_change`;
- `affected_component`;
- `justification`;
- `evidence_summary`;
- `target_version`;
- `approved_by`;
- `approved_at`;
- `effective_from` or `activation_condition`;
- `monitoring_window`;
- `rollback_condition`;
- canonical dashboard destination.

Fail closed when any required field is absent.

### 23.3 Under-evaluation projection

Project each active proposal into plain-English fields:

- `proposal_id`;
- `title`;
- `improvement_type`;
- `affected_component`;
- `source_lesson_id`;
- `source_lesson_summary`;
- `proposed_change`;
- `expected_benefit`;
- `historical_evidence_state`;
- `forward_observation_state`;
- `current_conclusion`;
- `blocker`;
- `next_action`;
- `current_behavior`;
- `public_state = under_evaluation`.

Expected benefit must remain visibly distinct from measured benefit.

### 23.4 Decision-history projection

Combine terminal proposals and applied versions into one chronological public
history without losing their distinct source records. Dedupe by stable proposal
and version identity.

### 23.5 Validator additions

Fail validation when:

- a scheduled record does not satisfy every scheduling predicate;
- a ready-for-review proposal is classified as scheduled;
- a rejected record appears under evaluation;
- an applied version is counted as scheduled;
- integrated count differs from valid applied-version records;
- current-answer state contradicts the classified records;
- the next-cycle section claims a change without a valid scheduled or applied
  version;
- a proposal lacks a Results & Lessons lineage ID;
- any dashboard authority flag permits mutation, approval, order creation,
  broker writes, proof credit, or live capital.

## 24. Frontend Renderer Changes

Refactor `renderQsaseTestsAndImprovements` around focused renderers:

1. `renderQsaseImprovementHeader`;
2. `renderQsaseIntegrationAnswer`;
3. `renderQsaseNextVersion`;
4. `renderQsaseImprovementCounters`;
5. `renderQsaseImprovementRepositories`;
6. `renderQsaseNextCycleDecision`.

### 24.1 Remove from the primary page

Remove:

- `renderQsaseLearningStageFlow(improvement, "improvements")`;
- six technical metric tiles;
- always-open active proposal workspace;
- six nested Stage 10 test cards per proposal;
- separate Stage 1 feedback destination grid;
- separate stopped-proposals disclosure;
- separate applied-version disclosure;
- separate historical-test diagnostics disclosure;
- repeated page-boundary paragraph when the shared dashboard boundary already
  communicates read-only authority;
- visible `Stage 10` body labels.

Do not delete source records or validators because their fields leave the
primary page.

### 24.2 Interaction state

Use stable page-scoped state for:

- the header explainer;
- Possible Future Improvements;
- Previous Improvement Decisions;
- expanded proposal identity when the approved dashboard pattern permits row
  expansion;
- visible counts for both repositories.

Preserve user state through polling rerenders. Do not infer open state from
proposal count or sort order.

### 24.3 Defensive rendering

When the v2 presentation block is missing during rollout:

- classify records conservatively in a compatibility adapter;
- never show a scheduled change without all required fields;
- render unavailable values honestly;
- keep current behavior unchanged;
- do not fall back to the legacy dense Stage 10 layout.

## 25. Visual, Accessibility, And Responsive Requirements

Use the same page rhythm, disclosure behavior, crimson controls, counter scale,
and open-state borders defined for Results & Lessons.

Additional requirements:

- Next Qadam Version is visually prominent but not celebratory;
- `Scheduled`, `Under evaluation`, `Integrated`, and `Not proceeding` use both
  text and restrained tone, never color alone;
- scheduled-change rows must not resemble trade-order cards;
- version, activation, monitoring, and rollback fields use readable labels, not
  chip clouds;
- proposal titles and affected components remain readable at 320px;
- disclosure controls meet 44px mobile touch targets;
- no independent scrolling pane;
- no horizontal page overflow;
- no automatic focus movement after refresh;
- expanded content never collapses during refresh;
- reduced-motion and print behavior match Results & Lessons;
- print output shows the current answer, counters, Next Qadam Version, and a
  concise repository summary without dumping all technical evidence.

## 26. Tests & Improvements Testing Strategy

### 26.1 Python tests

Extend `tests/test_qadam_improvement_pipeline.py` to cover:

1. current `0 scheduled / 1 under evaluation / 0 integrated` state;
2. no proposals and no applied versions;
3. proposal needs data;
4. proposal actively testing;
5. proposal ready for review but not scheduled;
6. approved proposal missing version or activation data remains unscheduled;
7. fully approved and versioned scheduled proposal;
8. applied version moves from scheduled to integrated;
9. rejected proposal appears only in decision history;
10. rolled-back version appears as not proceeding with rollback reason;
11. stale projection does not render false zeroes;
12. expected benefit never becomes measured benefit by inference;
13. every proposal retains source-lesson lineage;
14. next-cycle state matches scheduled or applied versions;
15. all authority booleans remain false.

### 26.2 Frontend tests

Update `scripts/check_dashboard_learn_improve_consolidation.js` and related
dashboard tests to assert:

- exact header copy;
- one integration-status answer;
- visible Next Qadam Version area;
- exactly three change counters;
- exactly two repositories;
- repositories closed by default;
- no permanent local Stage 10 flow;
- no six-tile technical metric grid;
- no separate destination grid;
- no separate stopped, applied, or diagnostics accordions;
- no visible raw internal states;
- ready-for-review does not render as scheduled;
- incomplete approval does not render as scheduled;
- `View More +` loads seven additional records;
- disclosure and pagination state survive refresh;
- the next-cycle section is truthful;
- the 13-route navigation remains unchanged;
- Results & Lessons handoff reaches this page;
- Return to Fund Overview uses the protected route helper.

### 26.3 Copy-quality tests

Reject these strings from rendered Tests & Improvements body HTML:

- `Inside Stage 10`;
- `Stage 10.1` through `Stage 10.6`;
- `inert_until_applied`;
- `not_started_no_eligible_hypothesis`;
- `provider partitions` in the primary collapsed view;
- `statistical paths attempted` in the primary collapsed view;
- `Supporting check - Quantum usefulness`;
- `Return to Stage 1`;
- `Cannot affect Qadam yet`.

Scope the test to rendered public body copy, not internal artifacts or historical
documentation.

### 26.4 Browser acceptance

Verify:

- current state reads as no scheduled change;
- the active operational proposal does not look like a strategy change;
- no proposal appears promised before approval;
- Next Qadam Version is immediately understandable;
- both repositories remain closed on entry;
- opened repositories remain open through two or more polling refreshes;
- seven-at-a-time loading;
- keyboard, mobile, print, and reduced-motion behavior;
- direct route, back/forward navigation, and Results & Lessons handoff;
- correct next-cycle destination;
- no clipped labels, arrows, or status text.

## 27. Tests & Improvements Implementation Stages

### Stage T1: Baseline Protection

- record core and dashboard repository state;
- preserve all unrelated dirty and untracked work;
- capture current desktop and mobile screenshots;
- record the canonical current improvement snapshot;
- run existing improvement and dashboard checks.

Exit criterion: current behavior and pre-existing failures are documented.

### Stage T2: Certainty-First Projection

- add public-state classifier;
- add strict scheduling predicate;
- add Next Qadam Version projection;
- add three new counters;
- add normalized proposal and decision-history repositories;
- add next-cycle projection;
- extend validation and Python tests.

Exit criterion: the backend exports the complete simplified page without
frontend inference.

### Stage T3: Direct Change-Roadmap Renderer

- implement the locked header and explainer;
- implement immediate answer and Next Qadam Version;
- implement three counters;
- implement two repositories;
- implement next-cycle decision;
- remove the dense legacy Stage 10 body.

Exit criterion: the page visibly prioritizes what will change.

### Stage T4: Interaction Persistence

- preserve disclosure, expanded-record, and pagination state through refresh;
- reset defaults only on route exit and re-entry;
- test changing proposal states without collapsing the page.

Exit criterion: the user never loses reading context during a refresh.

### Stage T5: Visual And Responsive Polish

- align with Results & Lessons tokens and controls;
- polish Next Qadam Version and status hierarchy;
- verify mobile, focus, print, and reduced-motion behavior.

Exit criterion: the two Learn & Improve pages feel like one designed system.

### Stage T6: Regression And Documentation

- update backend and frontend tests;
- update User Guide and lifecycle implementation log;
- run navigation, accessibility, responsive, authority, and deployment checks;
- verify Results & Lessons and Tests & Improvements together.

Exit criterion: the paired simplification passes all protected contracts.

### Stage T7: Integrated Release And Production Verification

- commit only scoped core and dashboard changes;
- push the dashboard release before deployment;
- deploy through the guarded production script;
- verify both production aliases, asset hashes, direct routes, mobile layout,
  and served copy;
- record deployment evidence.

Exit criterion: production serves both simplified pages from one committed
release.

## 28. Tests & Improvements Acceptance Criteria

Implementation is complete only when:

1. The protected Tests & Improvements route and sidebar label remain intact.
2. The shared 10-stage lifecycle remains available at the top.
3. No Stage 10 terminology appears in the page body.
4. Header copy renders exactly.
5. Immediate answer explains the complete improvement state in plain English.
6. Current behavior is explicitly described as unchanged when nothing is
   scheduled.
7. Next Qadam Version is visible without opening a disclosure.
8. No current proposal is shown as scheduled.
9. Scheduling fails closed unless every required release field exists.
10. Exactly three counters render.
11. Counters represent scheduled, under-evaluation, and integrated changes.
12. Missing counts are not silently treated as zero.
13. Exactly two repositories render.
14. Both repositories are collapsed on route entry.
15. Open state persists through refresh.
16. Possible Future Improvements contains only non-terminal, non-scheduled,
    non-applied proposals.
17. Previous Improvement Decisions contains rejected and applied history.
18. The active operational proposal is not presented as a trading strategy.
19. Not-started evidence is not described as testing underway.
20. Expected benefits are not described as measured results.
21. No repository contains a nested accordion maze.
22. Lists load seven records at a time.
23. `View More +` does not collapse content.
24. The six technical metric tiles are absent.
25. Separate stopped, applied, diagnostics, and destination blocks are absent.
26. Next-cycle state matches the actual scheduled or applied versions.
27. Results & Lessons lineage remains attached to every proposal.
28. The page remains read-only, command-disabled, paper-only, and unable to
    approve, apply, trade, write to brokers, grant proof credit, or enable live
    capital.
29. Desktop, mobile, keyboard, print, reduced-motion, route, and lifecycle tests
    pass.
30. Production aliases serve the committed paired Learn & Improve release.

## 29. Combined Learn & Improve Reading Experience

The two pages now form one simple governance story:

### Results & Lessons

1. What happened?
2. Is it attributable to Qadam?
3. What lesson does the evidence support?
4. What history must remain separate?
5. Which supported lesson moves to testing?

### Tests & Improvements

1. What will change?
2. What is only being considered?
3. What has already changed?
4. What did Qadam refuse to change?
5. What version enters the next cycle?

Together they express a strict rule:

> A result is not automatically a lesson, and a lesson is not automatically a
> change.

That sentence is the governing mental model for the entire Learn & Improve
module. The first page protects attribution. The second protects integration.
