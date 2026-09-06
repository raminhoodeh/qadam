# Qadam User Guide

**Document version:** 2026-08-12

**Accurate as of:** 12 August 2026

**Canonical source:** This Markdown file is the editorial source for the
published Qadam User Guide. The published guide should be generated from, or
checked against, this file rather than maintained as a separate narrative.

> This guide explains Qadam's stable operating model and how to read the
> dashboard. Current counts, provider availability, certifications, source
> freshness, service state, research maturity, and paper-trading readiness are
> deliberately not hard-coded here. Read those from the current dashboard and
> its backend-derived projections.

This guide is for someone who has never heard of Qadam and needs to understand
how to read it safely. The Whitepaper explains why the experiment exists, what
its three hypotheses are and what would count as proof. This guide starts where
the Whitepaper stops: it explains where to find the current answer, how to read
each dashboard state and what different users are allowed to do. Operator-only
commands and older implementation vocabulary are kept near the end so they do
not complicate the normal experience.

Qadam is a local-first macro intelligence and governed paper-trading system. An
unattended Python operator coordinates source ingestion, pattern research,
strategy formation, Akber review, shadow observation, portfolio governance,
guarded paper execution, lifecycle polling, learning and public visibility. It
learns only when the recorded evidence justifies a lesson. A temporal evidence
graph connects those records so a new cycle can retrieve earlier observations,
tests, rejections, decisions and outcomes instead of starting from an
unstructured set of files.

Qadam is not a public financial-advice product, a signal channel, or a
live-capital trading bot. The dashboard is an explanatory, read-only projection
of Qadam's public-safe operating state.

## Three Current Hypotheses

Qadam is currently testing three foundational hypotheses. They are falsifiable
research questions, not proven claims:

1. **Consumer AI execution:** Can advances in consumer-accessible AI execution
   technology enable the discovery of a genuine trading edge?
2. **Quantum pattern recognition:** Can quantum computers recognise a genuine
   trading pattern and form a successful trading strategy from backtested data
   where a matched classical approach cannot?
3. **Akber's investment filter:** Can hedge fund trader Akber's evaluation
   expertise - captured in his six-stage investment filter - be operationalised
   successfully through automated systems?

## 1. The Short Version

Open the dashboard at `https://qadam.trade/dashboard/`.

Use it to answer five questions:

1. What is Qadam observing and which evidence is usable?
2. Which possible relationships and strategies are being tested?
3. What did Akber's filter and Qadam's decision governance conclude?
4. Did a conclusion become a guarded Alpaca Paper order or position?
5. What can Qadam legitimately learn, and has that lesson earned the right to
   change future behaviour?

The dashboard can show an observation, hypothesis, experimental eligibility,
validated edge, decision, paper order, position, outcome, lesson, or proposed
improvement. Those states are not interchangeable. A hypothesis is not a trade.
A discovery experiment is not proof. A candidate is not an order. A blocked,
held, or empty state often means Qadam's controls are working.

### Whitepaper versus User Guide

| Read | Use it for | Do not use it for |
| --- | --- | --- |
| **Whitepaper** | The central experiment, origin story, three hypotheses, artificial team, ten-stage scientific method, proof standard, findings and limits. | Current source freshness, service state, portfolio values, orders or readiness. |
| **User Guide** | Dashboard navigation, status language, page-reading order, authority boundaries, daily routines and operator procedures. | Claims that a strategy, quantum method or filter has proven an edge. |
| **Live dashboard** | The current operating picture: data, research, decisions, paper account, learning and system health. | Creating commands, approvals, policy changes, broker writes or proof credit. |

## 2. Public Reading And Protected Member Access

Qadam separates visibility from authority.

### Public read-only access

The main dashboard is available as a sanitized, public-safe, read-only view. A
public visitor can inspect the fund's paper portfolio, evidence flow, research,
decision rationale, paper-order mirror, learning loop, team, and system health.
The public view cannot expose secrets, raw private payloads, member identities,
local paths, or command access.

### Protected member features

An authenticated, allowlisted member account is required for protected member
functions, including the User Guide and any private governance or forum
features that are enabled. Signing in may identify the member and
allow governance comments; it does not create trade approval, broker, shell,
deployment, or live-capital authority.

The local operator has a separate responsibility for running repository
commands and the unattended service. Public access and membership do not imply
local operator access. See **Appendix A: Operator-Only Procedures** only if that
is your role.

## 3. The Hedge Fund Team Inside The Laptop

Think of Qadam as a compact hedge fund team running inside a laptop.

| Role | Responsibility | Authority boundary |
| --- | --- | --- |
| Fund Manager | Defines constitutional boundaries, reviews major changes, challenges evidence, and decides whether the experiment has earned greater trust. | Human oversight does not turn a dashboard interaction into an order or retroactively change evidence. |
| COO - Python orchestration | Runs the unattended 18-service control plane, checks health, writes artifacts and logs, preserves the temporal evidence graph, and controls the guarded paper route. | It must follow the configured paper-only authority and cannot invent missing evidence. |
| Research Analyst - Gemma on Ramin's machine | Filters high-volume information locally and turns observations into structured research questions. | Its interpretation is not proof, risk approval, or execution approval. |
| Strategy Lead - Google Gemini | Builds and challenges strategy hypotheses, alternative explanations, and economic mechanisms from qualified evidence. | A strategy opinion cannot bypass validation, Akber, risk, Router, or PaperOps. |
| Head of Quant - classical models, Qiskit Aer, IBM Quantum and Q-CTRL | Runs linear, nonlinear, regime-dependent, and quantum-assisted research comparisons where justified. | A simulation, provider connection, or hardware experiment cannot create a market edge claim by itself. |
| Akber's 6-Stage Filter | Tests whether an evidence-classified setup is practical in the current market using the profile appropriate to that strategy. | A pass creates research eligibility for later governance only; it is not approval or execution authority. |
| Router and portfolio governance | Reconcile the decision with risk, duplication, drawdown, freshness, idempotency, and safety state. | Exactly one governed state is returned; only a clean paper-review state can proceed. |
| PaperOps | Handles the guarded Alpaca Paper handoff and reconciles orders and positions. | Paper-only. It has no live-capital route. |
| Event and learning records | Preserve lineage from evidence through decisions, outcomes, lessons, and tested improvements. | An untraceable result cannot receive Qadam proof credit. |
| Dashboard | Explains the public-safe operating picture to humans. | It is a mirror, not a command surface. |

