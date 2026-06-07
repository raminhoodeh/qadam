# Qadam Dashboard — Consolidation Cut (CC) Implementation Plan

**Date:** 2026-06-05
**Author:** UX + frontend architecture pass
**Surface:** Founder dashboard at `qadam.trade` (`landing-page-repo/dashboard/index.html`, `landing-page-repo/dashboard.js`, `landing-page-repo/auth.css`), fed by `landing-page-repo/status/cockpit-status.json` (assembled by `orchestrator/cockpit_status.py`, exported by `scripts/export_cockpit_status.py`).
**Supersedes the additive direction of:** `qadam-dashboard-overhaul-master-implementation-plan.md` (DX-0→14, D11A–O, D12, D13).

**Decisions locked (2026-06-05, Ramin):**
- *Status:* plan only — no code changes yet.
- *Drawer scope:* the **full system map stays on the main view** (founders want node-by-node detail), de-duplicated to a single rendering. **Governance comment form + Telegram delivery state move to the Diagnostics drawer.** Pure diagnostics (phases, paperops, rs certification, kill-switch ledger, event trail, process console, source heartbeat history) also live in the drawer.
- *Implementation order:* **CC1 must land before CC2/CC3.** The founder contract and Diagnostics namespace are created first; deletion follows once the default view has a stable replacement contract.
- *Authority-language metric:* the "read-only / paper-only / live-capital / cannot" count applies to the **default rendered founder view**, not hidden Diagnostics/audit surfaces.
- *Payload pruning:* CC8 is gated by checker migration. If any `scripts/check_*.py`, automations, or mirrors still need raw top-level keys, those keys stay and are marked as prune candidates rather than removed.
- *CC0 baseline:* created under `docs/dashboard-consolidation-cut/cc0-baseline-2026-06-05/` with snapshots, hashes, acceptance checklist, and delete list. No dashboard runtime behavior changed in CC0.

---

## 1. Entry Findings

The dashboard is not under-built. It is **over-built and never subtracted from**. Fourteen overhaul stages (DX series) and a fifteen-step "simplification pass" (D11A–O) each *added* a consolidated component, but the legacy components they replaced were left in place — several are still literally tagged `legacy-operations-panel` in the markup and still render. The result is archaeological: every prior pass is stacked on top of the last.

Measured on the current shipping page:

| Symptom | Count | Where |
|---|---|---|
| "read-only" restated | 16 | `index.html` |
| "live capital" off/disabled restated | 18 | `index.html` |
| "paper-only / paper mode" restated | 17 | `index.html` |
| "cannot …" (place/stage/write/approve) | 17 | `index.html` |
| `<dt>Limits</dt>` rows (tooltips) | 14 | `index.html` |
| `<dt>Boundary</dt>` rows (panel-briefs) | 7 | `index.html` |
| `panel-brief` blocks | 21 | `index.html` |
| info-card tooltips (Shows/Watch/Limits) | 14 | `index.html` |
| "Loading…" static placeholders | 49 | `index.html` |
| Pipeline narrative renderings of the same chain | 3 | 5 `fund-model-card` + 6 `flow-lane` + 10 `system-map-node` |
| `build*` view-model functions in JS | 17 | `dashboard.js` |
| Top-level status keys | 76 | `cockpit-status.json` |
| — of which `paperops_*` | 15 | overlapping paper-ops facets |
| — of which `phase*` | 19 | milestone status (phase5 alone = 12) |

**Two structural root causes:**

1. **The UI ignores its own curated contract.** A `mission_control` projection already exists in the payload with exactly the founder-facing slices — `data_sources`, `portfolio`, `thinking`, `trade_intent`, `trading_philosophy`, `safety`, `headline`, `mission_brief`. The dashboard does not render it; it re-derives all of these from the raw 76-key payload via 17 `build*` functions, then *also* renders an Overview that re-summarizes the detail views. Every datum therefore appears 2–4 times.
2. **Compliance language is treated as content.** The read-only / paper-only / no-broker-route guarantee is true and must stay, but it is repeated ~80 times instead of stated once.

