# --- Values to paste into GitHub repo Variables (Settings -> Secrets and
#     variables -> Actions -> Variables) so the deploy workflow can authenticate.
output "github_actions_variables" {
  description = "Set these as GitHub Actions repository variables."
  value = {
    GCP_PROJECT_ID                 = var.gcp_project_id
    GCP_REGION                     = var.gcp_region
    GCP_AR_REPO                    = google_artifact_registry_repository.images.repository_id
    GCP_SERVICE                    = google_cloud_run_v2_service.domovoy.name
    GCP_WORKLOAD_IDENTITY_PROVIDER = google_iam_workload_identity_pool_provider.github.name
    GCP_DEPLOYER_SA                = google_service_account.deployer.email
    GCP_RUNTIME_SA                 = google_service_account.runtime.email
  }
}

output "cloud_run_url" {
  description = "Public URL of the Cloud Run service (known after the first apply)."
  value       = google_cloud_run_v2_service.domovoy.uri
}

# --- Frontend (SPA) Auth0 config ---
output "auth0_spa_client_id" {
  value = auth0_client.spa.client_id
}

output "auth0_domain" {
  value = var.auth0_domain
}

output "auth0_api_audience" {
  value = auth0_resource_server.api.identifier
}
