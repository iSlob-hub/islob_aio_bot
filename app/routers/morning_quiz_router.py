from aiogram import Router, F
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardRemove,
)
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from typing import Optional
from app.states import MorningQuizStates
from app.routers.main_router import MainMenuState
from app.db.models import MorningQuiz, Notification, NotificationType, User
import datetime
import os
from app.keyboards import get_main_menu_keyboard
from app.utils.text_templates import get_template, format_template

async def _get_last_weight(user_id: str) -> Optional[float]:
    """
    Return last recorded weight for the user if exists.
    """
    last_quiz = await MorningQuiz.find(
        MorningQuiz.user_id == user_id,
        MorningQuiz.weight != None  # noqa: E711
    ).sort("-created_at").to_list(1)
    if last_quiz:
        return last_quiz[0].weight
    return None


def _weight_choice_keyboard(last_weight: Optional[float]) -> Optional[InlineKeyboardMarkup]:
    # Only show choices when we have at least one recorded weight
    if last_weight is None:
        return None

    buttons = [
        InlineKeyboardButton(
            text=f"Попередня ({last_weight:.1f} кг)",
            callback_data=f"use_prev_weight_{last_weight}",
        ),
    ]
    return InlineKeyboardMarkup(inline_keyboard=[buttons])


def _feeling_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="1", callback_data="how_do_you_feel_1"),
                InlineKeyboardButton(text="2", callback_data="how_do_you_feel_2"),
                InlineKeyboardButton(text="3", callback_data="how_do_you_feel_3"),
                InlineKeyboardButton(text="4", callback_data="how_do_you_feel_4"),
                InlineKeyboardButton(text="5", callback_data="how_do_you_feel_5"),
            ],
            [
                InlineKeyboardButton(text="6", callback_data="how_do_you_feel_6"),
                InlineKeyboardButton(text="7", callback_data="how_do_you_feel_7"),
                InlineKeyboardButton(text="8", callback_data="how_do_you_feel_8"),
                InlineKeyboardButton(text="9", callback_data="how_do_you_feel_9"),
                InlineKeyboardButton(text="10", callback_data="how_do_you_feel_10"),
            ],
        ]
    )


def _gym_choice_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Так", callback_data="is_going_to_gym_yes"),
                InlineKeyboardButton(text="Ні", callback_data="is_going_to_gym_no"),
            ]
        ]
    )


async def _edit_or_answer(callback: CallbackQuery, text: str, reply_markup=None) -> None:
    try:
        await callback.message.edit_text(text=text, reply_markup=reply_markup)
    except Exception as e:
        # Some clients silently drop edit errors; fall back to a fresh message
        print(f"Fallback to answer for morning quiz message: {e}")
        await callback.message.answer(text=text, reply_markup=reply_markup)


async def _get_quiz_or_reset(state: FSMContext, responder) -> Optional[MorningQuiz]:
    state_data = await state.get_data()
    quiz_id = state_data.get("morning_quiz_id")
    if not quiz_id:
        await responder.answer(await get_template("morning_quiz_issue_happened"))
        await state.clear()
        await state.set_state(MainMenuState.main_menu)
        return None

    quiz = await MorningQuiz.get(quiz_id)
    if not quiz:
        await responder.answer(await get_template("morning_quiz_issue_happened"))
        await state.clear()
        await state.set_state(MainMenuState.main_menu)
        return None
    return quiz


async def create_gym_reminder_notification(user_id: str, gym_time: datetime.datetime):
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
        
        print(f"✅ Created gym reminder for user {user_id}: user_time={user_time_str}, kyiv_time={kyiv_time_str}, offset={timezone_offset}")
        
    except Exception as e:
        print(f"❌ Failed to create gym reminder notification: {e}")


morning_quiz_router = Router()


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


@morning_quiz_router.callback_query(F.data.startswith("start_morning_quiz_"))
async def morning_quiz_start_handler(callback: CallbackQuery, state: FSMContext):
    morning_quiz_id = callback.data.split("_")[-1]

    morning_quiz = await MorningQuiz.get(morning_quiz_id)
    if morning_quiz.completed:
        await callback.message.edit_text(
            text= await get_template("morning_quiz_already_completed"),
            reply_markup=ReplyKeyboardRemove(),
        )
        await callback.answer()
        return

    await callback.answer()
    await state.set_state(MorningQuizStates.waiting_for_how_do_you_feel_today)
    await state.update_data(morning_quiz_id=morning_quiz_id)
    keyboard = _feeling_keyboard()
    await _edit_or_answer(
        callback,
        text=await get_template("how_do_you_feel_today"),
        reply_markup=keyboard,
    )


