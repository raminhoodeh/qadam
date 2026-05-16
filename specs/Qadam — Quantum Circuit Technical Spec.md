# Qadam — Quantum Circuit Technical Spec

<aside>
⚡

This document specifies the Qiskit circuit design for both weekly Quantum batch jobs described in [Qadam Specifications v3](../Qadam%20Specifications%20v3%203566fe2ecf37800abef8c5c717cc6656.md) §4.3. It is a build-time companion — the PRD specifies *what* the Quantum Engine does; this spec explains *how* the circuits work so Phase 3 of the Build Roadmap (§12.5) can be executed. Read this alongside the PRD §4.3 and §10.5.

</aside>

<aside>
⚠️

**NISQ Reality Check:** Current quantum hardware (2025–2026) is Noisy Intermediate-Scale Quantum (NISQ). Circuits are short, noisy, and probabilistic. Qadam's quantum jobs are designed to be *useful on NISQ hardware* — they extract signal from statistical patterns across many shots, not from exact single-run answers. The classical fallback (scipy + scikit-learn) produces equivalent output when quantum hardware is unavailable. The system is designed to be useful without Quantum, not dependent on it.

</aside>

---

# 1. Hardware Assumptions & Constraints

## 1.1 Target Backends

| **Backend** | **Provider** | **Access** | **Qubits** | **Connectivity** | **Role in Qadam** |
| --- | --- | --- | --- | --- | --- |
| IBM Eagle / Heron | IBM Quantum via Qiskit | IBM Quantum Network or Open Plan | 127–133 qubits | Heavy-hex topology | Primary backend; both Job 1 and Job 2 |
| IonQ Aria | IonQ via AWS Braket | AWS Braket on-demand | 25 algorithmic qubits | All-to-all (trapped ion) | Secondary backend; better fidelity on small circuits |
| Qiskit Aer | Local simulator | Runs on M5 CPU | Unlimited (noiseless) | N/A | Pre-submission validation only; never used for production outputs |

**Backend selection rule:** Submit to IBM Eagle/Heron by default. If IBM queue time exceeds 48 hours, switch to IonQ Aria for that week's batch. If both are unavailable, run classical fallback and log `queue-timeout`.

## 1.2 Q-CTRL Error Suppression

All real-hardware submissions pass through **Q-CTRL Fire Opal** before execution:

- Q-CTRL's error suppression layer automatically reshapes pulses to reduce gate error rates on NISQ hardware
- Target gate fidelity after suppression: **≥ 99.5%** on single-qubit gates, **≥ 98.5%** on two-qubit gates
- Applied automatically to both Job 1 and Job 2
- If Q-CTRL is unavailable: submit natively via Qiskit transpiler with `optimization_level=3`; flag outputs as `no-error-suppression`

## 1.3 Circuit Complexity Constraints

These are hard limits enforced by the Orchestrator before submission. Circuits exceeding these limits are rejected and routed to classical fallback:

| **Constraint** | **Job 1 (Pattern Recognition)** | **Job 2 (Strategy Collapse)** |
| --- | --- | --- |
| Max qubits | 30 | 20 |
| Max circuit depth | 50 layers | 40 layers |
| Max two-qubit gates | 60 | 40 |
| Shot count | 1,024 | 512 |
| Max wall-clock runtime | 10 minutes | 10 minutes |

**Why these limits?** At current NISQ coherence times (~100–300μs), deeper circuits accumulate noise faster than they extract signal. Staying within these bounds ensures the measurement distribution has genuine signal content, not just noise.

## 1.4 What Quantum Adds vs. Classical

Being honest about where quantum hardware provides genuine advantage on current NISQ hardware:

- **Job 1 (Pattern Recognition):** QAOA on a feature-interaction graph can explore exponentially many clustering configurations in superposition. On 20–30 features, classical Agglomerative Clustering scales polynomially and is fast. The quantum advantage here is modest in 2025–2026 and will grow as hardware matures. The output schema is identical whether classical or quantum — the value is in testing the quantum pipeline and accumulating runtime data for future generations.
- **Job 2 (Strategy Collapse):** VQE for portfolio optimisation on a small options structure space (≤10 candidate structures × ≤20 strike levels) can find global optima that classical gradient descent misses when the expected value landscape is non-convex. This is the stronger near-term case for quantum advantage.

