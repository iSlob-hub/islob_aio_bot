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


async def create_gym_reminder_notification(user_id: str, gym_time: datetime.datetime):
    """Створює нагадування про тренування в запланований час"""
    try:
        # Видаляємо старі нагадування про тренування для цього користувача
        await Notification.find({
            "user_id": user_id,
            "notification_type": "gym_reminder_notification"
        }).delete()
        
        # Час нагадування - саме в час тренування
        reminder_time = gym_time
        
        # Створюємо нове сповіщення
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
    except ValueError:
        try:
            hours, minutes = time_str.split(":")
            hours = int(hours)
            minutes = int(minutes)
            sleep_time = hours + minutes / 60.0
        except ValueError:
            return None

    return sleep_time


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
            "Це опитування вже завершено. Спробуй ще раз завтра вранці.",
            reply_markup=ReplyKeyboardRemove(),
        )
        await callback.answer()
        return

    await callback.answer("Розпочинаємо опитування")
    await state.set_state(MorningQuizStates.waiting_for_how_do_you_feel_today)
    await state.update_data(morning_quiz_id=morning_quiz_id)
    await callback.message.edit_text(
        "Як ти почуваєшся сьогодні?",
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
            "❌ Сталась помилка. Не вдалось знайти опитування. Зв'яжіться з адміністратором."
        )
        await callback.answer()
        await state.clear()
        await state.set_state(MainMenuState.main_menu)
        return

    morning_quiz = await MorningQuiz.get(morning_quiz_id)

    morning_quiz.how_do_you_feel_today = int(feeling)
    await morning_quiz.save()
    await callback.answer("✅ Твій стан збережено")
    await callback.message.edit_text(
        "Ти оцінюєш свій стан як: " f"<b>{feeling}</b>\n\n",
    )

    await state.set_state(MorningQuizStates.waiting_for_how_many_hours_of_sleep)

    await callback.message.answer(
        "Скільки годин ти спав? \n"
        "Введи число або у форматі ГГ:ХХ (наприклад, 7:30 для 7 годин 30 хвилин)",
    )


@morning_quiz_router.message(
    StateFilter(MorningQuizStates.waiting_for_how_many_hours_of_sleep)
)
async def handle_how_many_hours_of_sleep(message: Message, state: FSMContext):
    sleep_time_str = message.text.strip()
    sleep_time = validate_transform_time(sleep_time_str)

    if sleep_time is None:
        await message.answer(
            "❌ Невірний формат. Введи число або у форматі ГГ:ХХ (наприклад, 7:30 для 7 годин 30 хвилин)"
        )
        return

    state_data = await state.get_data()
    morning_quiz_id = state_data.get("morning_quiz_id")
    if not morning_quiz_id:
        await message.answer(
            "❌ Сталась помилка. Не вдалось знайти опитування. Зв'яжіться з адміністратором."
        )
        await state.clear()
        await state.set_state(MainMenuState.main_menu)
        return

    morning_quiz = await MorningQuiz.get(morning_quiz_id)
    morning_quiz.how_many_hours_of_sleep = sleep_time
    await morning_quiz.save()

    await message.answer(
        f"Твоє самопочуття: {morning_quiz.how_do_you_feel_today}\n"
        f"Ти спав <b>{sleep_time} годин</b>.\n\n"
        "Чи плануєш ти йти в спортзал сьогодні?",
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
            "❌ Сталась помилка. Не вдалось знайти опитування. Зв'яжіться з адміністратором."
        )
        await callback.answer()
        await state.clear()
        await state.set_state(MainMenuState.main_menu)
        return

    morning_quiz = await MorningQuiz.get(morning_quiz_id)
    morning_quiz.is_going_to_gym = True if is_going_to_gym == "yes" else False
    if is_going_to_gym:
        await callback.answer("✅ Супєр, йдем в зальчік!")
        morning_quiz.is_going_to_gym = True
    else:
        await callback.answer("✅ Поняв, прийняв, в зал не йдемо.")
        morning_quiz.is_going_to_gym = False
    await morning_quiz.save()

    if is_going_to_gym:
        await callback.message.answer(
            f"Твоє самопочуття: {morning_quiz.how_do_you_feel_today}\n"
            f"Ти спав <b>{morning_quiz.how_many_hours_of_sleep} годин</b>.\n"
            f"Ти плануєш йти в спортзал: <b>Так</b>.\n"
            "Коли ти плануєш відвідати спортзал?",
        )
        await state.set_state(MorningQuizStates.waiting_for_gym_attendance_time)
    else:
        await callback.message.edit_text(
            f"Твоє самопочуття: {morning_quiz.how_do_you_feel_today}\n"
            f"Ти спав <b>{morning_quiz.how_many_hours_of_sleep} годин</b>.\n"
            f"Ти плануєш йти в спортзал: <b>Ні</b>.\n"
            "Тепер вкажи свою вагу (в кг):",
        )
        await state.set_state(MorningQuizStates.waiting_for_weight)


