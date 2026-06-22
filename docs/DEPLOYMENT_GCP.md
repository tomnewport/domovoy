# GCP setup — idiot-proof guide

A linear, copy-paste guide to stand up the Google Cloud side of Domovoy's
deployment: **Cloud Run** (the container) talking to a **Neon** Postgres database,
with **GitHub Actions** deploying automatically and **no long-lived keys** (it uses
Workload Identity Federation) and **no secrets in the repo** (they live in Secret
Manager).

You do **not** need to install anything. Do everything in **Cloud Shell**:

> Open <https://console.cloud.google.com> → click the **`>_`** terminal icon
> (top-right) → a Linux shell opens in your browser with `gcloud` already
> installed and logged in.

Follow the steps **in order**. Each step has a ✅ checkpoint so you know it worked.
If a command fails, fix that step before moving on.

---

## 0. Before you start

You need:

- A Google account.
- A **billing account** linked to your project. Cloud Run has a generous free
  monthly allowance, but Google still requires billing to be enabled. You will
  not be charged within the free tier for a small app like this.
- Your **Neon** database connection string (from the Neon dashboard → your
  project → *Connection string*, "Pooled connection"). It looks like:
  `postgresql://user:password@ep-xxx-pooler.eu-central-1.aws.neon.tech/dbname?sslmode=require`
- (Later, for Step 5) your **Auth0** domain and API audience. Not needed yet.

---

## 1. Set your variables

Paste this into Cloud Shell, **editing the first five values**. Everything below
reuses these, so keep this terminal open (or re-paste if it times out).

```sh
# --- EDIT THESE ---
export PROJECT_ID="domovoy-prod-1234"     # must be globally unique; add digits if taken
export REGION="europe-west2"              # London. Pick the region closest to your Neon DB.
export GITHUB_REPO="tomnewport/domovoy"   # owner/repo, exactly
export REPO="domovoy"                      # Artifact Registry repo name (leave as-is)
export SERVICE="domovoy"                   # Cloud Run service name (leave as-is)

# --- leave these ---
export RUNTIME_SA="domovoy-run@${PROJECT_ID}.iam.gserviceaccount.com"
export DEPLOYER_SA="domovoy-deployer@${PROJECT_ID}.iam.gserviceaccount.com"
```

---

## 2. Create the project and link billing

```sh
gcloud projects create "$PROJECT_ID"
gcloud config set project "$PROJECT_ID"

# List your billing accounts, then link one:
gcloud billing accounts list
# Copy the ACCOUNT_ID (looks like 0X0X0X-0X0X0X-0X0X0X) and run:
export BILLING_ACCOUNT="PASTE_ACCOUNT_ID_HERE"
gcloud billing projects link "$PROJECT_ID" --billing-account="$BILLING_ACCOUNT"
```

✅ **Checkpoint:** `gcloud config get-value project` prints your `PROJECT_ID`.

---

## 3. Turn on the services you need

```sh
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  iam.googleapis.com \
  iamcredentials.googleapis.com \
  sts.googleapis.com \
  cloudresourcemanager.googleapis.com
```

✅ **Checkpoint:** the command finishes with no error (it can take ~30s).

---

## 4. Create the image repository

This is where your Docker images are stored (Artifact Registry).

```sh
gcloud artifacts repositories create "$REPO" \
  --repository-format=docker \
  --location="$REGION" \
  --description="Domovoy container images"
```

✅ **Checkpoint:**
`gcloud artifacts repositories list --location="$REGION"` shows `domovoy`.

---

## 5. Create the two service accounts

- **runtime** — the identity the running container uses (only needs to read secrets).
- **deployer** — the identity GitHub Actions uses to deploy.

```sh
gcloud iam service-accounts create domovoy-run \
  --display-name="Domovoy Cloud Run runtime"

gcloud iam service-accounts create domovoy-deployer \
  --display-name="Domovoy GitHub deployer"
```

Grant the minimum roles:

