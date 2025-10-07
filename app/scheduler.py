import asyncio
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.mongodb import MongoDBJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor
from app.config import settings
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from app.db.models import Notification, User, MorningQuiz, TrainingSession
from app.statistics_scheduler import statistics_scheduler
from zoneinfo import ZoneInfo
from croniter import croniter
import logging
from app.utils.text_templates import get_template

# Налаштовуємо логування - вимикаємо докладні логи MongoDB
logging.basicConfig(level=logging.DEBUG)
logging.getLogger("pymongo").setLevel(logging.WARNING)
logging.getLogger("pymongo.command").setLevel(logging.WARNING)
logging.getLogger("pymongo.connection").setLevel(logging.WARNING)

ADMIN_CHAT_ID = settings.ADMIN_CHAT_ID

logger = logging.getLogger(__name__)

zone_info = ZoneInfo("Europe/Kyiv")

def get_jobstore_config():
    from apscheduler.jobstores.memory import MemoryJobStore
    return MemoryJobStore()

jobstores = {
    "default": get_jobstore_config(),
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

            # Start statistics scheduler with bot instance
            statistics_scheduler.start_scheduler(bot=self.bot)

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
                minutes=1,
                id="morning_notifications",
                replace_existing=True,
            )

            self.scheduler.add_job(
                self.send_after_training_notification,
                "interval",
                minutes=1,
                id="after_training_notification",
                replace_existing=True,
            )

            self.scheduler.add_job(
                self.update_payment_days,
                "cron",
                hour="5",
                minute="0",
                id="update_payment_days",
                replace_existing=True,
            )

            self.scheduler.add_job(
                self.check_unpaid_users,
                "cron",
                hour="9",
                id="check_unpaid_users",
                replace_existing=True,
            )

            self.scheduler.add_job(
                self.send_too_long_training_notification,
                "interval",
                minutes=1,
                id="too_long_training_notification",
                replace_existing=True,
            )

            self.scheduler.add_job(
                self.send_custom_notifications,
                "interval",
                minutes=1,
                id="custom_notifications",
                replace_existing=True,
            )

            self.scheduler.add_job(
                self.send_gym_reminder_notifications,
                "interval",
                minutes=1,
                id="gym_reminder_notifications",
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
        current_time_str = datetime.now(tz=zone_info).strftime("%H:%M")
        print(f"DEBUG: Current time in Europe/Kyiv: {current_time_str}")
        
        notifications = await Notification.find(
            {"is_active": True, "notification_type": "daily_morning_notification"}
        ).to_list()

        print(f"DEBUG: Found {len(notifications)} morning notifications")
        
        for notification in notifications:
            logger.debug(f"Processing notification for {notification.user_id}")
            notification_time = notification.notification_time
            time_now_str = datetime.now(tz=zone_info).strftime("%H:%M")
            
            print(f"DEBUG: User {notification.user_id} notification time: {notification_time}, current: {time_now_str}")
            
            if not notification.system_data:
                notification.system_data = {}
            await notification.save()
            notification_last_sent_date = notification.system_data.get("last_sent_date")
            logger.debug(
                f"Processing notification for {notification.user_id} at {notification_time}, last sent date: {notification_last_sent_date}"
            )
            if notification_last_sent_date:
                notification_last_sent_date = notification_last_sent_date.date()
                if notification_last_sent_date == datetime.now(tz=zone_info).date():
                    logger.debug(
                        f"Skipping notification for {notification.user_id} at {notification_time}, already sent today"
                    )
                    continue
            try:
                notification_time_padded = datetime.strptime(notification_time, "%H:%M").strftime("%H:%M")
            except ValueError:
                notification_time_padded = datetime.strptime(notification_time, "%-H:%M").strftime("%H:%M")
            if notification_time_padded != time_now_str:
                logger.debug(
                    f"Skipping notification for {notification.user_id} at {notification_time_padded}, current time is {time_now_str}"
                )
                continue
            logger.debug(f"Sending morning notification to {notification.user_id}")
            recipient = notification.user_id

            morning_quiz = MorningQuiz(
                user_id=str(recipient),
            )
            logger.debug(f"Creating morning quiz for user {recipient}")
            await morning_quiz.save()
            morning_quiz_id = morning_quiz.id
            logger.debug(f"Morning quiz created with ID {morning_quiz_id} for user {recipient}")
            try:
                await self.bot.send_message(
                    chat_id=recipient,
                    text=await get_template("morning_quiz_intro"),
                    reply_markup=InlineKeyboardMarkup(
                        inline_keyboard=[
                            [
                                InlineKeyboardButton(
                                    text=await get_template("start_morning_quiz_button"),
                                    callback_data=f"start_morning_quiz_{morning_quiz_id}",
                                )
                            ]
                        ]
                    ),
                )
                logger.debug(f"✅ Sent morning quiz to {recipient}")
                notification.system_data = {
                    "last_sent_date": datetime.now(tz=zone_info).date(),
                }
                await notification.save()
            except Exception as e:
                logger.debug(f"Failed to send morning quiz to {recipient}: {e}")

    async def send_after_training_notification(self):
        """Send after training notifications - works similar to daily notifications"""
        try:
            current_time = datetime.now(tz=zone_info)
            current_time_str = current_time.strftime("%H:%M")
            current_date = current_time.date()
            
            print(f"DEBUG: Checking after-training notifications at {current_time_str}")
            
            notifications = await Notification.find(
                {
                    "notification_type": "after_training_notification",
                    "is_active": True,
                }
            ).to_list()

            print(f"DEBUG: Found {len(notifications)} after-training notifications")

            for notification in notifications:
                notification_time = notification.notification_time
                
                print(f"DEBUG: User {notification.user_id} notification time: {notification_time}, current: {current_time_str}")
                
                # Check if notification time matches current time
                if notification_time != current_time_str:
                    continue
                
                # Initialize system_data if not exists
                if not notification.system_data:
                    notification.system_data = {}
                
                # Check if we have a scheduled date and training session
                scheduled_date_str = notification.system_data.get("scheduled_date")
                if not scheduled_date_str:
                    print(f"No scheduled_date for notification {notification.id}")
                    continue
                    
                from datetime import date
                scheduled_date = date.fromisoformat(scheduled_date_str)
                
                # Only send if today is the scheduled date
                if scheduled_date != current_date:
                    print(f"Notification {notification.id} scheduled for {scheduled_date}, today is {current_date}")
                    continue
                    
                # Check if already sent today
                if notification.system_data.get("sent", False):
                    print(f"Notification {notification.id} already sent")
                    continue
                
                # Verify training session exists and is completed
                training_session_id = notification.system_data.get("training_session_id")
                if not training_session_id:
                    print(f"No training session ID for notification {notification.id}")
                    continue
                    
                training_session = await TrainingSession.get(training_session_id)
                if not training_session:
                    print(f"Training session {training_session_id} not found, deactivating notification")
                    notification.is_active = False
                    await notification.save()
                    continue
                    
                if not training_session.completed:
                    print(f"Training session {training_session_id} is not completed, skipping notification")
                    continue
                    
                # Send the notification
                await self.bot.send_message(
                    chat_id=notification.user_id,
                    text=await get_template("after_training_quiz_intro"),
                    reply_markup=InlineKeyboardMarkup(
                        inline_keyboard=[
                            [
                                InlineKeyboardButton(
                                    text=await get_template("start_after_training_quiz_button"),
                                    callback_data=f"start_after_training_quiz_{training_session_id}",
                                )
                            ]
                        ]
                    ),
                    parse_mode="HTML",
                )
                
                # Delete the notification after sending (one-time use)
                await notification.delete()
                
                print(f"✅ Sent and deleted after-training notification to {notification.user_id}")

        except Exception as e:
            print(f"Failed to send after training notification: {e}")

    async def send_too_long_training_notification(self):
        now_utc = datetime.now(ZoneInfo("Europe/Kyiv"))
        cutoff = now_utc - timedelta(hours=1)  # Змінено з hours=1 на minutes=5 для тестування

        sessions = await TrainingSession.find(
            TrainingSession.completed != True,
            TrainingSession.training_warning_message_sent != True,
            TrainingSession.training_started_at <= cutoff,
        ).to_list()

        for session in sessions:
            try:
                await self.bot.send_message(
                    chat_id=session.user_id,
                    text=await get_template("too_long_training_notification"),
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

    async def send_gym_reminder_notifications(self):
        """Send gym reminder notifications based on morning quiz responses"""
        try:
            current_time = datetime.now(tz=zone_info)
            current_time_str = current_time.strftime("%H:%M")

            notifications = await Notification.find(
                {
                    "notification_type": "gym_reminder_notification",
                    "is_active": True,
                }
            ).to_list()

            print(
                f"DEBUG: Checking gym reminders at {current_time_str}, found {len(notifications)} active notifications"
            )

            for notification in notifications:
                notification_time = notification.notification_time
                if notification_time != current_time_str:
                    print(
                        "DEBUG: Skipping gym reminder for "
                        f"{notification.user_id}: scheduled {notification_time}, current {current_time_str}"
                    )
                    continue
                
                print(f"DEBUG: Processing gym reminder for {notification.user_id} at {notification_time}")
                local_date = current_time.date()
                start_local = datetime.combine(local_date, datetime.min.time(), tzinfo=zone_info)
                end_local = start_local + timedelta(days=1)
                start_utc = start_local.astimezone(ZoneInfo("UTC"))
                end_utc = end_local.astimezone(ZoneInfo("UTC"))
                print(f"DEBUG: Local start {start_local}, end {end_local}, UTC start {start_utc}, end {end_utc}")

                existing_session = await TrainingSession.find_one(
                    {
                        "user_id": str(notification.user_id),
                        "$or": [
                            {"training_started_at": {"$gte": start_utc, "$lt": end_utc}},
                            {"training_ended_at": {"$gte": start_utc, "$lt": end_utc}},
                        ],
                    }
                )

                if existing_session is not None:
                    print(
                        "DEBUG: Skipping gym reminder for "
                        f"{notification.user_id}: session exists today (session_id={existing_session.id})"
                    )
                    continue
            
                if not notification.system_data:
                    notification.system_data = {}
                    await notification.save()
                    print(
                        f"DEBUG: Created empty system_data for notification {notification.id}"
                    )
                    
                last_sent_date = notification.system_data.get("last_sent_date")
                if last_sent_date is not None:
                    try:
                        last_date = last_sent_date.date()
                    except AttributeError:
                        last_date = last_sent_date
                    print(
                        f"DEBUG: Last sent date for {notification.user_id} is {last_date}"
                    )
                else:
                    last_date = None
                    print(
                        f"DEBUG: No last sent date recorded for {notification.user_id}"
                    )
                if last_date == current_time.date():
                    print(f"Skipping gym reminder for {notification.user_id}: already sent today")
                    continue
                
                # Відправляємо нагадування
                print(
                    f"DEBUG: Sending gym reminder to {notification.user_id} using template gym_reminder_notification_text"
                )
                await self.bot.send_message(
                    chat_id=notification.user_id,
                    text=await get_template("gym_reminder_notification_text"),
                )
                
                await notification.delete()
                
                print(f"✅ Sent gym reminder to {notification.user_id} at {notification_time}")

        except Exception as e:
            print(f"Failed to send gym reminder notifications: {e}")


    async def update_payment_days(self):
        try:
            users = await User.find(
                {
                    "payed_days_left": {"$gt": 0},
                    "paused_payment": False,
                }
            ).to_list()
            for user in users:
                user.payed_days_left -= 1
                await user.save()

        except Exception as e:
            print(f"Failed to process payment change: {e}")

    async def check_unpaid_users(self):
        try:
            users = await User.find(
                {
                    "payed_days_left": {"$gte": 0},
                    "paused_payment": False,
                }
            ).to_list()
            for user in users:
                if user.payed_days_left == 0:
                    await self.bot.send_message(
                        chat_id=ADMIN_CHAT_ID,
                        text=f'#Payments У користувача <a href="tg://user?id={user.telegram_id}"> {user.full_name} @{user.telegram_username} ({user.telegram_id})</a> закінчився платний період.',
                    )
                    print(f"Notified user {user.id} about subscription expiration")
                
                if user.payed_days_left == 7:
                    await self.bot.send_message(
                        chat_id=ADMIN_CHAT_ID,
                        text=f"#Payments У користувача <a href=\"tg://user?id={user.telegram_id}\"> {user.full_name} @{user.telegram_username} ({user.telegram_id})</a> залишився 1 тиждень платного періоду.",
                    )
                    print(f"Notified user {user.id} about 7 days left")

                if user.payed_days_left == 1:
                    await self.bot.send_message(
                        chat_id=ADMIN_CHAT_ID,
                        text=f"#Payments У користувача <a href=\"tg://user?id={user.telegram_id}\"> {user.full_name} @{user.telegram_username} ({user.telegram_id})</a> залишився 1 день платного періоду.",
                    )
                    print(f"Notified user {user.id} about 1 day left")

        except Exception as e:
            print(f"Failed to check unpaid users: {e}")

    def shutdown(self):
        """Gracefully shutdown the scheduler"""
        if self._running and self.scheduler.running:
            self.scheduler.shutdown(wait=True)
            self._running = False
            
            # Stop statistics scheduler
            statistics_scheduler.stop_scheduler()
            
            print("BotScheduler shut down successfully")

    def is_running(self):
        """Check if scheduler is running"""
        return self._running and self.scheduler.running
