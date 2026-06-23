# Auth0: the API the backend validates tokens against, and the SPA application
# the frontend logs in through. Social/database connections are configured
# separately (they need each provider's OAuth credentials) — enable them in the
# Auth0 dashboard, or extend this file with auth0_connection resources later.

resource "auth0_resource_server" "api" {
  name                                            = "Domovoy API"
  identifier                                      = var.api_audience
  signing_alg                                     = "RS256"
  allow_offline_access                            = true
  token_lifetime                                  = 86400
  skip_consent_for_verifiable_first_party_clients = true
}

resource "auth0_client" "spa" {
  name                = "Domovoy SPA"
  app_type            = "spa"
  oidc_conformant     = true
  callbacks           = [var.spa_url]
  allowed_logout_urls = [var.spa_url]
  web_origins         = [var.spa_url]
  allowed_origins     = [var.spa_url]
  grant_types         = ["authorization_code", "refresh_token"]

  jwt_configuration {
    alg = "RS256"
  }
}