**Real data is already live and the placeholders contradict it.** `capital` currently reports balance **£100,073.37**, **7 / 100** proof trades, realized P&L **−£99.42**, unrealized **+£73.33**, 7 open positions, 7 postmortems due, and a **stale broker mirror (~3 days)** — with a 20-point `equity_curve`. The static shell still shows `£100,000`, `0/100`, `35 sources`, `Static`. We are shipping misleading hardcoded numbers next to a working data feed.

---

## 2. Product Principle

> **This is a subtraction release. The dashboard's problem is not missing structure — it is that nothing was ever removed. We delete, we do not hide; we render the existing contract, we do not invent a new one.**

A founding Fund Manager opens this to answer six questions, fast, on a phone:

1. **Is the team healthy?** (the nodes / "hedge fund team")
2. **Are the data sources good?**
3. **What strategy is it running, and why?**
4. **How is the paper portfolio doing over time?**
5. **What trades is it making?**
6. **What is it thinking?**

Everything that does not serve one of those six — or that restates the safety guarantee, or that duplicates another panel — is removed from the default view. Nothing is deleted from the *system*: diagnostics, certification, governance, and Telegram all move behind one **Diagnostics** drawer (the toggle already exists). The **full system map stays on the main view** (it answers question 1, "is the team healthy?") but is de-duplicated from three parallel renderings to one. Default view = the six (system map among them). Drawer = the audit trail.

---

## 3. Non-Negotiable Invariants (must survive the cut)

These are guarantees, not copy. Reducing how often we *say* them must not change whether they are *true*.

- **Read-only / paper-only / live-capital-off / no browser→broker route.** Enforced by `app/api/cockpit-status/route.ts` (`validatePublicStatus`) and the signed snapshot. Untouched by this plan.
- **The public-safe contract.** `schema_version`, `mode === "paper"`, `d1_snapshot.public_safe`, `live_bridge.read_only`, etc. must continue to validate. The projection work in §5 is **additive then pruning**, never a contract break.
- **No fabricated data.** Where data is absent, render an honest empty state — never a hardcoded number.
- **Authority is stated once, prominently** — the single safety strip — and remains screen-reader-announced.
- **The certification/diagnostics surface is preserved** (moved, not removed), so `scripts/check_*.py` and the Fund Managers' audit workflow still have a UI.

---

## 4. Target Information Architecture

One authenticated route. **One vertical scroll. Seven blocks** (your six + the always-visible safety bar). No view-switcher tabs in the default experience — the tabs were a symptom of having too much to show. A single **Diagnostics** drawer holds everything we remove.

```
┌───────────────────────────────────────────────────────────────┐
│ ◐ Paper £100,073  ▲ +0.07%   ● Paper-only · read-only · live   │  ← STATUS BAR (sticky)
│                                              capital off  [Diagnostics ▸] │     safety stated ONCE
├───────────────────────────────────────────────────────────────┤
│ 1 · THE TEAM / MAP      COO ● · Analyst ● · Strategy ◐ ·         │  ← node health + node-by-node map,
│                         Quant ◐ · Risk ● · PaperOps ●  [▾ map]   │     ONE rendering (was 3: cards+lanes+nodes)
├───────────────────────────────────────────────────────────────┤
│ 2 · DATA SOURCES        28 ok · 5 degraded · 2 missing creds     │  ← quorum + expandable ledger
│                         [▾ source ledger]                        │
├───────────────────────────────────────────────────────────────┤
│ 3 · STRATEGY            "Watching crude + AI-infra power supply;  │  ← one narrative: what & why
│                          Akber filter: catalyst + mispricing…"   │
├───────────────────────────────────────────────────────────────┤
│ 4 · PORTFOLIO       ╭─ equity_curve sparkline ─────╮  −£99 real  │  ← real timeline (20 pts live)
│                     ╰──────────────────────────────╯  7/100 · DD 0% │
├───────────────────────────────────────────────────────────────┤
│ 5 · TRADES              idea → gate → paper → closed             │  ← one lifecycle board
│                         7 open · 7 postmortems due               │
├───────────────────────────────────────────────────────────────┤
│ 6 · THINKING            hypotheses · what's missing ·            │  ← reasoning feed
│                         worldview prior (1 labeled line)         │
└───────────────────────────────────────────────────────────────┘
   Diagnostics drawer ▸  event trail · phase/paperops/rs certification ·
                         kill-switch ledger · governance + comment form ·
                         Telegram delivery · process console · heartbeat history
                         (full system map stays on the main view, block 1)
```

