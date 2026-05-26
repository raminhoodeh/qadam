# Qadam Preference MCP Integration Plan

Date: 2026-05-24
Status: staged implementation plan, complete through PREF-12

## 1. Decision

Preference/PREF should be treated as a supplemental read-only data capability
plane for Qadam, not as an automatic replacement for the canonical 35-source
registry.

The useful shift is strategic: Preference can compress many currently missing,
deferred, or credential-heavy source classes behind one MCP interface. That can
improve Qadam's observation layer for prediction markets, physical movement
signals, weather, filings, crypto/wallet intelligence, macro, news, and sports
line context. But Qadam must not let a broad aggregator bypass the source
registry, provenance requirements, Signal Integrity Gate, Trust Score model,
approval records, or execution boundaries.

Initial classification:

- capability key: `preference_mcp`
- provider label: `preference_labs_mcp`
- role: `supplemental_multi_source_data_plane`
- source-count treatment: not counted as source 36
- promotion treatment: individual upstream sources discovered through
  Preference can be promoted later only through an explicit registry decision
- authority: read-only observation and research enrichment only
- default mode: disabled live, sample/catalog mode first
- first consuming phase: Phase 4 amendment and Phase 5 design inputs only after
  Q4-12 remains fail-closed or is rerun with explicit approval

## 2. Official Capability Facts To Carry

The Preference material describes a remote Streamable HTTP MCP endpoint at
`https://pref.trade/mcp` with Bearer authentication. Agent onboarding uses
`POST https://pref.trade/v1/agents/register` and returns a one-time
`pref_agent_*` key plus an optional human claim URL. MCP identity must be
verified inside the MCP by calling `preference_account_status`; `/v1/auth/whoami`
is not the verification path for agent keys.

The public docs describe anonymous, registered-agent, and linked-account tiers,
with daily quotas, and state that Polymarket and Kalshi tools are free. They
also instruct clients to discover current capability surface through
`search_tools` instead of assuming a fixed tool list.

Important interpretation for Qadam:

- "No APIs" means no per-source API integrations for the agent. Qadam still
  integrates a remote MCP over HTTPS and still handles a provider key.
- "No scraping" does not remove Qadam's provenance obligation. Each datapoint
  still needs upstream source identity, timestamp, query, tool reference, and
  payload hash.
- "Read-only" is compatible with Qadam's current safety posture, but Qadam must
  enforce that boundary locally rather than trusting marketing language.
- Broad MCP access is not the same thing as canonical source trust. Preference
  can supply observations; Qadam decides source rank, quorum, degradation, and
  whether the evidence can support later strategy work.

## 3. Fit With Current Qadam Architecture

Existing Qadam pieces this should reuse:

- `orchestrator/config.py` for runtime controls and budgets.
- `orchestrator/event_log.py` for local event records.
- `orchestrator/adapters.py` for raw payload archive, `SourceEnvelope`, and
  normalized events.
- `orchestrator/source_health.py` and `data_environment_map.json` for status.
- `orchestrator/resource_registry.py` for non-live capability references.
- `orchestrator/phase4_data_veracity.py` for canonical versus supplemental
  source scoring.
- `orchestrator/phase4_trust_scores.py` for Trust Score impact.
- `orchestrator/phase4_candidate_strategy_universe.py` for strategy-source
  weights.
- `orchestrator/cockpit_status.py` and `landing-page-repo/dashboard.js` for
  public-safe visibility.
- `docs/api-specs.md` and `docs/api-source-inventory.md` for source and
  credential posture.

The Yahoo Finance wrapper is the closest local pattern: sample mode first,
disabled live mode by default, explicit request budget, raw archive,
degraded-state handling, public-safe status, and no execution/fill/receipt/
reconciliation authority.

## 4. Required Improvements

Preference adds capability breadth, so Qadam needs more than a single adapter:

1. MCP client boundary

   Add a small remote MCP client wrapper that can call only:
   `preference_account_status`, `search_tools`, and allowlisted discovered tools.
   The wrapper should fail closed on anonymous identity, missing Authorization
   header, stale config, 401, 429, and 5xx errors.

