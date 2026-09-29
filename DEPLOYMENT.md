# Production Deployment

Run `bash scripts/deploy-vercel-production.sh` from a clean, reviewed dashboard
worktree whose HEAD is pushed to `origin/main`. Set `QADAM_CORE_ROOT` to the
matching core checkout and `QADAM_CREDENTIAL_ROOT` to the configured local root
when deploying from isolated worktrees. Never commit runtime credentials.

## Author Identity

This manual release workflow is owner-operated. Its commit author email must
match the authenticated Vercel account's primary email. Configure `user.name`
and `user.email` in this dashboard repository, not just its parent core
repository. Git configuration does not inherit across nested repositories.
Check `git show -s --format='%an <%ae>' HEAD` before release. Fix a missing local
identity and create a new reviewed commit; do not amend published history or
override deployment author metadata to defeat Vercel's access checks.

## Release Gates

The script runs deployment-guard tests and a read-only account check before
the mandatory production preflight. It creates a production deployment with
`--no-wait --skip-domain`, so a failed candidate does not replace the working
production aliases. The CLI command has a five-minute bound. Vercel API
readiness has a fifteen-minute bound and twenty-second request timeouts.

`BLOCKED`, access-related seat blocks, `ERROR`, `CANCELED`, unknown states,
missing or conflicting commit metadata, wrong project/target, and API failures
stop promotion. Only an exact `READY` candidate may be aliased. Both public
domains must then pass route, asset, lifecycle and commit verification before a
successful deployment receipt is written.

A timeout is not proof that Vercel canceled the remote deployment. Inspect the
returned deployment URL before retrying. If a Git integration deployment is
already serving the reviewed commit, verify it rather than blindly forcing a
second build. This workflow does not change team permissions or subscription
tiers. Collaborator-operated releases need their own reviewed identity policy;
do not impersonate the owner.

Regression tests: `node --test scripts/test-vercel-deployment-guard.js`.
