# Qadam Preference MCP - PREF-0 Capability Review Audit

Date: 2026-05-24
Stage: PREF-0 - Intake, Policy, And Current-State Baseline
Status: complete

## Objective

Decide what Preference/PREF MCP is allowed to be inside Qadam before creating a
key, installing an MCP server, calling live tools, or letting the capability
change Phase 4 or Phase 5 behavior.

## Safety Decision

PREF-0 is safe because it is document-only.

This stage did not:

- register a Preference agent
- create or store a `pref_agent_*` key
- install `https://pref.trade/mcp`
- configure Codex MCP
- call `preference_account_status`
- call `search_tools`
- call any live domain tool
- consume credits or paid tools
- alter source ingestion, Signal Integrity, Risk Agent, Execution Policy, paper
  order, broker, quantum-provider, scheduler, or live-capital behavior

## Classification

Preference/PREF MCP is classified as:

- capability key: `preference_mcp`
- provider label: `preference_labs_mcp`
- role: `supplemental_multi_source_data_plane`
- canonical source status: not source 36
- default mode: disabled live; status/catalog/sample first
- authority: read-only observation and research enrichment only
- promotion rule: one upstream source at a time, by explicit source-registry
  decision
- strategy impact: may amend Phase 4 before Fund Manager approval, but cannot
  certify Phase 4 or start Phase 5 by itself

## Official Setup Facts Carried Forward

The supplied Preference onboarding and public docs identify:

- MCP endpoint: `https://pref.trade/mcp`
- transport: Streamable HTTP
- authentication: `Authorization: Bearer <pref_agent_* or account key>`
- agent registration endpoint: `POST https://pref.trade/v1/agents/register`
- agent key format: `pref_agent_*`
- MCP verification tool: `preference_account_status`
- discovery tool: `search_tools`
- normal client setup: use the MCP endpoint, not `/mcp-gateway`
- agent onboarding path: API registration, not browser sign-up
- key rule: treat all Preference keys as secrets

Qadam interpretation:

- "No APIs" means no per-source provider integrations for the agent, but Qadam
  still integrates a remote MCP and still protects a provider key.
- "Read-only" is not trusted by default; Qadam must enforce local no-authority
  flags.
- Tool breadth does not equal source trust. Preference observations must carry
  upstream provenance before they can support source quorum.

## Forbidden Actions

Preference/PREF MCP cannot:

- execute trades
- approve risk
- create trade candidates
- stage paper orders
- submit paper orders
- write to brokers
- enable live capital
- call quantum providers
- submit hardware jobs
- enable schedulers
- provide fill truth
- provide receipt truth
- provide broker echo truth
- provide reconciliation truth
- become source 36 automatically
- satisfy source quorum without distinct upstream provenance
- consume paid tools without explicit approval

## Where Preference Can Help Qadam

Preference can strengthen the first trading universe only as read-only context:

- Prediction markets: Polymarket/Kalshi discovery, orderbook depth, liquidity,
  and cross-venue context.
- Crude oil: vessel movements, chokepoints, weather, physical disruption, and
  oil-linked market context.
- Defence: SEC filings, procurement/policy narratives, conflict context, and
  defence-linked prediction markets.
- Silver: macro, rates, weather/physical supply context, and market
  confirmation.
- Semiconductors: filings, policy/export controls, tech narratives, and
  wallet/KOL context as sentiment only.

Sports lines are permitted as research context only. They are outside Qadam's
current first trading universe unless a later strategy document explicitly adds
them.

## Documents Updated Or Confirmed

- `docs/qadam-preference-mcp-integration-plan.md`
- `docs/api-source-inventory.md`
- `docs/api-specs.md`
- `docs/qadam-master-implementation-plan.md`

The current plan now treats Preference as a pre-Phase-5 enrichment track and
keeps the next implementation step at PREF-1 identity/status gating.

## Acceptance Evidence

PREF-0 acceptance:

- Preference is classified as supplemental, read-only, and non-canonical.
- The source inventory says Preference is not source 36.
- The credential ledger identifies `PREFERENCE_API_KEY` and runtime controls
  without containing a real key.
- The master plan records Preference as a gated enrichment track.
- No live MCP calls were made.
- No runtime authority changed.
- Phase 5 remains blocked until Q4-12 certification passes.

## Required Next Step

Proceed to PREF-1 only when it is acceptable to add local configuration and a
status-only identity check. PREF-1 should still fail closed unless a valid
non-anonymous Preference identity is available through local ignored runtime
storage or the shell environment.
