###############################################################################
# GCP
###############################################################################

variable "gcp_project_id" {
  type        = string
  description = "GCP project id (create it during bootstrap)."
}

variable "gcp_region" {
  type        = string
  description = "GCP region for Cloud Run + Artifact Registry. Pick one close to the Neon DB."
  default     = "europe-west2"
}

variable "github_repo" {
  type        = string
  description = "owner/repo allowed to deploy via Workload Identity Federation."
  default     = "tomnewport/domovoy"
}

variable "ar_repo_name" {
  type        = string
  description = "Artifact Registry repository name."
  default     = "domovoy"
}

variable "service_name" {
  type        = string
  description = "Cloud Run service name."
  default     = "domovoy"
}

variable "initial_image" {
  type        = string
  description = <<-EOT
    Image the Cloud Run service is first created with. CI updates the image on
    every deploy (Terraform ignores image changes), so this is only the bootstrap
    placeholder. The Google 'hello' image lets the service come up before the
    real image exists.
  EOT
  default     = "us-docker.pkg.dev/cloudrun/container/hello"
}

###############################################################################
# Application config (non-secret -> plain Cloud Run env vars)
###############################################################################

variable "allowed_hosts" {
  type        = list(string)
  description = "ALLOWED_HOSTS. Add the *.run.app host after the first deploy, plus any custom domain."
  default     = []
}

variable "csrf_trusted_origins" {
  type        = list(string)
  description = "CSRF_TRUSTED_ORIGINS (scheme+host), e.g. the Cloud Run URL and custom domain."
  default     = []
}

variable "frontend_root" {
  type        = string
  description = "Public base URL of the SPA (used in email links). Include the trailing slash."
}

variable "smtp_server" {
  type    = string
  default = "localhost"
}

variable "smtp_port" {
  type    = number
  default = 587
}

variable "smtp_username" {
  type    = string
  default = "domovoy"
}

###############################################################################
# Secrets (sensitive -> Secret Manager). Values land in Terraform state, so the
# state bucket must stay private (it is by default). See README.md.
###############################################################################

variable "smtp_password" {
  type        = string
  description = "SMTP password for outbound mail. Placeholder is fine until real email is wired up."
  sensitive   = true
  default     = "unset"
}

###############################################################################
# Neon
###############################################################################

variable "neon_api_key" {
  type      = string
  sensitive = true
}

variable "neon_region" {
  type        = string
  description = "Neon region id, e.g. aws-eu-central-1 or aws-us-east-1."
  default     = "aws-eu-central-1"
}

variable "neon_pg_version" {
  type    = number
  default = 16
}

###############################################################################
# Auth0
###############################################################################

variable "auth0_domain" {
  type        = string
  description = "Auth0 tenant domain, e.g. dev-xxxx.eu.auth0.com."
}

variable "auth0_tf_client_id" {
  type      = string
  sensitive = true
}

variable "auth0_tf_client_secret" {
  type      = string
  sensitive = true
}

variable "api_audience" {
  type        = string
  description = "Auth0 API identifier / JWT audience the backend validates, e.g. https://api.domovoy.example.com."
}

variable "spa_url" {
  type        = string
  description = "Public URL of the SPA, used for Auth0 callback/logout/web-origins, e.g. https://app.domovoy.example.com."
}