2. Tool catalog ledger

   Store a sanitized snapshot of discovered tools in
   `data/runtime/preference_tool_catalog.json`. Each catalog row should include
   tool name/ref, domain, input schema summary, quota/credit metadata when
   available, upstream source classes, public-safe description, and whether Qadam
   has approved it for sample, live-read, or blocked use.

3. Source identity and provenance

   Every Preference observation must preserve:
   `tool_ref`, `pref_request_id` or response id when present, query hash,
   upstream source name, upstream provenance URL/id when present, fetched time,
   observed time, freshness/cadence, payload hash, and credit-cost metadata.
   If upstream provenance is missing, the observation is quarantined.

4. Quota and cost control

   Add local controls for daily call budget, per-run call budget, paid-tool
   block, domain allowlist, and account status. No paid/credit-consuming
   calls should happen unless a stage explicitly approves them. Quota pressure
   must degrade the adapter rather than retrying aggressively.

5. Domain packs

   Do not expose 670+ tools directly to agents. Map discovered tools into
   Qadam domain packs:

   - prediction markets: Polymarket, Kalshi, orderbooks, market metadata
   - physical movement: vessel, aircraft, satellite, weather, chokepoints
   - filings and corporate: SEC, company disclosures, ownership context
   - macro and commodities: NOAA/weather, oil-linked physical data, rates
   - crypto and wallets: Hyperliquid, dFlow, KOL wallets, on-chain context
   - sports lines: allowed as research only, outside the current first trading
     universe unless explicitly added later
   - news and narrative: media monitoring and event summaries

6. Corroboration policy

   Preference can return multiple upstream sources through one MCP provider.
   Qadam should count those as separate evidence only when the upstream source
   identities are distinct and traceable. A single Preference response without
   source separation is one supplemental observation, not a source quorum.

7. Strategy manifestation amendment

   Because Q4-12 is currently blocked pending explicit approval, this is the
   right time to add Preference as a capability consideration before approval.
   After implementation, rerun the Phase 4 data-veracity, trust-score,
   candidate-strategy, manifested-strategy, approval-record, cockpit, and
   certification checks before Phase 5 starts.

## 5. Modular Execution Roadmap

The Preference integration should be implemented in small slices. Each slice
must leave Qadam in a valid state and must be independently verifiable before
the next slice starts.

| Order | Stage | Mode | Primary deliverable | Network or key required | Stop condition |
| --- | --- | --- | --- | --- | --- |
| 1 | PREF-0 | docs only | Capability review and policy baseline | No | Preference is classified without authority. |
| 2 | PREF-1 | local config/check | Secret and identity contract | Key optional for degraded check; required for registered identity pass | Anonymous identity fails closed. |
| 3 | PREF-2 | catalog only | Tool catalog schema and discovery ledger | Key optional; live catalog waits for PREF-1 pass | Catalog is public-safe and does not call domain tools. |
| 4 | PREF-3 | offline sample | Qadam adapter skeleton and sample fixtures | No | Sample observations normalize and archive with zero authority. |
| 5 | PREF-4 | live smoke | Status/catalog-only live MCP gate | Yes | 401, anonymous, quota, timeout, or 5xx degrade cleanly. |
| 6 | PREF-5 | validation | Provenance and source-quorum contract | No for tests; live data later | Missing provenance and source-quorum overclaims are rejected. |
| 7 | PREF-6 | Qadam registry | Source inventory, Resource Registry, Data Veracity, Trust Score policy | No | Preference is supplemental and cannot affect canonical rank alone. |
| 8 | PREF-7 | domain mapping | First-trading-universe domain packs | No for mapping; live use later | Every domain pack has explicit allowed tools and no-trade boundaries. |
| 9 | PREF-8 | shadow context | Research Analyst, Strategy Lead, and Signal Integrity enrichment | No for deterministic shadow context; live identity still required later | Enrichment remains challenge-only and non-executable. |
| 10 | PREF-9 | visibility | Cockpit and Mission Control status | No for degraded/sample status | Public dashboard shows posture without secrets or readiness overclaim. |
| 11 | PREF-10 | Phase 4 amendment | Preference-aware strategy manifestation update | No | Phase 4 remains uncertified until explicit approval is logged. |
| 12 | PREF-11 | certification | Q4-10/Q4-12 approval and certification update | No | Phase 5 remains blocked unless amended strategy is approved and certified. |
| 13 | PREF-12 | optional promotion | Per-upstream-source canonical promotion decision | Case-by-case | No bulk promotion of the Preference aggregator. |

