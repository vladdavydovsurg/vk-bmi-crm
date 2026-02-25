import asyncio
import uuid

from app.config import get_settings
import app.database as db
from app.models import Manager


async def seed():
    settings = get_settings()

    # Инициализация БД
    db.init_database(settings.database_url)
    await db.create_tables()

    if db.SessionLocal is None:
        raise RuntimeError("SessionLocal is not initialized")

    async with db.SessionLocal() as session:
        session.add_all([
            Manager(
                id=uuid.uuid4(),
                name="Людмила",
                telegram_id=5243724163,
                active=True,
            ),
            Manager(
                id=uuid.uuid4(),
                name="Марина",
                telegram_id=383265770,
                active=True,
            ),
        ])
        await session.commit()

    print("Менеджеры добавлены корректно.")


if __name__ == "__main__":
    asyncio.run(seed())