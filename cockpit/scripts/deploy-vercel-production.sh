#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COCKPIT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${COCKPIT_DIR}"

if [[ -f ".env.local" ]]; then
  set -a
  # shellcheck disable=SC1091
  source ".env.local"
  set +a
fi

: "${VERCEL_TOKEN:?Set VERCEL_TOKEN before running this script.}"

VERCEL_TEAM_ID="${VERCEL_TEAM_ID:-team_Qv7iJDGRobHFyiyUsMUbVxyy}"
VERCEL_PROJECT_NAME="${VERCEL_PROJECT_NAME:-qadam}"
PRODUCTION_DOMAINS=(
  "qadam.trade"
  "www.qadam.trade"
)

deployment_env=()

add_env() {
  local name="$1"
  local value="${!name:-}"
  if [[ -n "${value}" ]]; then
    if [[ "${name}" == *"QADAM_ORCHESTRATOR_URL" && "${value}" =~ ^http://(localhost|127\.0\.0\.1)(:|/) ]]; then
      return
    fi
    deployment_env+=(--env "${name}=${value}" --build-env "${name}=${value}")
  fi
}

add_env "NEXT_PUBLIC_QADAM_ORCHESTRATOR_URL"
add_env "QADAM_ORCHESTRATOR_URL"
add_env "NEXT_PUBLIC_SUPABASE_URL"
add_env "NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY"
add_env "NEXT_PUBLIC_SUPABASE_ANON_KEY"
add_env "SUPABASE_SECRET_KEY"
add_env "QADAM_FOUNDING_MANAGER_ALLOWLIST"
add_env "QADAM_PENDING_FOUNDING_MANAGERS"

deploy_log="$(mktemp)"

npx --yes vercel@latest deploy \
  --prod \
  --yes \
  --scope "${VERCEL_TEAM_ID}" \
  --token "${VERCEL_TOKEN}" \
  "${deployment_env[@]}" 2>&1 | tee "${deploy_log}"

deployment_url="$(
  grep -Eo 'https://[^[:space:]]+\.vercel\.app' "${deploy_log}" | tail -n 1
)"

if [[ -z "${deployment_url}" ]]; then
  echo "Could not find the Vercel deployment URL in deploy output." >&2
  exit 1
fi

for domain in "${PRODUCTION_DOMAINS[@]}"; do
  npx --yes vercel@latest domains add "${domain}" "${VERCEL_PROJECT_NAME}" \
    --scope "${VERCEL_TEAM_ID}" \
    --token "${VERCEL_TOKEN}" \
    --force >/dev/null 2>&1 || true

  npx --yes vercel@latest alias set "${deployment_url}" "${domain}" \
    --scope "${VERCEL_TEAM_ID}" \
    --token "${VERCEL_TOKEN}"
done

echo "Production deployment: ${deployment_url}"
echo "Aliased domains: ${PRODUCTION_DOMAINS[*]}"