Dependency rules:

- PREF-0 must be completed before any key registration or MCP installation.
- PREF-1 must pass with a non-anonymous identity before any live MCP call beyond
  degraded/status checking is treated as valid.
- PREF-2 and PREF-3 can be implemented in parallel after PREF-0 because both can
  run without live domain data.
- PREF-4 must not call domain tools; it is status and catalog smoke only.
- PREF-5 must pass before Preference data can be used as evidence in Phase 2,
  Phase 4, or Phase 5.
- PREF-6 through PREF-10 make Preference visible and useful to Qadam, but still
  do not certify Phase 4 or start Phase 5.
- PREF-11 is required after Preference changes the Manifested Strategy
  Document before Fund Manager approval.
- PREF-12 is optional and should happen only one upstream source at a time.

Recommended working batches:

- Batch 1: PREF-0.
- Batch 2: PREF-1.
- Batch 3: PREF-2 and PREF-3.
- Batch 4: PREF-4 and PREF-5.
- Batch 5: PREF-6 and PREF-7.
- Batch 6: PREF-8 and PREF-9.
- Batch 7: PREF-10 and PREF-11.
- Batch 8: PREF-12 only if a specific upstream source deserves promotion.

## 6. Stage Details

### PREF-0 - Intake, Policy, And Current-State Baseline

Objective: decide what Preference is allowed to be before any key is created or
MCP call is wired into Qadam.

Work:

- Create a Preference capability review audit document.
- Record the official endpoint, transport, auth, registration, status-check,
  quota, and security posture.
- Classify Preference as supplemental, read-only, and non-canonical.
- Define forbidden actions:
  - no execution
  - no broker writes
  - no paper orders
  - no live capital
  - no fill/receipt/reconciliation truth
  - no automatic canonical-source promotion
  - no paid-tool calls without explicit approval
- Define where Preference can help the five current strategy families.

Verification:

```bash
rg -n "Preference|PREF|preference_mcp" docs/qadam-preference-mcp-integration-plan.md docs/api-source-inventory.md docs/api-specs.md docs/qadam-master-implementation-plan.md
```

Done when: the plan and source docs classify Preference without granting
authority.

Current status: Complete as of 2026-05-24. PREF-0 is recorded in
`docs/qadam-preference-mcp-pref-0-capability-review-audit-2026-05-24.md`.
Preference/PREF MCP is classified as a supplemental read-only multi-source data
plane, not source 36, not an execution venue, not a broker, and not a source of
fill, receipt, broker echo, or reconciliation truth. No key was registered, no
MCP server was installed, no live tools were called, and Phase 5 remains blocked
until Q4-12 certification passes.

### PREF-1 - Secret, MCP Identity, And Anonymous-Fail-Closed Contract

Objective: make the Preference identity explicit and private before any tool use.

Work:

- Add config fields:
  - `PREFERENCE_MCP_ENABLED=false`
  - `PREFERENCE_API_KEY_CONFIGURED`
  - `PREFERENCE_MCP_ENDPOINT=https://pref.trade/mcp`
  - `PREFERENCE_MCP_TRANSPORT=streamable-http`
  - `PREFERENCE_DAILY_CALL_BUDGET`
  - `PREFERENCE_RUN_CALL_BUDGET`
  - `PREFERENCE_PAID_TOOLS_ALLOWED=false`
  - `PREFERENCE_TOOL_ALLOWLIST`
  - `PREFERENCE_DOMAIN_ALLOWLIST`
- Store the real key only in local ignored runtime storage or the shell
  environment. Never put it in docs, prompts, logs, committed config, or public
  cockpit JSON.
- Add a check script that verifies the key through `preference_account_status`.
- Fail if identity is `anonymous`.
- Fail if the response omits quota/reset metadata.
- Redact every key-shaped value from stdout and Event Log.

Verification:

```bash
.venv/bin/python scripts/check_preference_mcp_identity.py
./scripts/run_pre_phase3_operational_routine.sh --stage secret-scan
```

Done when: Qadam can prove whether Preference is unavailable, anonymous,
registered-agent, or linked-account without leaking secrets.

