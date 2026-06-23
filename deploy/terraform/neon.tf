# Neon managed Postgres.
#
# NOTE: the community Neon provider's exact attribute names move between
# versions. This uses `connection_uri` from the project resource (the URI of the
# default branch/database/role Neon creates). If `terraform plan` reports that
# attribute doesn't exist for your provider version, check the provider docs
# (https://registry.terraform.io/providers/kislerdm/neon/latest/docs) — you may
# need to read it from a `neon_branch`/`neon_endpoint` resource, or compose the
# URL from host/role/password/database. Either way it feeds the
# `domovoy_database_url` secret in gcp.tf.

resource "neon_project" "domovoy" {
  name       = "domovoy"
  region_id  = var.neon_region
  pg_version = var.neon_pg_version
}
