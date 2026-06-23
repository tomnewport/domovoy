# --- Enable the APIs the rest of the config needs ---------------------------
resource "google_project_service" "apis" {
  for_each = toset([
    "run.googleapis.com",
    "artifactregistry.googleapis.com",
    "secretmanager.googleapis.com",
    "iam.googleapis.com",
    "iamcredentials.googleapis.com",
    "sts.googleapis.com",
  ])
  service            = each.value
  disable_on_destroy = false
}

# --- Container image repository ---------------------------------------------
resource "google_artifact_registry_repository" "images" {
  repository_id = var.ar_repo_name
  location      = var.gcp_region
  format        = "DOCKER"
  description   = "Domovoy container images"
  depends_on    = [google_project_service.apis]
}

# --- Service accounts -------------------------------------------------------
# Identity the running container uses (only reads secrets).
resource "google_service_account" "runtime" {
  account_id   = "domovoy-run"
  display_name = "Domovoy Cloud Run runtime"
}

# Identity GitHub Actions uses to deploy.
resource "google_service_account" "deployer" {
  account_id   = "domovoy-deployer"
  display_name = "Domovoy GitHub deployer"
}

# Deployer: deploy Cloud Run + push images.
resource "google_project_iam_member" "deployer_run_admin" {
  project = var.gcp_project_id
  role    = "roles/run.admin"
  member  = "serviceAccount:${google_service_account.deployer.email}"
}

resource "google_project_iam_member" "deployer_ar_writer" {
  project = var.gcp_project_id
  role    = "roles/artifactregistry.writer"
  member  = "serviceAccount:${google_service_account.deployer.email}"
}

# Deployer may deploy a service that runs *as* the runtime account.
resource "google_service_account_iam_member" "deployer_actas_runtime" {
  service_account_id = google_service_account.runtime.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.deployer.email}"
}

# --- Workload Identity Federation: let GitHub Actions impersonate deployer ---
resource "google_iam_workload_identity_pool" "github" {
  workload_identity_pool_id = "github"
  display_name              = "GitHub Actions"
  depends_on                = [google_project_service.apis]
}

resource "google_iam_workload_identity_pool_provider" "github" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "github-provider"
  display_name                       = "GitHub provider"

  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.repository" = "assertion.repository"
  }
  # Only tokens from this exact repository are accepted.
  attribute_condition = "assertion.repository == '${var.github_repo}'"

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

resource "google_service_account_iam_member" "deployer_wif" {
  service_account_id = google_service_account.deployer.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository/${var.github_repo}"
}

# --- Secrets (containers + values) ------------------------------------------
# Values are sourced from a generated key, Neon's output, and a variable; all
# three therefore exist in Terraform state — keep the state bucket private.
resource "random_password" "server_secret_key" {
  length  = 50
  special = false
}

locals {
  secrets = {
    domovoy_server_secret_key = random_password.server_secret_key.result
    domovoy_database_url      = neon_project.domovoy.connection_uri
    domovoy_smtp_password     = var.smtp_password
  }
}

resource "google_secret_manager_secret" "app" {
  for_each  = local.secrets
  secret_id = each.key
  replication {
    auto {}
  }
  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret_version" "app" {
  for_each    = local.secrets
  secret      = google_secret_manager_secret.app[each.key].id
  secret_data = each.value
}

# Runtime account may read each secret.
resource "google_secret_manager_secret_iam_member" "runtime_access" {
  for_each  = google_secret_manager_secret.app
  secret_id = each.value.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.runtime.email}"
}

# --- Cloud Run service ------------------------------------------------------
# Terraform owns the service definition (env + secrets); CI updates only the
# image, so image changes are ignored here to avoid a tug-of-war.
resource "google_cloud_run_v2_service" "domovoy" {
  name                = var.service_name
  location            = var.gcp_region
  ingress             = "INGRESS_TRAFFIC_ALL"
  deletion_protection = false

  template {
    service_account = google_service_account.runtime.email

    containers {
      image = var.initial_image

      ports {
        container_port = 8000
      }

      env {
        name  = "domovoy_allowed_hosts"
        value = jsonencode(var.allowed_hosts)
      }
      env {
        name  = "domovoy_csrf_trusted_origins"
        value = jsonencode(var.csrf_trusted_origins)
      }
      env {
        name  = "domovoy_frontend_root"
        value = var.frontend_root
      }
      env {
        name  = "domovoy_smtp_server"
        value = var.smtp_server
      }
      env {
        name  = "domovoy_smtp_port"
        value = tostring(var.smtp_port)
      }
      env {
        name  = "domovoy_smtp_username"
        value = var.smtp_username
      }

      env {
        name = "domovoy_server_secret_key"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.app["domovoy_server_secret_key"].secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "domovoy_database_url"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.app["domovoy_database_url"].secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "domovoy_smtp_password"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.app["domovoy_smtp_password"].secret_id
            version = "latest"
          }
        }
      }
    }
  }

  lifecycle {
    ignore_changes = [template[0].containers[0].image]
  }

  depends_on = [
    google_secret_manager_secret_version.app,
    google_secret_manager_secret_iam_member.runtime_access,
  ]
}

# Public (unauthenticated) access — the API does its own auth.
resource "google_cloud_run_v2_service_iam_member" "public" {
  name     = google_cloud_run_v2_service.domovoy.name
  location = var.gcp_region
  role     = "roles/run.invoker"
  member   = "allUsers"
}