Current status: Complete as of 2026-05-24. PREF-1 is recorded in
`docs/qadam-preference-mcp-pref-1-identity-status-gate-audit-2026-05-24.md`.
It added local Preference config, a public-safe identity/status contract, a
check script, masked secret status, and secret-scan coverage for
`pref_agent_*`-shaped values. Current runtime is correctly blocked because
`PREFERENCE_MCP_ENABLED=false`, no `PREFERENCE_API_KEY` is configured, and no
live status check was requested. No Preference endpoint was called during the
default check, no domain tools were called, and all execution, broker, paid-tool,
paper-order, quantum-provider, scheduler, fill, receipt, reconciliation, and
live-capital authority remains disabled.

### PREF-2 - Tool Catalog Discovery Snapshot

Objective: discover available tools without using domain tools yet.

Work:

- Add `orchestrator/preference_mcp_catalog.py`.
- Call `search_tools` with safe broad queries for the Qadam domain packs.
- Request callable detail only for candidate tools that match a domain allowlist.
- Write `data/runtime/preference_tool_catalog.json`.
- Write `data/runtime/preference_tool_catalog_history.jsonl`.
- Mark every discovered tool as:
  - `approved_for_catalog_only`
  - `candidate_read_only`
  - `blocked_paid_tool`
  - `blocked_no_provenance`
  - `blocked_outside_scope`
- Do not call market/orderbook/wallet/filing/weather tools in this stage.

Verification:

```bash
.venv/bin/python scripts/check_preference_tool_catalog.py
```

Done when: the catalog is replayable, public-safe, and no domain data was
fetched.

Implementation status: complete on 2026-05-24 in
`docs/qadam-preference-mcp-pref-2-tool-catalog-audit-2026-05-24.md`.
PREF-2 added `orchestrator/preference_mcp_catalog.py`,
`scripts/check_preference_tool_catalog.py`, and the runtime artifacts
`data/runtime/preference_tool_catalog.json` plus
`data/runtime/preference_tool_catalog_history.jsonl`. Current local outcome is
`blocked_pending_verified_identity`: no live catalog call was attempted,
`search_tools` was not called, no domain tool was called, no paid tool was
allowed, and sports-line discovery rows remain `blocked_outside_scope`.

### PREF-3 - Adapter Skeleton With Deterministic Sample Fixtures

Objective: make Preference look like a normal Qadam adapter before live calls.

Work:

- Add `orchestrator/preference_mcp_adapter.py`.
- Add deterministic sample payloads for:
  - Polymarket orderbook depth
  - Kalshi market summary
  - vessel movement near a chokepoint
  - NOAA/weather event
  - SEC filing metadata
  - smart-wallet movement
- Normalize samples into Qadam `UnifiedEvent` records.
- Archive raw sample payloads under `data/raw_payloads/preference_mcp/`.
- Write Event Log records with every authority flag false.
- Add `scripts/check_preference_mcp_adapter.py`.

Verification:

```bash
.venv/bin/python scripts/check_preference_mcp_adapter.py
.venv/bin/python -m compileall orchestrator/preference_mcp_adapter.py scripts/check_preference_mcp_adapter.py
```

Done when: sample mode works offline and validates the no-authority boundary.

Implementation status: complete on 2026-05-24 in
`docs/qadam-preference-mcp-pref-3-offline-sample-adapter-audit-2026-05-24.md`.
PREF-3 added `orchestrator/preference_mcp_adapter.py` and
`scripts/check_preference_mcp_adapter.py`. The adapter emits six deterministic
offline `UnifiedEvent` samples across Polymarket, Kalshi, vessel movement,
NOAA/weather, SEC filing metadata, and smart-wallet movement, then archives the
raw sample payload under `data/raw_payloads/preference_mcp/`. Current local
outcome is `ok` in sample mode: identity remains `blocked`, catalog remains
`blocked_pending_verified_identity`, no live MCP call was attempted,
`search_tools` was not called, no domain tool was called, no source-quorum
credit is granted, and no trading or execution authority exists.

### PREF-4 - Live Read-Only Smoke Gate

Objective: permit the smallest possible live read while preserving fail-closed
behavior.

Work:

