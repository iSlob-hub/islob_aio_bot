from datetime import datetime
from typing import List, Optional
from beanie import Document, Indexed
from pydantic import BaseModel, Field
from enum import Enum


class TrainingGoal(str, Enum):
    LOSE_WEIGHT = "Зниженя ваги"
    BUILD_MUSCLE = "Набір м'язової маси"
    MAINTAIN_FITNESS = "Підтримка форми"

class User(Document):
    telegram_id: str
    full_name: str
    telegram_username: str
    is_active: bool = True
    is_verified: bool = False
    training_goal: TrainingGoal = TrainingGoal.MAINTAIN_FITNESS
    created_at: datetime = Field(default_factory=datetime.now)

    training_file_url: Optional[str] = None

    class Settings:
        name = "users"


class ConversationTransition(Document):
    user_id: Indexed(str)
    from_flow: str
    to_flow: str
    timestamp: datetime = Field(default_factory=datetime.now)

    class Settings:
        name = "conversation_transitions"


class NotificationType(str, Enum):
    DAILY_MORNING_NOTIFICATION = "daily_morning_notification"
    AFTER_TRAINING_NOTIFICATION = "after_training_notification"
    CUSTOM_NOTIFICATION = "custom_notification"
    GYM_REMINDER_NOTIFICATION = "gym_reminder_notification"


class Notification(Document):
    user_id: Indexed(str)
    notification_time: str
    notification_text: str
    notification_type: NotificationType
    custom_notification_text: Optional[str] = None
    custom_notification_cron: Optional[str] = None
    custom_notification_execute_once: Optional[bool] = False
    system_data: Optional[dict] = None

    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.now)

    class Settings:
        name = "notifications"


class MorningQuiz(Document):
    user_id: Indexed(str)
    how_do_you_feel_today: Optional[int] = None
    how_many_hours_of_sleep: Optional[float] = None
    weight: Optional[float] = None
    is_going_to_gym: Optional[bool] = None
    gym_attendance_time: Optional[datetime] = None

    completed: bool = False
    created_at: datetime = Field(default_factory=datetime.now)

    class Settings:
        name = "morning_quizzes"


class TrainingSession(Document):
    user_id: Indexed(str)
    how_do_you_feel_before: Optional[int] = None
    how_hard_was_training: Optional[int] = None
    do_you_have_any_pain: Optional[bool] = None
    training_started_at: Optional[datetime] = None
    training_ended_at: Optional[datetime] = None
    training_duration: Optional[int] = None  # in minutes
    notes: Optional[str] = None
    training_warning_message_sent: bool = False

    # day after training
    do_you_have_soreness: Optional[bool] = None
    stress_level: Optional[int] = None

    training_pdf_link: Optional[str] = None

    completed: bool = False
    created_at: datetime = Field(default_factory=datetime.now)

    class Settings:
        name = "training_sessions"


class PeriodType(str, Enum):
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class UserStatistics(Document):
    user_id: Indexed(str)
    period_type: PeriodType
    period_start: datetime
    period_end: datetime
    
    # JSON fields for each chart type
    stress_data: Optional[dict] = None
    warehouse_data: Optional[dict] = None
    sleep_data: Optional[dict] = None
    wellbeing_data: Optional[dict] = None
    weight_data: Optional[dict] = None
    
    # Metadata
    total_training_sessions: int = 0
    total_morning_quizzes: int = 0
    is_complete: bool = False
    generated_at: datetime = Field(default_factory=datetime.now)
    
    # AI Analysis
    ai_analysis: Optional[str] = None
    ai_analysis_generated_at: Optional[datetime] = None

    class Settings:
        name = "user_statistics"


class TextTemplate(Document):
    template_key: str = Field(index=True)
    template_text: str
    description: Optional[str] = None
    last_updated: datetime = Field(default_factory=datetime.now)
    
    class Settings:
        name = "text_templates"