# Domovoy infrastructure (Terraform)

Provisions everything the deployment needs, as code:

- **GCP** — Artifact Registry, the runtime + deployer service accounts and their
  IAM, Workload Identity Federation (so GitHub Actions deploys without a key),
  Secret Manager secrets, and the Cloud Run service.
- **Neon** — the managed Postgres project (its connection string feeds the
  `domovoy_database_url` secret).
- **Auth0** — the API (token audience) and the SPA application.

A few things genuinely **cannot** be Terraformed and are done once by hand first
(the "Bootstrap" section): creating the cloud accounts, enabling billing, the
initial `gcloud` login, and the state bucket.

> ⚠️ **State contains secrets.** The Neon connection string and the generated
> Django key live in Terraform state. Keep state in the **private GCS bucket**
> below (never local, never committed). The bucket is private by default.

---

## Bootstrap (once, by hand)

You need accounts on **Google Cloud**, **Neon**, and **Auth0**. For the Google
account + billing, follow [Section A of DEPLOYMENT_GCP.md](../../docs/DEPLOYMENT_GCP.md).

Do the rest in **Cloud Shell** (<https://console.cloud.google.com> → `>_` icon):

```sh
# 1. Create the project and point gcloud + Terraform at it.
export PROJECT_ID="domovoy-prod-1234"        # globally unique
gcloud projects create "$PROJECT_ID"
gcloud config set project "$PROJECT_ID"
gcloud billing accounts list                 # copy your ACCOUNT_ID
gcloud billing projects link "$PROJECT_ID" --billing-account="PASTE_ACCOUNT_ID"

# 2. Give Terraform credentials (Application Default Credentials).
gcloud auth application-default login

# 3. Enable the one API needed to create the state bucket, then create it.
gcloud services enable storage.googleapis.com
export TF_STATE_BUCKET="${PROJECT_ID}-tfstate"
gcloud storage buckets create "gs://${TF_STATE_BUCKET}" \
  --location="europe-west2" --uniform-bucket-level-access
gcloud storage buckets update "gs://${TF_STATE_BUCKET}" --versioning
```

### Neon credentials
1. Sign up at <https://neon.tech>.
2. Create an API key: **Account settings → API keys → Create**.
3. Note your preferred **region id** (e.g. `aws-eu-central-1`).

### Auth0 credentials (a management app for Terraform)
1. Sign up at <https://auth0.com> and note your tenant **domain**
   (e.g. `dev-xxxx.eu.auth0.com`).
2. **Dashboard → Applications → Applications → Create Application** →
   *Machine to Machine* → authorize it for the **Auth0 Management API**.
3. Grant it (at least) `create/read/update/delete` on `clients` and
   `resource_servers`. Copy its **Client ID** and **Client Secret**.

---

## Configure

```sh
cd deploy/terraform
cp terraform.tfvars.example terraform.tfvars   # edit the non-secret values
```

Pass the **secrets via environment variables** (so they never touch disk):

```sh
export TF_VAR_neon_api_key="neon_api_key_..."
export TF_VAR_auth0_tf_client_id="..."
export TF_VAR_auth0_tf_client_secret="..."
export TF_VAR_smtp_password="..."          # placeholder is fine for now
```

---

## Apply

```sh
terraform init -backend-config="bucket=${TF_STATE_BUCKET}"
terraform plan       # READ THIS — it's the source of truth, not this repo
terraform apply
```

> **Provider schemas weren't validated when this was written** (the authoring
> environment couldn't reach the Terraform registry). `terraform plan` is
> authoritative: if it flags an unknown attribute — most likely on the Neon
> resource (see the note in `neon.tf`) — adjust per the provider docs and
> re-plan. The GCP resources are the well-established `hashicorp/google` ones.

On the **first apply** you won't yet know the Cloud Run hostname, so
`allowed_hosts`/`csrf_trusted_origins` are empty and the app may not pass health
checks. That's expected. Then:

```sh
terraform output cloud_run_url        # e.g. https://domovoy-xxxxxx.a.run.app
```

Put that host into `terraform.tfvars`:

```hcl
allowed_hosts        = ["domovoy-xxxxxx.a.run.app"]
csrf_trusted_origins = ["https://domovoy-xxxxxx.a.run.app"]
```

and `terraform apply` again. From here the service is stable.

---

## Hand off to CI

```sh
terraform output github_actions_variables
```

Add each key/value as a **GitHub repository *Variable*** (repo → Settings →
Secrets and variables → Actions → Variables). With Workload Identity Federation
there is **no key/secret** to store. The deploy workflow then builds the image,
pushes it to Artifact Registry, deploys it to Cloud Run (updating only the
image — Terraform still owns env/secrets), and runs migrations against Neon.

Also commit the generated **`.terraform.lock.hcl`** so provider versions are
pinned for everyone.

---

## Day 2

- **Change config/secrets:** edit `terraform.tfvars` (or the `TF_VAR_*` env) and
  `terraform apply`. A new secret version is created and Cloud Run picks up
  `latest` on the next deploy.
- **Rotate the Django key:** `terraform taint random_password.server_secret_key`
  then apply (note: invalidates existing sessions).
- **Tear it all down:** `terraform destroy` (removes GCP + Neon + Auth0
  resources; the state bucket and project remain).
