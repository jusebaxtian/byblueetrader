from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    supabase_url: str = ""
    supabase_service_key: str = ""
    bot_api_key: str = "dev-key"
    admin_session_secret: str = "dev-secret"
    admin_email: str = "admin@byblue.local"
    admin_password_hash: str = ""


settings = Settings()