- Keep live disabled by default.
- Permit `--live-status-only` to call only `preference_account_status`.
- Permit `--live-catalog-only` to call `search_tools`.
- Add `--live-read-only --tool-ref ...` only after a tool appears in the
  allowlist.
- Enforce timeout, call budget, quota check, and paid-tool block before each
  call.
- Degrade on 401/429/5xx and preserve provider error class locally.

Verification:

```bash
.venv/bin/python scripts/check_preference_mcp_adapter.py --live-status-only
.venv/bin/python scripts/check_preference_mcp_adapter.py --live-catalog-only
```

Done when: live status/catalog checks work or degrade cleanly without domain
data calls.

Implementation status: complete on 2026-05-24 in
`docs/qadam-preference-mcp-pref-4-live-read-only-smoke-gate-audit-2026-05-24.md`.
PREF-4 added status/catalog-only live smoke support to
`orchestrator/preference_mcp_adapter.py` and
`scripts/check_preference_mcp_adapter.py`. The current local outcome is
fail-closed: `--live-status-only` returns `blocked_preflight` and
`--live-catalog-only` returns `blocked_pending_verified_identity` because
`PREFERENCE_MCP_ENABLED=false` and `PREFERENCE_API_KEY` is not configured. No
live status call, live catalog call, `search_tools` call, domain tool call, paid
tool call, domain-data request, source-quorum credit, or trading authority was
attempted.

### PREF-5 - Provenance And Source-Quorum Contract

Objective: prevent source washing through a single aggregator.

Work:

- Add a `preference_provenance` block to every normalized event.
- Add validation that rejects or quarantines observations missing upstream
  source identity.
- Add source-quorum logic:
  - one Preference response with one upstream provenance path equals one
    supplemental observation
  - one Preference response with multiple distinct upstream sources can satisfy
    multi-source context only if each upstream identity is explicit
  - Preference plus Qadam canonical source can count as two only when upstream
    sources are genuinely distinct
- Add payload hashing and query hashing.

Verification:

```bash
.venv/bin/python scripts/check_preference_provenance.py
```

Done when: missing provenance, duplicate source identities, and source-quorum
overclaims fail validation.

Implementation status: complete on 2026-05-24 in
`docs/qadam-preference-mcp-pref-5-provenance-source-quorum-audit-2026-05-24.md`.
PREF-5 added `orchestrator/preference_mcp_provenance.py` and
`scripts/check_preference_provenance.py`, upgraded PREF-3 sample event
provenance with query hashes and payload hashes, and writes
`data/runtime/preference_provenance_source_quorum.json` plus history. Current
offline result is `validated`: 6 Preference observations, 6 explicit upstream
source identities, 0 quarantines, 0 duplicate identities, and 0 source-quorum
credit. Missing provenance, duplicate upstream identity, source-quorum
overclaim, payload hash tamper, aggregator-only identity, and duplicate
canonical overlap probes all fail validation.

### PREF-6 - Source Inventory, Resource Registry, And Trust Policy

Objective: make Preference visible to Qadam's planning system.

Work:

- Add a Resource Registry entry for Preference as a supplemental data-plane
  reference.
- Add a source inventory section that states it is not source 36.
- Add `docs/api-specs.md` credential placeholders and storage rules.
- Extend Phase 4 Data Veracity to include Preference as a supplemental row.
- Extend Trust Score recalculation to keep Preference out of canonical source
  rank unless a later registry decision promotes a specific upstream source.

Verification:

```bash
.venv/bin/python scripts/check_phase4_data_veracity_audit.py
.venv/bin/python scripts/check_phase4_trust_score_recalculation.py
.venv/bin/python scripts/check_phase4_resource_validation.py
```

Done when: Preference appears in supplemental capability posture and cannot
increase canonical source rank by itself.

Current status: Complete as of 2026-05-24. PREF-6 is recorded in
`docs/qadam-preference-mcp-pref-6-source-inventory-registry-trust-policy-audit-2026-05-24.md`.
Preference now appears in `docs/api-source-inventory.md`, the Resource Registry
as `supplemental_data_plane`, Phase 4 Data Veracity supplemental rows, and
Trust Score supplemental policy. It remains not source 36, score-included false,
source-quorum-credit false, and canonical-rank-impact false.

