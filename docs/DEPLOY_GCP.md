# Deploying to Google Cloud (Cloud Run + Firebase Hosting + Neon)

This is Domovoy's deployment. It replaced a single VPS on 2026-11-25 (see
"Cutover from the VPS"). There are two environments:

| Environment | Deployed from | Domain | Variable prefix | Cloud Run service | Firebase Hosting site | Neon branch |
| --- | --- | --- | --- | --- | --- | --- |
| prod | every push to `main` | `domovoy.tdn.sh` | `GCP_PROD_` | `domovoy-prod` | `domovoy-tdnsh.web.app` | `production` |
| dev | `main` after each prod deploy, or any branch on demand ("Run workflow") | `dom-dev.tdn.sh` | `GCP_DEV_` | `domovoy-dev` | `domovoy-tdnsh-dev.web.app` | `dev` |

There is no `dev` git branch. Dev is a scratch environment: after every prod
deploy its database is reset to a copy of prod's and `main` is deployed to it,
and between merges you can deploy any branch to it to try that branch out
(see "Deploying a branch to dev").

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
                   Neon Postgres, AWS eu-west-2, branch production|dev
                          ▲ direct URL
                   Cloud Run job domovoy-<env>-migrate (same image, `manage.py migrate`)
```

- **Image**: one build per push, pushed to
  `europe-west2-docker.pkg.dev/domovoy-tdnsh/domovoy/domovoy-<env>:<git sha>`.
  CI deploys the image **digest**, not the tag. A cleanup policy
  ([`ar-cleanup-policy.json`](../deploy/gcp/ar-cleanup-policy.json)) keeps the
  10 newest images per environment and deletes anything else older than 30 days.
- **Secrets** live in Secret Manager. Each environment has five:
  `domovoy-<env>-secret-key`, `-secret-key-fallbacks` (a JSON list of old
  keys, service only), `-smtp-password`, `-database-url` (pooled) and
  `-database-url-direct` (migrate job only). They are mounted as env vars with
  `--set-secrets`. Only that environment's runtime service account can read them.
  GitHub holds **no secrets** for this path.
- **Non-secret config** comes from repository-level GitHub Actions variables:
  shared `GCP_*` ones, plus `GCP_DEV_*` / `GCP_PROD_*`, chosen by the
  environment being deployed (see below), and `NEON_PROJECT_ID`. GitHub
  Environments are **not** used, because a private repository on GitHub Free
  may not have them. The restrictions they would add are enforced in GCP
  instead, by the WIF condition and per-environment deployer bindings. A
  `concurrency` group per environment (`gcp-prod`, `gcp-dev`) serialises
  deploys.
  CI also sets `domovoy_session_cookie_name=__session` and
  `domovoy_csrf_use_sessions=true`, which apply only on GCP (see "Firebase
  quirks").
- **CI → GCP auth** uses Workload Identity Federation. There are no keys.
  - The pool `domovoy-github` is used only for this repository.
  - Its provider accepts only tokens whose `repository_id` is `862461320` and
    whose `repository_owner_id` is `8523691`, from either a run on
    `refs/heads/main` or a manual "Run workflow" (`event_name ==
    'workflow_dispatch'`, which only people with write access can start).
    Pull requests, including from forks, can't get a token.
  - Each environment has its own deployer, with its own
    `workloadIdentityUser` binding:
    - prod: `principalSet://…/workloadIdentityPools/domovoy-github/attribute.repo_ref/862461320/refs/heads/main`,
      where `repo_ref` is mapped as `assertion.repository_id + '/' + assertion.ref`.
      Only this repo's `main` can act as the prod deployer.
    - dev: `principalSet://…/workloadIdentityPools/domovoy-github/attribute.repository_id/862461320`,
      so any run the provider admits from this repo: `main`, or a manual run
      on any branch.
  - A manual run uses the chosen branch's own copy of the workflow, so a
    branch can change what runs with the dev deployer. That is the point of
    deploying a branch to dev; it is limited by who can push branches and
    start runs (people with write access), and the dev deployer can't reach
    prod's service, secrets or database.

  | Service account | Roles (scope) |
  | --- | --- |
  | `domovoy-<env>-run` (runtime) | `secretmanager.secretAccessor` on its 5 secrets only |
  | `domovoy-<env>-deploy` (CI) | `run.developer` on its service and migrate job; `iam.serviceAccountUser` on its runtime SA; `artifactregistry.writer` on the `domovoy` repo; `firebasehosting.admin` and `serviceusage.serviceUsageConsumer` on the project (no narrower scope exists) |
