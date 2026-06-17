# Qadam Daily Edge Learning - Stage 8 Acceptance Tests

Date: 2026-06-17
Status: implemented

## Purpose

Stage 8 is the aggregate acceptance gate for Qadam's daily edge-learning loop.
It does not create a new trading capability. It proves that the already-built
Stages 1-7 still work together as one system before the dashboard or deployment
surface treats the learning loop as operational.

The Stage 8 checker is:

```bash
.venv/bin/python scripts/check_daily_edge_learning_acceptance.py
```

It writes:

```text
data/runtime/daily_edge_learning_acceptance.json
```

## What Stage 8 Proves

Stage 8 runs and cross-checks the following contracts:

- Daily Edge Findings artifact exists and is ready for review.
- Quantum-Mandatory Review Gate passes and rejects bypass probes.
- Pattern Recognition Engine scans all source context for every tracked sleeve
  and emits quantum-oracle-ready feature vectors.
- Edge Memory Ledger records recurring observations without trade authority.
- Strategy Update Record proposes changes but applies none.
- Hypothesis Lifecycle tracks held/retained hypotheses without promoting
  candidates by itself.
- Strategy Weight Updates proposes weighting changes but does not mutate active
  strategy weights.
- Quantum Meta-Review reviews the recursive loop without calling providers or
  applying changes.
- Self-Improvement Proposals are recommendation-only and cannot edit code,
  prompts, strategy, orders, or broker state.
- Promotion Gates hold every proposed improvement until human approval and
  outcome evidence exist.
- Telegram Human Brief is plain-language, specific, and non-commanding.
- Daily Learning Automation is due-or-forced in the check path, but it does not
  attempt live sends during acceptance.
- Dashboard Stage 7 visibility remains present and read-only.

## Non-Negotiable Boundaries

The acceptance artifact must preserve these false authority flags:

- dashboard write authority;
- Telegram command path;
- paper order submission;
- broker write;
- quantum provider call;
- live capital.

Passing Stage 8 means the learning system is testable and internally coherent.
It does not mean Qadam can bypass risk, create trades from pattern recognition
alone, mutate strategy automatically, send Telegram commands, call quantum
hardware from the dashboard, or enable live capital.

## Deployment Discipline

`scripts/preflight_dashboard_deployment.sh` now runs Stage 8 before production
deployment. Any future dashboard deploy must pass the aggregate daily
edge-learning acceptance gate as well as the existing source/evidence,
PaperOps, Telegram, and dashboard checks.

Expected output:

```text
daily_edge_learning_acceptance_check=ok
daily_edge_learning_acceptance_status=ok
daily_edge_learning_acceptance_stage=Stage 8 - Acceptance Tests
```
