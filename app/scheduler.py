import asyncio
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.mongodb import MongoDBJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor
from config import settings
from aiogram.types import Bot

jobstores = {
    "default": MongoDBJobStore(
        database=settings.MONGODB_DB_NAME,
        collection="apscheduler_jobs",
        host=settings.MONGODB_HOST,
        port=settings.MONGODB_PORT,
        username=settings.MONGODB_USER,
        password=settings.MONGODB_PASSWORD,
    )
}

executors = {
    "default": AsyncIOExecutor(),
}

job_defaults = {
    "coalesce": True,
    "max_instances": 1,
    "misfire_grace_time": 60,
}


class BotScheduler:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone="UTC",
        )