| `domovoy-prod-deploy` only | `secretmanager.secretAccessor` on `domovoy-neon-api-key`, to reset dev's database |

  The deployer cannot change who may invoke the service. The bootstrap script
  makes the service public (`allUsers` → `run.invoker`) once, because Firebase
  Hosting calls it anonymously.

  `firebasehosting.admin` can only be granted project-wide, so the dev deployer
  could technically deploy the prod Hosting site. This is accepted: both
  deployers can only be reached from this repository's `main` or a manual run
  by someone with write access, and the prod API, secrets and database stay
  out of the dev deployer's reach.

### CI flow (`.github/workflows/ci.yml` and `deploy-gcp.yml`)

Deploy jobs only run when the repository variable `GCP_DEPLOY_ENABLED` is
`true` (set it to anything else to pause deploys), and only after `checks` and
`tests-postgres` pass.

| Trigger | Jobs, in order |
| --- | --- |
| Push to `main` (a merged PR) | **Deploy prod** → **Reset dev database from prod** → **Deploy dev** (from `main`) |
| *Actions → Build and Deploy → Run workflow* on any branch | **Deploy dev** from that branch (database left as it is) |
| Pull request | checks only |

Each deploy (the reusable workflow `deploy-gcp.yml`, called with
`environment: prod` or `dev`):

1. selects the `GCP_PROD_*` or `GCP_DEV_*` variables, and fails if any is
   missing;
2. authenticates with WIF (with `gcloud` itself, no third-party action);
3. builds and pushes the image, then resolves its digest;
4. updates the `domovoy-<env>-migrate` job to that digest and runs it with
   `--wait`, which fails the deploy if migrations fail;
5. deploys the Cloud Run service at that digest;
6. builds the SPA and deploys the Firebase Hosting target `gcp-<env>`.

The database reset
([`deploy/gcp/reset-dev-database.py`](../deploy/gcp/reset-dev-database.py))
runs as the prod deployer, reads the Neon API key from Secret Manager, and
resets Neon's `dev` branch to the head of its parent `production` (Neon's
"reset from parent"). It refuses to touch a branch that is the project's
default, is protected, or isn't a child of `production`. Dev deploys and the
reset share the `gcp-dev` concurrency group, so they never overlap. If prod's
deploy fails, the reset and the dev deploy are skipped.

## One-time setup (in this order)

The script runs with macOS's stock bash 3.2 as well as newer versions. You
need `gcloud` (logged in as project owner), Node + `firebase-tools`
(`npm i -g firebase-tools && firebase login`), and optionally `gh`. The script
uses `gh` to double-check the repository IDs.

### 1. Neon

Reuse the existing Neon project `tdnsh` (it may be renamed `domovoy`), which
is on the free plan in **AWS Europe West 2 (London)**:

1. On the default branch **`production`** (prod), create the role `domovoy` and
   the database `domovoy` owned by it.
2. Create a child branch `dev` from `production`. It inherits the role and
   database. Leave it unprotected and don't give it children: CI resets it
   from `production` after every prod deploy, and refuses to if either is
   true.
3. For **each** branch, copy two connection strings for role `domovoy` and
   database `domovoy` from *Connect*:
   - **pooled**: "Connection pooling" on, so the host contains `-pooler`. This
     becomes `domovoy-<env>-database-url`.
   - **direct**: pooling off. This becomes `domovoy-<env>-database-url-direct`.

   Both strings must include `sslmode=require`. See [DATABASE.md](DATABASE.md).
4. Create a Neon **API key** for CI's dev reset (*Account settings → API keys*,
   or a project-scoped key for this project if your account offers one; a
   personal key can manage every project in the account). It goes into Secret
   Manager in step 3, not GitHub. Note the **project ID** from the project's
   *Settings* page for step 4.

