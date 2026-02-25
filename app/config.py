import os
from dataclasses import dataclass
from typing import List
from urllib.parse import quote_plus

from dotenv import load_dotenv


load_dotenv()


@dataclass(slots=True)
class Settings:
    bot_token: str
    admin_ids: List[int]
    database_url: str
    openai_api_key: str
    openai_model: str
    google_service_account_json: str
    master_sheet_id: str
    log_level: str


def _build_database_url() -> str:
    host = os.getenv("DB_HOST", "127.0.0.1")
    port = os.getenv("DB_PORT", "5432")
    name = os.getenv("DB_NAME", "vk_bmi_crm")
    user = os.getenv("DB_USER", "postgres")
    password = quote_plus(os.getenv("DB_PASSWORD", ""))  # <<< ВАЖНО

    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{name}"


def _parse_admin_ids(raw_ids: str) -> List[int]:
    if not raw_ids:
        return []
    return [int(item.strip()) for item in raw_ids.split(",") if item.strip()]


def get_settings() -> Settings:
    bot_token = os.getenv("BOT_TOKEN", "")
    if not bot_token:
        raise ValueError("BOT_TOKEN is not set in environment.")

    return Settings(
        bot_token=bot_token,
        admin_ids=_parse_admin_ids(os.getenv("ADMIN_IDS", "")),
        database_url=_build_database_url(),
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        google_service_account_json=os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", ""),
        master_sheet_id=os.getenv("MASTER_SHEET_ID", ""),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
    )