## 4. The Core Authority Rule

Qadam keeps research, governance, and execution separate:

| State | What it means | What it does not mean |
| --- | --- | --- |
| Observation | Something changed in a source, the world, or a market. | It does not mean a trade opportunity has been proven. |
| Qualified evidence | The information is timely, relevant, provenance-linked, and safe to compare with a watched market. | It does not mean a repeatable pattern exists. |
| Graph relationship | Qadam has connected evidence, an entity, an instrument or an earlier result into a queryable research path. | A graph connection is not independent source quorum, a probability of profit, a strategy or trade authority. |
| Pattern | A possible source-price relationship is worth investigating. | It does not mean the score is a probability of profit. |
| Strategy hypothesis | Qadam has described how a supported relationship might be expressed and invalidated. | It does not mean the hypothesis has passed a backtest or present-market review. |
| Discovery experiment eligibility | A complete current setup may be considered for a small, explicitly labelled paper experiment that gathers forward evidence. | It is not a validated edge, proof of profit, or permission to bypass Akber, risk, Router, or PaperOps. |
| Validated edge | The relationship has survived the required historical and forward evidence gates. | It does not mean it is automatically tradeable now. |
| Akber pass, hold, or veto | The present setup is eligible, incomplete, or unsuitable under Akber's practical filter. | A pass is not risk approval, a Router decision, or an order. |
| Governed decision | Router and portfolio controls have produced one current state. | It does not mean every positive decision will result in an order. |
| Paper execution state | A guarded Alpaca Paper instruction, order, fill, position, cancellation, or close has been recorded. | It does not enable live capital. |
| Supported lesson | An attributable outcome supports a cautious conclusion. | It does not mean Qadam may silently change a strategy, risk rule, or code. |
| Applied improvement | A separately tested, reviewed, approved, versioned change has entered the next cycle. | It does not mean the change is permanently correct or exempt from monitoring and rollback. |

Every dashboard page is read-only. It cannot promote research, approve risk,
submit paper orders, write to a broker, alter code or policy, award proof credit,
or enable live capital.

## 5. Stable Operating Model Versus Current State

The stable operating model is:

- Qadam uses evidence-gated research rather than forced trade cadence.
- Its broker execution boundary is Alpaca Paper only.
- Real-calendar evaluation windows are preserved without backfill, simulated
  elapsed time, or forced trades.
- Duplicate protection, risk, evidence freshness, Router state, and PaperOps
  authority must agree before a paper submission can occur.
- The append-only temporal graph is persistent experiment memory. Its local
  query index is rebuildable, and negative, held and inconclusive outcomes stay
  available to novelty and challenger checks.
- A bounded discovery lane may test a complete but under-evidenced setup at
  small size. It remains separate from the strict validated-strategy lane and
  cannot receive edge or proof status from one trade.
- The frozen paper risk ladder permits up to US$500 for a first discovery
  experiment, up to US$2,000 only after independent repeat confirmation, and an
  absolute US$5,000 ceiling only for a validated paper setup.
- A real closed Qadam paper outcome needs complete lineage and a postmortem
  before it can be considered for proof.
- Live-capital and broker-live authority remain outside the dashboard and the
  paper-only operating contract.

At this edition, the graph-assisted discovery implementation is installed and
its five-real-market-day conversion trial is accumulating only actual elapsed
market sessions. The current operator, circuit, repair, PaperOps, Router and
validated-edge states remain mutable and must be read from the live dashboard
and their timestamped backend projections rather than inferred from this guide.

These facts can change. Provider connections, source freshness, service
execution, quantum hardware evidence, certifications, candidates and paper
route state must be read from **System Overview**, **Decision Room**, **Order
Monitor**, and page-specific status cards rather than assumed from this dated
snapshot.

## 6. First Ten-Minute Tour

1. Open **Portfolio** for the paper fund's current financial picture.
2. Open **Trading History** to see the full chronology of broker-mirrored paper
   events.
3. Read **Data Sources** and **Trading Universe** to understand what Qadam can
   currently observe and where that evidence could matter.
4. Read **Pattern Recognition** before **Quantum Edge**. The first page shows
   candidate relationships, their evidence paths and next destinations; the
   second independently tests whether selected nonlinear or quantum-assisted
   analysis added anything useful.
5. Read **Trading Strategies** to see how a relationship becomes a testable
   strategy hypothesis and whether it has earned edge status.
6. Read the **Decision Room** in order: evidence approaching the gate,
   post-filter consequence, then the ultimate committee verdict.
7. Open **Order Monitor** only to see what happened after a governed decision.
   Use Trading History for the complete chronology.
8. Read **Results & Lessons** before **Tests & Improvements**. The first asks
   what Qadam may legitimately learn; the second asks whether that lesson may
   change future behaviour.
9. Open **Qadam Team** for qualitative context about the people-like operating
   roles inside the fund.
10. Open **System Overview** when you need to diagnose infrastructure,
    automations, data, lifecycle impact, incidents, or technical evidence.

Use the ten-stage lifecycle at the top of a page to see where that page fits.
The highlighted relationship explains whether the route owns, supports,
mirrors, or monitors a stage. Runtime status is a separate fact: Qadam can have
different records in several lifecycle stages at the same time.

## 7. The Current 13 Dashboard Routes

These are the canonical dashboard destinations. Older names found in logs or
historic implementation notes are not the normal user interface.

