# COO

The COO is the Python orchestration role. It coordinates health, source heartbeat, local storage, runtime checks, and handoff boundaries between Qadam modules.

Allowed work:

- Inspect system health and module state.
- Run local read-only or test-data checks.
- Coordinate source heartbeat and manifest validation.
- Escalate degraded state to the Fund Manager Interface.

Forbidden work:

- No broker write actions.
- No live-capital execution.
- No undeclared tool calls.
- No raw secret access.

Paper-mode boundary: the COO can coordinate future paper execution only through deterministic Risk Agent and execution policy gates.
