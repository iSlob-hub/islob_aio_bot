import asyncio
from datetime import datetime

from app.db.models import User
from app.db.database import init_db
from aiogram.fsm.storage.mongo import MongoStorage
from aiogram import Bot, Dispatcher
from app.config import settings
from app.utils.conversation_tracker_middleware import ConversationTrackerMiddleware
from aiogram.client.default import DefaultBotProperties
from app.scheduler import BotScheduler
import logging
import signal
import sys
from contextlib import asynccontextmanager

# Налаштовуємо логування - вимикаємо докладні логи MongoDB
logging.getLogger("pymongo").setLevel(logging.WARNING)
logging.getLogger("pymongo.command").setLevel(logging.WARNING)
logging.getLogger("pymongo.connection").setLevel(logging.WARNING)

bot_scheduler = None
bot = None


async def main():
    global bot_scheduler, bot

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    try:
        # Initialize database
        logging.info("Initializing database...")
        client = await init_db()

        # Setup bot storage
        storage = MongoStorage(
            client=client,
            db_name=settings.MONGODB_DB_NAME,
            collection_name="fsm_storage",
        )

        # Initialize bot and dispatcher
        bot = Bot(
            token=settings.BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML")
        )
        dp = Dispatcher(storage=storage)

        # Add middleware
        dp.message.middleware(ConversationTrackerMiddleware())
        dp.callback_query.middleware(ConversationTrackerMiddleware())

        # Include routers
        from app.routers.main_router import main_router
        from app.routers.report_problem_router import report_problem_router
        from app.routers.notifications_router import notifications_router
        from app.routers.morning_quiz_router import morning_quiz_router
        from app.routers.training_router import training_router
        from app.routers.statistics_router import statistics_router
        
        dp.include_router(main_router)
        dp.include_router(report_problem_router)
        dp.include_router(notifications_router)
        dp.include_router(morning_quiz_router)
        dp.include_router(training_router)
        dp.include_router(statistics_router)

        # Initialize and start scheduler
        logging.info("Initializing scheduler...")
        bot_scheduler = BotScheduler(bot=bot, db_client=client)
        await bot_scheduler.start()

        logging.info("Starting bot polling...")

        # Run bot polling (this will run indefinitely)
        await dp.start_polling(bot)

    except KeyboardInterrupt:
        logging.info("Received KeyboardInterrupt")
    except Exception as e:
        logging.error(f"Error in main: {e}")
        raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Bot stopped by user")
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        sys.exit(1)
