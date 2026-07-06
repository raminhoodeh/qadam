# Qadam Pattern Recognition Dashboard Overhaul Implementation Plan

## Objective

Overhaul the Qadam dashboard's pattern recognition sections so a non-technical user can understand what Qadam has recognised, why it matters, whether it is tradeable, and what must happen next.

The dashboard currently proves that backend pattern activity exists, but it does not communicate the findings clearly enough. The target state is a dashboard that explains Qadam's investment reasoning in plain language while preserving the existing safety model: read-only, paper-only, non-authoritative, and unable to create orders, approvals, broker writes, or proof credit.

## Current Problems

### 1. Counts appear before meaning

The dashboard currently leads with activity metrics such as "16 linear", "16 nonlinear", and "8 quantum reviews." These numbers show that analysis happened, but they do not tell the user what Qadam actually found.

### 2. Pattern cards are generic and repetitive

Many cards read like duplicated system records rather than distinct discoveries. They do not clearly answer:

```text
source signal -> price relationship -> market affected -> confidence -> blocker
```

### 3. Pattern lifecycle is unclear

The dashboard does not clearly distinguish between:

- Found
- Documented
- Validated
- Paper-review candidate
- Tradeable

As a result, "5 documented patterns" and "0 PaperOps handoff candidates" are technically accurate, but the user is forced to infer that these are research findings and not trade-ready setups.

### 4. Evidence chains are buried

The most important reasoning should be visible immediately. For example:

```text
ACLED + maritime disruption + oil futures divergence -> possible energy-security repricing
```

Instead, the current UI compresses sources, strategy, quantum state, and PaperOps metadata into dense cards.

### 5. Internal language dominates the UI

Terms such as "PaperOps handoff", "quantum review", "Akber filter", "thirty day persistence", and "review records" are accurate internally but should not be the primary language on the public dashboard.

### 6. Patterns are not ranked

All patterns currently look equally important. Qadam should make it obvious which pattern is closest to paper-trade review, which has the strongest evidence, which has the most important blocker, and which is simply being watched.

### 7. Telegram summary is treated like an artifact

The qualitative Telegram pattern note should be displayed as a readable human-facing explanation, not buried as another technical record.

## Target User Experience

The pattern recognition area should answer these questions in order:

1. What did Qadam find?
2. Which market could it affect?
3. What evidence supports it?
4. What does Qadam think it means?
5. Is it validated or just research?
6. Why is it not trading yet?
7. What will Qadam do next?
8. How would Qadam explain this briefly to the group?

The target pipeline per pattern is:

```text
Detected signal -> Market affected -> Evidence -> What Qadam thinks -> What would confirm it -> What blocks the trade -> Next action
```

## Scope

This overhaul should affect:

- Pattern and Opportunity Lab
- Pattern-To-Paper Workflow
- Telegram pattern summary mirror
- QSASE dashboard view-model artifacts
- Public cockpit/API summaries consumed by `qadam.trade/dashboard`
- Dashboard anti-slop and repetition checks
- Dashboard copy system for pattern findings

This overhaul must not affect:

- Broker write permissions
- Live-capital settings
- PaperOps guarded submission path
- Risk approval authority
- Source quorum rules
- Proof ledger credit rules
- Telegram command authority

## Stage 1: Create A Pattern Insight Presentation Artifact

Add a presentation-layer artifact derived from existing pattern records:

```text
data/runtime/qsase_pattern_insight_briefing.json
```

This artifact should not invent findings. It should translate existing pattern recognition, pattern-to-paper workflow, strategy router, and PaperOps gate state into readable insight records.

Required top-level fields:

```json
{
  "artifact_type": "qsase_pattern_insight_briefing",
  "status": "pattern_insight_briefing_ready",
  "generated_at": "...",
  "read_only": true,
  "paper_only": true,
  "public_safe": true,
  "live_capital_enabled": false,
  "broker_write_allowed": false,
  "paper_order_created_count": 0,
  "proof_credit_allowed": false,
  "top_pattern_headline": "...",
  "lifecycle_counts": {},
  "ranked_patterns": [],
  "telegram_brief": {},
  "plain_language_glossary": {},
  "trade_readiness_summary": {},
  "anti_slop_warnings": []
}
```

