(() => {
    "use strict";

    const STATUS_URL = "/status/quantum-edge-wave-h.json?v=20260719-engine-convergence-v2";
    const TARGET_SELECTOR = '[data-qwf-view="quantum-edge"]';
    let projection = null;
    let observer = null;
    let applyScheduled = false;

    function list(value) {
        return Array.isArray(value) ? value : [];
    }

    function escapeHtml(value, fallback = "") {
        return String(value ?? fallback)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    function titleCase(value, fallback = "Not available") {
        const text = String(value || "").trim();
        if (!text) return fallback;
        return text
            .replace(/[_-]+/g, " ")
            .replace(/\s+/g, " ")
            .replace(/^./, (character) => character.toUpperCase());
    }

    function renderProofStates(states) {
        return `
            <ol class="qwh-proof-key" aria-label="Quantum Edge proof states">
                ${list(states).map((row) => `
                    <li class="${row.current ? "is-current" : ""}">
                        <strong>${escapeHtml(titleCase(row.state))}</strong>
                        <p>${escapeHtml(row.meaning)}</p>
                        ${row.current ? "<em>Current</em>" : ""}
                    </li>
                `).join("")}
            </ol>
        `;
    }

    function renderRunLedger(runs) {
        return `
            <ol class="qwh-run-ledger">
                ${list(runs).map((row) => `
                    <li>
                        <div>
                            <strong>${escapeHtml(row.run)}</strong>
                            <span>${escapeHtml(row.fixture_only ? "Engineering control" : "Market evidence")}</span>
                        </div>
                        <p>${escapeHtml(row.result)}</p>
                        <em class="qwh-state-${escapeHtml(row.status)}">${escapeHtml(titleCase(row.status))}</em>
                    </li>
                `).join("")}
            </ol>
        `;
    }

    function renderCertification(certification) {
        const engineering = list(certification.engineering_checks);
        const scientific = list(certification.scientific_checks);
        return `
            <div class="qwh-certification-grid">
                <section>
                    <header>
                        <span>Engineering mechanism</span>
                        <strong>${escapeHtml(certification.engineering_pass_count)}/${escapeHtml(certification.engineering_check_count)} passed</strong>
                    </header>
                    <ul>
                        ${engineering.map((row) => `<li><strong>${escapeHtml(titleCase(row.key))}</strong><span>${escapeHtml(row.explanation)}</span></li>`).join("")}
                    </ul>
                </section>
                <section>
                    <header>
                        <span>Market proof</span>
                        <strong>${escapeHtml(certification.scientific_pass_count)}/${escapeHtml(certification.scientific_check_count)} passed</strong>
                    </header>
                    <ul>
                        ${scientific.map((row) => `<li><strong>${escapeHtml(titleCase(row.key))}</strong><span>${escapeHtml(row.explanation)}</span></li>`).join("")}
                    </ul>
                </section>
            </div>
        `;
    }

    function renderProjection(payload) {
        const evidence = payload.evidence_truth || {};
        const certification = payload.certification || {};
        const hardware = payload.hardware_authorization_checkpoint || {};
        const manifest = payload.pilot_manifest || {};
        return `
            <section class="qwh-certification" data-qwh-certification data-qwh-content-hash="${escapeHtml(payload.content_hash)}">
                <header class="qwh-header">
                    <div>
                        <span>Crude-oil pilot certification</span>
                        <h3>Can Qadam prove a quantum edge honestly?</h3>
                        <p>${escapeHtml(payload.plain_english_summary)}</p>
                    </div>
                    <aside>
                        <span>Current proof state</span>
                        <strong>${escapeHtml(titleCase(payload.public_proof_state))}</strong>
                        <small>${escapeHtml(titleCase(payload.scientific_verdict))}</small>
                    </aside>
                </header>
                ${renderProofStates(payload.proof_state_key)}
                <section class="qwh-pilot-facts">
                    <header><span>Frozen pilot</span><h3>What the crude-oil test will compare</h3></header>
                    <dl>
                        <div><dt>Paper targets</dt><dd>${escapeHtml(list(manifest.paper_targets).join(", "))}</dd></div>
                        <div><dt>Point-in-time features</dt><dd>${escapeHtml(list(manifest.point_in_time_features).length)}</dd></div>
                        <div><dt>Classified windows</dt><dd>${escapeHtml(evidence.classified_window_count || 0)}</dd></div>
                        <div><dt>Eligible holdout windows</dt><dd>${escapeHtml(evidence.eligible_window_count || 0)}</dd></div>
                        <div><dt>Provider-history rows</dt><dd>${escapeHtml(evidence.provider_row_count || 0)}</dd></div>
                        <div><dt>Lookahead violations</dt><dd>${escapeHtml(evidence.leakage_violation_count || 0)}</dd></div>
                    </dl>
                    <div class="qwh-features">
                        ${list(manifest.point_in_time_features).map((row) => `<span title="${escapeHtml(row.meaning)}">${escapeHtml(titleCase(row.key))}</span>`).join("")}
                    </div>
                </section>
                <section class="qwh-runs">
                    <header><span>Experiment ledger</span><h3>What ran, and what did not</h3></header>
                    ${renderRunLedger(payload.run_ledger)}
                </section>
                ${renderCertification(certification)}
                <section class="qwh-next">
                    <div>
                        <span>What blocks market proof</span>
                        <h3>Evidence first, hardware second</h3>
                        <ul>${list(payload.next_actions).map((action) => `<li>${escapeHtml(action)}</li>`).join("")}</ul>
                    </div>
                    <aside>
                        <span>Prepared engineering manifest</span>
                        <strong>${escapeHtml(String(hardware.engineering_manifest_hash || "not prepared").slice(0, 16))}</strong>
                        <p>${escapeHtml(hardware.circuit_count || 0)} circuits · ${escapeHtml(hardware.qubit_count || 0)} qubits · ${escapeHtml(hardware.total_shots || 0)} total shots</p>
                        <small>Not authorized or submitted. A real empirical manifest requires separate approval.</small>
                    </aside>
                </section>
                <p class="qwh-boundary">Other markets remain out of scope until the crude-oil pipeline has reproducible empirical and hardware evidence. This page is read-only and cannot authorize a provider job or trade.</p>
            </section>
        `;
    }

    function applyProjection() {
        applyScheduled = false;
        if (!projection) return;
        const target = document.querySelector(TARGET_SELECTOR);
        if (!target) return;
        const existing = target.querySelector("[data-qwh-certification]");
        const waveG = target.querySelector("[data-qwg-loop]");
        if (existing?.dataset.qwhContentHash === projection.content_hash) {
            if (waveG && waveG.nextElementSibling !== existing) {
                waveG.insertAdjacentElement("afterend", existing);
            }
            return;
        }
        if (existing) existing.remove();
        const wrapper = document.createElement("div");
        wrapper.innerHTML = renderProjection(projection).trim();
        const section = wrapper.firstElementChild;
        const boundary = target.querySelector(":scope > .qwf-boundary");
        if (waveG) waveG.insertAdjacentElement("afterend", section);
        else if (boundary) target.insertBefore(section, boundary);
        else target.appendChild(section);
        document.documentElement.dataset.qadamWaveH = "rendered";
    }

    function scheduleApply() {
        if (applyScheduled) return;
        applyScheduled = true;
        window.requestAnimationFrame(applyProjection);
    }

    async function loadProjection() {
        try {
            const response = await fetch(STATUS_URL, { cache: "no-store" });
            if (!response.ok) throw new Error(`Wave H status returned ${response.status}`);
            const payload = await response.json();
            if (payload?.schema_version !== "qadam.QuantumEdgeWaveHCrudeOilCertification.v1") {
                throw new Error("Wave H status schema mismatch");
            }
            projection = payload;
            scheduleApply();
        } catch (error) {
            document.documentElement.dataset.qadamWaveH = "unavailable";
            console.error("Qadam Wave H certification unavailable", error);
        }
    }

    observer = new MutationObserver(scheduleApply);
    observer.observe(document.body, { childList: true, subtree: true });
    window.addEventListener("qadam-wave-f-ready", scheduleApply);
    window.addEventListener("popstate", scheduleApply);
    window.QadamWaveH = {
        statusUrl: STATUS_URL,
        apply: scheduleApply,
        getProjection: () => projection,
        disconnect: () => observer?.disconnect()
    };
    loadProjection();
})();
