from aiogram import Router, F
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardRemove,
    URLInputFile,
)
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
import app.text_constants as tc
from app.routers.main_router import MainMenuState
from app.states import TrainingState, AfterTrainingState
from app.db.models import TrainingSession, Notification, User, NotificationType
from app.keyboards import get_main_menu_keyboard
from app.config import settings
import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import app.keyboards as kb
from app.utils.text_templates import sync_get_template, get_template, format_template

import os
from dotenv import load_dotenv

load_dotenv()


app_root = Path(__file__).resolve().parent.parent


training_router = Router()


@training_router.message(
    F.text == sync_get_template("start_training_button"), StateFilter(MainMenuState.training_menu)
)
async def start_training(message: Message, state: FSMContext) -> None:
    # remove reply keyboard if it exists
    await message.answer(
        text=await get_template("lets_start_training"),
        reply_markup=ReplyKeyboardRemove(),
    )

    await message.answer(
        text=await get_template("how_do_you_feel_before_training"),
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="1", callback_data="how_do_you_feel_before_1"
                    ),
                    InlineKeyboardButton(
                        text="2", callback_data="how_do_you_feel_before_2"
                    ),
                    InlineKeyboardButton(
                        text="3", callback_data="how_do_you_feel_before_3"
                    ),
                    InlineKeyboardButton(
                        text="4", callback_data="how_do_you_feel_before_4"
                    ),
                    InlineKeyboardButton(
                        text="5", callback_data="how_do_you_feel_before_5"
                    ),
                ],
                [
                    InlineKeyboardButton(
                        text="6", callback_data="how_do_you_feel_before_6"
                    ),
                    InlineKeyboardButton(
                        text="7", callback_data="how_do_you_feel_before_7"
                    ),
                    InlineKeyboardButton(
                        text="8", callback_data="how_do_you_feel_before_8"
                    ),
                    InlineKeyboardButton(
                        text="9", callback_data="how_do_you_feel_before_9"
                    ),
                    InlineKeyboardButton(
                        text="10", callback_data="how_do_you_feel_before_10"
                    ),
                ],
            ]
        ),
    )
    await state.set_state(TrainingState.how_do_you_feel_before)


@training_router.message(
    F.text == sync_get_template("back_to_main_menu_button"), StateFilter(MainMenuState.training_menu)
)
async def back_to_main_menu(message: Message, state: FSMContext) -> None:
    await message.answer(
        text=await get_template("back_to_main_menu"),
        reply_markup=await kb.get_main_menu_keyboard(),
    )
    await state.set_state(MainMenuState.main_menu)


@training_router.callback_query(
    F.data.startswith("how_do_you_feel_before_"),
    StateFilter(TrainingState.how_do_you_feel_before),
)
async def handle_how_do_you_feel_before(
    callback_query: CallbackQuery, state: FSMContext
) -> None:
    rating = callback_query.data.split("_")[-1]
    training_session = TrainingSession(
        user_id=str(callback_query.from_user.id),
        how_do_you_feel_before=int(rating),
        training_started_at=datetime.datetime.now(tz=ZoneInfo("UTC")),  # Використовуємо UTC
    )
    user = await User.find_one(User.telegram_id == str(callback_query.from_user.id))

    await training_session.save()
    training_session_id = training_session.id

    # Перевіряємо чи є файл тренування у користувача
    if user.training_file_url:
        base_host = settings.BASE_HOST  # Використовуємо settings замість os.environ
        print(f"DEBUG: BASE_HOST = {base_host}, training_file_url = {user.training_file_url}")
        if base_host:
            try:
                full_url = f"{base_host}{user.training_file_url}"
                print(f"DEBUG: Full URL = {full_url}")
                training_pdf = URLInputFile(
                    url=full_url,
                    filename="training_session.pdf",
                )
                
                await callback_query.message.answer_document(
                    document=training_pdf, caption=await get_template("here_is_your_training_file")
                )
                print(f"DEBUG: Successfully sent training PDF to {callback_query.from_user.id}")
            except Exception as e:
                print(f"Failed to send training PDF: {e}")
                await callback_query.message.answer(
                    text=await get_template("training_file_unavailable")
                )
        else:
            print("DEBUG: BASE_HOST is empty or None")
            await callback_query.message.answer(
                text=await get_template("training_file_unavailable")
            )
    else:
        print(f"DEBUG: User {callback_query.from_user.id} has no training_file_url")
        await callback_query.message.answer(
            text=await get_template("training_file_unavailable")
        )

    await callback_query.message.answer(
        text=await get_template("start_your_training"),
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=await get_template("finish_training_button"),
                        callback_data=f"finish_training_{training_session_id}",
                    )
                ]
            ]
        ),
    )

    await callback_query.answer()

    await state.set_state(TrainingState.training_started)


