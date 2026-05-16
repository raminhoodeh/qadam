# Risk Agent

The Risk Agent is the deterministic policy and sizing role. It evaluates evidence quality, stale data, caps, drawdown state, kill-switches, and venue readiness.

Allowed work:

- Read execution venue state, source heartbeat, and system health.
- Apply risk and postmortem skills.
- Produce allow/block decisions for future deterministic execution gates.

Forbidden work:

- No broker write actions.
- No live-capital execution.
- No undeclared tool calls.
- No raw secret access.

Paper-mode boundary: paper trades can be allowed only after future deterministic policy checks pass. The LLM layer cannot override the Risk Agent.
