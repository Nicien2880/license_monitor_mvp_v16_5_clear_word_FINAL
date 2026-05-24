from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "License Monitor"
    host: str = "0.0.0.0"
    port: int = 8000
    database_url: str = "sqlite:///./data/licenses.db"
    backup_dir: str = "./data/backups"
    warning_days: int = 60
    critical_days: int = 30
    urgent_days: int = 7

    # Авторизация веб-интерфейса
    auth_enabled: bool = True
    session_secret: str = "change-me-session-secret"
    initial_admin_username: str = "admin"
    initial_admin_password: str = "ChangeMe123!"
    initial_admin_email: str = "admin@company.local"

    # API-ключ для Zabbix/интеграций. Если пустой — API остается открытым.
    zabbix_api_key: str = ""

    # Email notifications
    license_monitor_url: str = "http://127.0.0.1:8000"
    smtp_host: str = ""
    smtp_port: int = 25
    smtp_from: str = ""
    smtp_to: str = ""
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_starttls: bool = False
    smtp_ssl: bool = False
    smtp_timeout: int = 20

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
