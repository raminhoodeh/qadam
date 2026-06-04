#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SITE_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
ROOT_DIR="$(cd "${SITE_DIR}/.." && pwd)"
LOCAL_VERCEL_ENV="${ROOT_DIR}/data/runtime/vercel.env"
QADAM_ORIGINAL_HOME="${HOME}"
QADAM_ORIGINAL_XDG_CACHE_HOME="${XDG_CACHE_HOME:-${QADAM_ORIGINAL_HOME}/.cache}"
QADAM_ORIGINAL_XDG_CONFIG_HOME="${XDG_CONFIG_HOME:-${QADAM_ORIGINAL_HOME}/.config}"
export npm_config_cache="${npm_config_cache:-${ROOT_DIR}/data/runtime/npm-cache}"
export QADAM_VERCEL_HOME="${QADAM_VERCEL_HOME:-${ROOT_DIR}/data/runtime/vercel-home}"
export HOME="${QADAM_VERCEL_HOME}"
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-${ROOT_DIR}/data/runtime/xdg-cache}"
export XDG_CONFIG_HOME="${XDG_CONFIG_HOME:-${ROOT_DIR}/data/runtime/xdg-config}"
export VERCEL_TELEMETRY_DISABLED="${VERCEL_TELEMETRY_DISABLED:-1}"
export npm_config_loglevel="${npm_config_loglevel:-notice}"
mkdir -p "${npm_config_cache}" "${HOME}" "${XDG_CACHE_HOME}" "${XDG_CONFIG_HOME}"

say() {
  printf '[qadam-deploy] %s\n' "$*"
}

say "Preparing dashboard production deploy from ${SITE_DIR}"
QADAM_PYTHON_BIN="${QADAM_PYTHON:-python3}"
if [[ -x "${ROOT_DIR}/.venv/bin/python" ]]; then
  QADAM_PYTHON_BIN="${QADAM_PYTHON:-${ROOT_DIR}/.venv/bin/python}"
fi

if [[ -f "${LOCAL_VERCEL_ENV}" ]]; then
  # shellcheck disable=SC1090
  source "${LOCAL_VERCEL_ENV}"
  say "Loaded local Vercel credentials from ${LOCAL_VERCEL_ENV}"
else
  say "No local Vercel env file found at ${LOCAL_VERCEL_ENV}; expecting exported VERCEL_TOKEN"
fi

cd "${SITE_DIR}"

: "${VERCEL_TOKEN:?Set VERCEL_TOKEN before running this script.}"

VERCEL_TEAM_ID="${VERCEL_TEAM_ID:-${VERCEL_ORG_ID:-team_Qv7iJDGRobHFyiyUsMUbVxyy}}"
PRODUCTION_DOMAINS=(
  "qadam.trade"
  "www.qadam.trade"
)

if [[ "${QADAM_SKIP_DEPLOY_PREFLIGHT:-0}" != "1" ]]; then
  say "Running local deployment preflight"
  env \
    HOME="${QADAM_ORIGINAL_HOME}" \
    XDG_CACHE_HOME="${QADAM_ORIGINAL_XDG_CACHE_HOME}" \
    XDG_CONFIG_HOME="${QADAM_ORIGINAL_XDG_CONFIG_HOME}" \
    bash "${ROOT_DIR}/scripts/preflight_dashboard_deployment.sh"
else
  say "Skipping local deployment preflight because QADAM_SKIP_DEPLOY_PREFLIGHT=1"
fi

vercel_cmd=()
if command -v vercel >/dev/null 2>&1; then
  vercel_cmd=("vercel")
  say "Using installed Vercel CLI"
elif [[ -x "${SITE_DIR}/node_modules/.bin/vercel" ]]; then
  vercel_cmd=("${SITE_DIR}/node_modules/.bin/vercel")
  say "Using project-local Vercel CLI"
else
  cached_vercel="$(
    find "${HOME}/.npm/_npx" -path '*/node_modules/.bin/vercel' -type f 2>/dev/null | sort | tail -n 1 || true
  )"
  if [[ -n "${cached_vercel}" ]]; then
    vercel_cmd=("${cached_vercel}")
    say "Using cached Vercel CLI at ${cached_vercel}"
  else
    say "Vercel CLI is not installed and no cached copy was found."
    say "Install it once with: npm install -g vercel"
    say "Then rerun: bash landing-page-repo/scripts/deploy-vercel-production.sh"
    exit 1
  fi