The free plan suspends idle compute and **archives idle branches**. The first
query after that wakes or unarchives the branch, which adds a few seconds of
latency. A slow first request on dev, on top of the Cloud Run cold start, is
most likely this and not a bug.

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
  printf '[]' | gcloud secrets versions add "domovoy-$env-secret-key-fallbacks" --project=domovoy-tdnsh --data-file=-
done
```

- Add the Django secret key **once**. A new version invalidates sessions and
  hashcash nonces on the next deploy, unless the old key goes into
  `-secret-key-fallbacks` (a JSON list; see `security/session_key.py`).
- `-secret-key-fallbacks` starts as `[]` and stays that way unless you rotate
  the key and want sessions to survive. Empty it again (and destroy the old
  version) a few weeks later.
- Setups bootstrapped before `-secret-key-fallbacks` existed: re-run
  `bootstrap.sh` (it creates the secret and its IAM binding), then add `[]`
  for both environments with the `printf` line above, **before** deploying a
  commit whose CI mounts it.
- SMTP isn't used yet (see `utils/email.py`), but the setting is required, so
  any placeholder works for the SMTP password.
- To rotate a secret, add a version and redeploy (re-run the workflow). Services
  read `:latest` when a revision starts.
- The Neon API key goes into `domovoy-neon-api-key` the same way (the script
  prints the command). Only the prod deployer can read it.

### 4. GitHub repository variables

Add these in *Settings → Secrets and variables → Actions → **Variables** → New
repository variable*. They are variables, not secrets, and no GitHub
Environments are needed. The script prints the exact values. Each deploy
picks `GCP_PROD_*` or `GCP_DEV_*` for the environment it's deploying, and fails
early if any is missing (it never falls back to the other set).

| Variable | Example |
| --- | --- |
| `GCP_PROJECT_ID` | `domovoy-tdnsh` |
| `GCP_REGION` | `europe-west2` |
| `GCP_WIF_PROVIDER` | `projects/429045293034/locations/global/workloadIdentityPools/domovoy-github/providers/domovoy` |
| `GCP_SMTP_SERVER`, `GCP_SMTP_PORT`, `GCP_SMTP_USERNAME` | your SMTP settings, shared by both environments (placeholders are fine for now) |
| `NEON_PROJECT_ID` | the Neon project's ID (*Settings* page), used to reset dev's database |
| `GCP_DEV_DEPLOYER_SA` | `domovoy-dev-deploy@domovoy-tdnsh.iam.gserviceaccount.com` |
| `GCP_DEV_RUNTIME_SA` | `domovoy-dev-run@domovoy-tdnsh.iam.gserviceaccount.com` |
| `GCP_DEV_IMAGE` | `europe-west2-docker.pkg.dev/domovoy-tdnsh/domovoy/domovoy-dev` |
| `GCP_DEV_SERVICE` | `domovoy-dev` |
| `GCP_DEV_FIREBASE_SITE` | `domovoy-tdnsh-dev` |
| `GCP_DEV_ALLOWED_HOSTS` | `["domovoy-dev-<hash>-nw.a.run.app","domovoy-dev-429045293034.europe-west2.run.app","domovoy-tdnsh-dev.web.app","domovoy-tdnsh-dev.firebaseapp.com"]` |
| `GCP_DEV_CSRF_TRUSTED_ORIGINS` | `["https://domovoy-tdnsh-dev.web.app","https://domovoy-tdnsh-dev.firebaseapp.com"]` |
| `GCP_DEV_FRONTEND_ROOT` | `https://domovoy-tdnsh-dev.web.app/` (trailing slash; used in login links) |
| `GCP_PROD_*` | the same eight, for `domovoy-prod` / site `domovoy-tdnsh` |

Finally, add the **repository** variable `GCP_DEPLOY_ENABLED=true` (*Settings →
Secrets and variables → Actions → Variables*). Until you do, the deploy jobs
are skipped.

### 5. First deploy

