import asyncio
from datetime import datetime

from db.models import User
from db.database import init_db
from routers import (
    main_router,
    report_problem_router,
    notifications_router,
    morning_quiz_router,
    training_router,
)
from aiogram.fsm.storage.mongo import MongoStorage
from aiogram import Bot, Dispatcher
from config import settings
from utils.conversation_tracker_middleware import ConversationTrackerMiddleware
from aiogram.client.default import DefaultBotProperties


async def main():
    client = await init_db()

    storage = MongoStorage(
        client=client,
        db_name=settings.MONGODB_DB_NAME,
        collection_name="fsm_storage",
    )

    bot = Bot(token=settings.BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher(storage=storage)

    dp.message.middleware(ConversationTrackerMiddleware())
    dp.callback_query.middleware(ConversationTrackerMiddleware())

    dp.include_router(main_router.main_router)
    dp.include_router(report_problem_router.report_problem_router)
    dp.include_router(notifications_router.notifications_router)
    dp.include_router(morning_quiz_router.morning_quiz_router)
    dp.include_router(training_router.training_router)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