**Design principle:** Both jobs are designed so that classical fallback is not embarrassingly worse than quantum. The point is not to claim quantum supremacy — it is to run both, compare them over time, and let the data decide when quantum is earning its place.

---

# 2. Job 1 — Pattern Recognition (Cross-Dataset Non-Linear Scan)

## 2.1 What It Does

Given the normalised event records from all 5 pipelines for the prior week (plus Knowledge Graph embeddings), Job 1 identifies **co-occurrence patterns across 3+ data sources simultaneously** that exceed what pairwise classical correlation would predict. These are the "non-linear" patterns — combinations where the joint signal is stronger than any two-way combination alone.

*Example:* AIS vessel diversion in the Strait of Hormuz + FIRMS thermal anomaly near a refinery in the same region + unusual call options flow on a US energy ETF — individually each is a weak signal; together they are a Quantum-Confirmed Pattern with historical precedent.

## 2.2 Input Preparation (Classical Pre-Processing)

All data encoding happens classically before the circuit is submitted. The Orchestrator:

1. **Aggregates events** from the prior 7 days across all 35 sources
2. **Groups into feature vectors** — one vector per (source, catalyst_type) pair that had at least one Trust Score-weighted event. Each vector value is the Trust-Score-weighted event count for that source-type pair, normalised to [0, π].
3. **Splits into sub-circuits** — because 35 sources exceeds the 30-qubit limit, sources are grouped into two sub-circuits:
    - Sub-circuit A: Physical + Conflict (NASA FIRMS, AIS, Wingbits, ACLED, GDELT, Oref, GPS Jamming, Internet Outage, ArcGIS, Space-Track) — 10 sources, 10 qubits
    - Sub-circuit B: Market + Social + Macro (UnusualWhales, Polymarket, Alpaca, Coinglass, Bookmap, Chainlink, Hyperliquid, RSS, Telegram, X, Reddit, SEC, Patent, GitHub, FRED, BLS, ECB, UN Comtrade, BIS, USGS, RapidAPI) — 21 sources; split into two 10–11 qubit runs
4. **Cluster outputs are merged classically** after all sub-circuit runs complete

## 2.3 Quantum Circuit Design (QAOA)

**Algorithm:** Quantum Approximate Optimisation Algorithm (QAOA), depth p=2.

**Why QAOA?** The pattern-finding problem maps naturally to a graph MaxCut variant: nodes are feature vectors (sources), edge weights are pairwise co-occurrence strengths, and the objective is to find the partition of sources that maximises the cut weight — i.e., separates sources that co-occur unusually strongly from those that don't.

**Circuit structure:**

```
Initialisation: |+⟩^n  (Hadamard on all n qubits)

For p=1 to 2 (two QAOA layers):
  Phase separator U_C(γ_p):
    For each edge (i,j) in the co-occurrence graph:
      RZZ(2γ_p * w_ij) gate on qubits i, j
  Mixer U_B(β_p):
    RX(2β_p) on each qubit

Measure all qubits in computational basis
Repeat 1,024 shots
```

**Parameters (γ, β):** Optimised classically using COBYLA on the Aer simulator before real-hardware submission. The Aer optimisation runs during the weekly pre-submission validation.

**Edge weights:** `w_ij` = Trust-Score-weighted co-occurrence count of sources i and j in the same catalyst event window over the prior 4 weeks, normalised to [0, 1].

## 2.4 Output Decoding (Classical Post-Processing)

