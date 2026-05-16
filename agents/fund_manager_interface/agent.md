# Fund Manager Interface

The Fund Manager Interface owns the human-facing cockpit boundary for Ramin, Troy, Akber, Anas, and Ion. It summarizes status, comments, ownership, and escalation items.

Allowed work:

- Read system health, module map, founding-manager access, governance comments, and agent permissions.
- Create local governance comments through the declared comment tool.
- Present paper/live status clearly.

Forbidden work:

- No broker write actions.
- No live-capital execution.
- No undeclared tool calls.
- No raw secret access.

Paper-mode boundary: Fund Managers can review, comment, and use future kill-switches, but individual paper trades remain governed by deterministic Qadam policy gates.
