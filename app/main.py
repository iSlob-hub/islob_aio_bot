import asyncio
import logging
from typing import Any, Dict

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.types import BotCommand

from app.config import settings
from app.handlers import router
from app.scheduler import scheduler
from app.utils.logging import setup_logging
from app.webapp.server import start_webapp_server, stop_webapp_server


async def on_startup(bot: Bot, dispatcher: Dict[str, Any]) -> None:
    """
    Execute startup actions
    
    Args:
        bot: Bot instance
        dispatcher: Dispatcher data
    """
    # Log startup
    logging.info("Starting bot...")
    
    # Set bot commands
    await bot.set_my_commands([
        BotCommand(command="start", description="Start the bot"),
        BotCommand(command="help", description="Show help"),
        BotCommand(command="webapp", description="Open WebApp"),
        BotCommand(command="reset", description="Reset conversation"),
        BotCommand(command="survey", description="Take our survey"),
    ])
    
    # Start scheduler
    scheduler.start()
    logging.info("Scheduler started")
    
    # Start WebApp server
    await start_webapp_server()
    logging.info(f"WebApp server started at {settings.WEBAPP_URL}")


async def on_shutdown(bot: Bot, dispatcher: Dict[str, Any]) -> None:
    """
    Execute shutdown actions
    
    Args:
        bot: Bot instance
        dispatcher: Dispatcher data
    """
    # Log shutdown
    logging.info("Shutting down bot...")
    
    # Shutdown scheduler
    scheduler.shutdown()
    logging.info("Scheduler stopped")
    
    # Stop WebApp server
    await stop_webapp_server()
    logging.info("WebApp server stopped")


async def main() -> None:
    """
    Main function to start the bot
    """
    # Setup logging
    setup_logging()
    
    # Initialize bot and dispatcher with default properties
    bot = Bot(
        token=settings.BOT_TOKEN.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher(storage=MemoryStorage())
    
    # Register handlers
    dp.include_router(router)
    
    # Register startup and shutdown handlers
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    # Start polling
    await dp.start_polling(bot, skip_updates=True)


if __name__ == "__main__":
    # Run the bot
    asyncio.run(main())