| # | Navigation group | Page | Route | What it answers |
| ---: | --- | --- | --- | --- |
| 1 | Pinned context | Qadam Team | `system/team` | Who performs each hedge-fund role, how the hybrid team works together, and where each role's authority stops. |
| 2 | Fund | Portfolio | `fund/portfolio` | What does the Alpaca Paper fund currently hold, and what is the current financial result? |
| 3 | Fund | Trading History | `fund/timeline` | What paper-order and position events have been reported, in chronological order? |
| 4 | Observe | Data Sources | `observe/sources` | Which sources are connected, fresh, trusted, degraded, missing, or unable to contribute? |
| 5 | Observe | Trading Universe | `observe/universe` | Which markets and liquid paper instruments are watched, and how can evidence map to them? |
| 6 | Find Patterns | Pattern Recognition | `patterns/findings` | Which source-price relationships are live, under testing, validated, disproved, or faded? |
| 7 | Find Patterns | Quantum Edge | `patterns/nonlinear` | Did selected nonlinear or quantum-assisted analysis contribute beyond the strongest fair classical comparison? |
| 8 | Test & Decide | Trading Strategies | `decide/strategies` | How did a supported pattern become a strategy hypothesis, and has that hypothesis earned edge status? |
| 9 | Test & Decide | Decision Room | `decide/decision` | What entered Akber's filter, what emerged from it, and what is Qadam's final governed position now? |
| 10 | Trade | Order Monitor | `trade/orders` | Did a governed paper decision become an order or position, and what did Alpaca Paper report next? |
| 11 | Learn & Improve | Results & Lessons | `learn/outcomes` | What happened, what is attributable to Qadam, and what can Qadam legitimately learn? |
| 12 | Learn & Improve | Tests & Improvements | `learn/improvements` | Has a supported lesson earned the right to change Qadam's behaviour through a tested, versioned improvement? |
| 13 | System | System Overview | `system/overview` | Is Qadam's operating infrastructure healthy, and what root issue needs attention? |

The corresponding deep-link pattern is:

```text
/dashboard/?module=<module>&view=<view>
```

For example, the Decision Room is
`/dashboard/?module=decide&view=decision`.

## 8. The Canonical Ten-Stage Lifecycle

The dashboard uses the same ten stages on all 13 routes:

| Stage | Canonical name | Main question | Principal dashboard destination |
| ---: | --- | --- | --- |
| 1 | Observe the World | What changed in the world or the markets? | Data Sources |
| 2 | Qualify the Evidence | Is the information reliable, timely, point-in-time safe, and relevant to a watched market? | Trading Universe |
| 3 | Discover Patterns | Is there a repeatable source-price relationship worth investigating? | Pattern Recognition and Quantum Edge |
| 4 | Form Strategy Hypotheses | How could the pattern become a disciplined, falsifiable trading approach? | Trading Strategies |
| 5 | Validate the Edge | What evidence class has the strategy earned: validated edge, bounded discovery eligibility, more research, or rejection? | Trading Strategies |
| 6 | Akber's 6-Stage Filter | Is this evidence-classified setup practical to test now under its declared evidence profile? | Decision Room |
| 7 | Govern the Decision | Is the setup allowed into the guarded paper route after portfolio, risk, safety, freshness, and idempotency checks? | Decision Room |
| 8 | Execute and Monitor | What happened to the guarded Alpaca Paper order and position? | Order Monitor, Portfolio, and Trading History |
| 9 | Learn From the Outcome | What did the trade, hold, veto, shadow result, research event, or system event legitimately teach Qadam? | Results & Lessons |
| 10 | Improve and Re-enter | Should a tested, reviewed, versioned change affect Qadam's next observation cycle? | Tests & Improvements, returning to Data Sources |

This is a loop, not a single progress bar. Several independent research and
paper records can occupy different stages simultaneously.

## 9. How To Read The Most Important Pages

### Pattern Recognition and Trading Strategies: relationship to version

Pattern Recognition shows graph-backed research relationships. Read the
**research rank** as prioritisation, not a probability of profit. The evidence
path shows which sources made the relationship stand out, whether they were
fresh and independent enough to count, the observation interval, the current
blocker and where the record goes next. A relationship may be preregistered for
testing, rejected as a duplicate, held for more evidence or mapped to a strategy
family without becoming a trade.

Trading Strategies shows the later version boundary. A **core refinement** is
a proposed declarative change to one configured family; an **emerging version**
is a pattern-sourced playbook outside the core five. Inspect the parent version,
pattern and experiment lineage, instrument and proxy, direction, horizon,
entry, invalidation, cost assumptions, evidence class, admission decision and
rollback state. A strategy version reaches Akber only after the required frozen
evidence and paper-risk admission pass. It still cannot create an order.

### Decision Room: evidence, consequence, decision

The Decision Room is the investment-committee governance page for Stages 6 and
7. It may contain no ideas, one idea, or several ideas; it is not a forced
"trade of the day" view.

Read its main sequence from top to bottom:

1. **Research Pipelines Approaching Gate — Evidence.** This shows active
   research relationships approaching Akber's filter and the evidence maturity
   entering it.
2. **Post-Filter Pipeline & Current Candidates — Consequence.** This shows what
   Akber's filter did to those ideas: current candidates when something passed,
   or a diagnostic explanation of where incomplete or adverse evidence stopped
   progression.
3. **Ultimate Committee Verdict — Decision.** This gives Qadam's reconciled,
   plain-English position after the relevant research and governance gates are
   reconciled.

The **What is Akber's 6-Stage Filter and how does it evaluate an edge?**
explainer is collapsed until selected. It explains the six buckets without
obscuring the current answer. The previous decision-review archive is also
collapsed inside the verdict and should be opened only when historical context
is useful.

The final verdict remains a read-only conclusion. It cannot allocate capital,
approve risk, create an order, or write to Alpaca.

### Quantum Edge: evidence, impact, verdict

Quantum Edge is Qadam's independent proof room, not a claim that every pattern
needs quantum computation. Qadam is a hybrid classical-quantum system: Python
prepares point-in-time evidence, classical models establish the strongest fair
baseline, and selected nonlinear or quantum-assisted methods examine problems
where interactions, sequence, regime, or path dependence could matter.

The current conclusion appears at the top of the page so the reader does not
have to search for it. The three principal rows are always collapsed by default
and should be opened in this order:

1. **Experiment & Evidence — What was tested, compared and verified?**
2. **Strategy & Paper Impact — Did the result improve a strategy or paper
   decision?**
3. **Quantum Edge Verdict — Has a genuine market-level quantum advantage been
   proven?**

The technical-evidence archive is a separate collapsed audit surface. Provider
access, local simulation, reproducibility, hardware execution, untouched market
comparison, strategy contribution, and paper impact are distinct facts. A
successful simulation or access to quantum hardware cannot be presented as
predictive or economic advantage. "Classical preferred" is a valid scientific
outcome because it establishes that the simpler method is sufficient.

