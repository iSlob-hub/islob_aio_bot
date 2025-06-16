from aiogram.filters import StateFilter
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram import Router
import text_constants as tc

from routers.main_router import MainMenuState
from keyboards import get_main_menu_keyboard


report_problem_router = Router()

REPORT_CHAT_ID = "-4989990832"


@report_problem_router.message(StateFilter(MainMenuState.report_problem))
async def process_report_problem(message: Message, state: FSMContext) -> None:
    await message.answer(
        text=tc.THANKS_FOR_REPORTING_PROBLEM,
        reply_markup=await get_main_menu_keyboard(),
    )
    await state.set_state(MainMenuState.main_menu)
    await message.bot.send_message(
        chat_id=REPORT_CHAT_ID,
        text=f"Проблема від @{message.from_user.username} {message.from_user.id}:\n\n{message.text}",
    )
