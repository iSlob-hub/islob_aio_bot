import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_session
from app.models import User

# Configure logging
logger = logging.getLogger(__name__)

# Create scheduler instance
scheduler = AsyncIOScheduler(
    jobstores={"default": MemoryJobStore()},
    executors={"default": AsyncIOExecutor()},
    timezone=settings.SCHEDULER_TIMEZONE,
)


async def schedule_follow_up(
    bot: Bot,
    chat_id: int,
    delay_days: int = 2,
    delay_hours: int = 0,
    delay_minutes: int = 0,
    message: str = "Here's your follow-up message!",
    context: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Schedule a follow-up message to be sent later
    
    Args:
        bot: Bot instance
        chat_id: User's chat ID
        delay_days: Days to delay
        delay_hours: Hours to delay
        delay_minutes: Minutes to delay
        message: Message to send
        context: Additional context data
        
    Returns:
        str: Job ID
    """
    run_date = datetime.now() + timedelta(
        days=delay_days, 
        hours=delay_hours, 
        minutes=delay_minutes
    )
    
    job_id = f"follow_up_{chat_id}_{run_date.timestamp()}"
    
    scheduler.add_job(
        send_follow_up,
        trigger=DateTrigger(run_date=run_date),
        id=job_id,
        kwargs={
            "bot": bot,
            "chat_id": chat_id,
            "message": message,
            "context": context or {},
        },
        replace_existing=True,
    )
    
    logger.info(f"Scheduled follow-up for chat_id {chat_id} at {run_date}")
    return job_id


async def send_follow_up(
    bot: Bot,
    chat_id: int,
    message: str,
    context: Dict[str, Any],
) -> None:
    """
    Send a follow-up message to a user
    
    Args:
        bot: Bot instance
        chat_id: User's chat ID
        message: Message to send
        context: Additional context data
    """
    try:
        # Get user from database to check if they're still active
        session: AsyncSession = await get_session()
        user = await session.get(User, chat_id)
        
        if user:
            await bot.send_message(chat_id=chat_id, text=message)
            logger.info(f"Sent follow-up message to chat_id {chat_id}")
        else:
            logger.warning(f"User with chat_id {chat_id} not found, skipping follow-up")
    except Exception as e:
        logger.error(f"Error sending follow-up to {chat_id}: {e}")
    finally:
        await session.close()


# Example of how to use the scheduler
async def schedule_example_follow_up(bot: Bot, user: User) -> None:
    """Example of scheduling a follow-up message"""
    await schedule_follow_up(
        bot=bot,
        chat_id=user.chat_id,
        delay_days=2,
        message="How are you enjoying our bot? Any feedback for us?",
        context={"user_id": user.id}
    )
