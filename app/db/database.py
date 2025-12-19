from typing import List, Type
from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

from app.config import settings
from app.db.models import (
    User,
    ConversationTransition,
    Notification,
    MorningQuiz,
    TrainingSession,
    UserStatistics,
    TextTemplate,
    ScheduledTrainingDelivery,
)


async def init_db():
    """Initialize database connection and register document models"""
    # Create motor client
    client = AsyncIOMotorClient(
        settings.mongodb_connection_string,
    )

    # Register models with beanie
    document_models: List[Type] = [
        User,
        ConversationTransition,
        Notification,
        MorningQuiz,
        TrainingSession,
        UserStatistics,
        TextTemplate,
        ScheduledTrainingDelivery,
    ]

    await init_beanie(
        database=client[settings.MONGODB_DB_NAME], document_models=document_models
    )

    print(f"Connected to MongoDB: {settings.MONGODB_DB_NAME}")
    return client