All current scores, experiment states, hardware facts, and the formal verdict
must come from the canonical Quantum Edge projection. This guide does not freeze
them in prose.

### System Overview: diagnosis without endless scrolling

System Overview spans all ten stages. Its top-level answer separates three
things that should never be confused:

- the current infrastructure-health verdict;
- an expected operating restriction, such as waiting for legitimate research
  evidence; and
- deduplicated root incidents that require attention.

Six diagnostic sections are collapsed by default:

1. **Infrastructure & Connections**
2. **Automations & Scheduled Work**
3. **Data Freshness & Monitoring**
4. **Effect on Qadam's Flow**
5. **Incidents & Recoveries**
6. **Technical Evidence**

Start with the top verdict and root incidents. Open only the section needed to
answer the next diagnostic question. A deliberate research hold or paper-only
restriction is not automatically an infrastructure failure.

### Results & Lessons versus Tests & Improvements

Read these as two different governance questions:

| Page | Governing question | What belongs here | What leaves the page |
| --- | --- | --- | --- |
| Results & Lessons | **What happened, and what can Qadam legitimately learn?** | Attributable research, hold, veto, shadow, system, and closed Qadam paper events; expectation-versus-outcome review; component attribution; postmortems; supported or rejected lessons. Historical broker records without full Qadam lineage remain separate reference context. | A supported lesson and a measurable next test—not a changed strategy or codebase. |
| Tests & Improvements | **Has that lesson earned the right to change Qadam's behaviour?** | One specific proposed change, point-in-time historical testing, no-order forward observation, governed review, monitoring, versioning, and rollback evidence. | A rejected proposal, more testing, or a separately approved and applied version that can re-enter Observe. |

A result is not automatically a lesson, and a sensible lesson is not
automatically an improvement. Only an attributable outcome can support a Qadam
lesson. Only an explicitly approved, timestamped, monitored, reversible version
can change future behaviour. Neither page can silently edit code, mutate a
strategy, change risk policy, or grant itself authority.

## 10. Status And Trade-State Language

### General status labels

| Label | Meaning |
| --- | --- |
| Online / Current | The exported evidence says the component or record is available within its current freshness policy. |
| Pending / Waiting | A normal prerequisite, time horizon, review, or evidence item is incomplete. |
| Degraded / Needs attention | The capability is partially available or its evidence is stale, incomplete, or lower confidence. |
| Blocked / Stopped | A safety, authority, evidence, risk, or policy rule deliberately prevents progression. |
| Unmonitored | Qadam does not currently have sufficient heartbeat or freshness evidence to assert health. |
| Local-only | The capability exists on the local operator machine and is not exposed as a public control. |
| Read-only | The surface can report state but cannot mutate Qadam. |
| Paper-only | The route or record is limited to simulated Alpaca Paper activity. |
| Dry-run | Qadam can prepare an artifact or message without performing the external action. |
| Eligible | The record may proceed to the next stated review. It is not execution approval. |
| Certified | A named checker passed a specific evidence contract at a recorded time. It does not imply broader or permanent trading authority. |

Always read the label with its timestamp, scope, and explanation. A current
provider or certification state belongs in the dashboard, not this guide.

### Paper lifecycle states

| State | Meaning |
| --- | --- |
| Observed signal | Something was seen; no trade idea or order exists. |
| Candidate | A structured current idea exists; no order exists. |
| Held or vetoed | Missing evidence or explicit adverse evidence stopped progression. |
| Shadow observation | Qadam watches the decision over real elapsed time without placing an order. |
| PaperOps handoff | A clean, idempotent review packet reached the guarded paper execution boundary. |
| Submitted paper order | The allowed service sent an instruction to Alpaca Paper. |
| Accepted / pending paper order | Alpaca Paper acknowledged the order and its next lifecycle event is pending. |
| Filled paper order / open position | The paper broker reports an executed fill and resulting paper position. |
| Cancelled or rejected | The paper broker or governed policy ended the order without an open position. |
| Closed paper position | The paper position ended and can enter attribution and postmortem review. |
| Postmortem complete | The outcome review is recorded; proof eligibility still depends on complete lineage. |

The dashboard must not imply that Qadam traded unless the broker-mirrored and
lineage-backed lifecycle says so.

### Current operating and evidence labels

| Label | Meaning |
| --- | --- |
| `observation_ready` | The unattended service, its artifacts and public projection are healthy enough to keep collecting evidence. It is not a claim that a trade exists. |
| `ready_idle` | The guarded PaperOps route passed its checks and had no accepted Router handoff to submit in that pass. |
| `provisional_soak` | The permanent reliability implementation is complete, but required multi-session real-time observations are still accumulating. |
| `active_discovery_trial_running` | The QEG implementation is certified and is counting only completed graph-assisted cycles on eligible real market days. It does not advance the 30-day paper growth trial or imply a trade. |
| `implementation_certified_evidence_maturing` | The graph, memory, strategy and safety contracts passed, while empirical outcomes are still too limited to claim conversion or edge. |
| Discovery eligible | The current setup is complete enough for the bounded paper evidence lane, subject to Akber, risk, Router and PaperOps. |
| Empirically conversion proven | Eligible provider-backed setups have repeatedly reached the expected guarded outcome over the required real market-day trial. This is stronger than structural readiness and is not yet a profit claim. |

## 11. How Qadam Could Make Money In Paper Trading

The operational hypothesis is that Qadam can find information or structural
relationships before they are fully reflected in market prices, prove that the
relationship repeats after realistic costs, and express it through a governed
liquid paper instrument. The actual flow is:

1. **Observe the World:** collect fresh geopolitical, macroeconomic, market,
   physical-world, and narrative evidence.
2. **Qualify the Evidence:** verify provenance, freshness, point-in-time safety,
   relevance, and a watched market or instrument.
3. **Discover Patterns:** score relationships before seeing their future
   outcomes; use nonlinear or quantum-assisted review only when justified.
4. **Form Strategy Hypotheses:** turn a supported relationship into a defined
   expression, time horizon, invalidation, and risk concept.