Each block maps to exactly one slice of the existing `mission_control` projection (plus `capital` for the timeline), so the render path is 1:1 with the contract.

| Block | Renders from | Replaces (deleted/merged) |
|---|---|---|
| Status bar | `mission_control.safety`, `mission_control.portfolio` | balance ticker + 4 safety badges + Safety Stops panel + all 14 "Limits" / 7 "Boundary" rows |
| 1 Team / system map | `modules` + `mission_control.system_stack` | the **3 parallel renderings** collapse to one: `fund-model-grid` (5) + `system-flow-diagram` (6 lanes/10 nodes) + role spine → a single node-by-node map kept on main; `buildOperationsRoleSpine` merged in |
| 2 Sources | `mission_control.data_sources` (+ `watching` for ledger) | Evidence workspace, Overview "Data sources" mini, static "35/Static/placeholder" rows |
| 3 Strategy | `mission_control.trading_philosophy` + `mission_control.thinking.strategy` | `strategy-manifestation` panel, Overview "Trading strategies" mini |
| 4 Portfolio | `capital.equity_curve`, `capital.*` | 3 stacked progress cards, `summary-strip`, fake `£100,000`/`0/100` |
| 5 Trades | `mission_control.trade_intent` (+ `trade_layer`) | 3 trade "diagnostic groups", Overview "Trades being considered" mini |
| 6 Thinking | `mission_control.thinking` | cognition workspace duplicate, `worldview` panel (merged), 3 reasoning-lane cards |
| Drawer | everything else | nothing lost — relocated |

---

## 5. Data & Contract Strategy

The founder contract already exists; it is just **polluted and unused**. Today `mission_control` mixes the founder slices with diagnostics (`phase3_readiness`, `phase4_strategy`, `phase5_layer_b`, `phase6_learning_loop`, `phase7_demo_proof`, `rs9_learning_loop`, `rs10_final_paper_autonomy_certification`, `system_stack`).

**Target shape** (in `orchestrator/cockpit_status.py`, the assembler):

```
mission_control:                 # the ONLY object the founder view reads
  schema_version, status, headline, source
  safety            { mode, read_only, live_capital_enabled, broker_write_route }
  team[]            { key, label, owner, status, one_line }   # node health
  data_sources      { ok, degraded, missing_credentials, quorum, ledger[] }
  strategy          { posture, why, akber_lens, universe[] }
  portfolio         { balance_gbp, delta_pct, equity_curve[], drawdown_pct,
                      closed/target, realized_pnl, unrealized_pnl, mirror_freshness }
  trades            { lifecycle_counts, board[], open[], postmortems_due }
  thinking          { hypotheses[], missing_corroboration[], worldview_prior }

diagnostics:                      # NEW sibling — drawer-only, audit/cert tooling
  system_map, event_trail, phase*, paperops_*, paper_*, rs9, rs10,
  kill_switch_ledger, governance_forum, telegram, process_console, source_heartbeat_history
```

Rules:
- **Additive first, prune second.** Stage CC1 *adds* the cleaned `mission_control` + `diagnostics` namespacing while leaving raw keys present, so nothing breaks mid-migration. Raw top-level keys are removed only in CC8 once the UI and all `check_*.py` consume the new shape.
- **No destructive payload pruning without migration proof.** CC8 may finish with a documented prune-candidate list instead of physical key removal if raw keys are still used by checkers, automations, or the live bridge.
- **`validatePublicStatus` unchanged** — it asserts safety flags that remain top-level (`mode`, `d1_snapshot`, `live_bridge`, `capital.live_capital_enabled`).
- **Currency:** payload is USD-native with `fx_to_gbp_rate`; the founder view is GBP. Keep the existing `formatCapitalMoney`/`fx_to_gbp_rate` path — do not reformat.

