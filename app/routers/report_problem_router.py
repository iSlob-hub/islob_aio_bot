from aiogram.filters import StateFilter
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram import Router

from app.routers.main_router import MainMenuState
from app.keyboards import get_main_menu_keyboard
from dotenv import load_dotenv
from app.utils.text_templates import get_template
import os
load_dotenv()


report_problem_router = Router()

REPORT_CHAT_ID = os.getenv("ADMIN_CHAT_ID")


@report_problem_router.message(StateFilter(MainMenuState.report_problem))
async def process_report_problem(message: Message, state: FSMContext) -> None:
    await message.answer(
        text=await get_template("thanks_for_reporting_problem"),
        reply_markup=await get_main_menu_keyboard(),
    )
    await state.set_state(MainMenuState.main_menu)
    await message.bot.send_message(
        chat_id=REPORT_CHAT_ID,
        text=f"Проблема від @{message.from_user.username} {message.from_user.id}:\n\n{message.text}",
    )