5. **Validate the Edge:** use historical, walk-forward, untouched holdout,
   cost, false-discovery, and real forward-shadow evidence, then assign the
   setup's evidence class.
6. **Apply Akber's 6-Stage Filter:** decide whether the evidence-classified
   setup is practical in the current market under its strategy profile.
7. **Govern the Decision:** reconcile Akber with portfolio risk, drawdown,
   duplicate exposure, safety, freshness, idempotency, and the Router state.
8. **Execute and Monitor:** only a clean PaperOps handoff may submit through
   Alpaca Paper; reconcile order and position events until closure.
9. **Learn From the Outcome:** attribute what helped, failed, or remained
   unmeasurable and record only a supported lesson.
10. **Improve and Re-enter:** test the proposed change separately; only an
    approved, versioned improvement may affect the next observation cycle.

This is the intended economic mechanism, not a promise of profit. Qadam still
has to prove any edge through attributable, out-of-sample, cost-aware paper
evidence.

### The two paper evidence lanes

The **validated-strategy lane** remains strict: the underlying relationship has
already survived Qadam's full edge standard. The **discovery lane** exists so a
complete, current and plausibly positive hypothesis can collect small real
paper evidence before full edge validation. Discovery eligibility requires a
real trigger, direction, current price and volatility, independent market
confirmation, positive expectancy after estimated costs, an invalidation,
decision-time shadow evidence, acceptable spread and liquidity, and complete
lineage.

The current risk ladder is US$500 for a first discovery experiment, up to
US$2,000 after at least five independent positive net outcomes across more than
one regime, and up to the US$5,000 absolute ceiling only for a validated paper
setup with substantially more independent evidence. No tier advances from one
score or one winning trade.

## 12. How Qadam Finds And Tests Edge

An edge is not one headline, one chart, one model opinion, one private prior, a
Telegram message, a green status label, or a high research score. It is a
repeatable, source-backed relationship that survives attempts to disprove it and
retains useful economic value after costs and risk.

Qadam's watched markets and instruments are dynamic. Read **Trading Universe**
for the current list rather than relying on a static list in this guide.

The minimum evidence ladder is:

1. Record a point-in-time observation and the information available then.
2. Map that observation to a watched price or probability without looking into
   the future.
3. Measure what happened only after the relevant horizon elapsed.
4. Test whether the relationship repeats on history after realistic costs and
   false-discovery controls.
5. Challenge it with walk-forward and untouched holdout evidence.
6. Use Quantum Edge only where nonlinear structure could plausibly add useful
   information beyond the strongest matched classical method.
7. Observe the frozen idea forward over real time without an order.
8. Promote, hold, reject, or mark the relationship as faded based on evidence.

A Pattern Recognition research score ranks evidence for investigation. It is
not automatically a calibrated probability, expected return, or chance of
profit. The row's evidence stage and advancement condition explain what the
score can currently support.

## 13. Akber's 6-Stage Decision-Making Filter

Akber does not originate an idea, prove a historical edge, approve risk, or
execute an order. It asks whether an evidence-classified strategy setup is
practical in current market conditions. A validated strategy and a bounded
discovery setup can use different evidence profiles, but neither can omit its
required current trigger, confirmation, expectancy, invalidation, liquidity or
lineage.

The six auditable stages are:

1. **Context — low volatility:** does the tested source-price relationship fit
   the affected market, instrument, historical memory, and current regime, and
   is the existing price distribution vulnerable to change?
2. **Catalyst — why now:** what fresh, specific, trusted real-world event could
   cause repricing now? Historical edge alone does not provide timing.
3. **Confirmation — pricing, technicals, and flow:** does measurable pricing,
   price structure, volume, flow, cross-market evidence, and any required
   nonlinear challenge support rather than contradict the thesis?
4. **Risk — judgment and invalidation:** does expected return remain positive
   after costs, is reward-to-risk justified, and is there a clear condition
   that proves the idea wrong? The separate risk and portfolio controls still
   own later risk governance.
5. **Execution suitability — clean paper expression:** is there a valid, liquid
   Alpaca Paper proxy with acceptable spread, friction, timing, and
   duplicate-exposure posture? Suitability review is not an order instruction.
6. **Postmortem learning — judgment after the outcome:** did the earlier pass,
   hold, or veto improve the decision? Any filter change remains a proposal
   until separately tested, reviewed, and versioned.

Akber returns **pass**, **hold**, or **veto**. A pass means the required
practical evidence is complete enough for later shadow and Router review. A
hold means required evidence is missing. A veto means explicit adverse evidence
or a critical safety rule stopped the setup. A high aggregate score cannot hide
a failed required stage.

An Akber pass creates research eligibility only. It does not create a trade
candidate by itself, risk approval, execution approval, a PaperOps handoff, a
paper order, a broker write, proof credit, or live-capital authority.

## 14. How To Review A Research Or Trade Idea

Ask:

1. What changed, and when was it known?
2. Which independent sources support or contradict it?
3. Which market and liquid paper instrument are affected?
4. What repeated historical relationship is being claimed?
5. Was the score produced before the future outcome was known?
6. What costs, leakage, false-discovery, walk-forward, and holdout checks were
   applied?
7. What is the current catalyst and expected time horizon?
8. What would invalidate the idea?
9. What did Akber pass, hold, or veto, and why?
10. Does a PaperOps handoff exist, or is the record still research-only?
11. What evidence would move the record to its next lifecycle stage?

If the answers are missing, the idea should remain under research, held, or
blocked.

## 15. Paper Evaluation Rules

Any declared paper evaluation window is a real-calendar discipline boundary,
not a license to force activity.

- Do not backfill calendar days.
- Do not simulate elapsed time.
- Do not force trades to satisfy cadence.
- Do not treat mirror-only historical broker records as proof of Qadam's
  decision quality.
- Do not manually override individual trades merely to improve a sample.
- Record the no-trade rationale when no setup qualifies.
- Keep drawdown, concentration, duplicate exposure, spread, liquidity,
  freshness, and idempotency controls active.
- Require a postmortem and complete lineage before a closed Qadam paper outcome
  can be considered for the proof ledger.
- Keep live capital outside the paper-only route.

Waiting is a valid outcome when the evidence is immature.

## 16. Daily Reading Routine

