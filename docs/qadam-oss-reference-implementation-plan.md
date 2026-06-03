# Qadam OSS Reference Implementation Plan

This plan turns the recent open-source repo review into an implementation path for Qadam.

It does not replace the master implementation plan. It is an overlay that sharpens Agent OS, Phase 2 shadow intelligence, the cockpit, the operator inbox, and later paper-trading operations.

## 1. Objective

Use external open-source financial-agent and agent-infrastructure projects as reference architecture, not as executable dependencies.

Qadam should gain five things:

1. Stricter role and authority contracts.
2. A research-goal lifecycle before trade ideas exist.
3. A richer data-source and market-context taxonomy.
4. A better Fund Manager operator surface.
5. Durable human-in-the-loop alert and approval workflows.

The implementation must preserve Qadam's current safety model:

- Paper mode only.
- Dashboard cannot place orders.
- LLMs cannot approve risk.
- Quantum output remains a shadow annotation.
- Live capital remains off.
- Broker write routes stay behind explicit policy gates.
- External repos can inform architecture, but their code is not copied into Qadam unless license, security, and safety review explicitly pass.

## 2. The Five Reference Recommendations

| Recommendation | Reference Pattern | What Qadam Should Adopt | What Qadam Must Not Adopt Blindly |
| --- | --- | --- | --- |
| Role contracts and execution separation | AutoHedge-style director, quant, risk, and execution separation | Make every Qadam role declare inputs, outputs, permissions, forbidden actions, and handoff rules in code. | Do not import autonomous execution or live broker behavior. |
| Research-goal lifecycle | Vibe-trading / agentic trading workflow patterns | Create explicit research goals before signals: thesis, watched instruments, evidence needs, kill conditions, owner agent, and status. | Do not let natural-language goals become order intent. |
| Financial terminal taxonomy | Fincept Terminal-style analytics and connector breadth | Improve source categories, market context, portfolio views, options context, economic data, and dashboard information architecture. | Do not copy AGPL/commercially restricted code or treat terminal UX as proof of signal quality. |
| Operator chat and tool UX | LibreChat-style multi-model, MCP, and multi-user operator patterns | Give Fund Managers an inspectable command/chat interface for asking what Qadam is watching, why, and what is blocked. | Do not allow chat commands to bypass policy, place orders, or expose secrets. |
| Durable inbox and approval workflows | Cloudflare Agents / durable human-in-the-loop workflow patterns | Add durable alerts, approval requests, acknowledgements, retries, and operator inbox items with explicit expiry. | Do not move canonical private state out of the MacBook/local spine. |

## 3. Architecture Principle

External repos become `Resource Registry` entries. They can affect:

- agent manifests,
- check scripts,
- dashboard UX,
- event schemas,
- source taxonomy,
- operator inbox design,
- research workflow design.

They cannot directly affect:

- broker POST routes,
- live capital,
- order submission,
- signal approval,
- risk approval,
- quantum hardware submission,
- secret handling.

## 4. Planned Runtime Flow

Target flow after this plan is implemented:

```text
Live observations / durable replay
  -> Research Goal intake
  -> Local Research Analyst compression
  -> Strategy Lead challenge packet
  -> Signal Integrity Gate
  -> Head of Quant shadow annotation
  -> Risk Agent policy review
  -> Paper intent / staged order contract
  -> Alpaca paper mirror
  -> Postmortem / learning loop
  -> Fund Manager inbox and dashboard visibility
```

No single step can create authority by itself. Authority is explicit, local, logged, and checked.

## 5. Implementation Stages

### OR-0 - Reference Intake And License Boundary

Objective: create a disciplined way to study external repos without contaminating Qadam with unsafe or incompatible code.

Build:

- Add `docs/qadam-oss-reference-implementation-plan.md`.
- Add or update Resource Registry entries for the five reference categories.
- Add a local-only review workspace convention:
  - clone external repos only into `/private/tmp/qadam-oss-review/` or another ignored scratch area;
  - never commit cloned repo contents;
  - record only short review notes in Qadam docs.
- Add a source-review checklist:
  - license;
  - execution behavior;
  - broker/API authority;
  - secret handling;
  - testability;
  - dashboard relevance;
  - Qadam adoption decision.

Artifacts:

- `docs/qadam-oss-reference-implementation-plan.md`
- `docs/qadam-resource-registry.md`
- Optional future: `docs/external-reference-reviews/*.md`

Acceptance:

- Master plan links to this appendix.
- Each external repo category has a Qadam adoption boundary.
- No third-party code is vendored accidentally.

### OR-1 - Agent Role Contract Hardening