1. Deploy a branch to dev with *Run workflow* (see "Deploying a branch to
   dev") and check the dev site (see "Verifying after a deploy").
2. Merge to `main`. That deploys prod, resets dev's database from prod and
   deploys `main` to dev. Smoke-test both with the `curl` checks below.

## Verifying after a deploy

Most Firebase behaviour can only be confirmed against a real deploy:

```sh
SITE=https://domovoy-tdnsh-dev.web.app
curl -sI "$SITE/" | grep -i cache-control                 # no-cache (SPA fallback)
curl -sI "$SITE/homes/1" | grep -i cache-control          # no-cache (deep link)
curl -sI "$SITE/api/openapi.json" | grep -iE '^HTTP|cache-control|x-cache'
# expect 200 and "no-store, ... private"; repeat it: x-cache should never be HIT
curl -s -o /dev/null -w '%{http_code}\n' "$SITE/api/users/v1/session"   # 401 (not 400/404)
curl -sI "$SITE/krimba/login/" | grep -i cache-control    # no-store, ... private
css=$(curl -s "$SITE/krimba/login/" | grep -oE '/api-static/[^"]+\.css' | head -1)
curl -sI "$SITE$css" | grep -i cache-control              # max-age=315360000, immutable
```

To try a `firebase.json` change before merging, deploy it to a temporary
preview channel of the dev site. The channel uses the same Cloud Run service.
From the repo root, with `domovoy_app/dist` built:

```sh
firebase target:apply hosting gcp-dev domovoy-tdnsh-dev --project=domovoy-tdnsh
firebase hosting:channel:deploy headers-test --only gcp-dev --expires 1h --project=domovoy-tdnsh
```

Run the checks above with `SITE` set to the channel URL it prints. Then delete
the `.firebaserc` and `.firebase/` these commands create; CI applies the target
itself.

- **400 Bad Request** from `/api/...` means `GCP_<ENV>_ALLOWED_HOSTS` doesn't
  include the `Host` that Firebase sends. With `DEBUG` off, Django doesn't log
  this.
- Log in to the SPA with an email link (see below).
- Log in to the admin at `$SITE/krimba/`. A 403 "CSRF verification failed"
  means the Origin isn't in `GCP_<ENV>_CSRF_TRUSTED_ORIGINS`, or the
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

## Deploying a branch to dev

To try a branch on `dom-dev.tdn.sh` before merging it: *Actions → Build and
Deploy → Run workflow*, choose the branch, and run. The same checks run first;
then **Deploy dev** deploys that branch. Or from a terminal:

```sh
gh workflow run "Build and Deploy" --ref <branch>
```

- Dev's database is left as it is, so the branch's migrations run on top of
  the last copy of prod. If they're incompatible with `main`'s, the next merge
  to `main` puts things right: the database is reset from prod before `main`
  is deployed.
- Dev holds one branch at a time. The next manual run or merge to `main`
  replaces it, and runs queue rather than overlap.

## Dev's data

After every prod deploy, CI resets Neon's `dev` branch to a copy of
`production`, so dev always starts from real, current data and anything
written to it since is discarded. Two things follow from it being a copy:

- **It's prod's data.** Treat dev with the same care as prod: real people's
  names and emails, and the same household history.
- **Logins don't carry over.** Sessions are copied too, but they're signed with
  the Django secret key and dev has its own, so prod's sessions don't work
  there (unless dev's `-secret-key-fallbacks` lists prod's key; keep it out).
  Log in to dev separately (its login links are in dev's Cloud Logging).

To reset it by hand, without a deploy: *Neon → Branches → dev → Reset from
parent*.

## DNS

`tdn.sh` is hosted in Cloud DNS: zone `tdn-sh` in the project `tdnsh-dns`. It
has its own project because the zone also holds the domain's email records
(ImprovMX, MailerSend). The commands below use this helper (bash or zsh):

```sh
dns() { gcloud dns record-sets "$@" --zone=tdn-sh --project=tdnsh-dns; }
dns list
```

The app's records:

| Name | Type | Value |
| --- | --- | --- |
| `domovoy.tdn.sh` | CNAME | `domovoy-tdnsh.web.app.` |
| `dom-dev.tdn.sh` | CNAME | `domovoy-tdnsh-dev.web.app.` |
| `_acme-challenge.domovoy.tdn.sh`, `_acme-challenge.dom-dev.tdn.sh` | TXT | Firebase's certificate challenge (keep them) |

The zone also has a wildcard `*.tdn.sh`. A wildcard only answers for names
that don't exist in the zone, and adding *any* record at or below a name
makes it exist: a TXT record there, or an `_acme-challenge.<name>` record.
Before adding such records for a name that currently resolves through the
wildcard, give it an explicit record first, or its address lookups will
return nothing.

To put a site on a new custom domain, add it in *Firebase console → Hosting
→ (site) → Add custom domain* (or the Hosting API's `customDomains`), then
create the records it asks for. Firebase asks for a CNAME to `<site>.web.app`
plus an `_acme-challenge` TXT record. Add the domain to that environment's
`GCP_<ENV>_ALLOWED_HOSTS` and `GCP_<ENV>_CSRF_TRUSTED_ORIGINS`, and set
`GCP_<ENV>_FRONTEND_ROOT` if login links should use it. Then redeploy.

## Cutover from the VPS (done 2026-11-25)

Until 2026-11-25 the app ran on a single VPS (Docker Compose + nginx +
SQLite, deployed over SSH). The move, kept here for reference:

1. **DNS first, on its own.** `tdn.sh` moved from DigitalOcean to Cloud DNS
   with identical records, checked name by name against both providers'
   nameservers before the nameservers changed at the registrar (Namecheap).
2. **Prep, without downtime.**
   - `domovoy.tdn.sh` got an explicit A record to the VPS with a 300s TTL. It
     had resolved through the wildcard (see "DNS").
   - The custom domain was added to the prod Hosting site, and its
     `_acme-challenge` TXT record created.
   - The domain was added to prod's allowed hosts and CSRF origins, and prod
     redeployed.
3. **Freeze and move** (about 25 minutes of downtime):
   1. Stopped the VPS container.
   2. Took an SQLite snapshot, then ran `dumpdata` and the length check
      ([DATABASE.md](DATABASE.md)).
   3. Ran `loaddata` into the empty `production` branch, using the direct
      URL, and compared row counts and ID sequences.
   4. Logged in at the `web.app` URL.
4. **Switch.** One Cloud DNS transaction replaced the A record with the
   CNAME. Firebase confirmed ownership and issued its certificate within
   about three minutes. Then `GCP_PROD_FRONTEND_ROOT` was set to the domain,
   and prod redeployed. `dom-dev.tdn.sh` followed the same way, without data.

Lessons:
- Firebase wanted a CNAME, not A records plus an ownership TXT, and wouldn't
  confirm ownership (or finish the certificate) until the CNAME was live.
- `loaddata` from a laptop took 21 minutes for about 6,000 rows: it makes
  several round trips per row at about 60 ms each. Running it inside GCP
  (Cloud Shell, or a Cloud Run job) would be much faster.
- Imported sessions didn't survive, because GCP has its own Django key, so
  everyone logged in again. `domovoy_server_secret_key_fallbacks` can carry
  sessions across a key change: see `security/session_key.py`.
- Local DNS caches (macOS's `mDNSResponder`, browsers) kept pointing at the
  VPS for a while. `sudo dscacheutil -flushcache; sudo killall -HUP
  mDNSResponder` fixes it on a Mac.

The VPS was stopped, not deleted. Its SQLite file is the pre-cutover backup.
Before shutting it down for good, decide where `tdn.sh`, `www` and the
wildcard should point; they still resolve to it.

## Rollback

- **A bad app deploy**: in *Cloud Run → service → Revisions*, route 100%
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
- **Secret Manager**: 10 secrets at a few cents per active version per month,
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
  The defaults (`sessionid` / `False`) keep local development unchanged.
- **Host vs Origin.** Behind the rewrite, `Host` is expected to be the run.app
  hostname, with the browser's `Origin` being the web.app or custom domain.
  `GCP_<ENV>_ALLOWED_HOSTS` lists both run.app forms plus the Firebase hostnames,
  and `GCP_<ENV>_CSRF_TRUSTED_ORIGINS` lists the public origins.
  `USE_X_FORWARDED_HOST` stays off: the run.app URL is publicly reachable, so
  trusting `X-Forwarded-Host` would let anyone choose the host Django sees.
- **CDN caching.** Firebase's CDN may cache rewritten responses that ask to be
  cached. Its cache key doesn't include the `x-session-key` header. Django
  therefore adds `Cache-Control: max-age=0, no-cache, no-store,
  must-revalidate, private` to every response that doesn't set its own
  (`domovoy/middleware.py`). WhiteNoise's static files keep their long-lived
  headers. Hosting replaces all of these with its own rules, so
  `firebase.json` repeats them (see "Hosting headers replace the backend's").
- **SPA caching.** Each Hosting release serves only its own hashed
  `/assets/*`. A browser holding an old `index.html` would therefore request
  assets that no longer exist and show a blank page. So `**` is sent
  `no-cache`, which covers `/` and deep links (the SPA fallback serves them as
  `index.html`), and the later `/assets/**` rule makes assets `immutable`.
  When several header rules match a path, the last one wins.
- **Hosting headers replace the backend's.** On live Hosting, a matching
  `headers` rule replaces the `Cache-Control` that Cloud Run sent on 2xx and
  3xx responses (4xx responses keep the backend's). Backend paths can't be
  left out, so `firebase.json` gives them the backend's own values:
  - `/api`, `/api/**`, `/krimba`, `/krimba/**`: Django's
    `max-age=0, no-cache, no-store, must-revalidate, private`. On GCP this
    also overrides any view that sets its own `Cache-Control`, so change
    `firebase.json` too if one ever needs to.
  - `/api-static/**`: WhiteNoise's `public, max-age=60`, or, for hashed file
    names (`name.<12 hex>.ext`, matched by a `regex` rule),
    `public, max-age=315360000, immutable`.

  The first version tried to exclude the backend with a negated glob,
  `!{/api,/api/**,…}`. The Hosting emulator honoured it, but live Hosting
  applied it to every path, so API and admin responses lost
  `no-store, private`. Check header changes on a preview channel (see
  "Verifying after a deploy"), not with the emulator.
- **Path coverage.** The rewrites list both `/api` and `/api/**` (and likewise
  `/krimba`), because `/x/**` doesn't match `/x` itself.

## Troubleshooting the CI deploy

- **`firebase deploy` can't authenticate** with the Workload Identity
  credentials file. `gcloud` steps succeed, but firebase-tools rejects the
  `external_account` ADC. Fall back to `google-github-actions/auth` (with
  `workload_identity_provider` / `service_account`) in place of the
  "Authenticate to Google Cloud" step, pinned to a commit SHA:
  - v3.0.0: `7c6bc770dae815cd3e89ee6cdf493a5fab2cc093`
  - v2.1.13: `c200f3691d83b41bf9bbd8638997a462592937ed`

  These SHAs came from `git ls-remote`. Check them against the tags before
  use.
- **`PERMISSION_DENIED` from `gcloud run deploy` or `run jobs execute`**:
  `run.developer` is granted on the individual service and job. If that turns
  out to be too narrow for an operation, grant `roles/run.developer` on the
  project to that environment's deployer. Note that this lets the dev deployer
  modify the prod service as well.
- **`firebase deploy` fails listing Cloud Functions**: firebase-tools checks
  for functions backends when rewrites exist, and tolerates a 403 there. If it
  fails some other way, enabling `cloudfunctions.googleapis.com` (no functions
  are created) should get past it.
- **The deploy jobs are skipped**: the repository variable
  `GCP_DEPLOY_ENABLED` isn't `true`, or the run was neither a push to `main`
  nor a manual *Run workflow*. **Deploy dev** is also skipped on `main` when
  prod's deploy or the database reset failed.
- **"Reset dev database from prod" fails**:
  - "NEON_API_KEY is not set" / a Secret Manager permission error: add the key
    to `domovoy-neon-api-key` (step 3), or re-run `bootstrap.sh`, which grants
    the prod deployer access to it.
  - "NEON_PROJECT_ID is not set": add the repository variable (step 4).
  - "Refusing to reset 'dev' …": the `dev` Neon branch is the default,
    protected, or no longer a child of `production`. Fix that in Neon; the
    script won't overwrite anything else.
  - HTTP 401/403 from Neon: the API key was revoked or can't access the
    project.
- **A manual run fails at "Authenticate to Google Cloud"**: the identity
  provider predates manual runs. Re-run `bootstrap.sh`; it updates the
  provider condition and the dev deployer's binding.
- **"Missing repository variables: …"**: add the variables it names (see step
  4). The job never falls back to the other environment's values.