1. Start with **Portfolio** and **Trading History** for the current paper-fund
   and broker-mirror context.
2. Read **Data Sources** for freshness or outages and **Trading Universe** for
   the affected markets.
3. Review **Pattern Recognition**, then open **Quantum Edge** only where a
   relationship was referred for specialist comparison.
4. Review **Trading Strategies** for hypothesis and validation state.
5. Read the **Decision Room** in its evidence → consequence → decision order.
6. Use **Order Monitor** to check active or recent order and position state.
7. Use **Results & Lessons** for attribution, then **Tests & Improvements** for
   change governance.
8. Open **System Overview** if a page is stale, unavailable, contradictory, or
   unexpectedly empty.
9. If protected member features are available, add a precise governance
   comment only when it improves the record. A comment is not an approval.
10. Record or accept a no-trade state when no setup qualifies. Do not force
    activity.

## 17. Telegram: Read-Only Communication And Status

Telegram is a communication surface, not an operating console.

### Outbound explanation

The outbound rail can send public-safe, plain-English notifications or learning
briefs when the relevant automation is enabled, due, non-dry-run, idempotent,
specific, human-readable, and correctly targeted. It explains what Qadam
noticed, what changed, and what remains uncertain. It cannot create commands,
trade candidates, risk approvals, execution approvals, paper orders, broker
writes, Q-CTRL jobs, deployments, proof credit, strategy mutations, or
live-capital authority.

### Read-only group queries

The configured Telegram group can ask Qadam for fresh, deterministic readouts
with `/status`, `/portfolio`, `/trading`, `/patterns`, `/health`, `/repairs`,
and `/help`. The bot answers from canonical runtime artifacts rather than an LLM
or remembered chat context. `/repairs` exposes what the independent reliability
critic found and whether a repair request is open; it does not trigger a repair.

The query service polls the same locked Telegram update rail every 30 seconds,
registers a group-scoped command menu, suppresses duplicate replies, and retries
a failed response without discarding the member's update. Only the configured
group receives replies. Runtime records retain hashes rather than raw member or
group identifiers.

### Inbound research intake

The inbound rail can poll messages from configured members and log useful
articles, world-event context, strategy ideas, or trading philosophy as
read-only research intake. An inbound message may become a provenance-linked
datapoint or a question for the Strategy Lead. It cannot place, approve, reject,
modify, close, or resize a trade; change a strategy; bypass Akber, Router, risk,
or PaperOps; or grant itself evidentiary status.

Telegram should never display or retain bot tokens, secret chat identifiers,
handles, raw private payloads, credentials, or local paths in public artifacts.
If Telegram and the dashboard appear to conflict, trust the fresh canonical
runtime projection and investigate the delivery or intake record.

## 18. What Visitors, Members, And Operators Can Do

### Public visitors can

- read the sanitized dashboard and public documentation;
- inspect public-safe evidence, decisions, paper states, lessons, and system
  status;
- use the explanations and tooltips to understand why Qadam waited or acted.

### Authenticated, allowlisted members can additionally

- use protected member documentation and enabled governance features;
- review and challenge evidence, decisions, outcomes, and proposed changes;
- write governance comments linked to a dashboard object;
- submit useful research context through the configured inbound Telegram rail.

### Only the local operator can

- run repository commands and local checkers;
- start or inspect configured local services;
- execute one governed PaperOps automation pass under the existing authority
  contract;
- manage local secrets outside Git and public artifacts.

### No dashboard, guide, comment, or Telegram user can

- place or approve a trade through the interface;
- approve risk or bypass Akber, Router, PaperOps, the Event Log, or idempotency;
- turn a private prior, comment, or message into evidence;
- mutate a strategy, policy, codebase, or active configuration;
- run a shell command through the Secure Live Bridge;
- write to broker-live endpoints or enable live capital;
- treat a candidate, Akber pass, Router review, or PaperOps handoff as an order;
- award paper proof without a real closed Qadam paper outcome and complete
  lineage.

## 19. Data Source Rules

Qadam can observe conflict, physical-world and OSINT, macroeconomic, market,
corporate, prediction-market, and narrative context through configured
read-only providers. The exact provider inventory and current contribution
state belong on **Data Sources**.

Rules:

- one source is rarely enough;
- freshness and provenance matter as much as the content;
- the point-in-time record must contain only information available then;
- private worldview priors are context, not evidence;
- supplemental providers remain context until registry and trust rules say
  otherwise;
- raw payloads, secrets, member identifiers, and local paths must not appear in
  the public dashboard;
- broker receipts and portfolio state are execution evidence, not independent
  market corroboration;
- a connected provider does not prove complete historical coverage or current
  monitoring;
- source information cannot create an order or satisfy authority by itself.

## 20. Troubleshooting

### If the public dashboard will not load

1. Reload `/dashboard/` without assuming login is required.
2. Confirm the static public-safe snapshot and page assets are reachable.
3. Ask the local operator to inspect System Overview generation and deployment
   evidence.

### If a protected member feature will not load

1. Confirm you are signed in with an allowlisted account.
2. Confirm the destination is a protected member feature rather than the public
   dashboard.
3. Sign in again through `/login/` and return to the protected destination.
4. Do not paste credentials or tokens into a comment or support message.

### If Qadam is healthy but no order appears

1. Confirm **System Overview** reports the unattended service as current and
   **Order Monitor** is not stale.
2. Read the latest conversion funnel in **Decision Room**: usable source,
   current trigger, directional hypothesis, Akber, shadow, risk, Router and
   PaperOps are distinct stages.
3. Treat `ready_idle` only as a no-handoff result. Separately confirm canonical
   execution is not frozen, broker reconciliation is current and position exits
   are protected. A process heartbeat alone does not establish trading health.
4. During a closed market, expect Qadam to preserve a setup for real-session
   revalidation rather than fabricate a spread or submit outside its window.
5. Do not promote an under-evidenced idea manually; the discovery lane exists to
   make complete low-risk hypotheses testable without claiming they are proven.

### Bounded unknown-expectancy experiments

