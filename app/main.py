import asyncio
import sys

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import logging
from typing import Any, Awaitable, Callable, Dict

from aiogram import Bot, Dispatcher
from aiogram.dispatcher.middlewares.base import BaseMiddleware
from aiogram.types import TelegramObject

from app.ai_parser import AIParserService
from app.config import get_settings
import app.database as db
from app.handlers import router
from app.ocr_service import OCRService
from app.sheets_service import SheetsService


class DatabaseSessionMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        if db.SessionLocal is None:
            raise RuntimeError("SessionLocal is not initialized. Did you call db.init_database()?")

        async with db.SessionLocal() as session:
            data["session"] = session
            return await handler(event, data)


async def main() -> None:
    settings = get_settings()

    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    # Init DB + create tables
    db.init_database(settings.database_url)
    await db.create_tables()

    bot = Bot(token=settings.bot_token)
    dp = Dispatcher()

    dp.update.middleware(DatabaseSessionMiddleware())
    dp.include_router(router)

    # Services
    dp["ocr_service"] = OCRService()
    dp["ai_parser"] = AIParserService(
        api_key=settings.openai_api_key,
        model=settings.openai_model,
    )
    dp["sheets_service"] = SheetsService(
        service_account_json=settings.google_service_account_json,
        master_sheet_id=settings.master_sheet_id,
    )

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())