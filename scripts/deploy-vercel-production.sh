#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SITE_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
DEFAULT_ROOT_DIR="$(cd "${SITE_DIR}/.." && pwd)"
ROOT_DIR="$(cd "${QADAM_CORE_ROOT:-${DEFAULT_ROOT_DIR}}" && pwd)"
CREDENTIAL_ROOT="$(cd "${QADAM_CREDENTIAL_ROOT:-${ROOT_DIR}}" && pwd)"
LOCAL_VERCEL_ENV="${CREDENTIAL_ROOT}/data/runtime/vercel.env"
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
elif [[ -x "${CREDENTIAL_ROOT}/.venv/bin/python" ]]; then
  QADAM_PYTHON_BIN="${QADAM_PYTHON:-${CREDENTIAL_ROOT}/.venv/bin/python}"
fi

for qadam_env in "${CREDENTIAL_ROOT}/.env.local" "${CREDENTIAL_ROOT}/data/runtime/qadam-secrets.env"; do
  if [[ -f "${qadam_env}" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "${qadam_env}"
    set +a
    say "Loaded configured Qadam environment from ${qadam_env}"
  fi
done

if [[ -f "${LOCAL_VERCEL_ENV}" ]]; then
  # shellcheck disable=SC1090
  source "${LOCAL_VERCEL_ENV}"
  say "Loaded local Vercel credentials from ${LOCAL_VERCEL_ENV}"
else
  say "No local Vercel env file found at ${LOCAL_VERCEL_ENV}; expecting exported VERCEL_TOKEN"
fi

cd "${SITE_DIR}"

: "${VERCEL_TOKEN:?Set VERCEL_TOKEN before running this script.}"

if [[ -n "$(git status --porcelain --untracked-files=all)" ]]; then
  say "Dashboard repository is dirty; production deployment is blocked."
  exit 1
fi

dashboard_commit="$(git rev-parse HEAD)"
remote_main_commit="$(git ls-remote origin refs/heads/main | awk '{print $1}')"
if [[ -z "${remote_main_commit}" || "${dashboard_commit}" != "${remote_main_commit}" ]]; then
  say "Dashboard release commit ${dashboard_commit} is not the pushed origin/main commit ${remote_main_commit:-missing}."
  exit 1
fi

node "${SITE_DIR}/scripts/build-dashboard-release-manifest.js"
release_manifest="${SITE_DIR}/status/dashboard-release.json"
release_id="$(node -p "require('${release_manifest}').release_id")"
javascript_hash="$(node -p "require('${release_manifest}').javascript_sha256")"
css_hash="$(node -p "require('${release_manifest}').css_sha256")"
route_count="$(node -p "require('${release_manifest}').route_count")"
stage_count="$(node -p "require('${release_manifest}').stage_count")"

VERCEL_TEAM_ID="${VERCEL_TEAM_ID:-${VERCEL_ORG_ID:-team_Qv7iJDGRobHFyiyUsMUbVxyy}}"
PRODUCTION_DOMAINS=(
  "qadam.trade"
  "www.qadam.trade"
)

if [[ "${QADAM_SKIP_DEPLOY_PREFLIGHT:-0}" == "1" ]]; then
  say "Production preflight cannot be skipped for a dashboard integration release."
  exit 1
fi

say "Running mandatory production deployment preflight"
env \
  HOME="${QADAM_ORIGINAL_HOME}" \
  XDG_CACHE_HOME="${QADAM_ORIGINAL_XDG_CACHE_HOME}" \
  XDG_CONFIG_HOME="${QADAM_ORIGINAL_XDG_CONFIG_HOME}" \
  QADAM_PYTHON="${QADAM_PYTHON_BIN}" \
  QADAM_DASHBOARD_SITE_ROOT="${SITE_DIR}" \
  bash "${ROOT_DIR}/scripts/preflight_dashboard_deployment.sh"

if [[ -n "$(git status --porcelain --untracked-files=all)" ]] || [[ "$(git rev-parse HEAD)" != "${dashboard_commit}" ]]; then
  say "Dashboard repository changed during preflight; production deployment is blocked."
  exit 1
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
  --force \
  --yes \
  --env "QADAM_RELEASE_COMMIT=${dashboard_commit}" \
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

verify_alias() {
  local domain="$1"
  local attempt
  for attempt in $(seq 1 15); do
    if node "${SITE_DIR}/scripts/verify-dashboard-production-release.js" \
      --base-url "https://${domain}" \
      --expected-commit "${dashboard_commit}"; then
      say "Verified integrated dashboard release on ${domain}"
      return 0
    fi
    say "Waiting for ${domain} to serve release ${release_id} (${attempt}/15)"
    sleep 4
  done
  say "Production verification failed for ${domain}."
  return 1
}

for domain in "${PRODUCTION_DOMAINS[@]}"; do
  verify_alias "${domain}"
done

receipt_path="${ROOT_DIR}/data/runtime/dashboard-deployment-receipt.json"
mkdir -p "$(dirname "${receipt_path}")"
node - "${receipt_path}" "${deployment_url}" "${dashboard_commit}" "${release_manifest}" "${PRODUCTION_DOMAINS[@]}" <<'NODE'
const fs = require("node:fs");

const [receiptPath, deploymentUrl, deployedCommit, manifestPath, ...domains] = process.argv.slice(2);
const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf8"));
const receipt = {
  deployed_at: new Date().toISOString(),
  surface: "qadam.trade static dashboard",
  deployment_url: deploymentUrl,
  aliases: domains,
  verified_aliases: domains,
  deployed_commit: deployedCommit,
  release_id: manifest.release_id,
  javascript_asset: manifest.javascript_asset,
  javascript_sha256: manifest.javascript_sha256,
  css_asset: manifest.css_asset,
  css_sha256: manifest.css_sha256,
  route_count: manifest.route_count,
  canonical_stage_count: manifest.canonical_stage_count,
  stage_count: manifest.stage_count,
  lifecycle_check_result: manifest.lifecycle_check_result,
  preflight: "passed",
  boundary: "Receipt only. Contains no Vercel token, session cookie, broker credential, or dashboard secret."
};

fs.writeFileSync(receiptPath, `${JSON.stringify(receipt, null, 2)}\n`);
NODE

say "Production deployment: ${deployment_url}"
say "Aliased domains: ${PRODUCTION_DOMAINS[*]}"
say "Deployment receipt: ${receipt_path}"

if [[ "${QADAM_SKIP_CODEBASE_UPGRADE_NOTIFICATION:-0}" == "1" ]]; then
  say "Skipping codebase upgrade Telegram notification by explicit deploy setting"
else
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
      --summary "Qadam has been updated and the live dashboard is ready for review." \
      --deployment-url "${deployment_url}" \
        --alias "qadam.trade" \
        --alias "www.qadam.trade"
  ); then
    say "Codebase upgrade Telegram notification failed; deployment and aliases completed, but the team notification did not."
    exit 1
  fi
  say "Codebase upgrade Telegram notification completed"
fi
