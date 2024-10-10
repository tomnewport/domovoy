from pydantic_settings import BaseSettings, SettingsConfigDict


class DmvSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')
    domovoy_server_secret_key: str
    domovoy_django_debug: bool = False
    domovoy_allowed_hosts: list[str] = []