```sh
# Runtime can read secrets at startup
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${RUNTIME_SA}" \
  --role="roles/secretmanager.secretAccessor"

# Deployer can deploy Cloud Run + push images
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${DEPLOYER_SA}" \
  --role="roles/run.admin"
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${DEPLOYER_SA}" \
  --role="roles/artifactregistry.writer"

# Deployer is allowed to deploy a service that *runs as* the runtime account
gcloud iam service-accounts add-iam-policy-binding "$RUNTIME_SA" \
  --member="serviceAccount:${DEPLOYER_SA}" \
  --role="roles/iam.serviceAccountUser"
```

✅ **Checkpoint:**
`gcloud iam service-accounts list` shows both `domovoy-run` and `domovoy-deployer`.

---

## 6. Store the secrets

Sensitive config goes in **Secret Manager** (never in the repo or the workflow).
Non-sensitive config (hostnames, ports) is set as plain env vars at deploy time —
see Step 9.

This helper creates a secret, or adds a new version if it already exists:

```sh
put_secret () {
  printf '%s' "$2" | gcloud secrets create "$1" --data-file=- --replication-policy=automatic 2>/dev/null \
  || printf '%s' "$2" | gcloud secrets versions add "$1" --data-file=-
}
```

Create the secrets (edit the values):

```sh
# A fresh Django secret key (this command generates one for you):
put_secret domovoy_server_secret_key "$(python3 -c 'import secrets; print(secrets.token_urlsafe(50))')"

# Your Neon pooled connection string (keep the ?sslmode=require on the end):
put_secret domovoy_database_url "postgresql://USER:PASSWORD@HOST-pooler.REGION.aws.neon.tech/DB?sslmode=require"

# Your SMTP password (for sending login emails):
put_secret domovoy_smtp_password "YOUR_SMTP_PASSWORD"
```

✅ **Checkpoint:** `gcloud secrets list` shows all three secrets.

---

## 7. Let GitHub Actions log in without a key (Workload Identity Federation)

This lets *only* your GitHub repo's Actions impersonate the deployer account —
no JSON key file to download, store, or leak.

```sh
export PROJECT_NUMBER="$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')"

# 7a. A pool to hold external identities
gcloud iam workload-identity-pools create github \
  --location=global --display-name="GitHub Actions"

# 7b. A provider that trusts GitHub's OIDC tokens, restricted to YOUR repo only
gcloud iam workload-identity-pools providers create-oidc github-provider \
  --location=global \
  --workload-identity-pool=github \
  --display-name="GitHub provider" \
  --issuer-uri="https://token.actions.githubusercontent.com" \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository" \
  --attribute-condition="assertion.repository=='${GITHUB_REPO}'"

# 7c. Allow that repo to impersonate the deployer service account
gcloud iam service-accounts add-iam-policy-binding "$DEPLOYER_SA" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/github/attribute.repository/${GITHUB_REPO}"

# 7d. Print the provider id GitHub needs — COPY THIS:
echo "projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/github/providers/github-provider"
```

✅ **Checkpoint:** step 7d prints a `projects/.../providers/github-provider`
string. Save it for Step 10.

---

## 8. (Optional but recommended) Smoke-test Cloud Run

Deploy Google's tiny "hello" image just to prove permissions and the region work.
This gives you a public URL in ~1 minute.

```sh
gcloud run deploy hello-test \
  --image=us-docker.pkg.dev/cloudrun/container/hello \
  --region="$REGION" \
  --allow-unauthenticated
```

✅ **Checkpoint:** it prints a `Service URL`. Open it — you'll see a "Congratulations"
page. Then delete it:

```sh
gcloud run services delete hello-test --region="$REGION" --quiet
```

> If `--allow-unauthenticated` is rejected, your organisation blocks public
> services. For a personal Google account this won't happen; on a Workspace/org
> account ask an admin to allow it (policy `iam.allowedPolicyMemberDomains`).

---

## 9. What the real deploy will run