@training_router.callback_query(
    F.data.startswith("finish_training_"),
    StateFilter(TrainingState.training_started),
)
async def finish_training(callback_query: CallbackQuery, state: FSMContext) -> None:
    training_session_id = callback_query.data.split("_")[-1]
    training_session = await TrainingSession.get(training_session_id)

    await state.update_data(training_session_id=training_session_id)

    if not training_session:
        await callback_query.message.answer(await get_template("training_not_found"))
        return

    training_session.training_ended_at = datetime.datetime.now(
        tz=ZoneInfo("UTC")  # Використовуємо UTC
    )

    # Спрощена логіка - переконуємось що обидва часи в UTC
    if training_session.training_started_at.tzinfo is None:
        # Якщо training_started_at наївний, вважаємо що це UTC
        training_session.training_started_at = training_session.training_started_at.replace(
            tzinfo=ZoneInfo("UTC")
        )
    else:
        # Якщо має timezone, конвертуємо в UTC
        training_session.training_started_at = (
            training_session.training_started_at.astimezone(ZoneInfo("UTC"))
        )

    # Розраховуємо тривалість
    duration_seconds = (
        training_session.training_ended_at - training_session.training_started_at
    ).total_seconds()
    
    # Додаткова перевірка - якщо різниця негативна або дуже велика, щось не так
    if duration_seconds < 0:
        print(f"WARNING: Negative duration! Started: {training_session.training_started_at}, Ended: {training_session.training_ended_at}")
        duration_seconds = 60  # Встановлюємо 1 хвилину як резервне значення
    elif duration_seconds > 86400:  # Більше 24 годин
        print(f"WARNING: Duration too long ({duration_seconds/3600:.1f} hours)! Started: {training_session.training_started_at}, Ended: {training_session.training_ended_at}")
        duration_seconds = 3600  # Встановлюємо 1 годину як максимум
    
    training_session.training_duration = max(1, int(round(duration_seconds / 60, 0)))

    # Відладкова інформація
    print(f"DEBUG: Training started at (UTC): {training_session.training_started_at}")
    print(f"DEBUG: Training ended at (UTC): {training_session.training_ended_at}")
    print(f"DEBUG: Raw duration in seconds: {duration_seconds}")
    print(f"DEBUG: Final duration in minutes: {training_session.training_duration}")

    await training_session.save()

    await callback_query.answer()

    await callback_query.message.answer(
        text=await get_template("how_hard_was_training"),
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="1", callback_data="how_hard_was_training_1"
                    ),
                    InlineKeyboardButton(
                        text="2", callback_data="how_hard_was_training_2"
                    ),
                    InlineKeyboardButton(
                        text="3", callback_data="how_hard_was_training_3"
                    ),
                    InlineKeyboardButton(
                        text="4", callback_data="how_hard_was_training_4"
                    ),
                    InlineKeyboardButton(
                        text="5", callback_data="how_hard_was_training_5"
                    ),
                ],
                [
                    InlineKeyboardButton(
                        text="6", callback_data="how_hard_was_training_6"
                    ),
                    InlineKeyboardButton(
                        text="7", callback_data="how_hard_was_training_7"
                    ),
                    InlineKeyboardButton(
                        text="8", callback_data="how_hard_was_training_8"
                    ),
                    InlineKeyboardButton(
                        text="9", callback_data="how_hard_was_training_9"
                    ),
                    InlineKeyboardButton(
                        text="10", callback_data="how_hard_was_training_10"
                    ),
                ],
            ]
        ),
    )
    await state.set_state(TrainingState.how_hard_was_training)


@training_router.callback_query(
    F.data.startswith("how_hard_was_training_"),
    StateFilter(TrainingState.how_hard_was_training),
)
async def handle_how_hard_was_training(
    callback_query: CallbackQuery, state: FSMContext
) -> None:
    rating = callback_query.data.split("_")[-1]
    state_data = await state.get_data()
    training_session_id = state_data.get("training_session_id")
    training_session = await TrainingSession.get(training_session_id)

    if not training_session:
        await callback_query.message.answer(await get_template("training_not_found"))
        return

    training_session.how_hard_was_training = int(rating)
    await training_session.save()

    await callback_query.answer()

    await callback_query.message.edit_text(
        text=await get_template("do_you_have_any_pain"),
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Так", callback_data="do_you_have_any_pain_yes"
                    ),
                    InlineKeyboardButton(
                        text="Ні", callback_data="do_you_have_any_pain_no"
                    ),
                ]
            ]
        ),
    )
    await state.set_state(TrainingState.do_you_have_any_pain)