### PREF-7 - First-Trading-Universe Domain Packs

Objective: use Preference where it directly strengthens Qadam's first trading
universe.

Work:

- Prediction markets:
  - orderbook depth
  - market liquidity
  - cross-venue Polymarket/Kalshi comparison
- Crude oil:
  - vessel movement
  - chokepoint monitoring
  - NOAA/weather context
  - oil-linked prediction-market pricing
- Defence:
  - SEC filing metadata
  - government/procurement narrative where available
  - conflict and defence-linked prediction-market context
- Silver:
  - macro/weather/physical supply context where relevant
  - market confirmation as corroboration only
- Semiconductors:
  - SEC filings
  - news/narrative
  - policy and export-control context
  - KOL/wallet data only as risk sentiment, not company truth

Verification:

```bash
.venv/bin/python scripts/check_preference_domain_packs.py
```

Done when: each active strategy family has an allowed Preference domain pack and
an explicit no-trade boundary.

Current status: Complete as of 2026-05-24. PREF-7 is recorded in
`docs/qadam-preference-mcp-pref-7-first-trading-universe-domain-packs-audit-2026-05-24.md`.
It added `orchestrator/preference_mcp_domain_packs.py` and
`scripts/check_preference_domain_packs.py`. All five first-trading-universe
strategy families now have allowed Preference domain-pack mappings:
prediction markets, crude oil, defence, silver, and semiconductors. Live MCP
calls, `search_tools`, domain tools, paid tools, source-quorum credit,
Preference-only confirmation, trade candidates, broker writes, and live capital
remain disabled.

### PREF-8 - Shadow Intelligence Enrichment

Objective: let Research Analyst and Strategy Lead see Preference context without
creating trade candidates.

Work:

- Add Preference observations to shadow triage packets only as read-only
  context.
- Add Strategy Lead required challenges when Preference context is stale,
  single-source, missing provenance, or quota-degraded.
- Add Signal Integrity policy checks:
  - Preference-only confirmation is a hold condition
  - orderbook depth is market context, not executable venue permission
  - wallet/KOL movement is sentiment/risk context, not factual corporate
    evidence
- Keep all trade-candidate, risk-handoff, execution, paper-order, broker-write,
  quantum-provider, scheduler, and live-capital counters at zero.

Verification:

```bash
.venv/bin/python scripts/check_preference_shadow_context.py
.venv/bin/python scripts/check_signal_integrity_gate.py
.venv/bin/python scripts/run_phase2_shadow_cycle.py --durable-replay
.venv/bin/python scripts/check_phase2_durable_replay_cycle.py
.venv/bin/python scripts/check_strategy_lead_durable_context.py
```

Done when: Preference context can enrich challenge-only packets and cannot move
anything to execution.

Current status: Complete as of 2026-05-24. PREF-8 is recorded in
`docs/qadam-preference-mcp-pref-8-shadow-intelligence-enrichment-audit-2026-05-24.md`.
It added `orchestrator/preference_mcp_shadow_context.py` and
`scripts/check_preference_shadow_context.py`, attached a public-safe
`read_only_shadow_challenge_context` block to Research Analyst shadow triage
packets, carried that context into Strategy Lead durable replay packets, and
upgraded Signal Integrity to schema version 3 with Preference policy checks.
Current local outcome is `challenge_only_ready`: 6 deterministic Preference
observations, 6 distinct upstream identities, 2 active challenge rules
(`quota_degraded` plus Preference-only hold), and zero source-quorum,
trade-candidate, risk-handoff, execution, paper-order, broker-write, quantum,
scheduler, or live-capital authority.

### PREF-9 - Cockpit And Mission Control Visibility

Objective: show Fund Managers what Preference adds without implying trading
readiness.

Work:

- Add a public-safe `preference_mcp` status object to cockpit status:
  - enabled
  - identity status
  - quota status
  - catalog status
  - approved domain packs
  - last successful catalog check
  - degraded reason
  - authority flags
- Add dashboard sections for:
  - data-plane status
  - domain-pack coverage
  - provenance health
  - quota/credit health
  - blocked paid tools
- Never show raw keys, full prompts, raw payloads, or private source payloads.

Verification:

