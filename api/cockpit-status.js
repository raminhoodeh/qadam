const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");

function stableStringify(value) {
    if (Array.isArray(value)) return `[${value.map(stableStringify).join(",")}]`;
    if (value && typeof value === "object") {
        return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${stableStringify(value[key])}`).join(",")}}`;
    }
    return JSON.stringify(value);
}

function safeEqual(left, right) {
    const a = Buffer.from(String(left || ""));
    const b = Buffer.from(String(right || ""));
    return a.length === b.length && crypto.timingSafeEqual(a, b);
}

function decorate(payload, delivery) {
    return {
        ...payload,
        live_bridge: {
            ...(payload.live_bridge || {}),
            delivery
        }
    };
}

function sendStatus(req, res, payload, digest, source) {
    const etag = `"${digest}"`;
    res.setHeader("content-type", "application/json; charset=utf-8");
    res.setHeader("cache-control", "private, no-cache, must-revalidate");
    res.setHeader("etag", etag);
    res.setHeader("x-qadam-status-source", source);
    if (req.headers["if-none-match"] === etag) return res.status(304).end();
    if (req.method === "HEAD") return res.status(200).end();
    return res.status(200).send(JSON.stringify(payload));
}

async function latestPublishedSnapshot() {
    const supabaseUrl = process.env.SUPABASE_URL || process.env.NEXT_PUBLIC_SUPABASE_URL || "";
    const supabaseKey = process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.SUPABASE_SECRET_KEY || "";
    const signingKey = process.env.QADAM_STATUS_BRIDGE_SIGNING_KEY || "";
    if (!supabaseUrl || !supabaseKey || !signingKey) return null;
    const endpoint = `${supabaseUrl.replace(/\/$/, "")}/rest/v1/qadam_public_status_snapshots?select=generated_at,payload_digest,signature,canonical_payload,payload,stored_at&order=stored_at.desc&limit=1`;
    const response = await fetch(endpoint, {
        headers: { apikey: supabaseKey, authorization: `Bearer ${supabaseKey}` }
    });
    if (!response.ok) throw new Error(`status_store_${response.status}`);
    const rows = await response.json();
    const record = rows[0];
    if (!record) return null;
    const canonical = record.canonical_payload || stableStringify(record.payload);
    const digest = crypto.createHash("sha256").update(canonical).digest("hex");
    const signature = crypto.createHmac("sha256", signingKey).update(canonical).digest("hex");
    if (!safeEqual(record.payload_digest, digest) || !safeEqual(record.signature, signature)) {
        throw new Error("stored_status_signature_invalid");
    }
    const verifiedPayload = record.canonical_payload ? JSON.parse(record.canonical_payload) : record.payload;
    const generatedMs = Date.parse(verifiedPayload.generated_at || record.generated_at || "");
    const ageSeconds = Number.isFinite(generatedMs) ? Math.max(0, Math.floor((Date.now() - generatedMs) / 1000)) : null;
    const staleAfter = Number(process.env.QADAM_STATUS_BRIDGE_STALE_AFTER_SECONDS || 60);
    return {
        payload: decorate(verifiedPayload, {
            state: ageSeconds !== null && ageSeconds <= staleAfter ? "live" : "stale",
            source: "signed_public_status_store",
            stored_at: record.stored_at,
            age_seconds: ageSeconds,
            stale_after_seconds: staleAfter,
            signature_verified: true,
            read_only: true
        }),
        digest
    };
}

module.exports = async function cockpitStatus(req, res) {
    if (!["GET", "HEAD"].includes(req.method)) {
        res.setHeader("allow", "GET, HEAD");
        return res.status(405).send(JSON.stringify({ status: "method_not_allowed" }));
    }
    const statusPath = path.join(process.cwd(), "status", "cockpit-status.json");
    try {
        const published = await latestPublishedSnapshot();
        if (published) return sendStatus(req, res, published.payload, published.digest, "signed_public_status_store");
    } catch (error) {
        res.setHeader("x-qadam-live-bridge-error", "signed_snapshot_unavailable");
    }
    try {
        const raw = fs.readFileSync(statusPath, "utf8");
        const payload = JSON.parse(raw);
        const digest = crypto.createHash("sha256").update(stableStringify(payload)).digest("hex");
        return sendStatus(req, res, decorate(payload, {
            state: "static_fallback",
            source: "deployed_static_snapshot",
            signature_verified: false,
            read_only: true
        }), digest, "deployed_static_snapshot");
    } catch (error) {
        res.setHeader("content-type", "application/json; charset=utf-8");
        return res.status(503).send(JSON.stringify({
            status: "cockpit_status_unavailable",
            error: error && error.message ? error.message : "status file unavailable",
            boundary: "Read-only public status bridge. No command, broker, or live-capital authority."
        }));
    }
};