Each pattern insight record should include:

```json
{
  "pattern_id": "...",
  "rank": 1,
  "headline": "Energy-security risk is rising faster than oil pricing reflects",
  "detected_signal": "Conflict, maritime disruption, aviation anomalies, and GPS interference are being cross-scanned.",
  "market_affected": "Oil: CL=F, BZ=F, USO, XLE",
  "evidence_chain": "Conflict and shipping stress rose before full oil market confirmation.",
  "qadam_interpretation": "Qadam is watching for an energy-security repricing setup.",
  "confidence_label": "Medium evidence, not trade-ready",
  "confidence_score": 0.72,
  "lifecycle_stage": "documented",
  "confirmation_needed": "Thirty-day persistence and market confirmation",
  "trade_blocker": "The persistence window is incomplete.",
  "next_action": "Keep shadow review; do not send to PaperOps yet.",
  "human_summary": "Qadam has found an oil-risk pattern, but it has not repeated long enough to become a paper-trade candidate.",
  "raw_refs": []
}
```

## Stage 2: Add A Clear Pattern Lifecycle

Add a lifecycle ladder at the top of the pattern recognition area.

Lifecycle stages:

- `Found`: Qadam detected a source-price relationship worth recording.
- `Documented`: Qadam created a structured thesis with source lineage, instruments, invalidation, and next action.
- `Validated`: Evidence survived backtest, shadow review, and repetition checks.
- `Paper-review candidate`: The setup can be considered by guarded PaperOps.
- `Tradeable`: PaperOps gates, risk, idempotency, source quorum, and safety checks passed.

The current visible summary should read like:

```text
5 documented research patterns. 0 validated. 0 ready for paper-trade review. No pattern has permission to create an order yet.
```

Implementation requirements:

- Lifecycle state must be derived from existing artifacts, not inferred visually by the frontend.
- Research-only patterns must never be styled as tradeable.
- The dashboard must show "not trade-ready" clearly when no PaperOps handoff candidate exists.

## Stage 3: Replace Count-First Pattern Cards With Insight Cards

Replace the current repetitive cards with ranked insight cards.

Each card should show:

- Headline
- Detected signal
- Market affected
- Evidence chain
- Qadam's interpretation
- Confidence label
- Lifecycle stage
- Blocker
- Next action

Example card:

```text
Energy-security repricing watch

Signal:
Conflict, maritime disruption, aviation anomalies, and macro stress are being cross-scanned.

Market:
Oil futures, USO, XLE.

Evidence:
Source pressure is elevated, but the thirty-day persistence test is incomplete.

Qadam thinks:
This may become a supply-risk trade if price confirms.

Current state:
Documented research pattern, not trade-ready.

Next:
Continue shadow review. No PaperOps handoff yet.
```

The default card should not show raw JSON-style fields. Raw fields should move into an expandable technical drawer.

## Stage 4: Add Pattern Ranking

Add a module titled:

```text
Most Important Patterns Right Now
```

Rank patterns by:

- Closest to paper-trade review
- Strongest evidence chain
- Highest source pressure
- Best market confirmation
- Lowest ambiguity
- Clearest next action

Display three callouts:

- Closest to trade review
- Strongest evidence
- Main blocker

Example:

```text
Closest to paper-trade review:
Oil energy-security repricing watch

Strongest evidence:
Semiconductor supply-chain stress

Main blocker:
Patterns need more persistence before Qadam can treat them as trade candidates.
```

## Stage 5: Surface Evidence Chains Visually

Each pattern should include a compact evidence-chain row.

Format:

```text
Sources -> Relationship -> Market -> Interpretation -> Gate
```

Example:

```text
ACLED + maritime + GPS interference -> energy-risk pressure rising -> CL=F / BZ=F -> possible oil repricing -> needs persistence
```

Implementation requirements:

- Do not require the user to expand technical detail to understand the evidence chain.
- Keep source labels readable.
- Show the affected instrument or sleeve clearly.
- Show the blocking gate in plain language.

## Stage 6: Translate Internal Language

