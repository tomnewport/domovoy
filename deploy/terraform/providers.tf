provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}

# Authenticates to the Auth0 Management API via a machine-to-machine application
# you create once in the Auth0 dashboard (see README.md "Bootstrap").
provider "auth0" {
  domain        = var.auth0_domain
  client_id     = var.auth0_tf_client_id
  client_secret = var.auth0_tf_client_secret
}

# Uses a Neon API key from https://console.neon.tech/app/settings/api-keys
provider "neon" {
  api_key = var.neon_api_key
}
