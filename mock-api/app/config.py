from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    database_url: str = 'sqlite:///./app.db'

    jwt_secret: str = 'change-me-please'
    jwt_algorithm: str = 'HS256'
    jwt_expires_minutes: int = 60 * 24

    storage_dir: str = './storage'
    cors_origins: str = 'http://localhost:5173,http://localhost:3000'

    demo_user_email: str = 'demo@cra.local'
    demo_user_password: str = 'demo1234'
    demo_user_fullname: str = 'Demo User'

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(',') if o.strip()]

    @property
    def storage_path(self) -> Path:
        p = Path(self.storage_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p


settings = Settings()
