# Qadam Agent Reach Source Enrichment

Date: 2026-06-15

Scope: local read-only enrichment from `Agent-Reach-main/`.

## What It Adds

Agent Reach gives Qadam a practical reference layer for sources that were
missing, brittle, or difficult through normal APIs:

- Reddit via local logged-in OpenCLI or `rdt-cli` routes;
- X/Twitter via local cookie/browser-session fallback;
- RSS/news and public web article readback;
- Exa-style semantic source discovery;
- GitHub public repository/release context;
- YouTube transcript/video context;
- V2EX, Xueqiu, Bilibili, Xiaohongshu, LinkedIn, and Xiaoyuzhou as optional
  regional, developer, company, consumer, video, or podcast context.

## Qadam Boundary

This is not a new canonical source count. Qadam remains at 35 canonical sources.

Agent Reach is a supplemental evidence capability layer only. It cannot:

- create source quorum;
- approve signals or risk;
- create trade candidates;
- submit paper orders;
- call brokers;
- expose cookies or browser sessions;
- run quantum jobs;
- enable live capital.

## Implementation Surface

- `orchestrator/agent_reach_bridge.py` maps Agent Reach channels to Qadam
  evidence roles.
- `scripts/check_agent_reach_bridge.py` validates channel coverage, authority
  boundaries, and normalized evidence packet compatibility.
- `scripts/check_evidence_packet_normalization.py` and
  `scripts/check_evidence_packet_runtime.py` now include an
  `agent_reach` supplemental packet.
- `orchestrator/cockpit_status.py` includes the Agent Reach packet in
  cognition/evidence runtime replay.
- `scripts/check_source_evidence_acceptance.py` includes the bridge in the
  aggregate non-dashboard source/evidence acceptance gate.

## Remaining User-Action Data Gaps

Agent Reach reduces the implementation gap but does not remove operator setup:

- Reddit still needs a local logged-in route.
- X/Twitter local fallback still needs a safe account/cookie path if used.
- Kalshi credentials are still missing.
- Capitol Trades/STOCK Act credentials are still missing.
- Any LinkedIn/Xiaohongshu/Xueqiu-style cookie channel should use a dedicated
  account and remain read-only.