Discovery can evaluate a plausible hypothesis whose mean return is not yet
estimated. It still needs a current trigger, direction, executable liquidity,
numeric invalidation, a decision-time shadow and all portfolio/broker checks.
This state is labelled `unestimated_discovery_experiment`, never a positive edge.
It is capped at US$250 notional and US$5 modelled loss at invalidation, inside all
existing parent limits. Gaps and slippage can exceed a synthetic stop's estimate.
Known zero or negative economics do not qualify for this exception.

The System view separately reports exact entry attribution, unresolved lineage,
gross reconstructed results and cost-measured results. Missing P&L is not zero.
Forward review uses registered rule versions, nonoverlapping event windows and
matched SPY/cash comparisons. Its review checkpoints are frozen at 20, 40, 80
independent events and subsequent doublings, with multiple-comparison controls.
This does not promise weekly profits or permission to use live capital.

Self-healing retries recognised transient faults with bounded attempts and
verifies the blocked consumer afterwards. It cannot safely repair arbitrary code,
restore missing provider entitlements or report a powered-off laptop's failure
from that same laptop. Unresolved faults must remain visibly degraded.

### If source evidence looks stale

1. Open **Data Sources** and expand the affected source category.
2. Read its freshness, trust, provider, and contribution state.
3. Open **System Overview → Data Freshness & Monitoring** for the underlying
   artifact or dependency diagnosis.
4. Treat affected research as lower confidence until current evidence exists.

### If a decision or paper state looks wrong

1. Check the **Decision Room** for the current evidence, Akber consequence, and
   ultimate verdict.
2. Check **Order Monitor** for the active order or position lifecycle.
3. Check **Trading History** for the full broker-mirrored chronology.
4. Open **System Overview → Effect on Qadam's Flow** and **Incidents &
   Recoveries** if the pages disagree.
5. Do not assume a candidate, decision, or handoff is an order.

### If a lesson or improvement looks overstated

1. Use **Results & Lessons** to confirm origin, lineage, attribution, and proof
   eligibility.
2. Confirm mirror-only broker history is kept as reference rather than Qadam
   proof.
3. Use **Tests & Improvements** to confirm historical testing, forward
   observation, review, versioning, monitoring, and rollback.
4. An unapproved proposal must remain inert.

## 21. Red Flags

Escalate or record a precise governance comment if:

- a page presents a stale or hard-coded count as current runtime truth;
- a source claims health without recent freshness or monitoring evidence;
- a research score is described as a guaranteed probability or profit;
- a pattern is presented as a validated edge without the required evidence;
- an Akber pass is presented as approval or an order;
- a candidate, Router review, or PaperOps handoff is presented as a broker fill;
- the paper balance changes without a corresponding broker-mirrored lifecycle
  record;
- reference-only broker history is used to claim Qadam performance;
- a supported lesson changes Qadam without testing, approval, versioning,
  monitoring, and rollback;
- Telegram creates or accepts an operating command rather than a read-only status query;
- a dashboard or bridge claims shell, deployment, broker-write, proof-credit, or
  live-capital authority;
- any secret, token, private chat identifier, credential, raw private payload,
  member email, or local path appears in a public artifact;
- the dashboard and its canonical backend-derived projection disagree.

## 22. Glossary

| Term | Meaning |
| --- | --- |
| Public-safe projection | Sanitized dashboard data that can explain Qadam without exposing secrets, raw private payloads, or command authority. |
| Dashboard | The public read-only operating view across the 13 canonical routes. |
| Lifecycle | The ten-stage loop from Observe the World through Improve and Re-enter. |
| Qualified evidence | Fresh, provenance-linked, point-in-time-safe information mapped to a watched market. |
| Pattern | A possible repeatable relationship under investigation; not automatically a probability or edge. |
| Research score | A ranking signal for prioritizing pattern investigation; its interpretation depends on the evidence stage. |
| Strategy hypothesis | A falsifiable proposed expression of a supported pattern, including instrument, horizon, and invalidation. |
| Discovery experiment | A small, explicitly labelled Alpaca Paper observation used to gather forward evidence for a complete setup that has not yet proved a validated edge. |
| Validated edge | A relationship that passed the required historical, untouched, cost, robustness, and forward evidence gates. |
| Quantum Edge | The independent evidence → impact → verdict proof room for selected nonlinear or quantum-assisted comparisons. |
| Akber pass | Eligibility for later shadow and Router review after all required practical evidence is present; not approval or an order. |
| Router state | The one governed disposition produced after decision, portfolio, risk, freshness, idempotency, and safety reconciliation. |
| PaperOps handoff | An idempotent packet allowed to reach the guarded Alpaca Paper review boundary. |
| Alpaca Paper | The simulated broker environment used for guarded paper orders and positions. |
| Order Monitor | The focused operational view of active and recent paper-order and position lifecycle state. |
| Trading History | The complete chronological broker-mirrored paper record. |
| Attribution | The evidence-backed account of which source, model, strategy, Akber stage, risk decision, Router state, or execution component contributed to an outcome. |
| Reference-only history | Historical broker records without complete Qadam decision lineage; useful context, not Qadam proof. |
| Paper proof ledger | The governed record of eligible real closed Qadam paper outcomes with complete lineage and postmortems. |
| Supported lesson | A cautious conclusion justified by attributable evidence; input to testing, not permission to change Qadam. |
| Improvement proposal | One specific, measurable possible change that remains inert until testing and approval finish. |
| Applied version | A separately approved, timestamped, monitored, reversible change allowed to affect the next cycle. |
| No-trade rationale | The recorded reason no setup qualified; a legitimate operating outcome. |
| `ready_idle` | The guarded paper route is healthy, but no accepted Router handoff existed for that pass. |
| Open-market conversion | The same-session refresh from current provider evidence through Akber, shadow, risk, Router and guarded PaperOps. |
| Live capital | Real-money trading authority, which is not part of the dashboard or paper-only route. |
| Secure Live Bridge | A read-only path for serving sanitized status. It is not shell or broker access. |

## 23. A Successful Reading Of Qadam

A new reader should be able to answer:

- What is Qadam observing and which evidence is currently usable?
- Which possible pattern is only being investigated, and which edge has actually
  been validated?
- How did a supported pattern become a strategy hypothesis?
- What did Akber pass, hold, or veto—and why?
- What did Router and portfolio governance decide?
- Does a real Alpaca Paper order or position exist, or is the record still
  research, shadow, or handoff state?