```bash
.venv/bin/python scripts/check_cockpit_status.py
node scripts/check_dashboard_renderer.js
node scripts/check_dashboard_mission_control.js
```

Done when: Fund Managers can see Preference posture and boundaries.

Current status: Complete as of 2026-05-24. PREF-9 is recorded in
`docs/qadam-preference-mcp-pref-9-cockpit-mission-control-visibility-audit-2026-05-24.md`.
It added a public-safe `preference_mcp` object to the cockpit status contract,
threaded the same posture into Mission Control, and rendered dashboard
visibility for data-plane status, domain-pack coverage, provenance health,
quota/credit health, and blocked paid tools. Current local outcome is
`challenge_only_ready` with live MCP disabled, identity not verified, quota
metadata missing, 6 approved domain packs, validated provenance, and zero
source-quorum, trade-candidate, risk-handoff, execution, paper-order,
broker-write, quantum, scheduler, or live-capital authority.

### PREF-10 - Phase 4 Re-Manifestation

Objective: amend the Manifested Strategy Document before Fund Manager approval.

Work:

- Rerun:
  - Q4-3 Data Veracity
  - Q4-4 Trust Score Recalculation
  - Q4-5 Resource Registry Validation
  - Q4-7 Candidate Strategy Universe
  - Q4-8 Manifested Strategy Draft
- Amend the strategy document to include Preference:
  - source role
  - domain packs
  - source-quorum rule
  - quota/freshness degradation rule
  - no-trade conditions
  - no execution authority
- Keep Q4-10 approval as `amendments_required` until the Fund Manager explicitly
  approves the amended document.

Verification:

```bash
.venv/bin/python scripts/check_phase4_data_veracity_audit.py
.venv/bin/python scripts/check_phase4_trust_score_recalculation.py
.venv/bin/python scripts/check_phase4_candidate_strategy_universe.py
.venv/bin/python scripts/check_phase4_manifested_strategy.py
```

Done when: Preference is reflected in strategy manifestation without certifying
Phase 4.

Current status: Complete as of 2026-05-24. PREF-10 is recorded in
`docs/qadam-preference-mcp-pref-10-phase-4-re-manifestation-audit-2026-05-24.md`.
It reran the Phase 4 data-veracity, trust-score, Resource Registry,
candidate-universe, and Manifested Strategy Draft path with Preference-aware
rules. Q4-7 strategy-family candidates now carry per-family
`preference_context_policy` blocks, including mapped domain packs, source-quorum
blocking, Preference-only hold rules, quota/freshness degradation rules, and
zero authority. `docs/qadam-manifested-strategy.md` is amended for
Preference/PREF MCP source role, six approved domain packs, per-strategy
domain-pack coverage, source-quorum rule, quota/freshness degradation rule,
no-trade conditions, and no execution authority. Q4-10 remains
`amendments_required`, and Q4-12 remains `blocked_pending_explicit_approval`.

### PREF-11 - Certification And Phase 5 Gate Update

Objective: require the amended Preference-aware strategy before Phase 5.

Work:

- Update Q4-12 certification blockers so Phase 5 remains blocked if:
  - Preference is enabled but identity is anonymous
  - Preference provenance validation fails
  - approved domain packs are missing for active strategy families
  - paid tools are enabled without explicit approval
  - source-quorum policy is violated
- Rerun Q4-10 and Q4-12 after explicit Fund Manager approval.

Verification:

```bash
.venv/bin/python scripts/check_phase4_approval_record.py
.venv/bin/python scripts/check_phase4_certification.py
```

Done when: Phase 4 can certify only with explicit approval of the
Preference-aware strategy document and all authority counts still zero.

Current status: Complete as of 2026-05-24. PREF-11 is recorded in
`docs/qadam-preference-mcp-pref-11-certification-phase-5-gate-audit-2026-05-24.md`.
It updates Q4-10 so Fund Manager approval is explicitly scoped to the amended
Preference-aware Manifested Strategy Document, with paid Preference tools,
source-quorum credit, execution, broker writes, and live capital still
unapproved. It also updates Q4-12 with a `preference_mcp_certification_gate`
that must validate identity posture, provenance, domain-pack coverage,
paid-tool policy, source-quorum policy, and zero authority before Phase 5
handoff can pass. In the current local posture, Preference live mode remains
disabled and identity is not verified, but that is not a live-mode blocker
because `PREFERENCE_MCP_ENABLED=false`; provenance is validated, six domain
packs cover five strategy families, paid tools are disabled, source-quorum
credit is false, and the only active Q4-12 blocker remains explicit Fund
Manager approval.