@morning_quiz_router.message(
    StateFilter(MorningQuizStates.waiting_for_gym_attendance_time)
)
async def handle_gym_attendance_time(message: Message, state: FSMContext):
    gym_attendance_time = message.text.strip()
    if not gym_attendance_time:
        await message.answer("❌ Будь ласка, введи час відвідування спортзалу.")
        return

    gym_attendance_time_dt = convert_time_to_datetime(gym_attendance_time)
    if gym_attendance_time_dt is None:
        await message.answer(
            "❌ Невірний формат часу. Введи час у форматі ГГ:ХХ (наприклад, 14:30 для 2:30 PM)"
        )
        return

    state_data = await state.get_data()
    morning_quiz_id = state_data.get("morning_quiz_id")
    if not morning_quiz_id:
        await message.answer(
            "❌ Сталась помилка. Не вдалось знайти опитування. Зв'яжіться з адміністратором."
        )
        await state.clear()
        await state.set_state(MainMenuState.main_menu)
        return
    morning_quiz = await MorningQuiz.get(morning_quiz_id)
    morning_quiz.gym_attendance_time = gym_attendance_time_dt
    await morning_quiz.save()
    await message.answer(
        f"Твоє самопочуття: {morning_quiz.how_do_you_feel_today}\n"
        f"Ти спав <b>{morning_quiz.how_many_hours_of_sleep} годин</b>.\n"
        f"Ти плануєш йти в спортзал: <b>Так</b>.\n"
        f"Час відвідування спортзалу: <b>{gym_attendance_time}</b>.\n\n"
        "Тепер вкажи свою вагу (в кг):",
        parse_mode="HTML",
    )
    await state.set_state(MorningQuizStates.waiting_for_weight)


@morning_quiz_router.message(StateFilter(MorningQuizStates.waiting_for_weight))
async def handle_weight(message: Message, state: FSMContext):
    weight_str = message.text.strip()
    try:
        weight = float(weight_str)
    except ValueError:
        await message.answer("❌ Невірний формат ваги. Введи число.")
        return

    state_data = await state.get_data()
    morning_quiz_id = state_data.get("morning_quiz_id")
    if not morning_quiz_id:
        await message.answer(
            "❌ Сталась помилка. Не вдалось знайти опитування. Зв'яжіться з адміністратором."
        )
        await state.clear()
        await state.set_state(MainMenuState.main_menu)
        return

    morning_quiz = await MorningQuiz.get(morning_quiz_id)
    morning_quiz.weight = weight
    await morning_quiz.save()
    response_text = (
        f"Твоє самопочуття: {morning_quiz.how_do_you_feel_today}\n"
        f"Ти спав <b>{morning_quiz.how_many_hours_of_sleep} годин</b>.\n"
        f"Ти плануєш йти в спортзал: <b>{'Так' if morning_quiz.is_going_to_gym else 'Ні'}</b>.\n"
    )

    if morning_quiz.is_going_to_gym:
        response_text += f"Час відвідування спортзалу: <b>{morning_quiz.gym_attendance_time.strftime('%H:%M')}</b>.\n"
    response_text += f"Твоя вага: <b>{weight} кг</b>.\n\n"
    response_text += "Ти красава! Гарного дня!"
    await message.answer(
        response_text, parse_mode="HTML", reply_markup=ReplyKeyboardRemove()
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
