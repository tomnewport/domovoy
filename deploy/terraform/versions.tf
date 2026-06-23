terraform {
  required_version = ">= 1.6"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
    auth0 = {
      source  = "auth0/auth0"
      version = "~> 1.7"
    }
    neon = {
      source  = "kislerdm/neon"
      version = "~> 0.6"
    }
  }

  # State lives in a GCS bucket created during bootstrap (see README.md). The
  # bucket name is supplied at init time so it isn't hard-coded:
  #   terraform init -backend-config="bucket=YOUR_TF_STATE_BUCKET"
  backend "gcs" {
    prefix = "domovoy"
  }
}