@training_router.callback_query(
    F.data.startswith("do_you_have_any_pain_"),
    StateFilter(TrainingState.do_you_have_any_pain),
)
async def handle_do_you_have_any_pain(
    callback_query: CallbackQuery, state: FSMContext
) -> None:
    answer = callback_query.data.split("_")[-1]
    state_data = await state.get_data()
    training_session_id = state_data.get("training_session_id")
    training_session = await TrainingSession.get(training_session_id)

    if not training_session:
        await callback_query.message.answer(await get_template("training_not_found"))
        return

    training_session.do_you_have_any_pain = answer == "yes"
    await training_session.save()

    if training_session.do_you_have_any_pain:
        admin_chat_id = os.getenv("ADMIN_CHAT_ID")
        await callback_query.bot.send_message(
            chat_id=admin_chat_id,
            text=(
                f"Користувач {callback_query.from_user.full_name} @{callback_query.from_user.username} "
                f"({callback_query.from_user.id}) відчуває біль після тренування."
            ),
        )

    await callback_query.message.edit_text(
        text=await format_template("thank_you_for_training", duration=f"{training_session.training_duration:.2f} хвилин")

    )

    # Create a new after training notification for this specific training session
    from datetime import datetime, timedelta
    from zoneinfo import ZoneInfo
    
    next_day = datetime.now(ZoneInfo("UTC")) + timedelta(days=1)
    next_day_date = next_day.date()
    
    # Отримуємо користувача для таймзони
    user = await User.find_one(User.telegram_id == str(callback_query.from_user.id))
    timezone_offset = user.timezone_offset or 0 if user else 0
    
    # Get user's default notification time from template notification or use 15:00
    default_time = "15:00"
    template_notification = await Notification.find_one(
        {
            "user_id": str(callback_query.from_user.id),
            "notification_type": "after_training_notification",
            "system_data.is_template": True
        }
    )
    if template_notification:
        default_time = template_notification.notification_time
    else:
        # Create template if it doesn't exist (for existing users)
        # Для шаблону використовуємо київський час, а base буде null
        template_notification = Notification(
            user_id=str(callback_query.from_user.id),
            notification_time="15:00",
            notification_time_base="15:00",  # За замовчуванням той самий час
            notification_text="Шаблон сповіщення після тренування",
            notification_type=NotificationType.AFTER_TRAINING_NOTIFICATION,
            is_active=False,
            system_data={"is_template": True}
        )
        await template_notification.save()
        print(f"Created template notification for existing user {callback_query.from_user.id}")
    
    # Розраховуємо notification_time_base (час в таймзоні користувача)
    try:
        kyiv_hour, kyiv_minute = map(int, default_time.split(':'))
        user_hour = kyiv_hour + timezone_offset
        
        if user_hour < 0:
            user_hour += 24
        elif user_hour >= 24:
            user_hour -= 24
        
        user_time_str = f"{user_hour:02d}:{kyiv_minute:02d}"
    except ValueError:
        user_time_str = default_time  # Fallback
    
    # Create a new notification for this specific training session
    after_training_notification = Notification(
        user_id=str(callback_query.from_user.id),
        notification_time=default_time,  # Київський час
        notification_time_base=user_time_str,  # Час користувача
        notification_text="Опитування після тренування",
        notification_type=NotificationType.AFTER_TRAINING_NOTIFICATION,
        is_active=True,
        system_data={
            "training_session_id": str(training_session.id),
            "scheduled_date": next_day_date.isoformat(),
            "sent": False,
            "created_for_training": str(training_session.id)  # Для ідентифікації в адмінці
        }
    )
    await after_training_notification.save()
    print(f"DEBUG: Created new after-training notification for user {callback_query.from_user.id} on {next_day_date} for training {training_session.id}")

    # Remove any existing training time notifications for user
    training_time_notifications = await Notification.find(
        {
            "user_id": str(callback_query.from_user.id),
            "notification_type": "gym_reminder_notification",
            "is_active": True
        }
    ).to_list()
    for notif in training_time_notifications:
        notif.is_active = False
        await notif.save()
        print(f"Deactivated training time notification {notif.id} for user {callback_query.from_user.id}")

    training_session.completed = True
    await training_session.save()

    await callback_query.message.answer(
        text=await get_template("back_to_main_menu"),
        reply_markup=await get_main_menu_keyboard(),
    )

    await callback_query.answer()
    await state.clear()
    await state.set_state(MainMenuState.main_menu)