### PREF-12 - Optional Later Source Promotion

Objective: decide whether individual Preference-backed upstream feeds should
become canonical Qadam sources.

Work:

- Evaluate one upstream source at a time, not the whole Preference plane.
- Require provenance, freshness, terms/usage review, deterministic tests,
  durable replay behavior, and independent corroboration.
- If promoted, update:
  - `world_monitor/source_registry.py`
  - `docs/api-source-inventory.md`
  - source heartbeat
  - data veracity
  - trust scores
  - cockpit
  - master plan source count
- Do not promote `preference_mcp` itself as one canonical source unless the
  Fund Manager explicitly decides an aggregator should be counted that way.

Verification:

```bash
.venv/bin/python scripts/check_phase1_data_spine.py
.venv/bin/python scripts/check_source_heartbeat.py
.venv/bin/python scripts/check_phase4_data_veracity_audit.py
```

Done when: a specific upstream source has a registry decision and all counts
match the new source model.

Current status: Complete as of 2026-05-24. PREF-12 is recorded in
`docs/qadam-preference-mcp-pref-12-source-promotion-decisions-audit-2026-05-24.md`.
It added a Preference upstream source-promotion decision artifact and checker.
The current decision set evaluates six Preference sample upstreams one at a
time: Polymarket, Kalshi, SEC EDGAR, and vessel tracking map to existing
registry sources with no new source count, while NOAA-style weather context and
KOL wallet context are deferred pending direct endpoint, terms, replay, and
corroboration review. No Preference-backed upstream source is promoted, the
Preference aggregator is not source 36, the canonical source count remains 35,
Data Veracity and Trust Score expose the decision summary, and cockpit status
shows `source_promotion_status=validated` with zero promoted decisions.

Phase 4 closeout update as of 2026-05-24: Q4-10 approval scope and Q4-12
certification now directly require this PREF-12 decision artifact. Phase 4
cannot certify if Preference promotes upstream sources unexpectedly, changes the
canonical source count from 35, promotes the Preference aggregator, or marks
`preference_mcp` as source 36. Audit:
`docs/qadam-phase-4-data-source-closeout-audit-2026-05-24.md`.

## 7. Acceptance Criteria

Preference integration is ready for strategy use only when:

- MCP identity is registered or linked, not anonymous.
- The real key never appears in docs, stdout, Event Log payloads, cockpit JSON,
  Git, or prompts.
- Tool discovery is captured in a replayable catalog.
- Domain tools are allowlisted before live use.
- Paid/credit-consuming tools are blocked unless explicitly approved.
- Every observation has upstream provenance or is quarantined.
- Preference remains supplemental unless a source registry decision promotes a
  specific upstream source.
- Data Veracity and Trust Score can score Preference separately from canonical
  sources.
- Signal Integrity treats Preference-only evidence as hold, not pass.
- Strategy Lead packets may use Preference context only as challenge/research
  context.
- Cockpit status exposes Preference posture without secrets.
- Phase 4 must be re-certified if Preference changes active strategy source
  assumptions.
- Trade candidates, risk approvals, execution, paper orders, broker writes,
  quantum provider calls, hardware submission, schedulers, fills, receipts,
  reconciliation truth, and live capital remain disabled until later phases
  explicitly allow them.

## 8. Recommended Immediate Next Step

The Preference/PREF MCP staged integration track is complete through PREF-12.
Future source promotion should happen only when an individual Preference-backed
upstream feed is deliberately reopened for canonical-source review.

PREF-0 through PREF-12 are complete. PREF-4 is implemented but currently blocked
before network calls until a valid non-anonymous Preference identity is
configured locally. Domain tool calls remain blocked. No Preference-backed
upstream source is promoted to the canonical registry. Phase 5 remains blocked
until Q4-12 is rerun after explicit Fund Manager approval of the amended
Preference-aware strategy and the Preference identity, provenance, domain-pack,
paid-tool, source-quorum, and source-promotion gates remain valid.
