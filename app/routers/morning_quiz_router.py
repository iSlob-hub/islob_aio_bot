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
from app.db.models import MorningQuiz, User
import datetime
from app.keyboards import get_main_menu_keyboard
from app.utils.text_templates import get_template, format_template
from app.utils.morning_quiz_utils import (
    validate_transform_time,
    convert_time_to_datetime,
    create_gym_reminder_notification,
    get_active_morning_quiz_for_today,
)

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


async def _safe_send_message(
    message: Message,
    text: str,
    reply_markup=None,
    parse_mode: Optional[str] = "HTML",
) -> None:
    try:
        await message.answer(
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
        )
    except Exception as e:
        # Fallback to plain text if Telegram rejects the markup
        print(f"Fallback to plain text for morning quiz message: {e}")
        await message.answer(text=text, reply_markup=reply_markup)


async def _cleanup_callback_message(callback: CallbackQuery) -> None:
    try:
        await callback.message.delete()
    except Exception:
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass


async def _send_template_message(
    message: Message,
    template_key: str,
    reply_markup=None,
    **kwargs,
) -> None:
    if kwargs:
        text = await format_template(template_key, **kwargs)
    else:
        text = await get_template(template_key)
    await _safe_send_message(message, text=text, reply_markup=reply_markup)


async def _get_quiz_or_reset(state: FSMContext, responder) -> Optional[MorningQuiz]:
    state_data = await state.get_data()
    quiz_id = state_data.get("morning_quiz_id")

    quiz = await MorningQuiz.get(quiz_id) if quiz_id else None
    if not quiz:
        quiz = await get_active_morning_quiz_for_today(responder.from_user.id)
        if quiz:
            await state.update_data(morning_quiz_id=str(quiz.id))
            return quiz

    if not quiz:
        await responder.answer(await get_template("morning_quiz_issue_happened"))
        await state.clear()
        await state.set_state(MainMenuState.main_menu)
        return None
    return quiz


morning_quiz_router = Router()