@morning_quiz_router.callback_query(
    F.data.startswith("how_do_you_feel_"),
    StateFilter(MorningQuizStates.waiting_for_how_do_you_feel_today),
)
async def handle_how_do_you_feel(callback: CallbackQuery, state: FSMContext):
    feeling = callback.data.split("_")[-1]
    morning_quiz = await _get_quiz_or_reset(state, callback.message)
    if not morning_quiz:
        return

    try:
        feeling_value = int(feeling)
    except ValueError:
        feeling_value = None

    if not feeling_value or not 1 <= feeling_value <= 10:
        await _edit_or_answer(
            callback,
            text=await get_template("wrong_format_number_1_10"),
        )
        return

    morning_quiz.how_do_you_feel_today = feeling_value
    await morning_quiz.save()
    await callback.answer(text= await get_template("your_state_saved"))
    await _edit_or_answer(
        callback,
        text=await format_template("morning_quiz_step1", feeling=feeling_value),
    )

    await state.set_state(MorningQuizStates.waiting_for_how_many_hours_of_sleep)

    await callback.message.answer(
        text= await get_template("how_much_sleep_last_night"),
    )


@morning_quiz_router.message(
    StateFilter(MorningQuizStates.waiting_for_how_many_hours_of_sleep)
)
async def handle_how_many_hours_of_sleep(message: Message, state: FSMContext):
    sleep_time_str = message.text.strip()
    sleep_time = validate_transform_time(sleep_time_str)

    if sleep_time is None:
        await message.answer(
            text= await get_template("invalid_time"),
        )
        return

    morning_quiz = await _get_quiz_or_reset(state, message)
    if not morning_quiz:
        return
    morning_quiz.how_many_hours_of_sleep = sleep_time
    await morning_quiz.save()

    await message.answer(
        text= await format_template(
            "morning_quiz_step2",
            how_do_you_feel_today=morning_quiz.how_do_you_feel_today,
            sleep_time=sleep_time
        ),
        reply_markup=_gym_choice_keyboard(),
        parse_mode="HTML",
    )

    await state.set_state(MorningQuizStates.waiting_for_is_going_to_gym)


@morning_quiz_router.callback_query(
    F.data.startswith("is_going_to_gym_"),
    StateFilter(MorningQuizStates.waiting_for_is_going_to_gym),
)
async def handle_is_going_to_gym(callback: CallbackQuery, state: FSMContext):
    is_going_to_gym = callback.data.split("_")[-1] == "yes"
    morning_quiz = await _get_quiz_or_reset(state, callback.message)
    if not morning_quiz:
        return

    morning_quiz.is_going_to_gym = is_going_to_gym
    await morning_quiz.save()
    await callback.answer(
        text=await get_template("going_to_gym" if is_going_to_gym else "not_going_to_gym")
    )

    if is_going_to_gym:
        await callback.message.answer(
            text= await format_template("morning_quiz_step31",
                how_do_you_feel_today=morning_quiz.how_do_you_feel_today,
                sleep_time=morning_quiz.how_many_hours_of_sleep
            ),
        )
        await state.set_state(MorningQuizStates.waiting_for_gym_attendance_time)
    else:
        await _edit_or_answer(
            callback,
            text= await format_template("morning_quiz_step32",
                how_do_you_feel_today=morning_quiz.how_do_you_feel_today,
                sleep_time=morning_quiz.how_many_hours_of_sleep
            ),
            reply_markup=_weight_choice_keyboard(
                await _get_last_weight(str(callback.from_user.id))
            ) or None,
        )
        await state.set_state(MorningQuizStates.waiting_for_weight)


@morning_quiz_router.message(
    StateFilter(MorningQuizStates.waiting_for_gym_attendance_time)
)
async def handle_gym_attendance_time(message: Message, state: FSMContext):
    gym_attendance_time = message.text.strip()
    if not gym_attendance_time:
        await message.answer( await get_template("enter_gym_attendance_time") )
        return

    gym_attendance_time_dt = convert_time_to_datetime(gym_attendance_time)
    if gym_attendance_time_dt is None:
        await message.answer(
            await get_template("invalid_time")
        )
        return

    morning_quiz = await _get_quiz_or_reset(state, message)
    if not morning_quiz:
        return
    morning_quiz.gym_attendance_time = gym_attendance_time_dt
    await morning_quiz.save()
    # Create reminder right after time is provided, even if the quiz is not finished
    await create_gym_reminder_notification(
        user_id=str(message.from_user.id),
        gym_time=gym_attendance_time_dt
    )
    last_weight = await _get_last_weight(str(message.from_user.id))
    await message.answer(
        text= await format_template("morning_quiz_step41",
            how_do_you_feel_today=morning_quiz.how_do_you_feel_today,
            sleep_time=morning_quiz.how_many_hours_of_sleep,
            gym_attendance_time=gym_attendance_time_dt.strftime("%H:%M")
        ),
        parse_mode="HTML",
        reply_markup=_weight_choice_keyboard(last_weight) or None,
    )
    await state.set_state(MorningQuizStates.waiting_for_weight)


