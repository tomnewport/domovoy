#!/usr/bin/env bash
# One-time, idempotent provisioning of the GCP side of the Domovoy deployment.
# See docs/DEPLOY_GCP.md. Run it from a machine where `gcloud` is logged in as a
# project owner (`gcloud auth login`). Re-running it is safe: it creates what is
# missing and leaves existing resources (including deployed services) alone.
#
# Usage:
#   deploy/gcp/bootstrap.sh [--project ID] [--region REGION] [--repo OWNER/NAME]
#                           [--repo-id N] [--owner-id N]
#                           [--prod-site SITE] [--dev-site SITE]
#
# It creates secrets *without* values; it prints how to add each value.
# It never prints or stores secret values itself.

set -euo pipefail

PROJECT_ID="domovoy-tdnsh"
REGION="europe-west2"
GITHUB_REPO="tomnewport/domovoy"
# Numeric IDs are what the WIF condition checks: a renamed or re-created repo
# with the same name does not match. Look them up with
#   gh api repos/OWNER/NAME --jq '.id, .owner.id'
GITHUB_REPO_ID="862461320"
GITHUB_OWNER_ID="8523691"
PROD_SITE="domovoy-tdnsh"
DEV_SITE="domovoy-tdnsh-dev"

AR_REPO="domovoy"
# Domovoy-specific pool: a provider for another repo must not share it.
WIF_POOL="domovoy-github"
WIF_PROVIDER="domovoy"
ENVS=(dev prod)

usage() { sed -n '2,13p' "$0" | sed 's/^# \{0,1\}//'; exit "${1:-0}"; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project) PROJECT_ID="$2"; shift 2 ;;
    --region) REGION="$2"; shift 2 ;;
    --repo) GITHUB_REPO="$2"; shift 2 ;;
    --repo-id) GITHUB_REPO_ID="$2"; shift 2 ;;
    --owner-id) GITHUB_OWNER_ID="$2"; shift 2 ;;
    --prod-site) PROD_SITE="$2"; shift 2 ;;
    --dev-site) DEV_SITE="$2"; shift 2 ;;
    -h|--help) usage 0 ;;
    *) echo "Unknown argument: $1" >&2; usage 1 ;;
  esac
done

log() { printf '\n==> %s\n' "$*"; }
gc() { gcloud --project="$PROJECT_ID" --quiet "$@"; }
exists() { "$@" >/dev/null 2>&1; }

command -v gcloud >/dev/null || { echo "gcloud is required" >&2; exit 1; }

if command -v gh >/dev/null && gh auth status >/dev/null 2>&1; then
  read -r found_repo_id found_owner_id < <(gh api "repos/$GITHUB_REPO" --jq '"\(.id) \(.owner.id)"')
  if [[ "$found_repo_id" != "$GITHUB_REPO_ID" || "$found_owner_id" != "$GITHUB_OWNER_ID" ]]; then
    echo "GitHub says $GITHUB_REPO is repo $found_repo_id / owner $found_owner_id," \
      "but this script was given $GITHUB_REPO_ID / $GITHUB_OWNER_ID." >&2
    exit 1
  fi
fi

PROJECT_NUMBER="$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')"
AR_HOST="$REGION-docker.pkg.dev"
WIF_POOL_NAME="projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/$WIF_POOL"
WIF_PROVIDER_NAME="$WIF_POOL_NAME/providers/$WIF_PROVIDER"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

runtime_sa() { echo "domovoy-$1-run@$PROJECT_ID.iam.gserviceaccount.com"; }
deployer_sa() { echo "domovoy-$1-deploy@$PROJECT_ID.iam.gserviceaccount.com"; }
branch_for() { if [[ "$1" == prod ]]; then echo main; else echo dev; fi; }
site_for() { if [[ "$1" == prod ]]; then echo "$PROD_SITE"; else echo "$DEV_SITE"; fi; }
# Secrets read by the service (pooled DB URL) and by the migrate job (direct URL).
# secret-key-fallbacks is a JSON list of old Django keys (service only).
SECRETS=(secret-key secret-key-fallbacks smtp-password database-url database-url-direct)

log "Enabling APIs"
gc services enable \
  run.googleapis.com artifactregistry.googleapis.com secretmanager.googleapis.com \
  iam.googleapis.com iamcredentials.googleapis.com sts.googleapis.com \
  serviceusage.googleapis.com cloudresourcemanager.googleapis.com \
  firebase.googleapis.com firebasehosting.googleapis.com

log "Artifact Registry repository $AR_HOST/$PROJECT_ID/$AR_REPO"
if ! exists gc artifacts repositories describe "$AR_REPO" --location="$REGION"; then
  gc artifacts repositories create "$AR_REPO" --location="$REGION" \
    --repository-format=docker --description="Domovoy API images"
