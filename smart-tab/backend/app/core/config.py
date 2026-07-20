from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "FretFlow Smart TAB Engine"
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/fretflow_db"
    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    class Config:
        env_file = ".env"

settings = Settings()