Net effect: the dashboard reads ~9 keys under one object instead of fanning across 76.

---

## 6. Implementation Stages

Sequenced so each stage ships independently, the safety contract holds at every step, and the visible win lands early. Stage code: **CC** (Consolidation Cut).

### CC0 — Freeze, snapshot, acceptance contract *(no UI change)*
- Tag current `index.html`, `dashboard.js`, `auth.css`, and a copy of a live `cockpit-status.json` as the rollback baseline.
- Write the acceptance checklist (§10) and a one-page "delete list" from the §4 table.
- **Status:** completed. Baseline folder: `docs/dashboard-consolidation-cut/cc0-baseline-2026-06-05/`.
- **Done when:** baseline tagged; delete list reviewed by a Fund Manager (Ramin) so we agree on what leaves the default view.

### CC1 — Founder projection in the assembler *(backend, additive)*
- In `orchestrator/cockpit_status.py`, build the cleaned `mission_control` (team/data_sources/strategy/portfolio/trades/thinking/safety) and a `diagnostics` sibling. Leave raw keys in place.
- Extend `scripts/check_cockpit_status.py` to assert the new contract (presence, types, public-safe).
- **Status:** completed. The exported snapshot now has `mission_control.schema_version = 2`, `mission_control.team`, `mission_control.strategy`, `mission_control.trades`, expanded source/portfolio/thinking slices, and a top-level read-only `diagnostics` namespace while preserving legacy raw keys for checker and dashboard migration.
- **Done when:** exported snapshot contains the new objects; `check_cockpit_status.py` green; `validatePublicStatus` still passes.

### CC2 — Delete legacy & duplicate panels *(HTML — the big subtraction)*
- Start only after CC1 has exported the cleaned `mission_control` and `diagnostics` objects.
- Remove from `index.html`: the `worldview` panel (it self-declares "Merged into Reasoning"), the standalone **Safety Stops** (`#forbidden`), **Communications** (`#communications`), **Process Console** (`#process-console`) panels (all `legacy-operations-panel`), the debug-only Overview duplicates (`overview-command-surface`, `overview-proof-flow`, `review-sequence`), and every static placeholder row / hardcoded metric (`35`, `Static`, `£100,000`, `0/100`, "Source registry placeholder").
- Relocate Governance + Telegram + Process Console content into the Diagnostics drawer markup.
- **Done when:** no `legacy-operations-panel` remains; zero hardcoded data values in markup; page still renders (empty states until CC5 wiring).
- **Status:** completed. The static dashboard shell now removes the legacy Safety Stops, Communications, Process Console, Governance, worldview, and debug-only Overview duplicate panels; old deep links redirect into consolidated Mission Control, Reasoning, and Operations readouts; hardcoded source/account placeholder metrics now defer to status-snapshot loading states.

### CC3 — Single safety statement *(HTML/CSS)*
- Keep one safety strip. Delete all 14 `<dt>Limits</dt>` and 7 `<dt>Boundary</dt>` rows; collapse 4 safety badges → 1; remove per-node `node-authority` badges (10).
- Keep one short authority sentence in the drawer for auditors.
- **Done when:** "read-only/live-capital/paper-only" string counts drop from ~50 to ≤5; safety strip still announced to screen readers.
- **Status:** completed. The founder-facing dashboard now has one screen-reader-announced safety strip, one visible safety badge, `Scope` rows instead of repeated `Limits`/`Boundary` rows, and no visible per-node `node-authority` badges. Detailed authority evidence remains in Operations diagnostics.

### CC4 — One system map (de-duplicate, keep on main) *(HTML/JS/CSS)*
- The pipeline is currently rendered **three times**: `fund-model-grid` (5 cards), `system-flow-diagram` (6 lanes / 10 nodes), and the operations role spine. Collapse to **one** canonical node-by-node system map that stays on the main view (per the 2026-06-05 decision — founders want the node detail). Lead it with a compact team-health row (COO · Research Analyst · Strategy Lead · Head of Quant · Risk Agent · PaperOps, each a status dot from `modules`), then the expandable map below it.
- Delete the two redundant renderings; keep `buildSystemConnectivityModel` as the single source for the kept map.
- **Done when:** the pipeline is rendered exactly once; node-by-node detail retained on main; team health legible in <2s.
- **Status:** completed. The default Overview now renders one canonical node-by-node operating map from `buildSystemConnectivityModel`, preceded by the six-role team-health row. The old fund-model card grid and Operations duplicate flow map are removed from the visible path; Operations now keeps diagnostics, edge states, event trail, governance, and communications audit only.