fi

deploy_log="$(mktemp)"

say "Deploying to Vercel production scope ${VERCEL_TEAM_ID}"
if ! "${vercel_cmd[@]}" deploy \
  --prod \
  --yes \
  --scope "${VERCEL_TEAM_ID}" \
  --token "${VERCEL_TOKEN}" 2>&1 | tee "${deploy_log}"; then
  say "Deploy failed."
  say "No production aliases were changed by this script and no deployment receipt was written."
  exit 1
fi

deployment_url="$(
  grep -Eo 'https://[^[:space:]]+\.vercel\.app' "${deploy_log}" | tail -n 1
)"

if [[ -z "${deployment_url}" ]]; then
  echo "Could not find the Vercel deployment URL in deploy output." >&2
  say "No production aliases were changed by this script and no deployment receipt was written."
  exit 1
fi

for domain in "${PRODUCTION_DOMAINS[@]}"; do
  say "Aliasing ${deployment_url} to ${domain}"
  if ! "${vercel_cmd[@]}" alias set "${deployment_url}" "${domain}" \
    --scope "${VERCEL_TEAM_ID}" \
    --token "${VERCEL_TOKEN}"; then
    say "Alias failed for ${domain}."
    say "A Vercel deployment URL may exist, but this script did not complete all production aliases or write a receipt."
    exit 1
  fi
done

receipt_path="${ROOT_DIR}/data/runtime/dashboard-deployment-receipt.json"
mkdir -p "$(dirname "${receipt_path}")"
node - "${receipt_path}" "${deployment_url}" "${PRODUCTION_DOMAINS[@]}" <<'NODE'
const fs = require("node:fs");

const [receiptPath, deploymentUrl, ...domains] = process.argv.slice(2);
const receipt = {
  deployed_at: new Date().toISOString(),
  surface: "qadam.trade static dashboard",
  deployment_url: deploymentUrl,
  aliases: domains,
  preflight: process.env.QADAM_SKIP_DEPLOY_PREFLIGHT === "1" ? "skipped" : "passed",
  boundary: "Receipt only. Contains no Vercel token, session cookie, broker credential, or dashboard secret."
};

fs.writeFileSync(receiptPath, `${JSON.stringify(receipt, null, 2)}\n`);
NODE

say "Production deployment: ${deployment_url}"
say "Aliased domains: ${PRODUCTION_DOMAINS[*]}"
say "Deployment receipt: ${receipt_path}"

say "Sending codebase upgrade Telegram notification"
if ! (
  cd "${ROOT_DIR}"
  env \
    HOME="${QADAM_ORIGINAL_HOME}" \
    XDG_CACHE_HOME="${QADAM_ORIGINAL_XDG_CACHE_HOME}" \
    XDG_CONFIG_HOME="${QADAM_ORIGINAL_XDG_CONFIG_HOME}" \
  "${QADAM_PYTHON_BIN}" "${ROOT_DIR}/scripts/send_codebase_upgrade_telegram_notification.py" \
    --live \
    --source "production_deploy" \
    --summary "Production dashboard deploy completed and Qadam codebase-upgrade notifications are active." \
    --detail "The deploy hook now sends this group update after Vercel production aliases are updated." \
    --detail "The runtime artifact records the core commit, dashboard commit, delivery status, and failure category." \
    --detail "The dashboard Communications panel mirrors the latest codebase-upgrade notification state." \
    --benefit "Fund Managers can see what changed and why it matters without checking Git, Vercel, or local logs." \
    --benefit "Failed upgrade notifications are visible instead of silently disappearing after deploy." \
    --benefit "The message states the safety boundary, so a dashboard/code update is not confused with trading authority." \
    --deployment-url "${deployment_url}" \
      --alias "qadam.trade" \
      --alias "www.qadam.trade"
); then
  say "Codebase upgrade Telegram notification failed; deployment and aliases completed, but the team notification did not."
  exit 1
fi
say "Codebase upgrade Telegram notification completed"