You don't run this by hand — the GitHub Actions workflow (Step 4 of the
deployment work) does. It's here so you understand what's happening and can run
it manually once if you want. It builds the image, pushes it, deploys it, wiring
secrets and plain env vars:

```sh
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/${SERVICE}:latest"

gcloud run deploy "$SERVICE" \
  --image="$IMAGE" \
  --region="$REGION" \
  --service-account="$RUNTIME_SA" \
  --allow-unauthenticated \
  --port=8000 \
  --set-secrets="domovoy_server_secret_key=domovoy_server_secret_key:latest,domovoy_database_url=domovoy_database_url:latest,domovoy_smtp_password=domovoy_smtp_password:latest" \
  --set-env-vars="^@^domovoy_allowed_hosts=[\"$SERVICE-xxxxxx.a.run.app\"]@domovoy_csrf_trusted_origins=[\"https://$SERVICE-xxxxxx.a.run.app\"]@domovoy_frontend_root=https://app.example.com/@domovoy_smtp_server=smtp.example.com@domovoy_smtp_port=587@domovoy_smtp_username=apikey"
```

Notes:

- `--set-secrets` injects the Secret Manager values as environment variables.
- `--set-env-vars` carries the non-sensitive config. The `^@^` prefix just changes
  the separator to `@` so the JSON-list values (which contain commas) survive.
- You won't know the exact `*.a.run.app` hostname until the first deploy creates
  it. So: deploy once (it'll fail health checks on bad hosts, that's fine), copy
  the URL Cloud Run prints, then re-run with the real hostname filled into
  `domovoy_allowed_hosts` and `domovoy_csrf_trusted_origins`. After that it's stable.
- **Migrations** are run as a separate release step against Neon; the workflow
  handles this (it runs `manage.py migrate` once per deploy).

---

## 10. Tell GitHub about your GCP setup

In GitHub: **repo → Settings → Secrets and variables → Actions → Variables tab →
New repository variable**. Add these (they are not secret — WIF means no key is
stored):

| Variable | Value |
| --- | --- |
| `GCP_PROJECT_ID` | your `PROJECT_ID` |
| `GCP_REGION` | your `REGION` (e.g. `europe-west2`) |
| `GCP_AR_REPO` | `domovoy` |
| `GCP_SERVICE` | `domovoy` |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | the string printed in Step 7d |
| `GCP_DEPLOYER_SA` | your `DEPLOYER_SA` email |
| `GCP_RUNTIME_SA` | your `RUNTIME_SA` email |

That's everything GitHub Actions needs to authenticate and deploy.

✅ **You're done with GCP setup.** Tell me when these variables are in place and
I'll wire up the deploy workflow (Step 4) to use them.

---

## Appendix A — Plan B: a service-account key (simpler, less secure)

If Workload Identity Federation gives you trouble, you can use a key file
instead. **Skip Step 7** and do this:

```sh
gcloud iam service-accounts keys create key.json --iam-account="$DEPLOYER_SA"
cat key.json   # copy the whole JSON
```

Then in GitHub add a **secret** (Secrets tab, not Variables) named `GCP_SA_KEY`
with the full JSON as its value, and **delete `key.json`** from Cloud Shell
(`rm key.json`). Tell me you used Plan B so the workflow authenticates with the
key instead of WIF. Rotate/delete the key if it's ever exposed.

## Appendix B — Later: the frontend and a custom domain

- **The Vue SPA** is served separately from the API (it's static files). Easiest
  options: a Cloud Storage bucket behind Cloud CDN, or Firebase Hosting. We'll
  set this up alongside the deploy workflow; for now the API is the priority.
- **Custom domain:** once the service is live,
  `gcloud run domain-mappings create --service="$SERVICE" --domain="api.example.com" --region="$REGION"`
  then add the DNS records it prints. Remember to add the custom domain to
  `domovoy_allowed_hosts` and `domovoy_csrf_trusted_origins`.
- **Avoiding cold starts:** add `--min-instances=1` to the deploy if the ~1–3s
  first-hit delay after idle bothers you (this has a small always-on cost).