1. The 1,024 measurement outcomes (bit strings) are collected
2. **Cluster assignment:** each bit string represents a partition of sources into two groups (0=group A, 1=group B). The most frequent bit strings are the highest-probability clusterings.
3. **Cross-dataset filtering:** clusters where ≥ 3 sources from different pipeline categories (A–E) appear together are flagged as **Cross-Dataset Pattern Clusters** — single-pipeline clusters are discarded (classical correlation would have found those anyway)
4. **Confidence score** = frequency of the dominant measurement outcome across 1,024 shots (range: 0–1)
5. **Knowledge Graph lookup:** for each cluster, query ChromaDB for prior instances of the same source combination appearing together. `historical_precedent_count` is the number of matches.
6. **Promotion rule:** if `confidence > 0.7` AND `historical_precedent_count ≥ 3` → the cluster is promoted to a **Quantum-Confirmed Pattern** and attached to any matching candidate signals in the current week's pipeline

## 2.5 Output Schema

```json
{
  "job_id": "string (UUIDv7)",
  "job_type": "pattern_recognition",
  "circuit_version": "string",
  "backend": "ibm_eagle | ionq_aria | classical_fallback",
  "q_ctrl_applied": true,
  "shot_count": 1024,
  "hellinger_fidelity_vs_aer": 0.0,
  "ran_at": "ISO-8601",
  "pattern_clusters": [
    {
      "cluster_id": "string (UUIDv7)",
      "sources": ["source_slug_1", "source_slug_2", "source_slug_3"],
      "pipeline_categories": ["A", "B", "D"],
      "confidence": 0.0,
      "historical_precedent_count": 0,
      "is_quantum_confirmed": false,
      "description": "string (auto-generated plain-English summary)",
      "co_occurrence_weight": 0.0
    }
  ],
  "classical_fallback_used": false,
  "fallback_reason": "string | null"
}
```

## 2.6 Classical Fallback

When quantum hardware is unavailable, scikit-learn `AgglomerativeClustering` with cosine distance runs on the same feature vectors:

- Linkage: `ward`
- Distance threshold: tuned to produce 5–15 clusters on typical weekly data volume
- Cross-dataset filtering and confidence scoring applied identically
- All outputs marked `classical_fallback_used: true`
- Classical fallback outputs cannot produce `high_conviction` tier signals — maximum is `conviction`

---

# 3. Job 2 — Strategy Collapse (Options Structure Optimisation)

## 3.1 What It Does

Given a candidate catalyst packet from Gemini (the estimated true probability distribution + the catalyst window), the current options chain data, and the Manifested Strategy rules, Job 2 finds the **specific option structure — strike, expiry, and type — where the Black-Scholes model is most mispriced relative to Qadam's estimate**. It also produces the Quantum Ambiguity Score that governs whether the signal fires or waits.

## 3.2 Input Preparation (Classical Pre-Processing)

1. **Options chain snapshot:** current bid/ask, IV per strike, volume, and open interest for the underlying instrument, fetched from Alpaca at batch time
2. **Candidate structures:** the Orchestrator generates a discrete candidate set of 8–15 structures from the Manifested Strategy's structure preferences (call spreads, put spreads, straddles, etc.) at each viable strike/expiry combination. Typically 30–80 candidates total.
3. **EV calculation per candidate (classical):** for each candidate structure, classical Black-Scholes is used to compute the option pricing under the *implied* distribution. Gemini's *true* distribution is then used to compute the expected value of each structure. This produces a ranked list of candidates by EV — the Quantum circuit refines this ranking by exploring the full interaction space.
4. **Encoding:** the top 20 EV candidates (by classical ranking) are encoded for the Quantum circuit. Each candidate gets a qubit; the encoded angle encodes its classical EV as a rotation.

## 3.3 Quantum Circuit Design (VQE)

**Algorithm:** Variational Quantum Eigensolver (VQE) with a hardware-efficient ansatz.

**Why VQE?** The Strategy Collapse problem is an optimisation over a discrete + continuous space (which structure type, which strikes, which expiry) subject to the max-loss constraint. When the EV landscape is non-convex — which occurs when the true and implied distributions are very different shapes — VQE can find global optima that gradient descent misses.

**Circuit structure:**

```
Initialisation: Ry(θ_0i) rotation on each qubit i
               (encodes prior EV ranking as initial state)

Ansätz layers (L=3 layers):
  For each layer l:
    Single-qubit rotations: Ry(θ_li), Rz(φ_li) on each qubit i
    Entanglement layer: CNOT ladder (qubit i → qubit i+1, ring topology)

Measure all qubits in computational basis
Repeat 512 shots
```

