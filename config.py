from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_TOKEN: str = "N1ZXIiLCJVc2Vy"
    REDIS_URL: str = "redis://localhost:6379"
    RETRY_ATTEMPTS: int = 3
    RETRY_DELAY: int = 5
    DB_PATH: str = "products.json"
    IMAGES_PATH: str = "images/"
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)


settings = Settings()
