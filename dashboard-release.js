(() => {
    "use strict";

    const RELEASE_META = "qadam-dashboard-release";
    const MANIFEST_URL = "/api/dashboard-release";
    const CHECK_INTERVAL_MS = 5 * 60 * 1000;
    const FIRST_CHECK_DELAY_MS = 15 * 1000;
    const loadedRelease = document.querySelector(`meta[name="${RELEASE_META}"]`)?.content || "";
    let lastCheckAt = 0;

    function updateBanner(manifest) {
        let banner = document.querySelector("[data-qadam-release-update]");
        if (!banner) {
            banner = document.createElement("aside");
            banner.className = "qadam-release-update";
            banner.dataset.qadamReleaseUpdate = "true";
            banner.setAttribute("role", "status");
            banner.setAttribute("aria-live", "polite");
            banner.hidden = true;

            const message = document.createElement("span");
            message.textContent = "A newer dashboard is available";

            const refresh = document.createElement("button");
            refresh.type = "button";
            refresh.textContent = "Refresh";
            refresh.addEventListener("click", () => window.location.reload());

            banner.append(message, refresh);
            document.body.appendChild(banner);
        }

        banner.dataset.deployedRelease = String(manifest.release_id || "");
        banner.hidden = false;
    }

    async function checkForNewRelease() {
        if (!loadedRelease) return;
        lastCheckAt = Date.now();
        try {
            const response = await fetch(`${MANIFEST_URL}?t=${lastCheckAt}`, {
                cache: "no-store",
                credentials: "omit",
                headers: { accept: "application/json" }
            });
            if (!response.ok) return;
            const manifest = await response.json();
            const deployedRelease = String(manifest?.release_id || "");
            if (deployedRelease && deployedRelease !== loadedRelease) {
                updateBanner(manifest);
            }
        } catch (_error) {
            // The dashboard remains usable if the public release probe is unavailable.
        }
    }

    window.setTimeout(checkForNewRelease, FIRST_CHECK_DELAY_MS);
    window.setInterval(checkForNewRelease, CHECK_INTERVAL_MS);
    window.addEventListener("focus", () => {
        if (Date.now() - lastCheckAt >= 60 * 1000) checkForNewRelease();
    });
})();
