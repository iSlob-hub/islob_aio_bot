import asyncio
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor
from app.config import settings
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from app.db.models import Notification, User, MorningQuiz, TrainingSession
from zoneinfo import ZoneInfo
from croniter import croniter
import logging

logging.basicConfig(level=logging.DEBUG)


zone_info = ZoneInfo("Europe/Kyiv")

jobstores = {
    "default": MemoryJobStore(),
}


class BotScheduler:
    def __init__(self, bot, db_client):
        self.bot = bot
        self.db_client = db_client
        self.scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            timezone="Europe/Kyiv",
        )
        self._running = False

    async def start(self):
        """Start the scheduler and add all jobs"""
        if self._running:
            return

        try:
            # Add your jobs before starting
            await self.add_jobs()

            # Start the scheduler
            self.scheduler.start()
            self._running = True

            print("BotScheduler started successfully")

        except Exception as e:
            print(f"Failed to start scheduler: {e}")
            raise

    async def add_jobs(self):
        """Add all scheduled jobs"""
        try:
            self.scheduler.add_job(
                self.send_morning_notifications,
                "interval",
                seconds=5,
                id="morning_notifications",
                replace_existing=True,
            )

            self.scheduler.add_job(
                self.send_after_training_notification,
                "cron",
                hour=15,
                minute=0,
                second=0,
                id="after_training_notification",
                replace_existing=True,
            )

            self.scheduler.add_job(
                self.send_too_long_training_notification,
                "interval",
                seconds=10,
                id="too_long_training_notification",
                replace_existing=True,
            )

            self.scheduler.add_job(
                self.send_custom_notifications,
                "interval",
                seconds=10,
                id="custom_notifications",
                replace_existing=True,
            )

            print("All scheduled jobs added successfully")

        except Exception as e:
            print(f"Failed to add jobs: {e}")
            raise

    async def frequent_task(self):
        """Task that runs every 10 seconds"""
        try:
            now = datetime.now(tz=zone_info).strftime("%H:%M")
            print(f"🔄 Frequent task executed at {now}")
            me = await self.bot.get_me()
            print(f"✅ Bot @{me.username} is responsive")

        except Exception as e:
            print(f"Frequent task failed: {e}")

    async def send_morning_notifications(self):
        """Send morning notifications"""
        notifications = await Notification.find(
            {"is_active": True, "notification_type": "daily_morning_notification"}
        ).to_list()

        for notification in notifications:
            notification_time = notification.notification_time
            time_now_str = datetime.now(tz=zone_info).strftime("%H:%M")
            if not notification.system_data:
                notification.system_data = {}
            await notification.save()
            notification_last_sent_date = notification.system_data.get("last_sent_date")
            if notification_last_sent_date:
                notification_last_sent_date = notification_last_sent_date.date()
                if notification_last_sent_date == datetime.now(tz=zone_info).date():
                    print(
                        f"Skipping notification for {notification.user_id} at {notification_time}, already sent today"
                    )
                    continue
            if notification_time != time_now_str:
                print(
                    f"Skipping notification for {notification.user_id} at {notification_time}, current time is {time_now_str}"
                )
                continue
            recipient = notification.user_id

            morning_quiz = MorningQuiz(
                user_id=str(recipient),
            )
            await morning_quiz.save()
            morning_quiz_id = morning_quiz.id

            try:
                await self.bot.send_message(
                    chat_id=recipient,
                    text="Ейоу, пора пройти ранкове опитування!",
                    reply_markup=InlineKeyboardMarkup(
                        inline_keyboard=[
                            [
                                InlineKeyboardButton(
                                    text="Почати опитування",
                                    callback_data=f"start_morning_quiz_{morning_quiz_id}",
                                )
                            ]
                        ]
                    ),
                )
                print(f"✅ Sent morning quiz to {recipient}")
                notification.system_data = {
                    "last_sent_date": datetime.now(tz=zone_info).date(),
                }
                await notification.save()
            except Exception as e:
                print(f"Failed to send morning quiz to {recipient}: {e}")

    async def send_after_training_notification(self):
        """Send after training notification"""
        try:
            notifications = await Notification.find(
                {
                    "notification_type": "after_training_notification",
                    "is_active": True,
                }
            ).to_list()

            for notification in notifications:
                training_session_id = notification.system_data.get(
                    "training_session_id"
                )
                training_session = await TrainingSession.get(training_session_id)
                if not training_session:
                    print(f"Training session {training_session_id} not found")
                    continue
                if not training_session.completed:
                    print(
                        f"Training session {training_session_id} is not completed, skipping notification"
                    )
                    continue
                await self.bot.send_message(
                    chat_id=notification.user_id,
                    text="Ейоу! Пора пройти опитування після тренування вчора!",
                    reply_markup=InlineKeyboardMarkup(
                        inline_keyboard=[
                            [
                                InlineKeyboardButton(
                                    text="Почати опитування",
                                    callback_data=f"start_after_training_quiz_{training_session_id}",
                                )
                            ]
                        ]
                    ),
                    parse_mode="HTML",
                )
                await notification.delete()

        except Exception as e:
            print(f"Failed to send after training notification: {e}")

    async def send_too_long_training_notification(self):
        now_utc = datetime.now(ZoneInfo("Europe/Kyiv"))
        cutoff = now_utc - timedelta(hours=1)

        sessions = await TrainingSession.find(
            TrainingSession.completed == False,
            TrainingSession.training_warning_message_sent == False,
            TrainingSession.training_started_at <= cutoff,
        ).to_list()

        for session in sessions:
            try:
                await self.bot.send_message(
                    chat_id=session.user_id,
                    text="Тренування триває вже більше 60 хвилин, будь ласка, заверши його, якщо забув.",
                )
                session.training_warning_message_sent = True
                await session.save()
                print(
                    f"Sent warning for training session {session.id} to {session.user_id}"
                )
            except Exception as e:
                print(f"Failed to send warning for session {session.id}: {e}")

    async def send_custom_notifications(self):
        """Custom notification example:
                    {
          "_id": {
            "$oid": "68527ece216c82303db1a627"
          },
          "user_id": "379872548",
          "notification_time": "12:00",
          "notification_text": "Понюхай",
          "notification_type": "custom_notification",
          "custom_notification_text": "Понюхай",
          "custom_notification_cron": "0 12 * * 0,5,2",
          "custom_notification_execute_once": false,
          "is_active": true,
          "created_at": {
            "$date": "2025-06-18T08:54:38.790Z"
          }
        }
        """
        try:
            notifications = await Notification.find(
                {
                    "notification_type": "custom_notification",
                    "is_active": True,
                }
            ).to_list()

            for notification in notifications:
                current_time = datetime.now(tz=zone_info).strftime("%H:%M")
                if not notification.system_data:
                    notification.system_data = {}
                    await notification.save()
                last_sent_date = notification.system_data.get("last_sent_date")
                if (
                    last_sent_date
                    and last_sent_date.date() == datetime.now(tz=zone_info).date()
                ):
                    print(
                        f"Skipping custom notification for {notification.user_id} at {notification.notification_time}, already sent today"
                    )
                    continue
                if notification.notification_time != current_time:
                    print(
                        f"Skipping custom notification for {notification.user_id} at {notification.notification_time}, current time is {current_time}"
                    )
                    continue

                if not notification.custom_notification_cron:
                    print(f"No cron expression for notification {notification.id}")
                    continue

                cron_expr = notification.custom_notification_cron
                now = datetime.now(tz=zone_info)

                cron = croniter(cron_expr, now)
                prev_time = cron.get_prev(datetime)

                if prev_time.replace(second=0, microsecond=0) == now.replace(
                    second=0, microsecond=0
                ):
                    await self.bot.send_message(
                        chat_id=notification.user_id,
                        text=notification.custom_notification_text,
                    )

                    notification.system_data = {
                        "last_sent_date": datetime.now(tz=zone_info).date(),
                    }
                    await notification.save()

                    if getattr(notification, "custom_notification_execute_once", False):
                        notification.is_active = False
                        await notification.save()
                else:
                    print(
                        f"Skipping custom notification for {notification.user_id} at {notification.notification_time}, cron does not match"
                    )
                print(f"✅ Sent custom notification to {notification.user_id}")

        except Exception as e:
            print(f"Failed to send custom notifications: {e}")

    def shutdown(self):
        """Gracefully shutdown the scheduler"""
        if self._running and self.scheduler.running:
            self.scheduler.shutdown(wait=True)
            self._running = False
            print("BotScheduler shut down successfully")

    def is_running(self):
        """Check if scheduler is running"""
        return self._running and self.scheduler.running
