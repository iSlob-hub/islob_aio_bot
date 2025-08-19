import re
from aiogram import F
from aiogram.filters import Command, StateFilter
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram import Router
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    ReplyKeyboardRemove,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from app.db.models import User, Notification, NotificationType, MorningQuiz
from app.keyboards import get_main_menu_keyboard, get_notifications_menu_keyboard
import app.text_constants as tc


def generate_username_from_name(full_name: str) -> str:
    """Генерує username з повного імені користувача"""
    if not full_name:
        return "user"
    
    # Видаляємо всі символи крім букв та цифр, перетворюємо в нижній регістр
    clean_name = re.sub(r'[^a-zA-Zа-яА-Я0-9\s]', '', full_name.lower())
    # Замінюємо пробіли на підкреслення
    username = re.sub(r'\s+', '_', clean_name.strip())
    
    # Обмежуємо довжину до 32 символів (ліміт Telegram)
    if len(username) > 32:
        username = username[:32]
    
    # Якщо нічого не залишилося, повертаємо дефолтне значення
    if not username:
        return "user"
        
    return username
from app.utils.bot_utils import is_valid_morning_time
from app.states import NotificationsState
import datetime


class InitialConversationState(StatesGroup):
    waiting_for_name = State()
    waiting_for_morning_notification_time = State()


class MainMenuState(StatesGroup):
    training_menu = State()
    notifications_menu = State()
    report_problem = State()
    main_menu = State()


main_router = Router()


# ------- MAIN ROUTER (Entry points) -------
@main_router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext) -> None:

    user_telegram_id = message.from_user.id
    user_telegram_username = message.from_user.username

    user = await User.find_one(User.telegram_id == str(user_telegram_id))
    if user and user.is_verified:

        await message.answer(
            f"Привіт! {user.telegram_username}!",
            reply_markup=await get_main_menu_keyboard(),
        )
        await state.set_state(MainMenuState.main_menu)
        return

    if not user:
        # Генеруємо username якщо його немає
        generated_username = user_telegram_username or generate_username_from_name(
            message.from_user.full_name or "Unknown User"
        )
        
        user = User(
            telegram_id=str(user_telegram_id),
            telegram_username=generated_username,
            is_verified=False,
            full_name=message.from_user.full_name or "Unknown User",
        )
        await user.save()
    await state.set_state(InitialConversationState.waiting_for_name)
    await message.answer(
        text=tc.INTRO_MESSAGE,
        reply_markup=ReplyKeyboardRemove(),
    )


@main_router.message(StateFilter(InitialConversationState.waiting_for_name))
async def process_name(message: Message, state: FSMContext) -> None:
    user_name = message.text
    user_telegram_id = message.from_user.id
    user = await User.find_one(User.telegram_id == str(user_telegram_id))
    if user:
        user.full_name = user_name
        user.is_verified
        await user.save()
        await state.set_state(
            InitialConversationState.waiting_for_morning_notification_time
        )
        await message.answer(
            text=tc.MORNING_NOTIFICATION_TIME_MESSAGE.format(name=user_name),
            reply_markup=ReplyKeyboardRemove(),
        )
    else:
        await message.answer(
            tc.SORRY_ISSUE_HAPPENED,
            reply_markup=ReplyKeyboardRemove(),
        )
        await state.set_state(InitialConversationState.waiting_for_name)


@main_router.message(
    StateFilter(InitialConversationState.waiting_for_morning_notification_time)
)
async def process_morning_notification_time(
    message: Message, state: FSMContext
) -> None:
    user_telegram_id = message.from_user.id
    user = await User.find_one(User.telegram_id == str(user_telegram_id))
    if user:
        time_str = message.text
        if is_valid_morning_time(time_str):
            notification = Notification(
                user_id=str(user_telegram_id),
                notification_time=time_str,
                notification_text="",
                notification_type=NotificationType.DAILY_MORNING_NOTIFICATION,
            )
            await notification.save()
            user.is_verified = True
            await user.save()
            await state.set_state(MainMenuState.main_menu)
            await message.answer(
                text=tc.MORNING_NOTIFICATION_SETTINGS_FINISHED,
                reply_markup=await get_main_menu_keyboard(),
            )

        else:
            await message.answer(
                "Невірний формат часу. Спробуйте ще раз.",
                reply_markup=ReplyKeyboardRemove(),
            )
            await state.set_state(
                InitialConversationState.waiting_for_morning_notification_time
            )


@main_router.message(
    StateFilter(MainMenuState.main_menu), F.text == tc.TRAINING_MENU_BUTTON
)
async def process_training_menu(message: Message, state: FSMContext) -> None:
    await message.answer(
        "Шо робимо з тренуваннями?",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [
                    KeyboardButton(text=tc.START_TRAINING_BUTTON),
                ],
                [
                    KeyboardButton(text=tc.BACK_TO_MAIN_MENU_BUTTON)
                ]
            ],
            resize_keyboard=True,
        ),
    )
    await state.set_state(MainMenuState.training_menu)


@main_router.message(
    StateFilter(MainMenuState.main_menu), F.text == tc.NOTIFICATIONS_MENU_BUTTON
)
async def process_notifications_menu(message: Message, state: FSMContext) -> None:
    await message.answer(
        text="Шо робимо зі сповіщеннями?",
        reply_markup=await get_notifications_menu_keyboard(),
    )
    await state.set_state(MainMenuState.notifications_menu)


@main_router.message(
    StateFilter(MainMenuState.main_menu), F.text == tc.REPORT_PROBLEM_BUTTON
)
async def process_report_problem(message: Message, state: FSMContext) -> None:
    await message.answer(
        "Опишіть свою проблему у повідомленні",
        reply_markup=ReplyKeyboardRemove(),
    )
    await state.set_state(MainMenuState.report_problem)


@main_router.message(Command("morning_quiz"), StateFilter(MainMenuState.main_menu))
async def cmd_morning_quiz(message: Message, state: FSMContext) -> None:
    user_telegram_id = message.from_user.id
    morning_quiz = MorningQuiz(
        user_id=str(user_telegram_id),
    )
    await morning_quiz.save()
    morning_quiz_id = morning_quiz.id

    await message.answer(
        "Ейоу, пора пройти ранкове опитування!",
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


@main_router.message(StateFilter(MainMenuState.main_menu))
async def process_main_menu(message: Message, state: FSMContext) -> None:
    await message.answer(
        "Виберіть опцію:",
        reply_markup=await get_main_menu_keyboard(),
    )
