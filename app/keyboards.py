from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
import app.text_constants as tc
from app.utils.text_templates import get_template, sync_get_template


async def get_main_menu_keyboard(
    include_morning_quiz_resume: bool = False,
) -> ReplyKeyboardMarkup:
    """
    Create the main menu keyboard.
    """
    resume_row = (
        [KeyboardButton(text=tc.CONTINUE_MORNING_QUIZ_BUTTON)]
        if include_morning_quiz_resume
        else []
    )
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            *([resume_row] if resume_row else []),
            [
                KeyboardButton(text=tc.TRAINING_MENU_BUTTON),
                KeyboardButton(text=tc.NOTIFICATIONS_MENU_BUTTON),
            ],
            [
                KeyboardButton(text=tc.REPORT_PROBLEM_BUTTON),
            ],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    return keyboard


async def get_notifications_menu_keyboard() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=tc.CREATE_NEW_NOTIFICATION_BUTTON),
                KeyboardButton(text=tc.VIEW_NOTIFICATIONS_BUTTON),
            ],
            [
                KeyboardButton(text=tc.BACK_TO_MAIN_MENU_BUTTON),
            ],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    return keyboard


async def get_notification_frequency_keyboard() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="Щодня"),
                KeyboardButton(text="Щотижня"),
            ],
            [
                KeyboardButton(text="Щомісяця"),
            ],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    return keyboard


async def go_back_button() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=tc.BACK_BUTTON),
            ],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    return keyboard


async def get_report_problem_keyboard() -> ReplyKeyboardMarkup:
    """Keyboard for the report problem flow with a back-to-menu button."""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=tc.BACK_TO_MAIN_MENU_BUTTON),
            ],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    return keyboard
