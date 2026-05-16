# Qadam Orchestrator

The Orchestrator is the nervous system. It coordinates source polling, writes normalized events, enforces degraded mode, and routes work to agents. It does not invent trading logic.

## Startup Gates

1. Load environment and source registry.
2. Verify the registry count and unresolved source notes.
3. Check storage reachability.
4. Open the local Event Log fallback and write a startup event.
5. Load the founding Fund Manager allowlist.
6. Load the Execution Venue Registry in disabled/read-only mode.
7. Start the health endpoint.
8. Start source heartbeat monitoring.
9. Fail closed if the event log is unavailable during active trading hours.

## Routing Rules

- Source adapters write raw payloads and normalized event candidates.
- Every module writes an Event Log entry before it is treated as real.
- Triage reads only normalized event candidates.
- Research reads triaged candidate packets and evidence trails.
- Quantum jobs read weekly batches only.
- Execution venues start with health, permissions, positions, balances, and limits only.
- Broker adapters read approved signal objects only.
- Order-creating POST calls are never automatically retried.
- PriveX-style perps rails remain `live_blocked` in first-release mode unless a separate paper/sandbox approval exists.

## Degraded Mode

- A missing research source degrades only the affected signal type.
- A missing execution source blocks all order submission.
- A silent event log blocks new signal proposal.
- Every degraded transition is logged and sent to the cockpit.