@training_router.callback_query(
    F.data.startswith("start_after_training_quiz_"),
)
async def after_training_quiz(callback_query: CallbackQuery, state: FSMContext) -> None:
    training_session_id = callback_query.data.split("_")[-1]
    training_session = await TrainingSession.get(training_session_id)

    if not training_session:
        await callback_query.message.answer(await get_template("training_not_found"))
        return

    await callback_query.message.edit_text(
        text=await get_template("do_you_have_soreness"),
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Так", callback_data="do_you_have_soreness_yes"
                    ),
                    InlineKeyboardButton(
                        text="Ні", callback_data="do_you_have_soreness_no"
                    ),
                ]
            ]
        ),
    )
    await state.update_data(training_session_id=training_session_id)
    await state.set_state(AfterTrainingState.do_you_have_soreness)


@training_router.callback_query(
    F.data.startswith("do_you_have_soreness_"),
    StateFilter(AfterTrainingState.do_you_have_soreness),
)
async def handle_do_you_have_soreness(
    callback_query: CallbackQuery, state: FSMContext
) -> None:
    answer = callback_query.data.split("_")[-1]
    state_data = await state.get_data()
    training_session_id = state_data.get("training_session_id")
    training_session = await TrainingSession.get(training_session_id)

    if not training_session:
        await callback_query.message.answer(await get_template("training_not_found"))
        return

    training_session.do_you_have_soreness = answer == "yes"
    await training_session.save()

    if training_session.do_you_have_soreness:
        admin_chat_id = os.getenv("ADMIN_CHAT_ID")
        await callback_query.bot.send_message(
            chat_id=admin_chat_id,
            text=(
                f"Користувач {callback_query.from_user.full_name} @{callback_query.from_user.username} "
                f"({callback_query.from_user.id}) відчуває крепатуру після тренування."
            ),
        )

    await callback_query.message.edit_text(
        text=await get_template("stress_level_prompt"),
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="1", callback_data="stress_level_1"
                    ),
                    InlineKeyboardButton(
                        text="2", callback_data="stress_level_2"
                    ),
                    InlineKeyboardButton(
                        text="3", callback_data="stress_level_3"
                    ),
                    InlineKeyboardButton(
                        text="4", callback_data="stress_level_4"
                    ),
                    InlineKeyboardButton(
                        text="5", callback_data="stress_level_5"
                    ),
                ],
                [
                    InlineKeyboardButton(
                        text="6", callback_data="stress_level_6"
                    ),
                    InlineKeyboardButton(
                        text="7", callback_data="stress_level_7"
                    ),
                    InlineKeyboardButton(
                        text="8", callback_data="stress_level_8"
                    ),
                    InlineKeyboardButton(
                        text="9", callback_data="stress_level_9"
                    ),
                    InlineKeyboardButton(
                        text="10", callback_data="stress_level_10"
                    ),
                ],
            ]
        ),
    )
    await state.set_state(AfterTrainingState.stress_level)


@training_router.callback_query(
    F.data.startswith("stress_level_"),
    StateFilter(AfterTrainingState.stress_level),
)
async def handle_stress_level(callback_query: CallbackQuery, state: FSMContext) -> None:
    stress_level = int(callback_query.data.split("_")[-1])
    state_data = await state.get_data()
    training_session_id = state_data.get("training_session_id")
    training_session = await TrainingSession.get(training_session_id)

    if not training_session:
        await callback_query.message.answer(await get_template("training_not_found"))
        return

    training_session.stress_level = stress_level
    await training_session.save()

    # After training quiz completed - notification will be automatically deleted by scheduler
    print(f"After-training quiz completed for user {callback_query.from_user.id}")

    await callback_query.message.answer(
        text=await get_template("thanks_for_your_training_feedback"),
        reply_markup=await get_main_menu_keyboard(),
    )

    await callback_query.answer()
    await state.clear()
    await state.set_state(MainMenuState.main_menu)
