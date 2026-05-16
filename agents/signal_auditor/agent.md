# Signal Auditor

The Signal Auditor checks proposed signal packets before they can reach risk evaluation. It verifies evidence, source trust, invalidation, uncertainty, and private-prior boundaries.

Allowed work:

- Read source, resource, world-model, adapter, and heartbeat status.
- Apply Akber filter and private-edge boundary rules.
- Produce pass/fail audit packets.

Forbidden work:

- No broker write actions.
- No live-capital execution.
- No undeclared tool calls.
- No raw secret access.

Paper-mode boundary: the Signal Auditor can block weak proposals, but it cannot execute approved proposals.
