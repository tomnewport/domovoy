from pydantic_settings import BaseSettings, SettingsConfigDict


class DmvSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
    domovoy_server_secret_key: str
    # Previous secret keys (a JSON list), still accepted when reading signed
    # data such as sessions. Lets sessions survive a key change, e.g. the move
    # from the VPS to GCP.
    domovoy_server_secret_key_fallbacks: list[str] = []
    domovoy_django_debug: bool = False
    domovoy_allowed_hosts: list[str] = ["localhost", "dom-dev.tdn.sh", "domovoy.tdn.sh"]
    domovoy_smtp_server: str
    domovoy_smtp_port: int
    domovoy_smtp_username: str
    domovoy_smtp_password: str
    domovoy_allowed_cors_origins: list[str] = []
    domovoy_csrf_trusted_origins: list[str] = []
    domovoy_frontend_root: str
    domovoy_database_url: str | None = None
    # Firebase Hosting forwards only a cookie named "__session" to Cloud Run, so
    # the GCP deployment sets these to "__session" / True. Defaults keep Django's
    # standard cookie behaviour (local development).
    domovoy_session_cookie_name: str = "sessionid"
    domovoy_csrf_use_sessions: bool = False
