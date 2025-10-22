from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from typing import List, Any
import asyncio


class Settings(BaseSettings):
    # Pydantic будет автоматически читать переменные из .env файла
    # и применять к ним типы данных, указанные в аннотациях.
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    bot_token: str
    admin_ids: List[int] = Field(default=[])
    payment_token: str = Field(default="")
    speechmatics_api_url: str
    database_url: str
    default_language: str = "ru"
    speechmatics_max_wait_time_seconds: int = 300

    @field_validator("admin_ids", mode="before")
    @classmethod
    def parse_admin_ids(cls, v: Any) -> List[int]:
        if isinstance(v, (int, float)):
            return [int(v)]
        if isinstance(v, str):
            if not v.strip():
                return []
            return [int(i.strip()) for i in v.split(",")]
        return v


settings = Settings()

MAX_CONCURRENT_TRANSCRIPTIONS = 3
transcription_semaphore = asyncio.Semaphore(MAX_CONCURRENT_TRANSCRIPTIONS)