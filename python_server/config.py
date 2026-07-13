"""Configurações — Ferrari IoT Postdoc Lab."""

from pathlib import Path
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent
DB_DIR = BASE_DIR / "database"
DB_DIR.mkdir(parents=True, exist_ok=True)


class Settings(BaseSettings):
    app_name: str = "Ferrari IoT Postdoc Platform"
    host: str = "127.0.0.1"
    port: int = 8001
    database_url: str = f"sqlite:///{DB_DIR / 'ferrari.db'}"
    mqtt_enabled: bool = False
    mqtt_host: str = "127.0.0.1"
    mqtt_port: int = 1883
    mqtt_client_id: str = "ferrari-server"
    jwt_secret: str = "ferrari-postdoc-dev-secret"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 12
    admin_user: str = "admin"
    admin_password: str = "ferrari123"
    simulation_mode: bool = True
    sensor_interval_seconds: float = 1.8


settings = Settings()
