from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    anthropic_api_key: str
    whatsapp_phone_number_id: str
    whatsapp_access_token: str
    webhook_verify_token: str
    api_key: str
    whatsapp_user_phone: str

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
