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
from app.db.models import MorningQuiz, Notification, NotificationType
import datetime
from app.keyboards import get_main_menu_keyboard
from app.utils.text_templates import get_template, format_template


async def create_gym_reminder_notification(user_id: str, gym_time: datetime.datetime):
    try:
        await Notification.find({
            "user_id": user_id,
            "notification_type": "gym_reminder_notification"
        }).delete()
        
        reminder_time = gym_time
        
        notification = Notification(
            user_id=user_id,
            notification_time=reminder_time.strftime("%H:%M"),
            notification_text=f"Час тренування: {gym_time.strftime('%H:%M')}",
            notification_type="gym_reminder_notification",
            is_active=True,
            system_data={
                "gym_time": gym_time.strftime("%H:%M"),
                "created_date": datetime.datetime.now().date().isoformat()
            }
        )
        await notification.save()
        
        print(f"✅ Created gym reminder for user {user_id} at {reminder_time.strftime('%H:%M')}")
        
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
    await callback.message.edit_text(
        text= await get_template("how_do_you_feel_today"),
        reply_markup=InlineKeyboardMarkup(
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
        ),
    )


@morning_quiz_router.callback_query(
    F.data.startswith("how_do_you_feel_"),
    StateFilter(MorningQuizStates.waiting_for_how_do_you_feel_today),
)
async def handle_how_do_you_feel(callback: CallbackQuery, state: FSMContext):
    feeling = callback.data.split("_")[-1]
    state_data = await state.get_data()
    morning_quiz_id = state_data.get("morning_quiz_id")
    if not morning_quiz_id:
        await callback.message.edit_text(
            text= await get_template("morning_quiz_issue_happened"),
        )
        await callback.answer()
        await state.clear()
        await state.set_state(MainMenuState.main_menu)
        return

    if not 1 <= int(feeling) <= 10:
        await callback.message.edit_text(
            text = await get_template("wrong_format_number_1_10"),
        )
        await callback.answer()
        return

    morning_quiz = await MorningQuiz.get(morning_quiz_id)

    morning_quiz.how_do_you_feel_today = int(feeling)
    await morning_quiz.save()
    await callback.answer(text= await get_template("your_state_saved"))
    await callback.message.edit_text(
        text = await format_template("morning_quiz_step1", feeling=feeling),
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

    state_data = await state.get_data()
    morning_quiz_id = state_data.get("morning_quiz_id")
    if not morning_quiz_id:
        await message.answer(
            text= await get_template("morning_quiz_issue_happened"),
        )
        await state.clear()
        await state.set_state(MainMenuState.main_menu)
        return

    morning_quiz = await MorningQuiz.get(morning_quiz_id)
    morning_quiz.how_many_hours_of_sleep = sleep_time
    await morning_quiz.save()

    await message.answer(
        text= await format_template(
            "morning_quiz_step2",
            how_do_you_feel_today=morning_quiz.how_do_you_feel_today,
            sleep_time=sleep_time
        ),
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Так", callback_data="is_going_to_gym_yes"
                    ),
                    InlineKeyboardButton(text="Ні", callback_data="is_going_to_gym_no"),
                ]
            ]
        ),
        parse_mode="HTML",
    )

    await state.set_state(MorningQuizStates.waiting_for_is_going_to_gym)


@morning_quiz_router.callback_query(
    F.data.startswith("is_going_to_gym_"),
    StateFilter(MorningQuizStates.waiting_for_is_going_to_gym),
)
async def handle_is_going_to_gym(callback: CallbackQuery, state: FSMContext):
    is_going_to_gym = callback.data.split("_")[-1] == "yes"
    state_data = await state.get_data()
    morning_quiz_id = state_data.get("morning_quiz_id")
    if not morning_quiz_id:
        await callback.message.edit_text(
            text= await get_template("morning_quiz_issue_happened"),
        )
        await callback.answer()
        await state.clear()
        await state.set_state(MainMenuState.main_menu)
        return

    morning_quiz = await MorningQuiz.get(morning_quiz_id)
    morning_quiz.is_going_to_gym = True if is_going_to_gym == "yes" else False
    if is_going_to_gym:
        await callback.answer(text= await get_template("going_to_gym"))
        morning_quiz.is_going_to_gym = True
    else:
        await callback.answer(text= await get_template("not_going_to_gym"))
        morning_quiz.is_going_to_gym = False
    await morning_quiz.save()

    if is_going_to_gym:
        await callback.message.answer(
            text= await format_template("morning_quiz_step31",
                how_do_you_feel_today=morning_quiz.how_do_you_feel_today,
                sleep_time=morning_quiz.how_many_hours_of_sleep
            ),
        )
        await state.set_state(MorningQuizStates.waiting_for_gym_attendance_time)
    else:
        await callback.message.edit_text(
            text= await format_template("morning_quiz_step32",
                how_do_you_feel_today=morning_quiz.how_do_you_feel_today,
                sleep_time=morning_quiz.how_many_hours_of_sleep
            ),
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

    state_data = await state.get_data()
    morning_quiz_id = state_data.get("morning_quiz_id")
    if not morning_quiz_id:
        await message.answer(
            await get_template("morning_quiz_issue_happened")
        )
        await state.clear()
        await state.set_state(MainMenuState.main_menu)
        return
    morning_quiz = await MorningQuiz.get(morning_quiz_id)
    morning_quiz.gym_attendance_time = gym_attendance_time_dt
    await morning_quiz.save()
    await message.answer(
        text= await format_template("morning_quiz_step41",
            how_do_you_feel_today=morning_quiz.how_do_you_feel_today,
            sleep_time=morning_quiz.how_many_hours_of_sleep,
            gym_attendance_time=gym_attendance_time_dt.strftime("%H:%M")
        ),
        parse_mode="HTML",
    )
    await state.set_state(MorningQuizStates.waiting_for_weight)


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


    state_data = await state.get_data()
    morning_quiz_id = state_data.get("morning_quiz_id")
    if not morning_quiz_id:
        await message.answer(
            await get_template("morning_quiz_issue_happened")
        )
        await state.clear()
        await state.set_state(MainMenuState.main_menu)
        return

    morning_quiz = await MorningQuiz.get(morning_quiz_id)
    morning_quiz.weight = weight
    await morning_quiz.save()

    await message.answer(
        text= await format_template("morning_quiz_step5",
            how_do_you_feel_today=morning_quiz.how_do_you_feel_today,
            sleep_time=morning_quiz.how_many_hours_of_sleep,
            is_going_to_gym="Так" if morning_quiz.is_going_to_gym else "Ні",
            gym_attendance_time=morning_quiz.gym_attendance_time.strftime("%H:%M") + "\n" if morning_quiz.is_going_to_gym else "",
            weight=weight
        ),
        parse_mode="HTML", reply_markup=await get_main_menu_keyboard()
    )
    
    morning_quiz.completed = True
    await morning_quiz.save()

    # Створюємо нагадування про тренування, якщо користувач планує йти в зал
    if morning_quiz.is_going_to_gym and morning_quiz.gym_attendance_time:
        await create_gym_reminder_notification(
            user_id=str(message.from_user.id),
            gym_time=morning_quiz.gym_attendance_time
        )

    await state.clear()
    await state.set_state(MainMenuState.main_menu)