Objective: make the AutoHedge-style role split useful inside Qadam without inheriting unsafe autonomy.

Build:

- Extend existing agent manifests with:
  - `input_contract`;
  - `output_contract`;
  - `handoff_contract`;
  - `authority_contract`;
  - `blocked_actions`;
  - `operator_visibility`.
- Define role-specific authority:
  - COO / Python Orchestrator: can schedule, fetch, ingest, export status, and run checks.
  - Research Analyst / Local LLM: can compress observations and propose shadow interpretations only.
  - Strategy Lead / Frontier LLM: can challenge, compare, and write strategy review packets only.
  - Head of Quant: can annotate ambiguity and pattern strength only.
  - Signal Auditor: can pass, hold, or block signals for risk-shadow review only.
  - Risk Agent: can block/hold/size in shadow or paper policy only, depending on current gate.
  - Execution Auditor: can validate lifecycle and reconciliation, not submit orders directly.
  - Fund Manager Interface: can display, acknowledge, and comment, not execute.
- Add check coverage for any agent missing a handoff or authority section.

Likely files:

- `agents/*/agent.md`
- `orchestrator/agent_registry.py`
- `orchestrator/agent_runtime.py`
- `scripts/check_agent_manifests.py`
- `scripts/check_agent_runtime.py`
- `scripts/check_phase1_agent_os.py`

Acceptance:

- Every agent has explicit allowed inputs and outputs.
- Every agent has at least one forbidden action.
- No agent can call a broker-write route.
- No LLM role can approve risk.
- No quantum role can originate trades.
- Dashboard can show each role's current purpose and boundary.

### OR-2 - Research Goal Lifecycle

Objective: implement the strongest practical lesson from agentic trading repos: Qadam should reason through research goals before trade candidates.

Implementation status, 2026-06-02:

- `orchestrator/research_goal.py` now defines the Phase 2 Research Goal schema, JSONL store, deterministic sample seeding, public-safe summary, validation rules, secret-like value rejection, and hard-false authority fields.
- `scripts/check_research_goal_lifecycle.py` validates the lifecycle with sample energy/chokepoint and semiconductor goals, minimum source quorum, required sources, watched instruments, missing corroboration, and zero execution/paper-order/risk/broker/live-capital authority.
- `orchestrator/phase2_shadow_cycle.py` now creates/updates Research Goals from source observations in sample, live-source, and durable-replay modes, attaches a sanitized research-goal context to Research Analyst packets, and reports research-goal counts and authority counters.
- `orchestrator/strategy_lead.py` now receives Research Goal lifecycle context and turns recent goals into challenge questions while preserving challenge-only status and zero authority.
- `orchestrator/cockpit_status.py` now exposes `cognition.research_goals`, `cognition.research_goal_records`, Mission Control research-goal counts, and the research-goal intake step in the analysis timeline.
- `landing-page-repo/dashboard.js` now renders Research Goals as the pre-hypothesis queue inside the Reasoning workspace.
- Verified locally: `scripts/check_research_goal_lifecycle.py`, `scripts/check_phase2_durable_replay_cycle.py`, `scripts/export_cockpit_status.py`, and `scripts/check_cockpit_status.py` pass. PaperOps is exposed truthfully as safe-idle/no-current-qualified-setup; Qadam waits for a real qualified setup rather than forcing a trade to satisfy the later PT-4/PT-5/PT-6/PT-7/30-day chain.

Build a new research-goal contract with these fields:

- `goal_id`
- `created_at`
- `status`: `watching`, `needs_evidence`, `researching`, `strategy_review`, `blocked`, `candidate_ready`, `closed`
- `origin`: live source, worldview lens, Fund Manager note, Telegram intake, postmortem, or scheduled scan
- `hypothesis`
- `market_channel`
- `watched_instruments`
- `required_sources`
- `minimum_source_quorum`
- `worldview_lens`
- `akber_stage`
- `evidence_packets`
- `contradictory_evidence`
- `missing_corroboration`
- `invalidation_conditions`
- `owner_agent`
- `next_handoff`
- `execution_allowed=false`
- `paper_order_allowed=false`

Build:

- Add `orchestrator/research_goal.py`.
- Add deterministic sample data and sample validation.
- Add a JSONL store at `data/runtime/research_goals.jsonl`.
- Add a check script:
  - `scripts/check_research_goal_lifecycle.py`
- Wire research goals into Phase 2 shadow cycle:
  - source observations can create or update research goals;
  - Research Analyst consumes goals, not raw loose observations;
  - Strategy Lead gets goal packets with context and contradictions;
  - trade candidates can only reference a research goal.