fi
# Keep the 10 newest images per package (domovoy-dev, domovoy-prod) for
# rollback; delete anything else older than 30 days.
gc artifacts repositories set-cleanup-policies "$AR_REPO" --location="$REGION" \
  --policy="$SCRIPT_DIR/ar-cleanup-policy.json" --no-dry-run

log "Workload Identity Federation: pool $WIF_POOL, provider $WIF_PROVIDER"
if ! exists gc iam workload-identity-pools describe "$WIF_POOL" --location=global; then
  gc iam workload-identity-pools create "$WIF_POOL" --location=global \
    --display-name="Domovoy GitHub Actions"
fi
WIF_CONDITION="assertion.repository_id == '$GITHUB_REPO_ID' \
&& assertion.repository_owner_id == '$GITHUB_OWNER_ID' \
&& assertion.ref in ['refs/heads/main', 'refs/heads/dev']"
# repo_ref ("<repository id>/<ref>") lets each deployer binding name the
# repository as well as the branch.
WIF_MAPPING="google.subject=assertion.sub,attribute.repository_id=assertion.repository_id,\
attribute.repository=assertion.repository,attribute.ref=assertion.ref,\
attribute.repo_ref=assertion.repository_id + '/' + assertion.ref"
if exists gc iam workload-identity-pools providers describe "$WIF_PROVIDER" \
    --location=global --workload-identity-pool="$WIF_POOL"; then
  provider_cmd=update-oidc
else
  provider_cmd=create-oidc
fi
gc iam workload-identity-pools providers "$provider_cmd" "$WIF_PROVIDER" \
  --location=global --workload-identity-pool="$WIF_POOL" \
  --display-name="$GITHUB_REPO" \
  --issuer-uri="https://token.actions.githubusercontent.com" \
  --attribute-mapping="$WIF_MAPPING" \
  --attribute-condition="$WIF_CONDITION"

for env in "${ENVS[@]}"; do
  service="domovoy-$env"
  run_sa="$(runtime_sa "$env")"
  deploy_sa="$(deployer_sa "$env")"
  branch="$(branch_for "$env")"

  log "[$env] Service accounts"
  if ! exists gc iam service-accounts describe "$run_sa"; then
    gc iam service-accounts create "${run_sa%%@*}" --display-name="Domovoy $env runtime"
  fi
  if ! exists gc iam service-accounts describe "$deploy_sa"; then
    gc iam service-accounts create "${deploy_sa%%@*}" --display-name="Domovoy $env CI deployer"
  fi

  log "[$env] Secrets (created empty; add values as shown at the end)"
  for name in "${SECRETS[@]}"; do
    secret="$service-$name"
    if ! exists gc secrets describe "$secret"; then
      gc secrets create "$secret" --replication-policy=user-managed --locations="$REGION"
    fi
    gc secrets add-iam-policy-binding "$secret" \
      --member="serviceAccount:$run_sa" --role=roles/secretmanager.secretAccessor >/dev/null
  done

  # Create placeholder service/job once, so IAM can be scoped to them and the
  # deployer never needs permission to change who may invoke the service. CI
  # replaces the image and config on every deploy; re-runs leave them alone.
  log "[$env] Cloud Run service $service (placeholder until the first deploy)"
  if ! exists gc run services describe "$service" --region="$REGION"; then
    gc run deploy "$service" --region="$REGION" \
      --image=us-docker.pkg.dev/cloudrun/container/hello \
      --service-account="$run_sa" --allow-unauthenticated \
      --min-instances=0 --max-instances=2
  fi
  # Firebase Hosting calls the service as an anonymous client.
  gc run services add-iam-policy-binding "$service" --region="$REGION" \
    --member=allUsers --role=roles/run.invoker >/dev/null

  log "[$env] Cloud Run job $service-migrate (placeholder until the first deploy)"
  if ! exists gc run jobs describe "$service-migrate" --region="$REGION"; then
    gc run jobs create "$service-migrate" --region="$REGION" \
      --image=us-docker.pkg.dev/cloudrun/container/job \
      --service-account="$run_sa" --max-retries=0
  fi

  log "[$env] Deployer permissions for $deploy_sa"
  gc run services add-iam-policy-binding "$service" --region="$REGION" \
    --member="serviceAccount:$deploy_sa" --role=roles/run.developer >/dev/null
  gc run jobs add-iam-policy-binding "$service-migrate" --region="$REGION" \
    --member="serviceAccount:$deploy_sa" --role=roles/run.developer >/dev/null
  gc iam service-accounts add-iam-policy-binding "$run_sa" \
    --member="serviceAccount:$deploy_sa" --role=roles/iam.serviceAccountUser >/dev/null
  gc artifacts repositories add-iam-policy-binding "$AR_REPO" --location="$REGION" \
    --member="serviceAccount:$deploy_sa" --role=roles/artifactregistry.writer >/dev/null
  # Firebase Hosting and API quota have no finer-grained scope than the project.
  for role in roles/firebasehosting.admin roles/serviceusage.serviceUsageConsumer; do
    gc projects add-iam-policy-binding "$PROJECT_ID" --condition=None \
      --member="serviceAccount:$deploy_sa" --role="$role" >/dev/null
  done
  # Only workflow runs of this repository on this environment's branch may
  # act as its deployer.
  gc iam service-accounts add-iam-policy-binding "$deploy_sa" \
    --role=roles/iam.workloadIdentityUser \
    --member="principalSet://iam.googleapis.com/$WIF_POOL_NAME/attribute.repo_ref/$GITHUB_REPO_ID/refs/heads/$branch" \
    >/dev/null