Add a glossary mapping internal system terms into plain English.

Required mappings:

| Internal term | Dashboard language |
| --- | --- |
| PaperOps handoff | Ready for paper-trade review |
| PaperOps gate | Paper-trade safety check |
| Akber filter | Akber's trade-quality checklist |
| Quantum review | Nonlinear pattern check |
| Quantum state | Nonlinear review state |
| Thirty day persistence | The pattern has not repeated long enough yet |
| Source quorum | Enough independent sources agree |
| Review records | Evidence reviews |
| Paper proof ledger | Paper proof ledger |
| Guarded Alpaca Paper route | Guarded paper brokerage route |

Rules:

- The public label should be plain English.
- The internal term can appear as small secondary text or in the technical drawer.
- A research-only state must never use wording that implies trading authority.

## Stage 7: Promote The Telegram Brief

Add a visible module titled:

```text
How Qadam would explain this to the group
```

Display the current Telegram pattern candidate as readable copy:

```text
Qadam pattern note:
5 patterns are documented, but none are ready for paper-trade review yet.

Closest watch:
Oil, silver, and semiconductors have active evidence chains.

Main blocker:
The patterns need more persistence before Qadam can treat them as trade candidates.

Order:
None submitted.
```

Telegram quality rules:

- Maximum 5 short lines.
- Must mention whether any order was submitted.
- Must avoid generic deployment/update language.
- Must avoid repeated lines.
- Must translate internal terms.
- Must be review-only and command-disabled.
- Must not create candidates, approvals, broker writes, or proof credit.

## Stage 8: Move Raw Technical Detail Behind Expanders

The default pattern UI should show:

- Human insight
- Evidence chain
- Market affected
- Lifecycle state
- Blocker
- Next action

Expandable technical detail can show:

- Raw artifact refs
- Source packet keys
- Linear state
- Nonlinear state
- Quantum state
- Evidence scores
- Router state
- PaperOps state
- Invalidation
- Idempotency material

This keeps the dashboard transparent without forcing non-technical users to read backend records.

## Stage 9: Update The Frontend Layout

Update `landing-page-repo/dashboard.js` to replace the current pattern display with:

1. Pattern Intelligence Summary
2. Most Important Patterns Right Now
3. Pattern Lifecycle
4. Ranked Pattern Insight Cards
5. Telegram Group Explanation
6. Technical Detail Drawers
7. Router and PaperOps Gate

Recommended flow near the bottom of the page:

```text
Pattern Lab -> Pattern Intelligence Summary -> Ranked Findings -> Pattern-To-Paper Readiness -> Telegram Explanation -> Router/PaperOps Gate
```

The section should make the following immediately visible:

- Qadam has found research patterns.
- They are documented, not trade-ready.
- The main blocker is persistence/validation.
- No orders were created from the dashboard.
- The next action is continued shadow review or guarded PaperOps review only after gates pass.

## Stage 10: Update Dashboard View-Model Builders

Update `orchestrator/qsase_dashboard_view_model.py` to:

- Build `qsase_pattern_insight_briefing.json`.
- Add `pattern_insight_briefing` into `view_model_refs`.
- Add a new dashboard section for `pattern_intelligence_summary`.
- Derive lifecycle counts from the pattern workflow and router/PaperOps states.
- Derive ranking from evidence score, readiness, missing criteria, ambiguity, and actionability.
- Preserve all non-authority flags.

The builder should fail closed if required source artifacts are missing.

## Stage 11: Update Public Cockpit Status

Update `orchestrator/cockpit_status.py` to expose safe summary fields:

- `pattern_insight_status`
- `pattern_insight_top_headline`
- `pattern_insight_found_count`
- `pattern_insight_documented_count`
- `pattern_insight_validated_count`
- `pattern_insight_paper_review_candidate_count`
- `pattern_insight_tradeable_count`
- `pattern_insight_main_blocker`
- `pattern_insight_telegram_brief_ready`

Do not expose secrets, raw prompts, credentials, broker payloads, or live endpoints.

## Stage 12: Update Telegram Boundary

Update `orchestrator/qsase_telegram_notification_boundary.py` to consume the pattern insight briefing artifact.

