# Qadam Dashboard D11O - Deployment Discipline

Date: 2026-05-26

D11O tightens the release discipline around the simplified dashboard. It does
not deploy by itself. It makes the deploy path auditable so Qadam is only
described as live when the guarded deploy script has run the local preflight,
received a Vercel production URL, aliased the production domains, and written a
local deployment receipt.

## Scope

- Add a D11O deployment-discipline checker.
- Verify the deploy script runs `scripts/preflight_dashboard_deployment.sh`
  before attempting production deployment unless an explicit skip flag is set.
- Verify the deploy script fails closed when deployment URL extraction or domain
  aliasing fails.
- Verify the deploy receipt is written only after successful deployment and
  aliasing, and that it cannot contain tokens, cookies, broker credentials, or
  dashboard secrets.
- Verify the deployment preflight now includes D11N guide alignment and D11O
  deployment discipline.
- Keep production deployment separate from local readiness checks.

## Acceptance

- `scripts/check_dashboard_d11o_deployment_discipline.js` exists and passes.
- `scripts/preflight_dashboard_deployment.sh` runs the D11O checker.
- `scripts/check_dashboard_acceptance.js` treats the D11O checker as an
  acceptance dependency.
- `scripts/check_dashboard_deployment_readiness.js` knows the D11O contract
  files exist.
- The master dashboard overhaul plan records D11O as complete and moves the
  deferred performance cleanup to D11P.

## Authority Boundary

D11O changes deployment checks and documentation only. It does not call Vercel,
change aliases, modify provider calls, change broker routes, enable Telegram
commands, change paper-trading permissions, grant proof credit, write learning
state, or enable live capital.