Acceptance:

- A live observation can create a research goal.
- A research goal can be updated by durable replay.
- A research goal can be closed as `no_trade`.
- A trade candidate cannot exist without `goal_id`.
- Every research goal remains non-executable until later gates pass.

### OR-3 - Data Taxonomy And Market Context Upgrade

Objective: use the financial-terminal reference pattern to make Qadam's data universe easier to inspect and more useful to reasoning.

Build:

- Add a canonical source taxonomy layer:
  - geopolitical/conflict;
  - physical/logistics;
  - macro/economic;
  - market/price/volume;
  - options/volatility;
  - prediction markets;
  - company/fundamental;
  - social/sentiment;
  - operator/member intake;
  - broker/account mirror.
- Add per-source capabilities:
  - latency class;
  - cost class;
  - credential status;
  - trust score;
  - freshness;
  - raw archive availability;
  - historical backfill availability;
  - dashboard visibility.
- Promote Yahoo Finance / yfinance from supplemental note to a bounded market-confirmation adapter once dependencies pass:
  - price;
  - volume;
  - options chain availability;
  - news context;
  - market status;
  - instrument metadata.
- Add a `market_context_packet` schema that Phase 2 and Phase 3 can consume.

Likely files:

- `orchestrator/source_registry.py`
- `orchestrator/yahoo_finance_adapter.py`
- `orchestrator/intelligence.py`
- `scripts/check_phase1_live_source_hardening.py`
- `scripts/check_yahoo_finance_market_confirmation.py`
- `docs/api-source-inventory.md`
- `docs/api-specs.md`
- `landing-page-repo/status/cockpit-status.json`
- `landing-page-repo/dashboard.js`

Acceptance:

- Dashboard source tracker can expand all sources by taxonomy.
- Each source reports connected/degraded/missing/deferred.
- Market-confirmation context can attach to a research goal.
- Price context is never treated as broker truth.
- Broker/account truth still comes only from Alpaca paper mirror.

### OR-4 - Fund Manager Operator Surface

Objective: borrow the operator UX idea from LibreChat without turning Qadam into a chat-only product.

Build:

- Add a protected operator panel in the cockpit:
  - "What is Qadam watching?"
  - "What is Qadam thinking about?"
  - "What is blocked?"
  - "Which research goals are active?"
  - "Which trade candidates exist?"
  - "What changed since last login?"
- Add a read-only command vocabulary:
  - `/status`
  - `/sources`
  - `/research-goals`
  - `/trades`
  - `/blocked`
  - `/portfolio`
  - `/worldview`
  - `/postmortems`
- Route commands to local/public-safe status data only.
- Store Fund Manager comments separately from model output.
- Add optional future MCP-style tool registry visibility:
  - tool name;
  - owning agent;
  - permission;
  - status;
  - whether it can write.

Likely files:

- `landing-page-repo/dashboard.js`
- `landing-page-repo/auth.css`
- `orchestrator/cockpit_status.py`
- `orchestrator/operator_intake.py`
- `scripts/check_operator_command_contract.py`
- `docs/qadam-user-guide.md`

Acceptance:

- Commands cannot create signals, orders, approvals, or broker writes.
- The cockpit answers from structured records, not raw model text.
- Every answer can link back to a source, research goal, trade intent, or safety block.
- Dashboard remains useful on mobile.

### OR-5 - Durable Inbox, Alerts, And Human-In-The-Loop Workflow

Objective: use durable agent/inbox patterns for Qadam's human oversight rail.

Build an operator inbox with these item classes:

- `source_degraded`
- `credential_expiring`
- `research_goal_needs_review`
- `strategy_challenge_ready`
- `signal_blocked`
- `paper_trade_candidate_ready`
- `paper_order_submitted`
- `position_opened`
- `position_closed`
- `postmortem_due`
- `kill_switch_triggered`

Each inbox item should include:

- `item_id`
- `created_at`
- `expires_at`
- `severity`
- `owner`
- `source_artifact`
- `summary`
- `required_action`
- `allowed_actions`
- `forbidden_actions`
- `acknowledged_by`
- `acknowledged_at`
- `status`

Build:

- Add `orchestrator/operator_inbox.py`.
- Add JSONL/local durable store first.
- Later mirror public-safe summaries into cockpit status.
- Add Telegram outbound hooks only for allowed message classes.
- Add dashboard inbox/notification rail.
- Keep all approval/action state local.

Likely files:

- `orchestrator/operator_inbox.py`
- `orchestrator/telegram_notifications.py`
- `scripts/check_operator_inbox.py`
- `scripts/send_telegram_test.py`
- `orchestrator/cockpit_status.py`
- `landing-page-repo/dashboard.js`
- `docs/qadam-telegram-bot-implementation-plan.md`

Acceptance:

- Qadam can create durable inbox items.
- Inbox items can be acknowledged.
- Expired items remain auditable.
- Telegram can notify but cannot execute.
- Dashboard shows inbox state without secrets or raw local paths.

## 6. Cross-Cutting Tests

Add or extend checks so this plan stays enforceable:

| Check | Purpose |
| --- | --- |
| `scripts/check_oss_reference_plan.py` | Verify docs/resource registry/master-plan links exist. |
| `scripts/check_agent_authority_contracts.py` | Verify every agent has authority and handoff contracts. |
| `scripts/check_research_goal_lifecycle.py` | Verify research goals are replayable and non-executable. |
| `scripts/check_market_context_packet.py` | Verify source taxonomy and market context packets are public-safe. |
| `scripts/check_operator_command_contract.py` | Verify commands are read-only and structured-record backed. |
| `scripts/check_operator_inbox.py` | Verify durable inbox lifecycle and Telegram boundaries. |

All checks should print explicit counters:

- created records;
- blocked records;
- execution authority count;
- paper-order authority count;
- broker-write authority count;
- live-capital authority count;
- secret-exposure count.

Acceptance rule: all authority counts must remain zero unless a later master-plan gate explicitly changes them.

## 7. Dashboard Changes

The cockpit should expose the OSS-driven improvements as practical user value:

- Mission Control shows:
  - active research goals;
  - source coverage;
  - what the Local LLM is compressing;
  - what the Strategy Lead is challenging;
  - what the Head of Quant annotated;
  - candidate trades;
  - open positions;
  - blocked reasons.
- Sources view shows:
  - source taxonomy;
  - source credentials;
  - freshness;
  - latency;
  - trust score;
  - read-only/write status.
- Reasoning view shows:
  - research goal lifecycle;
  - evidence packets;
  - contradictions;
  - world-model lens;
  - Akber stage;
  - Strategy Lead challenge.
- Trades view shows:
  - candidate/blocked/open/closed/postmortem states;
  - linked research goal;
  - linked evidence;
  - linked risk status;
  - linked broker mirror.
- Operations view shows:
  - operator inbox;
  - Telegram rail;
  - commands;
  - credential warnings;
  - source degradation.

## 8. First Sprint

Recommended implementation order:

1. Add OR-0 docs and Resource Registry updates.
2. Add research-goal schema in dry mode.
3. Add `scripts/check_research_goal_lifecycle.py`.
4. Connect Phase 2 shadow cycle to research goals in deterministic mode.
5. Add public-safe research-goal summary to `cockpit-status.json`.
6. Add dashboard Research Goals panel.
7. Add operator inbox schema in dry mode.
8. Add Telegram notify-only link for inbox items after local checks pass.

Do not start with broker execution. The useful first gain is not more trades; it is a better reasoning and oversight spine.

## 9. Definition Of Done

This plan is complete when:

- The master plan links to this appendix.
- Resource Registry includes the OSS reference categories.
- At least one research goal can be created from a live or replayed observation.
- Local Research Analyst consumes research goals rather than loose observations.
- Strategy Lead challenge packets reference research goals.
- Dashboard exposes active research goals, blocked reasons, source posture, and inbox items.
- Telegram can report inbox items without execution authority.
- All new checks prove:
  - no broker writes;
  - no live capital;
  - no LLM risk approval;
  - no quantum trade origination;
  - no secret exposure.

## 10. Risks And Controls

| Risk | Control |
| --- | --- |
| Copying incompatible code | Review license first; use pattern-only unless explicitly approved. |
| Importing unsafe execution behavior | Keep all external execution patterns behind Qadam's existing policy gates. |
| Dashboard becoming too complex | Add segmented navigation and collapsible details, not another infinite-scroll panel. |
| Chat interface becoming authority surface | Commands are read-only and structured-record backed. |
| Durable inbox becoming cloud state of record | Keep canonical inbox state local; public dashboard only receives safe summaries. |
| External repo hype biasing Qadam | Every adoption must map to a Qadam module, check script, or dashboard improvement. |

## 11. Immediate Next Step

Start with OR-2 Research Goal Lifecycle.

Reason: it improves Qadam's intelligence quality without changing trading authority. It also gives the dashboard a clear answer to the user's core questions:

- What is Qadam watching?
- What is Qadam thinking about?
- Why is it blocked?
- What trade ideas are forming?
- What evidence is still missing?
