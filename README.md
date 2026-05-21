<img width="1438" height="746" alt="Qadam cockpit overview" src="https://github.com/user-attachments/assets/cefef041-c789-4e3a-a619-a9aea6f04e8b" />

# Qadam

Qadam is a local-first macro intelligence cockpit for a boutique trading fund.

It is designed as a small, inspectable fund team running on one machine: a Python COO, a local LLM Research Analyst, a frontier LLM Strategy Lead, and a future quantum/classical Head of Quant. The system watches geopolitical, physical, macro, market, and narrative sources, then turns observations into evidence-gated shadow signals, risk reviews, and paper-mode decision records.

Qadam is not a signal channel, copy-trading bot, high-frequency strategy, or live-capital autopilot. The first release is a private paper-mode cockpit for founding Fund Managers.

<img width="1369" height="771" alt="Qadam dashboard system map" src="https://github.com/user-attachments/assets/8fe5e18e-0e58-45f2-8014-2182267b58fe" />

## What Is Live

- Public entry point: [qadam.trade](https://qadam.trade)
- Protected cockpit: Supabase-authenticated dashboard for founding members.
- Static public branch: landing page, login, sign-up, dashboard shell, guide, whitepaper, and signed status snapshot.
- Local orchestrator branch: source registry, status contracts, agent manifests, intelligence contracts, paper-account mirror, and read-only safety gates.
- First-release access: Ramin, Troy, Akber, Ion, with Anas pending until his email is added.

## Current Build State

Qadam is currently in a foundation plus shadow-intelligence phase.

- Phase 0 foundation is substantially implemented.
- Phase 1 data spine has 35 canonical sources across 5 pipelines, with 19 promoted read-only adapter contracts.
- Phase 1E/1F Agent OS is implemented with named agents, skill bundles, least-privilege tool grants, and broker-write blocks.
- Phase 2 shadow intelligence is active: evidence trails, shadow signals, local Research Analyst compression, Strategy Lead handoffs, Signal Integrity reviews, Risk Agent policy reviews, Execution Policy reviews, disabled staged paper-order reviews, broker reconciliation reviews, and dry-run paper-submit receipt reviews.
- Phase 3 has a hardened quantum/classical oracle contract: local/classical fallback first, provider readiness visible, and hardware submission blocked.
- Dashboard Plan D0-D10J is implemented locally, including Mission Control, source watching, cognition, trade board, paper mirror, TradingView observed alerts, communications, comments, guide, signed bridge status, and sticky navigation UX.

The main blocker before deeper replayable autonomy is durable local Postgres/Timescale replay. Until that is green, source observations remain public-safe and read-only, and no observation can create a broker action.

## Architecture

Qadam separates thinking from authority.

**Layer A: Intelligence**

- World Monitor source registry across conflict, physical, macro, market, and narrative pipelines.
- Local Research Analyst for compression and triage.
- Frontier LLM research path for deeper synthesis.
- Private world-model lens used as hypothesis generation, not evidence.
- Signal Integrity Gate that blocks or holds weak signals before risk review.

**Layer B: Orchestration**

- Risk Agent policy router.
- Execution Policy and kill-switch router.
- Disabled staged paper-order contract.
- Read-only broker reconciliation contract.
- Dry-run paper-submit receipt contract.
- Paper-account mirror with no write authority.

## Safety Boundaries

The current system can observe, summarize, review, block, and explain. It cannot:

- submit paper orders,
- call broker POST routes,
- write to brokers,
- enable live capital,
- turn a TradingView alert directly into a trade candidate,
- let an LLM bypass Signal Integrity, Risk Agent, or Execution Policy checks.

Every public status artifact is sanitized to avoid secrets, local absolute paths, raw prompts, broker IDs, and hidden execution authority.

## Cockpit Surfaces

- `index.html`: public entry page.
- `login/index.html` and `sign-up/index.html`: founding-member Supabase auth.
- `dashboard/index.html`: protected cockpit shell.
- `guide/index.html`: protected user guide.
- `whitepaper/index.html`: public project explanation.
- `status/cockpit-status.json`: public-safe read-only snapshot.
- `status/cockpit-status.signature.json`: detached status signature.

## Operating Mode

Qadam is private, local-first, paper-mode infrastructure. The goal is to build each module as a small, observable contract before allowing the next layer to depend on it.

The current focus is durability and proof discipline: get local Postgres/Timescale replay green, keep live credential validation fresh, keep all intelligence outputs non-executable, and only move toward paper execution after the safety gates and replay trail are boring.