The Telegram pattern candidate should be generated from the same human-readable interpretation shown on the dashboard.

Required behavior:

- Deduplicate repeated pattern notes.
- Reject generic summaries.
- Reject command-like language.
- Reject anything that implies live capital or broker execution.
- State "Order: none submitted" unless a guarded paper order was actually submitted through the canonical route.

## Stage 13: Add Validation Scripts

Add a dedicated check:

```text
scripts/check_qsase_pattern_insight_briefing.py
```

The check should validate:

- Artifact exists.
- Artifact is read-only, paper-only, public-safe.
- Live capital is false.
- Broker write allowed is false.
- Paper order created count is zero unless sourced from canonical PaperOps.
- Every pattern has headline, detected signal, market affected, evidence chain, interpretation, blocker, and next action.
- Lifecycle counts match records.
- No research-only pattern is labeled tradeable.
- Telegram brief is short, specific, deduped, and safe.
- Internal terms are translated in public fields.

## Stage 14: Strengthen Anti-Slop Checks

Extend dashboard anti-slop checks to fail if:

- More than two pattern cards have the same headline.
- A card lacks a detected signal.
- A card lacks a market or instrument.
- A card lacks an evidence chain.
- A card lacks a blocker.
- A card lacks a next action.
- Counts appear before any human-readable pattern insight.
- Internal terms appear without plain-English translation.
- Telegram copy exceeds the allowed length.
- A research-only pattern is visually presented as tradeable.
- The same phrase appears repeatedly across multiple cards.

This should be added to existing dashboard check scripts and included in dashboard preflight.

## Stage 15: Deployment And Verification

Run local checks:

```text
.venv/bin/python scripts/check_qsase_dashboard_view_model.py
.venv/bin/python scripts/check_qsase_pattern_to_paper_workflow.py
.venv/bin/python scripts/check_qsase_pattern_insight_briefing.py
.venv/bin/python scripts/check_qsase_telegram_notification_boundary.py
.venv/bin/python scripts/check_qsase_telegram_message_quality.py
node --check landing-page-repo/dashboard.js
node scripts/check_dashboard_qsase_public_frontend.js
node scripts/check_dashboard_renderer.js
.venv/bin/python scripts/check_cockpit_status.py
.venv/bin/python scripts/export_cockpit_status.py
```

Run dashboard deployment preflight:

```text
bash landing-page-repo/scripts/deploy-vercel-production.sh
```

Verify live:

```text
https://qadam.trade/dashboard
https://qadam.trade/api/cockpit-status
```

Live verification should confirm:

- New pattern insight section is visible.
- Top pattern headline is present.
- Lifecycle ladder is present.
- Ranked pattern cards are present.
- Telegram explanation is readable.
- No dashboard action creates orders.
- Portfolio value remains consistent with the cockpit API.

## Acceptance Criteria

The overhaul is complete when:

- A non-technical user can answer "what did Qadam find?" within 10 seconds.
- The dashboard clearly says whether each pattern is found, documented, validated, or tradeable.
- Every pattern shows source signal, market affected, evidence, blocker, and next action.
- The most actionable pattern is ranked above less actionable patterns.
- Telegram copy is short, specific, readable, and deduped.
- No section implies that Qadam can place trades directly from the dashboard.
- Portfolio values remain consistent with public cockpit status.
- Existing PaperOps safety checks still pass.
- The deployed `qadam.trade/dashboard` visibly shows the redesigned pattern sections.

## Non-Negotiable Safety Boundaries

- Dashboard remains read-only.
- Telegram remains review-only and command-disabled.
- No live-capital enablement.
- No broker live endpoints.
- No broker writes from dashboard or Telegram.
- No PaperOps bypass.
- No proof credit from backtest, shadow, dashboard, or Telegram artifacts.
- No order creation unless a setup passes the guarded Alpaca Paper route through canonical PaperOps.

## Implementation Principle

The dashboard should stop saying:

```text
Qadam ran 40 reviews.
```

It should start saying:

```text
Qadam found this possible market relationship, here is the evidence, here is why it matters, here is why it is not tradeable yet, and here is the next safe action.
```
