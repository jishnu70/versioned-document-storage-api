# congif.py

from pydantic_settings import BaseSettings, SettingsConfigDict

class AppSetting(BaseSettings):
    DATABASE_URL: str = ""
    SECRET_KEY : str = ""
    JWT_ALGORITHM: str = ""
    MAIL_ACCOUNT: str = ""
    MAIL_PASSWORD: str = ""
    MAX_FILE_SIZE: int = 10 * 1024 * 1024

    REDIS_URL: str = ""
    CELERY_BROKER_URL: str = ""
    CELERY_BACKEND_URL: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

config = AppSetting()
