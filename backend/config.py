from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    gemini_api_key: str
    twilio_account_sid: str
    twilio_auth_token: str
    twilio_from_number: str  # e.g. "whatsapp:+14155238886"
    api_key: str
    whatsapp_user_phone: str

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
