const fs = require("node:fs");
const path = require("node:path");

module.exports = function cockpitStatus(req, res) {
    const statusPath = path.join(process.cwd(), "status", "cockpit-status.json");
    try {
        const raw = fs.readFileSync(statusPath, "utf8");
        const payload = JSON.parse(raw);
        res.setHeader("content-type", "application/json; charset=utf-8");
        res.setHeader("cache-control", "no-store, max-age=0");
        res.status(200).send(JSON.stringify(payload));
    } catch (error) {
        res.setHeader("content-type", "application/json; charset=utf-8");
        res.status(503).send(JSON.stringify({
            status: "cockpit_status_unavailable",
            error: error && error.message ? error.message : "status file unavailable",
            boundary: "Read-only public status bridge. No command, broker, or live-capital authority."
        }));
    }
};
