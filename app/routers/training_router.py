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
import text_constants as tc
from routers.main_router import MainMenuState
from states import TrainingState
from db.models import TrainingSession, Notification
from keyboards import get_main_menu_keyboard
import datetime
import os
from pathlib import Path
from zoneinfo import ZoneInfo


app_root = Path(__file__).resolve().parent.parent


training_router = Router()


@training_router.message(
    F.text == tc.START_TRAINING_BUTTON, StateFilter(MainMenuState.training_menu)
)
async def start_training(message: Message, state: FSMContext) -> None:
    # remove reply keyboard if it exists
    await message.answer(
        text="Починаємо тренування!",
        reply_markup=ReplyKeyboardRemove(),
    )

    await message.answer(
        text="Як ти себе почуваєш перед тренуванням?",
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
        training_started_at=datetime.datetime.now(tz=ZoneInfo("Europe/Kyiv")),
    )

    await training_session.save()
    training_session_id = training_session.id

    # Send test PDF file to user

    training_pdf = URLInputFile(
        url="https://storage.googleapis.com/islobbot_files/test_pdf.pdf",
        filename="training_session.pdf",
    )
    await callback_query.message.answer_document(
        document=training_pdf, caption="Ось твій тренувальний план на сьогодні."
    )

    await callback_query.message.answer(
        text="Тренування розпочато! Для завершення - натисни кнопку нижче.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Завершити тренування",
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
        await callback_query.message.answer("Тренування не знайдено.")
        return

    training_session.training_ended_at = datetime.datetime.now(tz=ZoneInfo("Europe/Kyiv"))

    training_session.training_started_at = training_session.training_started_at.astimezone(
        ZoneInfo("Europe/Kyiv")
    )

    training_session.training_duration = int(
        round(
            ((
                training_session.training_ended_at
                - training_session.training_started_at
            ).total_seconds())
            / 60,
            0,
        )
    )
    if training_session.training_duration < 1:
        training_session.training_duration = 1

    await training_session.save()

    await callback_query.answer()

    await callback_query.message.answer(
        text="Супер! Тренування завершено! \nОціни важкість тренування?",
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
        await callback_query.message.answer("Тренування не знайдено.")
        return

    training_session.how_hard_was_training = int(rating)
    await training_session.save()

    await callback_query.answer()

    await callback_query.message.edit_text(
        text="Чи відчуваєш ти біль після тренування?",
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
        await callback_query.message.answer("Тренування не знайдено.")
        return

    training_session.do_you_have_any_pain = answer == "yes"
    await training_session.save()

    if training_session.do_you_have_any_pain:
        admin_chat_id = "-4989990832"
        await callback_query.bot.send_message(
            chat_id=admin_chat_id,
            text=(
                f"Користувач {callback_query.from_user.full_name} @{callback_query.from_user.username} "
                f"({callback_query.from_user.id}) відчуває біль після тренування."
            ),
        )

    await callback_query.message.edit_text(
        text=(
            f"Дякую за тренування!"
            f"Тренування тривало {training_session.training_duration:.2f} хвилин.\n"
        )
    )

    after_training_notification = Notification(
        user_id=str(callback_query.from_user.id),
        notification_time="12:00",
        system_data={
            "training_session_id": str(training_session.id),
        },
        notification_text="",
        notification_type="after_training_notification",
    )

    await after_training_notification.save()

    training_session.completed = True
    await training_session.save()

    await callback_query.message.answer(
        text="Повертаємося до головного меню.",
        reply_markup=await get_main_menu_keyboard(),
    )

    await callback_query.answer()
    await state.clear()
    await state.set_state(MainMenuState.main_menu)