- What happened after the decision?
- What can Qadam legitimately learn from that outcome?
- Has the lesson earned a tested, approved, versioned change?
- Is the operating infrastructure healthy enough to trust the displayed state?

Qadam should feel understandable before it feels powerful.

---

## Appendix A: Operator-Only Procedures

> **Operator boundary:** This appendix is not part of the normal dashboard
> walkthrough. Run these commands only from the local Qadam repository, with
> the appropriate operator responsibility and existing configuration. They do
> not authorize backfill, forced trades, live capital, broker-live endpoints,
> Telegram operating commands, or manual promotion around failed gates.

### Local setup and diagnostic prerequisites

Keep secrets in ignored local secret stores or environment variables. Never
commit them, paste them into chat, or expose them in dashboard artifacts.

Bootstrap the configured runtime when required:

```bash
scripts/bootstrap_runtime.sh
```

Start the durable observation spine when durable replay is required:

```bash
scripts/start_postgres_timescale_ingestion.sh
```

Check the current dashboard projection:

```bash
.venv/bin/python scripts/check_cockpit_status.py
```

Check the unattended operator and its real-time reliability state:

```bash
scripts/status_qadam_operator_launch_agent.sh
.venv/bin/python scripts/check_qadam_operator_service.py
.venv/bin/python scripts/check_qadam_permanent_operator_reliability.py
```

The installed service uses macOS `launchd` and `caffeinate` to dispatch the
declared jobs while the laptop is awake. It applies cadence separation,
single-instance leases, resource locks, bounded retries, circuit breakers,
repair requests and disk-pressure limits. It cannot edit code, install software,
change secrets or expand authority autonomously.

### Canonical PaperOps pass

The canonical command for one autonomous PaperOps pass is:

```bash
.venv/bin/python scripts/run_paperops_autonomous_pass.py
```

Run it once and allow the current market, evidence, calendar, Router, risk,
idempotency, and PaperOps state to determine the result. Do not backfill, fake
elapsed time, force a setup, bypass a blocker, or substitute an older phase
harness. The canonical pass summary is written to:

```text
data/runtime/paperops_autonomous_pass_summary.json
```

The retired `run_phase7_demo_proof_harness.py` routine is not the canonical
PaperOps entry point and should not be taught as the daily operating command.

### Focused operator checks

Use focused checks only when their scope is relevant:

```bash
.venv/bin/python scripts/check_postgres_timescale_replay.py --require-full-source-coverage
```

### Canonical daily learning pass

When the configured daily learning window is due, the canonical live pass is:

```bash
.venv/bin/python scripts/run_daily_learning_automation.py --live
```

Qadam normally runs this command automatically twice each day, after 08:00 and
20:00 Asia/Dubai. The morning and evening briefs explain what the research loop
tested, the strongest current relationship, what failed validation, what the
quantum/classical comparison contributed, and what Qadam will test next. When a
verified IBM hardware result exists, every brief identifies it as real hardware,
states the relationship it surfaced, reports how that exact candidate performed
against the matched classical baseline, and explains whether Qadam supported,
rejected, or is still testing it. Simulator and classical fallback results are
labelled separately and can never be described as hardware evidence. Each
slot sends at most once and remains outbound-only, public-safe, and unable to
create commands, approvals, candidates, orders, or proof credit. After each
slot, the terminal delivery state is mirrored into the signed cockpit status
used by the dashboard Communications surface.

The local scheduler requests the two slots at 08:02 and 20:02. A lightweight
five-minute fallback checks Asia/Dubai time, the sent-delivery ledger, and a
15-minute failure cooldown so a mistimed macOS trigger cannot lose a brief and
cannot create a duplicate. The expensive learning pass runs only for a due,
unsent slot.

Run it once against the actual calendar. Do not backfill, simulate elapsed time,
or force delivery outside the configured daily window. Its Telegram output is a
public-safe, plain-English learning explanation only; it cannot create commands,
trade candidates, approvals, orders, broker writes, Q-CTRL jobs, deployments,
proof credit, strategy mutations, or live-capital authority.

A green dashboard is not authority. Authority comes from the current backend
gates, runtime artifacts, and the guarded paper-only service boundary.

### Explicit IBM Quantum device discovery

Quantum provider credentials are local secrets. An explicitly authorized device
discovery probe may inspect configured provider availability:

```bash
.venv/bin/python scripts/check_qctrl_fire_opal_ibm_quantum.py --probe-devices
```

Device discovery is not a hardware experiment. It does not submit a quantum
job, prove a market edge, create a strategy or candidate, approve risk, create a
PaperOps handoff, call a broker, or enable live capital. Current access and
hardware-execution facts must be read from the resulting evidence rather than
assumed from this guide.

## Appendix B: Legacy And Debug Vocabulary

Advanced / Debug Mode and the older implementation terms below are retained
only for operators reading historic logs, migration evidence, or compatibility
checks. Beginners should navigate with the 13 canonical routes in Section 7.

| Older term | Current place to look |
| --- | --- |
| Mission Control / QSASE Overview | The complete 13-route dashboard, with Portfolio as the default and System Overview as the cross-cutting diagnostic page. |
| Overview | Portfolio plus the current navigation, not a separate all-purpose operating view. |
| Trades / Trade Layer | Decision Room for the decision, Order Monitor for active lifecycle state, and Trading History for chronology. |
| Evidence / Watching | Data Sources and Trading Universe. |
| Pattern Discovery | Pattern Recognition. |
| Quantum Review | Quantum Edge. |
| Reasoning / Cognition / Worldview | Pattern Recognition, Trading Strategies, and Decision Room, with worldview retained only as contextual prior material. |
| Money / Paper Account History | Portfolio and Trading History. |
| Operations / System map / Process Console | System Overview and its six collapsed diagnostic disclosures. |
| Forbidden / Safety Status | Page-level authority boundaries, Decision Room governance, and System Overview operating restrictions. |
| Communications | Telegram's outbound explanations, read-only status queries, and read-only research intake. |
| Advanced / Debug Mode | Operator-only technical evidence, compatibility, and migration inspection—not a beginner-facing navigation system. |

Legacy labels can help interpret an old record. They should not be used to
describe the current user journey or to imply hidden trading controls.
