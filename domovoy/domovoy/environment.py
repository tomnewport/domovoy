from pydantic_settings import BaseSettings, SettingsConfigDict


class DmvSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
    domovoy_server_secret_key: str
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
