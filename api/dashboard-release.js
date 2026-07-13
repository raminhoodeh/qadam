const fs = require("node:fs");
const path = require("node:path");

module.exports = function dashboardRelease(_req, res) {
    const manifestPath = path.join(process.cwd(), "status", "dashboard-release.json");
    try {
        const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf8"));
        const gitCommit = process.env.QADAM_RELEASE_COMMIT
            || process.env.VERCEL_GIT_COMMIT_SHA
            || manifest.git_commit
            || "not_exported";

        res.setHeader("content-type", "application/json; charset=utf-8");
        res.setHeader("cache-control", "no-store, max-age=0");
        res.status(200).send(JSON.stringify({ ...manifest, git_commit: gitCommit }));
    } catch (error) {
        res.setHeader("content-type", "application/json; charset=utf-8");
        res.setHeader("cache-control", "no-store, max-age=0");
        res.status(503).send(JSON.stringify({
            status: "dashboard_release_unavailable",
            boundary: "Public release metadata only. No command, broker, credential, or live-capital authority.",
            error: error && error.message ? error.message : "release manifest unavailable"
        }));
    }
};
