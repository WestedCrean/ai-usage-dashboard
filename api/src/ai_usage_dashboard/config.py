from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite:///./dev.db"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    model_config = {"env_prefix": ""}


settings = Settings()
