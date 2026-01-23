import datetime
from typing import Optional

from app.db.models import MorningQuiz, Notification, User


def validate_transform_time(time_str: str) -> Optional[float]:
    try:
        sleep_time = float(time_str)
        if sleep_time < 0 or sleep_time > 24:
            return None
    except ValueError:
        try:
            hours, minutes = time_str.split(":")
            hours = int(hours)
            minutes = int(minutes)
            if hours < 0 or hours > 23 or minutes < 0 or minutes > 59:
                return None

            sleep_time = hours + minutes / 60.0

            if sleep_time > 24:
                return None
        except ValueError:
            return None

    return round(sleep_time, 2)


def convert_time_to_datetime(time_str: str) -> Optional[datetime.datetime]:
    try:
        hours, minutes = map(int, time_str.split(":"))
        if 0 <= hours < 24 and 0 <= minutes < 60:
            today_date_time = datetime.datetime.now()
            return today_date_time.replace(
                hour=hours, minute=minutes, second=0, microsecond=0
            )
        else:
            return None
    except ValueError:
        return None


async def create_gym_reminder_notification(
    user_id: str,
    gym_time: datetime.datetime,
) -> None:
    try:
        await Notification.find({
            "user_id": user_id,
            "notification_type": "gym_reminder_notification"
        }).delete()

        # gym_time приходить в часовому поясі користувача (з ранкового опитування)
        user = await User.find_one(User.telegram_id == user_id)
        timezone_offset = user.timezone_offset or 0 if user else 0

        # Конвертуємо час користувача в київський час
        user_hour = gym_time.hour
        user_minute = gym_time.minute

        kyiv_hour = user_hour - timezone_offset
        if kyiv_hour < 0:
            kyiv_hour += 24
        elif kyiv_hour >= 24:
            kyiv_hour -= 24

        kyiv_time_str = f"{kyiv_hour:02d}:{user_minute:02d}"
        user_time_str = gym_time.strftime("%H:%M")

        notification = Notification(
            user_id=user_id,
            notification_time=kyiv_time_str,  # Київський час для scheduler
            notification_time_base=user_time_str,  # Оригінальний час користувача
            notification_text=f"Час тренування: {user_time_str}",
            notification_type="gym_reminder_notification",
            is_active=True,
            system_data={
                "gym_time": user_time_str,
                "created_date": datetime.datetime.now().date().isoformat()
            }
        )
        await notification.save()

        print(
            f"✅ Created gym reminder for user {user_id}: "
            f"user_time={user_time_str}, kyiv_time={kyiv_time_str}, "
            f"offset={timezone_offset}"
        )

    except Exception as e:
        print(f"❌ Failed to create gym reminder notification: {e}")


async def get_active_morning_quiz_for_today(
    user_id: str,
    *,
    is_test: Optional[bool] = None,
) -> Optional[MorningQuiz]:
    user = await User.find_one(User.telegram_id == str(user_id))
    timezone_offset = user.timezone_offset or 0 if user else 0
    now = datetime.datetime.now()
    user_now = now + datetime.timedelta(hours=timezone_offset)
    user_date = user_now.date()
    user_start = datetime.datetime.combine(user_date, datetime.time.min)
    user_end = datetime.datetime.combine(user_date, datetime.time.max)
    start = user_start - datetime.timedelta(hours=timezone_offset)
    end = user_end - datetime.timedelta(hours=timezone_offset)

    query = [
        MorningQuiz.user_id == str(user_id),
        MorningQuiz.completed == False,  # noqa: E712
        MorningQuiz.created_at >= start,
        MorningQuiz.created_at <= end,
    ]
    if is_test is not None:
        query.append(MorningQuiz.is_test == is_test)  # noqa: E712

    quiz = await MorningQuiz.find(*query).sort("-created_at").to_list(1)
    return quiz[0] if quiz else None
