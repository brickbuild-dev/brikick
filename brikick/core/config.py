from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="BRK_",
        env_file=".env",
        case_sensitive=False,
    )

    project_name: str = "Brikick"
    api_v1_prefix: str = "/api/v1"

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "brikick"
    postgres_user: str = "brikick"
    postgres_password: str = "brikick"

    redis_url: str = "redis://localhost:6379/0"

    minio_endpoint: str = "http://localhost:9000"
    minio_access_key: str = "minio"
    minio_secret_key: str = "minio123"
    minio_secure: bool = False

    jwt_secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    @property
    def database_url(self) -> str:
        return (
            "postgresql+asyncpg://"
            f"{self.postgres_user}:{self.postgres_password}@"
            f"{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()
