from aiogram.filters import StateFilter
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram import Router, F

from app.routers.main_router import MainMenuState
from app.keyboards import get_main_menu_keyboard, get_report_problem_keyboard
from app.utils.morning_quiz_utils import get_active_morning_quiz_for_today
import app.text_constants as tc
from dotenv import load_dotenv
from app.utils.text_templates import get_template
import os
load_dotenv()


report_problem_router = Router()

REPORT_CHAT_ID = os.getenv("ADMIN_CHAT_ID")


@report_problem_router.message(
    StateFilter(MainMenuState.report_problem), F.text == tc.BACK_TO_MAIN_MENU_BUTTON
)
async def report_problem_back_to_menu(message: Message, state: FSMContext) -> None:
    active_quiz = await get_active_morning_quiz_for_today(
        message.from_user.id,
        is_test=None,
    )
    await message.answer(
        text=await get_template("back_to_main_menu"),
        reply_markup=await get_main_menu_keyboard(
            include_morning_quiz_resume=bool(active_quiz),
        ),
    )
    await state.set_state(MainMenuState.main_menu)


@report_problem_router.message(StateFilter(MainMenuState.report_problem))
async def process_report_problem(message: Message, state: FSMContext) -> None:
    active_quiz = await get_active_morning_quiz_for_today(
        message.from_user.id,
        is_test=None,
    )
    await message.answer(
        text=await get_template("thanks_for_reporting_problem"),
        reply_markup=await get_main_menu_keyboard(
            include_morning_quiz_resume=bool(active_quiz),
        ),
    )
    await state.set_state(MainMenuState.main_menu)
    await message.bot.send_message(
        chat_id=REPORT_CHAT_ID,
        text=f"Проблема від @{message.from_user.username} {message.from_user.id}:\n\n{message.text}",
    )
