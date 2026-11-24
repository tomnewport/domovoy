# Deploying to Google Cloud (Cloud Run + Firebase Hosting + Neon)

This deployment runs **in parallel** with the VPS deployment
([`README.md#deployment`](../README.md#deployment)) until the cutover below.
There are two environments:

| GitHub Environment | Branch | Cloud Run service | Firebase Hosting site | Neon branch |
| --- | --- | --- | --- | --- |
| `gcp-dev` | `dev` | `domovoy-dev` | `domovoy-tdnsh-dev.web.app` | `dev` |
| `gcp-prod` | `main` | `domovoy-prod` | `domovoy-tdnsh.web.app` | `main` |

GCP project `domovoy-tdnsh` (number `429045293034`), region `europe-west2`
(London). The site names are the defaults in
[`deploy/gcp/bootstrap.sh`](../deploy/gcp/bootstrap.sh). Firebase site IDs are
global, so if one is taken, pass `--prod-site` / `--dev-site`.

## Architecture

```
browser ──https──▶ Firebase Hosting (<site>.web.app, CDN)
                    ├─ /assets/**, /index.html, SPA fallback ── domovoy_app/dist
                    └─ /api, /api/**, /api-static/**, /krimba, /krimba/**
                          │ rewrite (same origin for the browser)
                          ▼
                   Cloud Run service domovoy-<env>   (scale 0..2, uvicorn on $PORT)
                          │ pooled URL (-pooler, PgBouncer)
                          ▼
                   Neon Postgres, AWS eu-west-2, branch main|dev
                          ▲ direct URL
                   Cloud Run job domovoy-<env>-migrate (same image, `manage.py migrate`)
```

- **Image**: one build per push, pushed to
  `europe-west2-docker.pkg.dev/domovoy-tdnsh/domovoy/domovoy-<env>:<git sha>`.
  CI deploys the image **digest**, not the tag. A cleanup policy
  ([`ar-cleanup-policy.json`](../deploy/gcp/ar-cleanup-policy.json)) keeps the
  10 newest images per environment and deletes anything else older than 30 days.
- **Secrets** live in Secret Manager. Each environment has four:
  `domovoy-<env>-secret-key`, `-smtp-password`, `-database-url` (pooled) and
  `-database-url-direct` (migrate job only). They are mounted as env vars with
  `--set-secrets`. Only that environment's runtime service account can read them.
  GitHub holds **no secrets** for this path.
- **Non-secret config** comes from GitHub Environment variables (see below).
  CI also sets `domovoy_session_cookie_name=__session` and
  `domovoy_csrf_use_sessions=true`, which apply only on GCP (see "Firebase
  quirks").
- **CI → GCP auth** uses Workload Identity Federation. There are no keys. The
  provider accepts only tokens whose `repository_id` is `862461320`, whose
  `repository_owner_id` is `8523691`, and whose ref is `refs/heads/main` or
  `refs/heads/dev`. Each environment has its own deployer, and only its own
  branch can impersonate it:

  | Service account | Roles (scope) |
  | --- | --- |
  | `domovoy-<env>-run` (runtime) | `secretmanager.secretAccessor` on its 4 secrets only |
  | `domovoy-<env>-deploy` (CI) | `run.developer` on its service and migrate job; `iam.serviceAccountUser` on its runtime SA; `artifactregistry.writer` on the `domovoy` repo; `firebasehosting.admin` and `serviceusage.serviceUsageConsumer` on the project (no narrower scope exists) |

  The deployer cannot change who may invoke the service. The bootstrap script
  makes the service public (`allUsers` → `run.invoker`) once, because Firebase
  Hosting calls it anonymously.

### CI flow (`.github/workflows/ci.yml`, job `deploy-gcp`)

The job runs on push to `main`/`dev`, after `checks` passes, and only when the
repository variable `GCP_DEPLOY_ENABLED` is `true`. Its concurrency group
(`gcp-<branch>`) has no cancel-in-progress. It:

1. authenticates with WIF (with `gcloud` itself, no third-party action);
2. builds and pushes the image, then resolves its digest;
3. updates the `domovoy-<env>-migrate` job to that digest and runs it with
   `--wait`, which fails the deploy if migrations fail;
4. deploys the Cloud Run service at that digest;
5. builds the SPA and deploys the Firebase Hosting target `gcp-<env>`.

## One-time setup (in this order)

You need `gcloud` (logged in as project owner), Node + `firebase-tools`
(`npm i -g firebase-tools && firebase login`), and optionally `gh`. The script
uses `gh` to double-check the repository IDs.

### 1. Neon

1. Create a Neon project in **AWS eu-west-2 (London)**, with database
   `domovoy`. Its default branch is `main` (prod).
2. Create a branch `dev` from `main`.
3. For **each** branch, copy two connection strings from *Connect*:
   - **pooled**: "Connection pooling" on, so the host contains `-pooler`. This
     becomes `domovoy-<env>-database-url`.
   - **direct**: pooling off. This becomes `domovoy-<env>-database-url-direct`.

   Both strings must include `sslmode=require`. See [DATABASE.md](DATABASE.md).

### 2. Bootstrap script

```sh
deploy/gcp/bootstrap.sh            # defaults: --project domovoy-tdnsh --region europe-west2 --repo tomnewport/domovoy
```

The script is idempotent. It enables the APIs, then creates the Artifact
Registry repo with its cleanup policy, the WIF pool and provider, the service
accounts and IAM bindings, and the empty secrets. It also creates **placeholder**
Cloud Run services and jobs (Google's hello image), so IAM can be scoped to them.
Re-running it never replaces a deployed image. If `firebase` is on your PATH,
the script also adds Firebase to the project and creates both Hosting sites.
Otherwise it prints the `firebase` commands to run, and you re-run the script
afterwards.

At the end it prints the exact secret commands and GitHub variables for steps
3 and 4.

### 3. Secret values

The commands below read each value without echoing it, so it never lands in
shell history (they work in bash and zsh). Paste each Neon URL when prompted:

```sh
for env in dev prod; do
  python3 -c 'import secrets; print(secrets.token_urlsafe(50), end="")' \
    | gcloud secrets versions add "domovoy-$env-secret-key" --project=domovoy-tdnsh --data-file=-
  for s in smtp-password database-url database-url-direct; do
    printf '%s for %s: ' "$s" "$env"; read -rs v; echo
    printf '%s' "$v" | gcloud secrets versions add "domovoy-$env-$s" --project=domovoy-tdnsh --data-file=-
    unset v
  done
done
```

- Add the Django secret key **once**. A new version invalidates sessions and
  hashcash nonces on the next deploy.
- SMTP isn't used yet (see `utils/email.py`), but the setting is required, so
  any placeholder works for the SMTP password.
- To rotate a secret, add a version and redeploy (re-run the workflow). Services
  read `:latest` when a revision starts.

### 4. GitHub Environment variables

In *Settings → Environments*, create `gcp-dev` and `gcp-prod`. Then add these as
**variables**, not secrets, with the values the script printed:

| Variable | Example (`gcp-dev`) |
| --- | --- |
| `GCP_PROJECT_ID` | `domovoy-tdnsh` |
| `GCP_REGION` | `europe-west2` |
| `GCP_WIF_PROVIDER` | `projects/429045293034/locations/global/workloadIdentityPools/github/providers/domovoy` |
| `GCP_DEPLOYER_SA` | `domovoy-dev-deploy@domovoy-tdnsh.iam.gserviceaccount.com` |
| `GCP_RUNTIME_SA` | `domovoy-dev-run@domovoy-tdnsh.iam.gserviceaccount.com` |
| `GCP_IMAGE` | `europe-west2-docker.pkg.dev/domovoy-tdnsh/domovoy/domovoy-dev` |
| `CLOUD_RUN_SERVICE` | `domovoy-dev` |
| `FIREBASE_SITE` | `domovoy-tdnsh-dev` |
| `DOMOVOY_ALLOWED_HOSTS` | `["domovoy-dev-<hash>-nw.a.run.app","domovoy-dev-429045293034.europe-west2.run.app","domovoy-tdnsh-dev.web.app","domovoy-tdnsh-dev.firebaseapp.com"]` |
| `DOMOVOY_CSRF_TRUSTED_ORIGINS` | `["https://domovoy-tdnsh-dev.web.app","https://domovoy-tdnsh-dev.firebaseapp.com"]` |
| `DOMOVOY_FRONTEND_ROOT` | `https://domovoy-tdnsh-dev.web.app/` (trailing slash; used in login links) |
| `DOMOVOY_SMTP_SERVER`, `DOMOVOY_SMTP_PORT`, `DOMOVOY_SMTP_USERNAME` | your SMTP settings (placeholders are fine for now) |

Recommended: under each environment's *Deployment branches*, allow only `main`
(`gcp-prod`) and only `dev` (`gcp-dev`). GCP already enforces this through WIF;
the branch rule makes the GitHub side match.

Finally, add the **repository** variable `GCP_DEPLOY_ENABLED=true` (*Settings →
Secrets and variables → Actions → Variables*). Until you do, the `deploy-gcp`
job is skipped, so merging this PR before bootstrap leaves CI green.

### 5. First deploy

1. Push to `dev`, or re-run the latest `dev` workflow run. Watch `deploy-gcp`.
2. Check the environment (see "Verifying after a deploy").
3. Either seed dev with a copy of the data (below), or create an admin user
   with the **direct** URL. Run this from `domovoy/`, with the other required
   `domovoy_*` variables set to anything:
   `domovoy_database_url='<dev direct url>' poetry run python manage.py createsuperuser`.
4. Repeat for `main` → `gcp-prod` when ready. Keep prod's database **empty
   apart from migrations** until the cutover (no test users), so the cutover
   load is clean. Smoke-test prod with the `curl` checks below.

## Verifying after a deploy

Most Firebase behaviour can only be confirmed against a real deploy:

```sh
SITE=https://domovoy-tdnsh-dev.web.app
curl -sI "$SITE/" | grep -i cache-control                 # no-cache (index.html)
curl -sI "$SITE/api/openapi.json" | grep -iE '^HTTP|cache-control|x-cache'
# expect 200 and "no-store, ... private"; repeat it: x-cache should never be HIT
curl -s -o /dev/null -w '%{http_code}\n' "$SITE/api/users/v1/session"   # 401 (not 400/404)
```

- **400 Bad Request** from `/api/...` means `DOMOVOY_ALLOWED_HOSTS` doesn't
  include the `Host` that Firebase sends. With `DEBUG` off, Django doesn't log
  this.
- Log in to the SPA with an email link (see below).
- Log in to the admin at `$SITE/krimba/`. A 403 "CSRF verification failed"
  means the Origin isn't in `DOMOVOY_CSRF_TRUSTED_ORIGINS`, or the
  `__session` settings aren't applied.

## Finding login links (Cloud Logging)

Login links are printed to stdout (`utils/email.py`). On Cloud Run, stdout goes
to Cloud Logging. Each printed line is its own log entry, so query for the link
line:

```sh
gcloud logging read \
  'resource.type="cloud_run_revision" AND resource.labels.service_name="domovoy-dev" AND textPayload:"auth_link"' \
  --project=domovoy-tdnsh --freshness=1h --limit=5 --format='value(timestamp,textPayload)'
```

In the console, use *Logging → Logs Explorer* with the same filter, or open
*Cloud Run → domovoy-dev → Logs* and search `auth_link`. Anyone with log access
to the project can read these links, which are live credentials until used or
expired.

## Seeding gcp-dev with a trial copy of the data

You run this yourself; CI never touches data. Follow
[DATABASE.md → Moving existing data](DATABASE.md#moving-existing-data-from-sqlite-to-postgres),
but you don't need to stop the VPS for a trial:

1. Copy the prod SQLite file from the VPS
   (`/opt/applications/domovoy/main/data/db.sqlite3`) into
   `domovoy/data/db.sqlite3` of a checkout at the commit prod runs.
2. Dump it (`dumpdata`, as in DATABASE.md), and run the length check.
3. Load it into the **dev** branch with the **dev direct** URL (DATABASE.md
   step 4). The `migrate` there is a no-op if a deploy already ran it. Load
   before you create any users on dev. If you already created some, reset the
   branch first (*Neon → Branches → dev → Reset from parent* while `main` is
   still empty), then re-run the `dev` workflow so the migrate job recreates
   the schema.
4. Verify the row counts, then log in at the dev site. Session keys live in
   each browser's localStorage per origin, so expect to log in again.

The trial copy holds real household data, so treat the dev site accordingly.

## Cutover runbook (VPS → GCP)

Prerequisite: both GCP environments have been tested. Do this in a quiet window,
because the app is read-only/offline for the duration.

**A day before**

1. Lower the TTL of the `domovoy` and `dom-dev` records at DigitalOcean to 300s.
2. Add the custom domains in *Firebase console → Hosting → (site) → Add custom
   domain*: `domovoy.tdn.sh` on the prod site, `dom-dev.tdn.sh` on the dev site.
   Firebase then shows the exact records to create. Add **only** these at
   DigitalOcean (*Networking → Domains → tdn.sh*), and leave every other
   record as it is:
   - the ownership **TXT** record Firebase shows (on `domovoy` / `dom-dev`),
     and
   - the `_acme-challenge.domovoy` / `_acme-challenge.dom-dev` record it shows
     for the certificate, if offered.

   Don't change the existing A/AAAA records yet. Use Firebase's values, not
   examples from these docs.
3. Add the custom origin to the GitHub variables and redeploy (re-run the
   workflow):
   - `DOMOVOY_CSRF_TRUSTED_ORIGINS` += `"https://domovoy.tdn.sh"` (prod) /
     `"https://dom-dev.tdn.sh"` (dev)
   - `DOMOVOY_ALLOWED_HOSTS` += `"domovoy.tdn.sh"` / `"dom-dev.tdn.sh"`
   - leave `DOMOVOY_FRONTEND_ROOT` on web.app until the switch.

**Cutover (prod)**

1. **Freeze the VPS.** Don't merge to `main` during the window, because the
   VPS deploy job would restart the container. On the VPS, run
   `cd /opt/applications/domovoy/main && docker-compose stop`.
2. **Fresh dump** of `/opt/applications/domovoy/main/data/db.sqlite3`, as in
   DATABASE.md steps 1–3.
3. **Load into Neon `main`** with the **prod direct** URL (DATABASE.md step 4).
   The database must hold only the schema created by the migrate job. If you
   created anything there while testing, restore the branch to a point before
   that (*Neon → Branches → main → Restore*).
4. **Verify** the row counts (DATABASE.md step 5), then log in at
   `https://domovoy-tdnsh.web.app` and check the job list and stats.
5. **Switch DNS** at DigitalOcean. Replace the existing `domovoy` A record
   (and any AAAA record) that points at the VPS with the record(s) Firebase
   shows for `domovoy.tdn.sh`. Keep the old VPS IP written down for rollback.
6. Wait until Firebase shows the domain as *Connected* and serves a valid
   certificate:
   `curl -sI https://domovoy.tdn.sh/ | head -1`.
7. Set `DOMOVOY_FRONTEND_ROOT=https://domovoy.tdn.sh/` on `gcp-prod` and
   redeploy, so new login links use the custom domain.
8. Repeat steps 5–7 for `dom-dev.tdn.sh` / `gcp-dev`. There's no data to move
   unless you want it.

**After the cutover**, open a follow-up PR that removes the VPS jobs
(`build-frontend`, `build-api`), the `deploy/docker-compose.yml` and
`deploy/site.conf` templates, and the `SSH_*`, `DOCKERHUB_*` and
`ENV_BACKEND_*` GitHub secrets. Until then, every push to `main` also restarts
the VPS container. That is harmless, because no DNS points at it, but it is
wasted work. Keep the VPS SQLite file and the dump until GCP has run for a
while.

## Rollback

- **Before DNS changes**, there is nothing to roll back. Restart the VPS
  container (`docker-compose start`).
- **After the DNS switch**, point the `domovoy` A record back at the old VPS IP
  and start the VPS container. Any writes made on GCP since the cutover exist
  only in Neon. Either accept losing them, or dump them from Neon (`dumpdata`
  against the direct URL) and reconcile them by hand. The low TTL makes the
  switch back take effect within minutes.
- **A bad app deploy on GCP**: in *Cloud Run → service → Revisions*, route 100%
  of traffic to the previous revision, or redeploy an earlier image with
  `gcloud run deploy domovoy-prod --region=europe-west2 --image=<earlier digest>`.
  The previous 10 images are retained. Migrations don't roll back automatically.
- **Neon**: restore a branch to an earlier point in time within your plan's
  history window (*Branches → Restore*).

## Costs and guardrails

All of this should fit in free tiers at household scale. These are as of
writing, so check current pricing:

- **Cloud Run**: request-based billing with a monthly free allowance
  (vCPU-seconds, GiB-seconds, 2M requests). Guardrails: `--min-instances=0`
  (scale to zero), `--max-instances=2`, `--timeout=60s`, 1 vCPU / 512 MiB.
  The cost of scale-to-zero is a cold start of a few seconds on the first
  request.
- **Artifact Registry**: 0.5 GB free; the cleanup policy keeps it small.
- **Secret Manager**: 8 secrets at a few cents per active version per month,
  beyond a small free allowance. Old versions also count while enabled, so
  disable or destroy superseded ones after rotating.
- **Firebase Hosting**: free storage and transfer quotas are well above this
  app's needs.
- **Cloud Logging**: the free ingestion allowance far exceeds this app's logs.
- **Neon**: free plan, with compute that suspends when idle. Check the
  storage limit and the point-in-time-restore window of your plan.

**Set a budget alert.** Alerts notify you, but they do **not** cap spend:

```sh
gcloud billing accounts list                     # find BILLING_ACCOUNT_ID
gcloud services enable billingbudgets.googleapis.com --project=domovoy-tdnsh
gcloud billing budgets create --billing-account=BILLING_ACCOUNT_ID \
  --display-name="domovoy monthly" --budget-amount=5GBP \
  --filter-projects=projects/domovoy-tdnsh \
  --threshold-rule=percent=0.5 --threshold-rule=percent=0.9 --threshold-rule=percent=1.0
```

Or use *Billing → Budgets & alerts* in the console. Alerts go to billing-account
admins by email.

## Firebase quirks this setup handles

- **Firebase forwards only the `__session` cookie to Cloud Run.** It strips
  every other cookie. The SPA is unaffected because it authenticates with the
  `x-session-key` header. The Django admin needs cookies, so on GCP:
  - `SESSION_COOKIE_NAME` is `__session`;
  - `CSRF_USE_SESSIONS = True` keeps the CSRF token in the session rather than
    a `csrftoken` cookie;
  - admin flash messages use session storage too.

  These come from `domovoy_session_cookie_name` / `domovoy_csrf_use_sessions`.
  The defaults (`sessionid` / `False`) leave the VPS unchanged.
- **Host vs Origin.** Behind the rewrite, `Host` is expected to be the run.app
  hostname, with the browser's `Origin` being the web.app or custom domain.
  `DOMOVOY_ALLOWED_HOSTS` lists both run.app forms plus the Firebase hostnames,
  and `DOMOVOY_CSRF_TRUSTED_ORIGINS` lists the public origins.
  `USE_X_FORWARDED_HOST` stays off: the run.app URL is publicly reachable, so
  trusting `X-Forwarded-Host` would let anyone choose the host Django sees.
- **CDN caching.** Firebase's CDN may cache rewritten responses that ask to be
  cached. Its cache key doesn't include the `x-session-key` header. Django
  therefore adds `Cache-Control: max-age=0, no-cache, no-store,
  must-revalidate, private` to every response that doesn't set its own
  (`domovoy/middleware.py`). WhiteNoise's static files keep their long-lived
  headers.
- **Path coverage.** The rewrites list both `/api` and `/api/**` (and likewise
  `/krimba`), because `/x/**` doesn't match `/x` itself.