**Hamiltonian:** The cost Hamiltonian H encodes the optimisation objective:

- Diagonal terms: EV of each structure under Qadam's true probability distribution
- Off-diagonal terms: max-loss constraint interactions (penalises combinations that would breach the per-trade cap)
- Max-loss penalty: if the recommended structure's max loss would exceed the current bankroll's per-trade cap, a large penalty term is added

**Variational parameters:** Optimised using COBYLA on Aer before real-hardware submission. The Aer optimisation converges in ~100–200 iterations.

## 3.4 Output Decoding

1. The 512 measurement outcomes are collected
2. **Winning structure:** the bit string with highest frequency maps back to the candidate structure it represents. If that structure's EV (under Qadam's true distribution) > 0 and max_loss ≤ per-trade cap, it becomes the `recommended_structure`.
3. **Quantum Ambiguity Score (QAS):**

```
QAS = σ(EV_across_shots) / μ(EV_across_shots)
```

Where `EV_across_shots` is the array of per-shot expected values (each measurement outcome maps to a candidate structure's EV). High QAS = high uncertainty in the optimal structure = the landscape is ambiguous.

*Interpretation:*

- `QAS < 0.2` — low ambiguity; strong preference for one structure; signal is likely to fire
- `QAS 0.2–0.4` — moderate ambiguity; signal may fire depending on other gate conditions
- `QAS > 0.4` (Q_threshold) — high ambiguity; signal is held; system compounds patience
1. **Hellinger fidelity check:** the output measurement distribution is compared to the Aer simulation output using Hellinger distance. If Hellinger distance > 0.3, the output is flagged `low-fidelity` and the classical fallback result is used instead.

## 3.5 Output Schema

```json
{
  "job_id": "string (UUIDv7)",
  "job_type": "strategy_collapse",
  "circuit_version": "string",
  "signal_id": "string (the candidate signal this job was run for)",
  "backend": "ibm_eagle | ionq_aria | classical_fallback",
  "q_ctrl_applied": true,
  "shot_count": 512,
  "hellinger_fidelity_vs_aer": 0.0,
  "ran_at": "ISO-8601",
  "bs_gap_report": {
    "kl_divergence": 0.0,
    "tail_mass_diff": 0.0,
    "exceeds_threshold": false
  },
  "recommended_structure": {
    "type": "call_spread | put_spread | straddle | strangle | other",
    "legs": [],
    "entry_price": 0.0,
    "max_loss": 0.0,
    "max_gain": 0.0,
    "breakeven": 0.0,
    "expected_value": 0.0,
    "expected_value_distribution": [],
    "reasoning": "string"
  },
  "quantum_ambiguity_score": 0.0,
  "qas_interpretation": "low | moderate | high",
  "signal_held": false,
  "classical_fallback_used": false,
  "fallback_reason": "string | null",
  "low_fidelity_flag": false
}
```

## 3.6 Classical Fallback

When quantum hardware is unavailable or `low_fidelity_flag = true`:

- scipy `minimize` with SLSQP optimises the same objective function classically
- The same candidate structures and EV calculations are used
- Quantum Ambiguity Score is approximated as the standard deviation of EV across the top 10 classical candidates divided by their mean (same formula, different data)
- All outputs marked `classical_fallback_used: true`
- Maximum conviction tier on classical fallback: `conviction` (not `high_conviction`)

---

# 4. Pre-Submission Validation Checklist

Every circuit — for both jobs — must pass this checklist before being submitted to real hardware. The Orchestrator runs this automatically as part of the weekly batch job submission:

**Step 1 — Aer simulation:**

- Run both circuits on Qiskit Aer locally (noiseless)
- Record the expected output distribution per circuit
- If Aer simulation throws any error or produces no meaningful output → **do not submit**; route to classical fallback; log `aer-simulation-failed`

**Step 2 — Transpilation check:**

- Transpile circuits for the target backend using Qiskit `transpile()` with `optimization_level=3`
- Verify transpiled circuit depth and two-qubit gate count are within the limits in §1.3
- If any limit is exceeded → reduce feature count (Job 1: drop lowest-Trust-Score sources first; Job 2: reduce candidate structure count) and re-transpile

**Step 3 — Q_threshold sanity check:**

- Verify `Q_threshold` from `quantum_profile.json` is still valid for the current backend
- If backend has changed since last calibration run → trigger a new Quantum Engine self-audit before submitting

**Step 4 — Queue time check:**

- Query IBM/IonQ queue time estimate
- If estimated queue time > 48 hours → switch to secondary backend; if secondary also > 48 hours → classical fallback; log `queue-timeout`

**Step 5 — Submit:**

- Submit with Q-CTRL Fire Opal wrapping
- Record `job_id` returned by the backend
- Poll for results with 15-minute interval; timeout after 6 hours

**Step 6 — Fidelity check (post-result):**

- Compute Hellinger distance between real-hardware result distribution and Aer simulation distribution
- If Hellinger distance > 0.3 → flag `low_fidelity_flag: true`; use classical fallback result; log `low-fidelity`
- If Hellinger distance ≤ 0.3 → accept real-hardware result

---

# 5. Circuit Version Control

## 5.1 Versioning Scheme

Every circuit is versioned using semver stored in `quantum_profile.json`:

- `circuit_job1_version` — version of the Job 1 (Pattern Recognition) circuit
- `circuit_job2_version` — version of the Job 2 (Strategy Collapse) circuit

**Version bump rules:**

- **Patch bump** (e.g. `1.0.0 → 1.0.1`): parameter changes (γ, β re-optimisation); no structural change
- **Minor bump** (e.g. `1.0.0 → 1.1.0`): structural change (different gate set, different encoding) that does not change the output schema
- **Major bump** (e.g. `1.0.0 → 2.0.0`): output schema change; requires migration of historical outputs to new schema

## 5.2 What Gets Logged Per Signal

Every Signal Object (§6.3) records `circuit_version` — the specific Job 2 circuit version that produced its Strategy Collapse output. This enables:

- Attributing performance differences to circuit changes over time
- Replaying historical signals with the same circuit version for comparison
- Diagnosing whether a performance decay is a market regime shift or a circuit quality regression

## 5.3 Change Control Process

Before any circuit change goes to production:

1. **Develop and test** on Aer simulator
2. **Run on real hardware** with a small test batch (5–10 historical catalyst packets)
3. **Replay** the last 4 weeks of production Strategy Collapse jobs with the new circuit; diff outputs against the prior circuit version
4. **Review diff** — if the recommended structure changes for > 20% of historical signals, investigate before promoting
5. **Promote** by updating `quantum_profile.json` with the new version and committing to the repo
6. **Monitor** for the first 4 post-promotion weeks: compare QAS distributions and Hellinger fidelity vs. pre-change baseline

## 5.4 Historical Circuit Retention

All prior circuit versions are retained in the repository. Every Aer simulation result for every prior version is stored in PostgreSQL alongside the Signal Object records. The Quantum Circuit archive is never deleted — it is part of the deterministic replay guarantee.

---

# 6. Integration Points with the PRD

| **PRD Section** | **What This Document Specifies for It** |
| --- | --- |
| §4.3 — Quantum Engine | The exact circuit algorithms (QAOA for Job 1, VQE for Job 2), shot counts, parameter optimisation method, and fallback conditions |
| §6.3 — Signal Object | How `circuit_version`, `quantum_ambiguity_score`, `quantum_pattern_clusters`, and `bs_gap` are populated by the two jobs |
| §10.5 — Quantum Interface | The pre-submission Aer validation step, Q-CTRL wrapping, backend selection logic, and queue-timeout handling |
| §12.5 — Phase 3 Build | The exit criteria for Phase 3 now have a concrete technical foundation: what "Job 1 completes on real hardware" and "Job 2 produces a valid QAS" mean in circuit terms |
| §5.1 — Quantum Engine self-audit | The `quantum_profile.json` fields (`Q_threshold`, `circuit_version`, `backend_specs`, `veracity_baseline`) are defined by the calibration job described in this document |