### CC5 — Render only the contract *(JS — the core refactor)*
- Rewrite the render entrypoint to consume `mission_control` and render the seven blocks in order. Collapse the 17 `build*` functions to ~6 (`team`, `sources`, `strategy`, `portfolio`, `trades`, `thinking`) + `diagnostics`. Delete the Overview/detail duplication and the view-switcher logic from the default path.
- Keep `fetchDashboardStatus`, currency, time, and status-tone helpers.
- **Done when:** every block reads its single contract slice; no value is rendered twice; `dashboard.js` materially smaller; no console errors against a live snapshot.
- **Status:** completed for the default founder view. `dashboard.js` now builds `founder_contract_model` from `mission_control` and renders the default Overview through seven contract-backed blocks: Mission Control brief, operating team map, source ledger, strategy narrative/ledger, paper portfolio line, trade lifecycle board, and thinking feed. Legacy raw-derived models remain exported for Diagnostics and checker compatibility until CC8 pruning.

### CC6 — Real portfolio timeline *(JS/CSS)*
- Render `capital.equity_curve` (20 live points) as an inline SVG sparkline using existing `--green/--coral` tokens and the present `.chart-*` classes; show balance, Δ%, drawdown, realized/unrealized, `closed/target`, and a **stale-mirror** badge driven by `mirror_freshness_status` (currently `stale`).
- **Done when:** the curve reflects real data; staleness is visible; no fabricated points.
- **Status:** completed. The founder Overview portfolio block now reads `capital.equity_curve` through the Mission Control contract, renders 20 real portfolio points, shows balance/Delta/drawdown/realized/unrealized/closed-target, exposes the stale mirror badge from `mirror_freshness_status`, and fails preflight if the renderer fabricates fallback points.

### CC7 — Visual system, responsive, a11y *(CSS/HTML)*
- Reuse `auth.css` tokens only (no new palette). Tighten vertical rhythm to `--section-gap`; ensure single-column phone layout; verify focus order, `aria-current`, contrast (AA), reduced-motion for the sparkline, and that the drawer is keyboard-operable.
- **Done when:** clean on a 390px viewport in one scroll; axe/Lighthouse a11y ≥ 95.
- **Status:** completed. The dashboard now uses the existing `--font-sans`/`--font-mono` tokens in the latest visual block, ships the `20260607-cc7-visual-a11y` asset key, keeps the founder view single-column on phone widths, exposes plus/minus click/tap disclosures, adds keyboard tab navigation plus Escape-to-close for diagnostics, labels the diagnostics drawer as a region, and validates the contract through `scripts/check_dashboard_cc7_visual_a11y.js`.

### CC8 — Prune payload, tests, docs, deploy *(backend/infra)*
- Remove now-unused raw top-level keys from the assembler only after every referencing checker, automation, and mirror has migrated. If any production path still depends on a key, keep it and record it in a `diagnostics.prune_candidates` list.
- CC8 migration rule: keep `diagnostics.prune_candidates` as the compatibility list and add `diagnostics.prune_audit` for every retained raw key. The audit must name the retained key, dependent surfaces, namespace shadow, and safe-removal state. Current posture is conservative: `safe_to_remove_count=0` until checker, automation, mirror, and diagnostics references have migrated.
- Update the User Guide (`landing-page-repo/guide/index.html`) and the whitepaper "How To Use Qadam" section to match the new six-block IA.
- Deploy via `landing-page-repo/scripts/deploy-vercel-production.sh` with the CC0 rollback ready; bump the asset version query to `20260607-cc8-prune-docs`.
- **Done when:** payload key count is reduced where safe or every retained raw key has a documented dependent; all checkers green; guide/whitepaper aligned; production verified.