async def _finish_morning_quiz(
    responder,
    state: FSMContext,
    morning_quiz: MorningQuiz,
    weight_value: Optional[float],
    weight_display: str,
) -> None:
    gym_time_str = (
        morning_quiz.gym_attendance_time.strftime("%H:%M")
        if morning_quiz.gym_attendance_time
        else ""
    )
    gym_time_text = (
        f"Час відвідування спортзалу: <b>{gym_time_str}</b>.\n"
        if morning_quiz.is_going_to_gym and gym_time_str
        else ""
    )

    if morning_quiz.is_going_to_gym and morning_quiz.gym_attendance_time:
        await responder.answer(
            text= await format_template(
                "morning_quiz_step5",
                how_do_you_feel_today=morning_quiz.how_do_you_feel_today,
                sleep_time=morning_quiz.how_many_hours_of_sleep,
                is_going_to_gym="Так",
                gym_attendance_time=gym_time_str,
                gym_attendance_time_text=gym_time_text,
                weight=weight_display
            ),
            parse_mode="HTML", reply_markup=await get_main_menu_keyboard()
        )
    else:
        await responder.answer(
            text= await format_template("morning_quiz_step51",
                how_do_you_feel_today=morning_quiz.how_do_you_feel_today,
                sleep_time=morning_quiz.how_many_hours_of_sleep,
                is_going_to_gym="Ні",
                gym_attendance_time_text=gym_time_text,
                weight=weight_display
            ),
            parse_mode="HTML", reply_markup=await get_main_menu_keyboard()
        )
    
    morning_quiz.weight = weight_value
    morning_quiz.completed = True
    await morning_quiz.save()

    # Створюємо нагадування про тренування, якщо користувач планує йти в зал
    if morning_quiz.is_going_to_gym and morning_quiz.gym_attendance_time:
        await create_gym_reminder_notification(
            user_id=str(responder.from_user.id),
            gym_time=morning_quiz.gym_attendance_time
        )

    await state.clear()
    await state.set_state(MainMenuState.main_menu)


@morning_quiz_router.message(StateFilter(MorningQuizStates.waiting_for_weight))
async def handle_weight(message: Message, state: FSMContext):
    weight_str = message.text.strip()
    try:
        weight = float(weight_str)
    except ValueError:
        await message.answer(await get_template("invalid_weight"))
        return
    

    if  weight > 150 or weight < 30:
        await message.answer(await get_template("invalid_weight"))
        return

    morning_quiz = await _get_quiz_or_reset(state, message)
    if not morning_quiz:
        return
    await _finish_morning_quiz(
        responder=message,
        state=state,
        morning_quiz=morning_quiz,
        weight_value=weight,
        weight_display=f"{weight}",
    )


@morning_quiz_router.callback_query(
    F.data == "skip_weight",
    StateFilter(MorningQuizStates.waiting_for_weight),
)
async def skip_weight(callback: CallbackQuery, state: FSMContext) -> None:
    if await _get_last_weight(str(callback.from_user.id)) is None:
        await callback.answer("Спочатку введи свою вагу", show_alert=True)
        return

    morning_quiz = await _get_quiz_or_reset(state, callback.message)
    if not morning_quiz:
        return
    await callback.answer(text="Пропустили вагу")
    await _finish_morning_quiz(
        responder=callback.message,
        state=state,
        morning_quiz=morning_quiz,
        weight_value=None,
        weight_display="—",
    )


@morning_quiz_router.callback_query(
    F.data.startswith("use_prev_weight_"),
    StateFilter(MorningQuizStates.waiting_for_weight),
)
async def use_previous_weight(callback: CallbackQuery, state: FSMContext) -> None:
    last_weight = await _get_last_weight(str(callback.from_user.id))
    if last_weight is None:
        await callback.answer("Спочатку введи свою вагу", show_alert=True)
        return

    try:
        previous_weight = float(callback.data.removeprefix("use_prev_weight_"))
    except ValueError:
        await callback.answer(await get_template("invalid_weight"), show_alert=True)
        return

    morning_quiz = await _get_quiz_or_reset(state, callback.message)
    if not morning_quiz:
        return
    await callback.answer(text=f"Використовую {previous_weight:.1f} кг")
    await _finish_morning_quiz(
        responder=callback.message,
        state=state,
        morning_quiz=morning_quiz,
        weight_value=previous_weight,
        weight_display=f"{previous_weight}",
    )