done

log "Firebase Hosting"
if command -v firebase >/dev/null; then
  if ! firebase projects:list --json 2>/dev/null | grep -q "\"$PROJECT_ID\""; then
    firebase projects:addfirebase "$PROJECT_ID"
  fi
  for site in "$PROD_SITE" "$DEV_SITE"; do
    if ! firebase hosting:sites:get "$site" --project="$PROJECT_ID" >/dev/null 2>&1; then
      firebase hosting:sites:create "$site" --project="$PROJECT_ID"
    fi
  done
else
  cat <<EOF
firebase-tools is not installed, so Firebase was not set up. Run:
  npm install -g firebase-tools && firebase login
  firebase projects:addfirebase $PROJECT_ID
  firebase hosting:sites:create $PROD_SITE --project=$PROJECT_ID
  firebase hosting:sites:create $DEV_SITE --project=$PROJECT_ID
then re-run this script.
EOF
fi

log "Done. Next steps"
cat <<EOF

1. Add secret values (see docs/DEPLOY_GCP.md). Each command reads the value
   without echoing it, so it never lands in shell history:

EOF
for env in "${ENVS[@]}"; do
  service="domovoy-$env"
  cat <<EOF
   # $env
   python3 -c 'import secrets; print(secrets.token_urlsafe(50), end="")' \\
     | gcloud secrets versions add $service-secret-key --project=$PROJECT_ID --data-file=-
   for s in smtp-password database-url database-url-direct; do
     printf '%s for $env: ' "\$s"; read -rs v; echo; printf '%s' "\$v" \\
       | gcloud secrets versions add "$service-\$s" --project=$PROJECT_ID --data-file=- ; unset v
   done
   # No old keys yet (prod gets the VPS key before cutover; see the docs).
   printf '[]' | gcloud secrets versions add $service-secret-key-fallbacks --project=$PROJECT_ID --data-file=-

EOF
done

cat <<EOF
2. Add these repository variables in GitHub: Settings -> Secrets and
   variables -> Actions -> Variables -> New repository variable. They are not
   secrets, and GitHub Environments are not used.

   GCP_PROJECT_ID=$PROJECT_ID
   GCP_REGION=$REGION
   GCP_WIF_PROVIDER=$WIF_PROVIDER_NAME
   GCP_SMTP_SERVER=<smtp host>
   GCP_SMTP_PORT=<smtp port>
   GCP_SMTP_USERNAME=<smtp username>

EOF
for env in "${ENVS[@]}"; do
  service="domovoy-$env"
  site="$(site_for "$env")"
  p="GCP_$(echo "$env" | tr '[:lower:]' '[:upper:]')"
  run_url="$(gc run services describe "$service" --region="$REGION" --format='value(status.url)' 2>/dev/null || true)"
  run_host="${run_url#https://}"
  hosts="\"$service-$PROJECT_NUMBER.$REGION.run.app\",\"$site.web.app\",\"$site.firebaseapp.com\""
  [[ -n "$run_host" ]] && hosts="\"$run_host\",$hosts"
  cat <<EOF
   ${p}_DEPLOYER_SA=$(deployer_sa "$env")
   ${p}_RUNTIME_SA=$(runtime_sa "$env")
   ${p}_IMAGE=$AR_HOST/$PROJECT_ID/$AR_REPO/$service
   ${p}_SERVICE=$service
   ${p}_FIREBASE_SITE=$site
   ${p}_ALLOWED_HOSTS=[$hosts]
   ${p}_CSRF_TRUSTED_ORIGINS=["https://$site.web.app","https://$site.firebaseapp.com"]
   ${p}_FRONTEND_ROOT=https://$site.web.app/

EOF
done
cat <<EOF
3. When the secrets and variables are in place, add the repository variable
   GCP_DEPLOY_ENABLED=true to turn on the deploy-gcp CI job.
EOF