@morning_quiz_router.callback_query(F.data.startswith("start_morning_quiz_"))
async def morning_quiz_start_handler(callback: CallbackQuery, state: FSMContext):
    morning_quiz_id = callback.data.split("_")[-1]

    morning_quiz = await MorningQuiz.get(morning_quiz_id)
    if not morning_quiz:
        await callback.answer()
        await _cleanup_callback_message(callback)
        await _safe_send_message(
            callback.message,
            text=await get_template("morning_quiz_issue_happened"),
            reply_markup=ReplyKeyboardRemove(),
        )
        return
    if morning_quiz.completed:
        await callback.answer()
        await _cleanup_callback_message(callback)
        await _safe_send_message(
            callback.message,
            text=await get_template("morning_quiz_already_completed"),
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    state_data = await state.get_data()
    current_state = await state.get_state()
    if (
        state_data.get("morning_quiz_id") == morning_quiz_id
        and current_state in {
            MorningQuizStates.waiting_for_how_do_you_feel_today.state,
            MorningQuizStates.waiting_for_how_many_hours_of_sleep.state,
            MorningQuizStates.waiting_for_is_going_to_gym.state,
            MorningQuizStates.waiting_for_gym_attendance_time.state,
            MorningQuizStates.waiting_for_weight.state,
        }
    ):
        await callback.answer()
        return

    await callback.answer()
    await _cleanup_callback_message(callback)
    await state.update_data(morning_quiz_id=morning_quiz_id)

    if morning_quiz.how_do_you_feel_today is None:
        await state.set_state(MorningQuizStates.waiting_for_how_do_you_feel_today)
        keyboard = _feeling_keyboard()
        await _send_template_message(
            callback.message,
            "how_do_you_feel_today",
            reply_markup=keyboard,
        )
        return

    if morning_quiz.how_many_hours_of_sleep is None:
        await state.set_state(MorningQuizStates.waiting_for_how_many_hours_of_sleep)
        await _send_template_message(callback.message, "how_much_sleep_last_night")
        return

    if morning_quiz.is_going_to_gym is None:
        await state.set_state(MorningQuizStates.waiting_for_is_going_to_gym)
        await _send_template_message(
            callback.message,
            "morning_quiz_step2",
            reply_markup=_gym_choice_keyboard(),
            how_do_you_feel_today=morning_quiz.how_do_you_feel_today,
            sleep_time=morning_quiz.how_many_hours_of_sleep,
        )
        return

    if morning_quiz.is_going_to_gym and morning_quiz.gym_attendance_time is None:
        await state.set_state(MorningQuizStates.waiting_for_gym_attendance_time)
        await _send_template_message(
            callback.message,
            "morning_quiz_step31",
            how_do_you_feel_today=morning_quiz.how_do_you_feel_today,
            sleep_time=morning_quiz.how_many_hours_of_sleep,
        )
        return

    if (not morning_quiz.is_going_to_gym) and morning_quiz.weight is None:
        await state.set_state(MorningQuizStates.waiting_for_weight)
        await _send_template_message(
            callback.message,
            "morning_quiz_step32",
            reply_markup=_weight_choice_keyboard(
                await _get_last_weight(str(callback.from_user.id))
            ) or None,
            how_do_you_feel_today=morning_quiz.how_do_you_feel_today,
            sleep_time=morning_quiz.how_many_hours_of_sleep,
        )
        return

    if morning_quiz.weight is None:
        await state.set_state(MorningQuizStates.waiting_for_weight)
        await _send_template_message(
            callback.message,
            "morning_quiz_step41",
            reply_markup=_weight_choice_keyboard(
                await _get_last_weight(str(callback.from_user.id))
            ) or None,
            how_do_you_feel_today=morning_quiz.how_do_you_feel_today,
            sleep_time=morning_quiz.how_many_hours_of_sleep,
            gym_attendance_time=morning_quiz.gym_attendance_time.strftime("%H:%M"),
        )
        return


@morning_quiz_router.callback_query(
    F.data.startswith("how_do_you_feel_"),
    StateFilter(MorningQuizStates.waiting_for_how_do_you_feel_today, MainMenuState.main_menu),
)
async def handle_how_do_you_feel(callback: CallbackQuery, state: FSMContext):
    feeling = callback.data.split("_")[-1]
    morning_quiz = await _get_quiz_or_reset(state, callback.message)
    if not morning_quiz:
        return
    if morning_quiz.how_do_you_feel_today is not None:
        await callback.answer()
        return

    try:
        feeling_value = int(feeling)
    except ValueError:
        feeling_value = None

    if not feeling_value or not 1 <= feeling_value <= 10:
        await callback.answer()
        await _send_template_message(callback.message, "wrong_format_number_1_10")
        return

    morning_quiz.how_do_you_feel_today = feeling_value
    await morning_quiz.save()
    await callback.answer(text= await get_template("your_state_saved"))
    await _cleanup_callback_message(callback)
    await _send_template_message(
        callback.message,
        "morning_quiz_step1",
        feeling=feeling_value,
    )

    await state.set_state(MorningQuizStates.waiting_for_how_many_hours_of_sleep)

    await _send_template_message(callback.message, "how_much_sleep_last_night")


@morning_quiz_router.message(
    StateFilter(MorningQuizStates.waiting_for_how_many_hours_of_sleep)
)
async def handle_how_many_hours_of_sleep(message: Message, state: FSMContext):
    sleep_time_str = message.text.strip()
    sleep_time = validate_transform_time(sleep_time_str)

    if sleep_time is None:
        await _send_template_message(message, "invalid_time")
        return

    morning_quiz = await _get_quiz_or_reset(state, message)
    if not morning_quiz:
        return
    morning_quiz.how_many_hours_of_sleep = sleep_time
    await morning_quiz.save()

    await _send_template_message(
        message,
        "morning_quiz_step2",
        reply_markup=_gym_choice_keyboard(),
        how_do_you_feel_today=morning_quiz.how_do_you_feel_today,
        sleep_time=sleep_time,
    )

    await state.set_state(MorningQuizStates.waiting_for_is_going_to_gym)


@morning_quiz_router.callback_query(
    F.data.startswith("is_going_to_gym_"),
    StateFilter(MorningQuizStates.waiting_for_is_going_to_gym, MainMenuState.main_menu),
)
async def handle_is_going_to_gym(callback: CallbackQuery, state: FSMContext):
    is_going_to_gym = callback.data.split("_")[-1] == "yes"
    morning_quiz = await _get_quiz_or_reset(state, callback.message)
    if not morning_quiz:
        return
    if morning_quiz.is_going_to_gym is not None:
        await callback.answer()
        return

    morning_quiz.is_going_to_gym = is_going_to_gym
    await morning_quiz.save()
    await callback.answer(
        text=await get_template("going_to_gym" if is_going_to_gym else "not_going_to_gym")
    )
    await _cleanup_callback_message(callback)

    if is_going_to_gym:
        await _send_template_message(
            callback.message,
            "morning_quiz_step31",
            how_do_you_feel_today=morning_quiz.how_do_you_feel_today,
            sleep_time=morning_quiz.how_many_hours_of_sleep,
        )
        await state.set_state(MorningQuizStates.waiting_for_gym_attendance_time)
    else:
        await _send_template_message(
            callback.message,
            "morning_quiz_step32",
            reply_markup=_weight_choice_keyboard(
                await _get_last_weight(str(callback.from_user.id))
            ) or None,
            how_do_you_feel_today=morning_quiz.how_do_you_feel_today,
            sleep_time=morning_quiz.how_many_hours_of_sleep,
        )
        await state.set_state(MorningQuizStates.waiting_for_weight)


@morning_quiz_router.message(
    StateFilter(MorningQuizStates.waiting_for_gym_attendance_time)
)
async def handle_gym_attendance_time(message: Message, state: FSMContext):
    gym_attendance_time = message.text.strip()
    if not gym_attendance_time:
        await _send_template_message(message, "enter_gym_attendance_time")
        return

    gym_attendance_time_dt = convert_time_to_datetime(gym_attendance_time)
    if gym_attendance_time_dt is None:
        await _send_template_message(message, "invalid_time")
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
    await _send_template_message(
        message,
        "morning_quiz_step41",
        reply_markup=_weight_choice_keyboard(last_weight) or None,
        how_do_you_feel_today=morning_quiz.how_do_you_feel_today,
        sleep_time=morning_quiz.how_many_hours_of_sleep,
        gym_attendance_time=gym_attendance_time_dt.strftime("%H:%M"),
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
        await _safe_send_message(
            responder,
            text=await format_template(
                "morning_quiz_step5",
                how_do_you_feel_today=morning_quiz.how_do_you_feel_today,
                sleep_time=morning_quiz.how_many_hours_of_sleep,
                is_going_to_gym="Так",
                gym_attendance_time=gym_time_str,
                gym_attendance_time_text=gym_time_text,
                weight=weight_display,
            ),
            reply_markup=await get_main_menu_keyboard(),
        )
    else:
        await _safe_send_message(
            responder,
            text=await format_template(
                "morning_quiz_step51",
                how_do_you_feel_today=morning_quiz.how_do_you_feel_today,
                sleep_time=morning_quiz.how_many_hours_of_sleep,
                is_going_to_gym="Ні",
                gym_attendance_time_text=gym_time_text,
                weight=weight_display,
            ),
            reply_markup=await get_main_menu_keyboard(),
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
        await _send_template_message(message, "invalid_weight")
        return
    

    if weight > 200 or weight < 40:
        await _send_template_message(message, "invalid_weight")
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
    StateFilter(MorningQuizStates.waiting_for_weight, MainMenuState.main_menu),
)
async def skip_weight(callback: CallbackQuery, state: FSMContext) -> None:
    if await _get_last_weight(str(callback.from_user.id)) is None:
        await callback.answer("Спочатку введи свою вагу", show_alert=True)
        return

    morning_quiz = await _get_quiz_or_reset(state, callback.message)
    if not morning_quiz:
        return
    if morning_quiz.completed or morning_quiz.weight is not None:
        await callback.answer()
        return
    await callback.answer(text="Пропустили вагу")
    await _cleanup_callback_message(callback)
    await _finish_morning_quiz(
        responder=callback.message,
        state=state,
        morning_quiz=morning_quiz,
        weight_value=None,
        weight_display="—",
    )


@morning_quiz_router.callback_query(
    F.data.startswith("use_prev_weight_"),
    StateFilter(MorningQuizStates.waiting_for_weight, MainMenuState.main_menu),
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
    if morning_quiz.completed or morning_quiz.weight is not None:
        await callback.answer()
        return
    await callback.answer(text=f"Використовую {previous_weight:.1f} кг")
    await _cleanup_callback_message(callback)
    await _finish_morning_quiz(
        responder=callback.message,
        state=state,
        morning_quiz=morning_quiz,
        weight_value=previous_weight,
        weight_display=f"{previous_weight}",
    )
