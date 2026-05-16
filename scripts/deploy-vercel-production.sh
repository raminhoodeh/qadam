#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SITE_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${SITE_DIR}"

: "${VERCEL_TOKEN:?Set VERCEL_TOKEN before running this script.}"

VERCEL_TEAM_ID="${VERCEL_TEAM_ID:-team_Qv7iJDGRobHFyiyUsMUbVxyy}"
PRODUCTION_DOMAINS=(
  "qadam.trade"
  "www.qadam.trade"
)

deploy_log="$(mktemp)"

npx --yes vercel@latest deploy \
  --prod \
  --yes \
  --scope "${VERCEL_TEAM_ID}" \
  --token "${VERCEL_TOKEN}" 2>&1 | tee "${deploy_log}"

deployment_url="$(
  grep -Eo 'https://[^[:space:]]+\.vercel\.app' "${deploy_log}" | tail -n 1
)"

if [[ -z "${deployment_url}" ]]; then
  echo "Could not find the Vercel deployment URL in deploy output." >&2
  exit 1
fi

for domain in "${PRODUCTION_DOMAINS[@]}"; do
  npx --yes vercel@latest alias set "${deployment_url}" "${domain}" \
    --scope "${VERCEL_TEAM_ID}" \
    --token "${VERCEL_TOKEN}"
done

echo "Production deployment: ${deployment_url}"
echo "Aliased domains: ${PRODUCTION_DOMAINS[*]}"