---

## 7. Render Refactor Detail (17 → 6)

| Keep (≈6) | Fold in / delete |
|---|---|
| `buildTeam` (new, from `modules`) + `buildSystemConnectivityModel` (kept — renders the single main-view map) | `buildOperationsRoleSpine` merged in; `buildOperationsModel`, `buildOperationsFeedClusters` → Diagnostics-only |
| `buildSources` (was `buildSourcesModel`) | Overview source mini |
| `buildStrategy` (new, from `trading_philosophy`+`thinking.strategy`) | `strategy-manifestation` render |
| `buildPortfolio` (was `buildPerformanceModel`) | `buildBalanceTickerModel` merges in |
| `buildTrades` (was `buildTradesModel`) | `buildTradeTimelineTokens` merges in; 3 diagnostic groups → drawer |
| `buildThinking` (was `buildReasoningModel`) | worldview render, reasoning-lane cards |
| `buildOverviewModel` | **deleted** — Overview is the page now, not a separate summary |
| `buildGovernance*` (3 fns) | **Diagnostics-only** |
| `buildDashboardSafetyStripModel` | kept, simplified to the single strip |

---

## 8. Risks & Rollback

| Risk | Likelihood | Mitigation |
|---|---|---|
| Public-safe contract regression | Low | Projection is additive until CC8; `validatePublicStatus` untouched; checker green-gates each stage |
| Certification/audit loses its UI | Medium | Diagnostics drawer preserves full map, phases, kill-switch ledger, governance, Telegram |
| `check_*.py` break on pruned keys (CC8) | Medium | Grep all referencing checkers in CC1; migrate them before CC8 prune |
| Equity curve gaps / stale mirror misread as failure | Low | Explicit stale-mirror badge from `mirror_freshness_status`; never interpolate |
| Founder expects a removed panel | Low | CC0 delete list signed off by Ramin; drawer still contains it |
| Scope creep back into "add a panel" | Medium | Principle §2 is the gate: new content must replace, not append |

**Rollback:** every stage is a separate commit; CC0 baseline + asset version query lets us revert `index.html`/`dashboard.js`/`auth.css` and re-export the prior snapshot without backend changes.

---

## 9. Implementation Order & Effort (relative)

`CC0` (S) → `CC1` (M, backend contract) → `CC2` (M, the satisfying delete) → `CC3` (S) → `CC4` (M) → `CC5` (L, core JS) → `CC6` (M) → `CC7` (M) → `CC8` (M, guarded pruning/docs/deploy).

Fastest visible win after the contract is safe: **CC2 + CC3 immediately after CC1** (delete legacy panels + collapse safety language). This is mostly `index.html`, but it must follow CC1 so deleted panels have a clean founder contract and Diagnostics drawer to land in.

---

## 10. Acceptance Criteria (Success Definition)

The cut succeeds when, against a **live** snapshot:

1. Authority language ("read-only/paper-only/live-capital/cannot") appears **≤ 5 times in the default rendered founder view** (hidden Diagnostics/audit surfaces may retain precise boundary language).
2. **No value is rendered twice** across the default view (no Overview/detail duplication).
3. The pipeline/team narrative is rendered **once** — one canonical node-by-node system map on the main view, not three parallel renderings.
4. **Zero hardcoded data** in markup — balance, counts, sources all from the snapshot or an honest empty state.
5. Default view answers the **six questions** above the fold-equivalent on a 390px phone in **one scroll**.
6. `dashboard.js` `build*` functions reduced to ~6 in the default path.
7. `cockpit-status.json` founder data read from **`mission_control` only**; key count reduced from 76 where safe, with any retained raw top-level keys documented as dependent-driven prune candidates after CC8.
8. All `scripts/check_*.py` green; `validatePublicStatus` passes; a11y ≥ 95; safety strip screen-reader-announced.
9. User Guide + whitepaper "How To Use" reflect the six-block IA.

> The dashboard should read like the whitepaper's closing line: **no edge, no trade** — and, for the UI, **no signal, no pixel.**
