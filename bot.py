import asyncio
from aiogram import *
from aiogram.fsm.storage.memory import *
from loguru import logger
from config import BOT_TOKEN
from database import Base, engine
from handlers import common, client, cleaner, admin

logger.add("logs/bot.log", rotation="10 MB", retention="7 days", level="INFO")

MAX_START_RETRIES = 8


async def main():
    logger.info("🚀 Запуск бота TidyUp...")

    Base.metadata.create_all(bind=engine)
    logger.success("✅ База данных готова")

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(common.router)
    dp.include_router(client.router)
    dp.include_router(cleaner.router)
    dp.include_router(admin.router)

    last_err = None
    for attempt in range(1, MAX_START_RETRIES + 1):
        try:
            logger.success("✅ Подключение к Telegram…")
            await dp.start_polling(bot)
            return
        except Exception as e:
            last_err = e
            wait = min(5 * attempt, 45)
            logger.warning(
                f"Нет связи с api.telegram.org (попытка {attempt}/{MAX_START_RETRIES}): {e}. "
                f"Повтор через {wait} с…"
            )
            await asyncio.sleep(wait)


if __name__ == "__main__":
    asyncio.run(main())