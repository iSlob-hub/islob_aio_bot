from aiogram.filters import StateFilter
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram import Router, F
import app.text_constants as tc
from aiogram.types import ReplyKeyboardRemove
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
)
import re
from app.routers.main_router import MainMenuState
from app.states import NotificationsState
import app.keyboards as kb
from app.db.models import Notification, NotificationType, User
from app.utils.bot_utils import cron_to_human_readable
from app.utils.text_templates import get_template, format_template

notifications_router = Router()


async def _cancel_new_notification(message_or_callback, state: FSMContext):
    """Return user to notifications menu and clear creation state."""
    if isinstance(message_or_callback, CallbackQuery):
        await message_or_callback.answer()
        responder = message_or_callback.message
    else:
        responder = message_or_callback
    await responder.answer(
        text=await get_template("notif_return_to_menu"),
        reply_markup=await kb.get_notifications_menu_keyboard(),
    )
    await state.clear()
    await state.set_state(MainMenuState.notifications_menu)


@notifications_router.message(StateFilter(MainMenuState.notifications_menu))
async def process_notification_menu(message: Message, state: FSMContext) -> None:
    if message.text == tc.BACK_TO_MAIN_MENU_BUTTON:
        await message.answer(
            text=await get_template("notif_back_to_main_menu"),
            reply_markup=await kb.get_main_menu_keyboard(),
        )
        await state.set_state(MainMenuState.main_menu)

    elif message.text == tc.CREATE_NEW_NOTIFICATION_BUTTON:
        await message.answer(
            text=await get_template("notif_create_new"),
            reply_markup=await kb.go_back_button(),
        )
        await state.set_state(NotificationsState.creating_notification_request_text)
    elif message.text == tc.VIEW_NOTIFICATIONS_BUTTON:
        notifications = await Notification.find(
            Notification.user_id == str(message.from_user.id),
            Notification.notification_type == NotificationType.CUSTOM_NOTIFICATION,
        ).to_list()
        if not notifications:
            await message.answer(
                await get_template("notif_none"),
                reply_markup=await kb.get_notifications_menu_keyboard(),
            )
            return

        for idx, notification in enumerate(notifications, start=1):
            status = (await get_template("status_active")) if notification.is_active else (await get_template("status_disabled"))
            cron_human = cron_to_human_readable(notification.custom_notification_cron)
            text = (
                f"{idx}. {notification.notification_text}\n"
                f"({cron_human})\n"
                f"{await format_template('status_label', 'Статус: {status}', status=status)}"
            )
            turn_action = await get_template("turn_off") if notification.is_active else await get_template("turn_on")
            turn_callback = f"turn_on_off_{notification.id}"
            delete_callback = f"delete_{notification.id}"
            edit_callback = f"edit_{notification.id}"

            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text=turn_action, callback_data=turn_callback
                        ),
                        InlineKeyboardButton(
                            text=await get_template("button_delete"), callback_data=delete_callback
                        ),
                        InlineKeyboardButton(
                            text=await get_template("button_edit"), callback_data=edit_callback
                        ),
                    ]
                ]
            )
            await message.answer(text, reply_markup=keyboard)
        await message.answer(
            text=await get_template("notif_all"),
            reply_markup=await kb.go_back_button(),
        )
        await state.set_state(NotificationsState.viewing_notifications)


    @notifications_router.callback_query(
        lambda c: c.data.startswith("edit_"),
        StateFilter(NotificationsState.viewing_notifications),
    )
    async def edit_notification_start(callback: CallbackQuery, state: FSMContext):
        callback.answer()
        notification_id = callback.data.removeprefix("edit_")
        notification = await Notification.get(notification_id)
        if not notification:
            await message.answer(await get_template("notif_none"))
            return
        await state.update_data(edit_notification_id=notification_id)
        await state.update_data(edit_notification_text=notification.notification_text)
        await state.update_data(edit_notification_cron=notification.custom_notification_cron)
        await callback.message.answer(
            text=await format_template(
                "edit_start",
                "Редагування сповіщення:\nПоточний текст: {text}\nВведіть новий текст або залиште поточний:",
                text=notification.notification_text,
            ),
            reply_markup=ReplyKeyboardRemove(),
        )
        await state.set_state(NotificationsState.editing_notification_request_text)


    @notifications_router.message(
        StateFilter(NotificationsState.editing_notification_request_text)
    )
    async def edit_notification_text(message: Message, state: FSMContext):
        text = message.text.strip()
        if not text:
            await message.answer(await get_template("text_empty"))
            return
        await state.update_data(edit_notification_text=text)
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="Щодня", callback_data="edit_freq_freq_daily"),
                    InlineKeyboardButton(text="Щотижня", callback_data="edit_freq_freq_weekly"),
                ],
                [
                    InlineKeyboardButton(text="Щомісяця", callback_data="edit_freq_freq_monthly"),
                ],
            ]
        )
        await message.answer(
            text=await get_template("edit_choose_frequency"),
            reply_markup=keyboard,
        )
        await state.set_state(NotificationsState.editing_notification_request_frequency)


    @notifications_router.callback_query(
        StateFilter(NotificationsState.editing_notification_request_frequency)
    )
    async def edit_notification_frequency(callback: CallbackQuery, state: FSMContext):
        frequency = callback.data.removeprefix("edit_freq_")
        await state.update_data(edit_frequency=frequency)
        data = await state.get_data()
        text = f"Редагування сповіщення:\nТекст: {data['edit_notification_text']}\nЧастота: {tc.frequency_options.get(frequency)}"
        if frequency == "freq_weekly":
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text=key, callback_data=f"edit_weekday_{key}") for key in tc.WEEKDAYS]
                ] + [[InlineKeyboardButton(text="✅ Продовжити", callback_data="edit_weekdays_done")]]
            )
            await callback.message.edit_text(text + "\n" + (await get_template("choose_days_prompt")), reply_markup=keyboard)
            await state.set_state(NotificationsState.editing_notification_request_weekdays)
        elif frequency == "freq_monthly":
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text=str(day), callback_data=f"edit_monthday_{day}") for day in range(row, min(row+5, 31))] for row in range(1, 31, 5)
                ] + [[InlineKeyboardButton(text="✅ Продовжити", callback_data="edit_monthdays_done")]]
            )
            await callback.message.edit_text(text + "\n" + (await get_template("choose_days_prompt")), reply_markup=keyboard)
            await state.set_state(NotificationsState.editing_notification_request_monthdays)
        else:
            await callback.message.edit_text(text + "\n" + (await get_template("edit_choose_time")))
            await state.set_state(NotificationsState.editing_notification_request_time)
        await callback.answer()


    # Аналогічно handle_weekday_selection/monthday_selection/time_input, додати обробку вибору днів та часу для редагування
    @notifications_router.callback_query(
        StateFilter(NotificationsState.editing_notification_request_weekdays)
    )
    async def edit_weekday_selection(callback: CallbackQuery, state: FSMContext):
        data = await state.get_data()
        weekday_code = callback.data.removeprefix("edit_weekday_")
        if weekday_code in tc.WEEKDAYS:
            selected = set(data.get("edit_weekdays", []))
            if weekday_code in selected:
                selected.remove(weekday_code)
            else:
                selected.add(weekday_code)
            await state.update_data(edit_weekdays=list(selected))
            text = f"Редагування сповіщення:\nТекст: {data['edit_notification_text']}\nЧастота: {tc.frequency_options.get(data['edit_frequency'])}\nДні: {', '.join(selected) if selected else 'не обрано'}"
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text=key + (" ✅" if key in selected else ""), callback_data=f"edit_weekday_{key}") for key in tc.WEEKDAYS]
                ] + [[InlineKeyboardButton(text="✅ Продовжити", callback_data="edit_weekdays_done")]]
            )
            await callback.message.edit_text(text + "\n(оберіть ще або натисніть 'Продовжити')", reply_markup=keyboard)
            await callback.answer()
        elif callback.data == "edit_weekdays_done":
            selected = data.get("edit_weekdays", [])
            if not selected:
                await callback.answer(await get_template("choose_at_least_one_day"))
                return
            await callback.message.edit_text(await get_template("edit_choose_time"))
            await state.set_state(NotificationsState.editing_notification_request_time)
            await callback.answer()

    @notifications_router.callback_query(
        StateFilter(NotificationsState.editing_notification_request_monthdays)
    )
    async def edit_monthday_selection(callback: CallbackQuery, state: FSMContext):
        data = await state.get_data()
        monthday_code = callback.data.removeprefix("edit_monthday_")
        if monthday_code in tc.MONTHDAYS:
            selected = set(data.get("edit_monthdays", []))
            if monthday_code in selected:
                selected.remove(monthday_code)
            else:
                selected.add(monthday_code)
            await state.update_data(edit_monthdays=list(selected))
            text = f"Редагування сповіщення:\nТекст: {data['edit_notification_text']}\nЧастота: {tc.frequency_options.get(data['edit_frequency'])}\nДні: {', '.join(selected) if selected else 'не обрано'}"
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text=str(day) + (" ✅" if str(day) in selected else ""), callback_data=f"edit_monthday_{day}") for day in range(row, min(row+5, 31))] for row in range(1, 31, 5)
                ] + [[InlineKeyboardButton(text="✅ Продовжити", callback_data="edit_monthdays_done")]]
            )
            await callback.message.edit_text(text + "\n(обери ще або натисни 'Продовжити')", reply_markup=keyboard)
            await callback.answer()
        elif callback.data == "edit_monthdays_done":
            selected = data.get("edit_monthdays", [])
            if not selected:
                await callback.answer(await get_template("choose_at_least_one_day"))
                return
            await callback.message.edit_text(await get_template("edit_choose_time"))
            await state.set_state(NotificationsState.editing_notification_request_time)
            await callback.answer()

    @notifications_router.message(
        StateFilter(NotificationsState.editing_notification_request_time)
    )
    async def edit_time_input(message: Message, state: FSMContext):
        user_input = message.text.strip()
        if not re.fullmatch(r"\d{2}:\d{2}", user_input):
            await message.answer(await get_template("notif_invalid_time_format"))
            return
        hours, minutes = map(int, user_input.split(':'))
        if hours < 0 or hours > 23 or minutes < 0 or minutes > 59:
            await message.answer(await get_template("notif_invalid_time_range"))
            return
        await state.update_data(edit_time=user_input)
        data = await state.get_data()
        status_text = f"Редагування сповіщення:\nТекст: {data['edit_notification_text']}\nЧастота: {tc.frequency_options.get(data['edit_frequency'])}\n"
        if data["edit_frequency"] == "freq_weekly":
            weekdays = ", ".join([day for day in data.get("edit_weekdays", [])])
            status_text += f"Дні: {weekdays}\n"
            status_text += f"Час: {user_input}\n" + await get_template("confirm_changes_prompt")
        if data["edit_frequency"] == "freq_monthly":
            monthdays = ", ".join([day for day in data.get("edit_monthdays", [])])
            status_text += f"Дні: {monthdays}\n"
            status_text += f"Час: {user_input}\n" + await get_template("confirm_changes_prompt")
        if data["edit_frequency"] == "freq_daily":
            status_text += f"Час: {user_input}\n" + await get_template("confirm_changes_prompt")
        confirm_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="✅ Зберегти зміни", callback_data="confirm_edit_notification")]]
        )
        await message.answer(status_text, reply_markup=confirm_keyboard)
        await state.set_state(NotificationsState.editing_notification_finalize)

    @notifications_router.callback_query(
        lambda c: c.data == "confirm_edit_notification",
        StateFilter(NotificationsState.editing_notification_finalize),
    )
    async def confirm_edit_notification(callback: CallbackQuery, state: FSMContext):
        data = await state.get_data()
        notification_id = data.get("edit_notification_id")
        notification = await Notification.get(notification_id)
        if not notification:
            await callback.answer(await get_template("notif_not_found"), show_alert=True)
            return
        frequency_key = data.get("edit_frequency")
        text = data.get("edit_notification_text")
        time = data.get("edit_time")  # Час в таймзоні користувача
        weekdays = data.get("edit_weekdays", [])
        monthdays = data.get("edit_monthdays", [])
        
        # Отримуємо таймзону користувача
        user = await User.find_one(User.telegram_id == notification.user_id)
        timezone_offset = user.timezone_offset or 0 if user else 0
        
        # Конвертуємо час користувача в київський час
        try:
            user_hour, user_minute = map(int, time.split(':'))
            kyiv_hour = user_hour - timezone_offset
            
            if kyiv_hour < 0:
                kyiv_hour += 24
            elif kyiv_hour >= 24:
                kyiv_hour -= 24
            
            kyiv_time = f"{kyiv_hour:02d}:{user_minute:02d}"
        except ValueError:
            kyiv_time = time  # Fallback
        
        # В cron використовуємо київський час
        if frequency_key == "freq_daily":
            cron_expr = f"{int(kyiv_time.split(':')[1])} {int(kyiv_time.split(':')[0])} * * *"
        elif frequency_key == "freq_weekly":
            cron_days = ",".join([
                str(["Нд", "Пн", "Вт", "Ср", "Чт", "Пт", "Сб"].index(day))
                for day in weekdays
            ])
            cron_expr = f"{int(kyiv_time.split(':')[1])} {int(kyiv_time.split(':')[0])} * * {cron_days}"
        elif frequency_key == "freq_monthly":
            cron_days = ",".join(monthdays)
            cron_expr = f"{int(kyiv_time.split(':')[1])} {int(kyiv_time.split(':')[0])} {cron_days} * *"
        else:
            await callback.answer(await get_template("error_unknown_frequency"), show_alert=True)
            return
        notification.notification_text = text
        notification.custom_notification_text = text
        notification.notification_time = kyiv_time  # Київський час
        notification.notification_time_base = time  # Оригінальний час користувача
        notification.custom_notification_cron = cron_expr
        await notification.save()
        await callback.answer(await get_template("edit_saved"))
        await callback.message.edit_text(text=await get_template("edit_saved_text"))
        await callback.message.answer(
            text=await get_template("notif_return_to_menu"),
            reply_markup=await kb.get_notifications_menu_keyboard(),
        )
        await state.clear()
        await state.set_state(MainMenuState.notifications_menu)


@notifications_router.message(
    StateFilter(
        NotificationsState.creating_notification_request_text,
        NotificationsState.creating_notification_request_frequency,
        NotificationsState.creating_notification_request_weekdays,
        NotificationsState.creating_notification_request_monthdays,
        NotificationsState.creating_notification_request_time,
        NotificationsState.creating_notification_finalize,
    ),
    F.text == tc.BACK_BUTTON,
)
async def cancel_notification_creation_message(message: Message, state: FSMContext):
    await _cancel_new_notification(message, state)


@notifications_router.callback_query(
    F.data == "cancel_new_notification",
    StateFilter(
        NotificationsState.creating_notification_request_frequency,
        NotificationsState.creating_notification_request_weekdays,
        NotificationsState.creating_notification_request_monthdays,
        NotificationsState.creating_notification_request_time,
        NotificationsState.creating_notification_finalize,
    ),
)
async def cancel_notification_creation_callback(callback: CallbackQuery, state: FSMContext):
    await _cancel_new_notification(callback, state)


@notifications_router.message(
    StateFilter(NotificationsState.creating_notification_request_text)
)
async def process_notification_text(message: Message, state: FSMContext) -> None:
    notification_text = message.text.strip()

    if not notification_text:
        await message.answer(
            text=await get_template("notif_enter_text_prompt"),
        )
        return

    await state.update_data(
        new_notification_text=notification_text,
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Щодня", callback_data="freq_daily"),
                InlineKeyboardButton(text="Щотижня", callback_data="freq_weekly"),
            ],
            [
                InlineKeyboardButton(text="Щомісяця", callback_data="freq_monthly"),
                # InlineKeyboardButton("Власний розклад", callback_data="freq_custom")
            ],
            [
                InlineKeyboardButton(text=tc.BACK_BUTTON, callback_data="cancel_new_notification"),
            ],
        ]
    )
    await message.answer(
        text=await format_template("create_summary", "📌 Створення сповіщення:\nТекст: {text}\nОбери частоту:", text=notification_text),
        reply_markup=keyboard,
    )
    await state.set_state(NotificationsState.creating_notification_request_frequency)


@notifications_router.callback_query(
    StateFilter(NotificationsState.creating_notification_request_frequency)
)
async def handle_frequency(callback: CallbackQuery, state: FSMContext):

    frequency = callback.data
    if not frequency:
        await callback.answer(await get_template("error_unknown_frequency"))
        return

    await state.update_data(frequency=frequency)
    data = await state.get_data()
    text = f"📌 Створення сповіщення:\nТекст: {data['new_notification_text']}\nЧастота: {tc.frequency_options.get(frequency)}"

    if frequency == "freq_weekly":

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=key, callback_data=f"weekday_{key}")]
                for key in tc.WEEKDAYS
            ]
            + [
                [
                    InlineKeyboardButton(
                        text="✅ Продовжити", callback_data="weekdays_done"
                    )
                ],
                [
                    InlineKeyboardButton(text=tc.BACK_BUTTON, callback_data="cancel_new_notification"),
                ]
            ]
        )

        await callback.message.edit_text(
            text + "\nДні: (обери один або кілька)", reply_markup=keyboard
        )
        await state.set_state(NotificationsState.creating_notification_request_weekdays)
    elif frequency == "freq_monthly":
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text=str(day), callback_data=f"monthday_{day}")
                    for day in range(row, min(row + 5, 31))
                ]
                for row in range(1, 31, 5)
            ]
            + [
                [
                    InlineKeyboardButton(
                        text="✅ Продовжити", callback_data="monthdays_done"
                    )
                ],
                [
                    InlineKeyboardButton(text=tc.BACK_BUTTON, callback_data="cancel_new_notification"),
                ]
            ]
        )
        await callback.message.edit_text(
            text + "\nДні: (обери один або кілька)", reply_markup=keyboard
        )
        await state.set_state(
            NotificationsState.creating_notification_request_monthdays
        )
    else:
        await callback.message.edit_text(
            text + "\n" + await get_template("enter_time_prompt"),
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text=tc.BACK_BUTTON, callback_data="cancel_new_notification")]
                ]
            ),
        )
        await state.set_state(NotificationsState.creating_notification_request_time)

    await callback.answer()


@notifications_router.callback_query(
    StateFilter(NotificationsState.creating_notification_request_weekdays)
)
async def handle_weekday_selection(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    weekday_code = callback.data.removeprefix("weekday_")

    if weekday_code in tc.WEEKDAYS:
        selected = set(data.get("weekdays", []))
        if weekday_code in selected:
            selected.remove(weekday_code)
        else:
            selected.add(weekday_code)
        await state.update_data(weekdays=list(selected))

        text = (
            f"📌 Створення сповіщення:\n"
            f"Текст: {data['new_notification_text']}\n"
            f"Частота: {tc.frequency_options.get(data['frequency'])}\n"
            f"Дні: {', '.join([d for d in selected]) if selected else 'не обрано'}"
        )

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=key + (" ✅" if key in selected else ""),
                        callback_data=f"weekday_{key}",
                    )
                ]
                for key in tc.WEEKDAYS
            ]
            + [
                [
                    InlineKeyboardButton(
                        text="✅ Продовжити", callback_data="weekdays_done"
                    )
                ],
                [
                    InlineKeyboardButton(text=tc.BACK_BUTTON, callback_data="cancel_new_notification"),
                ]
            ]
        )

        await callback.message.edit_text(
            text + "\n(обери ще або натисни 'Продовжити')", reply_markup=keyboard
        )
        await callback.answer()

    elif callback.data == "weekdays_done":
        selected = data.get("weekdays", [])
        if not selected:
            await callback.answer(await get_template("choose_at_least_one_day"))
            return

        await callback.message.edit_text(
            f"📌 Створення сповіщення:\n"
            f"Текст: {data['new_notification_text']}\n"
            f"Частота: {tc.frequency_options.get(data['frequency'])}\n"
            f"Дні: {', '.join([d for d in selected])}\n"
            f"" + await get_template("enter_time_prompt"),
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text=tc.BACK_BUTTON, callback_data="cancel_new_notification")]
                ]
            ),
        )
        await state.update_data(status_message_id=callback.message.message_id)
        await state.set_state(NotificationsState.creating_notification_request_time)
        await callback.answer()


@notifications_router.callback_query(
    StateFilter(NotificationsState.creating_notification_request_monthdays)
)
async def handle_monthday_selection(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    monthday_code = callback.data.removeprefix("monthday_")

    if monthday_code in tc.MONTHDAYS:
        selected = set(data.get("monthdays", []))
        if monthday_code in selected:
            selected.remove(monthday_code)
        else:
            selected.add(monthday_code)
        await state.update_data(monthdays=list(selected))

        text = (
            f"📌 Створення сповіщення:\n"
            f"Текст: {data['new_notification_text']}\n"
            f"Частота: {tc.frequency_options.get(data['frequency'])}\n"
            f"Дні: {', '.join([d for d in selected]) if selected else 'не обрано'}"
        )

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=str(day) + (" ✅" if str(day) in selected else ""),
                        callback_data=f"monthday_{day}",
                    )
                    for day in range(row, min(row + 5, 31))
                ]
                for row in range(1, 31, 5)
            ]
            + [
                [
                    InlineKeyboardButton(
                        text="✅ Продовжити", callback_data="monthdays_done"
                    )
                ],
                [
                    InlineKeyboardButton(text=tc.BACK_BUTTON, callback_data="cancel_new_notification"),
                ]
            ]
        )

        await callback.message.edit_text(
            text + "\n(обери ще або натисни 'Продовжити')", reply_markup=keyboard
        )
        await callback.answer()

    elif callback.data == "monthdays_done":
        selected = data.get("monthdays", [])
        if not selected:
            await callback.answer(await get_template("choose_at_least_one_day"))
            return

        await callback.message.edit_text(
            f"📌 Створення сповіщення:\n"
            f"Текст: {data['new_notification_text']}\n"
            f"Частота: {tc.frequency_options.get(data['frequency'])}\n"
            f"Дні: {', '.join([d for d in selected])}\n"
            f"" + await get_template("enter_time_prompt"),
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text=tc.BACK_BUTTON, callback_data="cancel_new_notification")]
                ]
            ),
        )
        await state.update_data(status_message_id=callback.message.message_id)
        await state.set_state(NotificationsState.creating_notification_request_time)
        await callback.answer()


@notifications_router.message(
    StateFilter(NotificationsState.creating_notification_request_time)
)
async def handle_time_input(message: Message, state: FSMContext):
    user_input = message.text.strip()

    if not re.fullmatch(r"\d{2}:\d{2}", user_input):
        await message.answer(
            await get_template("notif_invalid_time_format")
        )
        return
        
    # Валідація що час у межах 00:00 - 23:59
    hours, minutes = map(int, user_input.split(':'))
    if hours < 0 or hours > 23 or minutes < 0 or minutes > 59:
        await message.answer(
            await get_template("notif_invalid_time_range")
        )
        return

    await state.update_data(time=user_input)
    data = await state.get_data()

    status_text = (
        f"📌 Створення сповіщення:\n"
        f"Текст: {data['new_notification_text']}\n"
        f"Частота: {tc.frequency_options.get(data['frequency'])}\n"
    )
    if tc.frequency_options.get(data["frequency"]) == "Щотижня":
        weekdays = ", ".join([day for day in data["weekdays"]])
        status_text += f"Дні: {weekdays}\n"

    if tc.frequency_options.get(data["frequency"]) == "Щомісяця":
        monthdays = ", ".join([day for day in data.get("monthdays", [])])
        status_text += f"Дні: {monthdays}\n"

    status_text += f"Час: {user_input}\n" + await get_template("notif_ready")
    confirm_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=await get_template("confirm_button"), callback_data="confirm_notification"
                )
            ],
            [
                InlineKeyboardButton(
                    text=tc.BACK_BUTTON, callback_data="cancel_new_notification"
                )
            ],
        ]
    )
    try:
        await message.bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=data["status_message_id"],
            text=status_text,
            reply_markup=confirm_keyboard,
        )
    except Exception:
        await message.answer(await get_template("here_summary"))
        await message.answer(status_text, reply_markup=confirm_keyboard)
    await state.set_state(NotificationsState.creating_notification_finalize)


@notifications_router.callback_query(
    lambda c: c.data == "confirm_notification",
    StateFilter(NotificationsState.creating_notification_finalize),
)
async def confirm_notification(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user_id = str(callback.from_user.id)

    frequency = tc.frequency_options.get(data.get("frequency"))
    text = data.get("new_notification_text")
    time = data.get("time")  # Час в таймзоні користувача
    weekdays = data.get("weekdays", [])
    monthdays = data.get("monthdays", [])
    
    # Отримуємо таймзону користувача для конверсії
    user = await User.find_one(User.telegram_id == user_id)
    timezone_offset = user.timezone_offset or 0 if user else 0
    
    # Конвертуємо час користувача в київський час
    try:
        user_hour, user_minute = map(int, time.split(':'))
        kyiv_hour = user_hour - timezone_offset
        
        # Обробка переходу через межу доби
        if kyiv_hour < 0:
            kyiv_hour += 24
        elif kyiv_hour >= 24:
            kyiv_hour -= 24
        
        kyiv_time = f"{kyiv_hour:02d}:{user_minute:02d}"
    except ValueError:
        kyiv_time = time  # Fallback
    
    # В cron використовуємо київський час
    if frequency == "Щодня":
        cron_expr = f"{int(kyiv_time.split(':')[1])} {int(kyiv_time.split(':')[0])} * * *"
    elif frequency == "Щотижня":
        cron_days = ",".join(
            [
                str(["Нд", "Пн", "Вт", "Ср", "Чт", "Пт", "Сб"].index(day))
                for day in weekdays
            ]
        )
        cron_expr = (
            f"{int(kyiv_time.split(':')[1])} {int(kyiv_time.split(':')[0])} * * {cron_days}"
        )
    elif frequency == "Щомісяця":
        cron_days = ",".join(monthdays)
        cron_expr = (
            f"{int(kyiv_time.split(':')[1])} {int(kyiv_time.split(':')[0])} {cron_days} * *"
        )
    else:
        await callback.answer(await get_template("error_unknown_frequency"), show_alert=True)
        return

    notification = Notification(
        user_id=user_id,
        notification_time=kyiv_time,  # Київський час для scheduler
        notification_time_base=time,  # Оригінальний час користувача
        notification_text=text,
        notification_type=NotificationType.CUSTOM_NOTIFICATION,
        custom_notification_text=text,
        custom_notification_cron=cron_expr,
        custom_notification_execute_once=False,
    )
    await notification.insert()

    await callback.answer(await get_template("notif_saved"))

    await callback.message.edit_text(text=await get_template("notif_saved_active"))

    await callback.message.answer(
        text=await get_template("notif_return_to_menu"),
        reply_markup=await kb.get_notifications_menu_keyboard(),
    )

    await state.clear()
    await state.set_state(MainMenuState.notifications_menu)


@notifications_router.callback_query(
    lambda c: c.data.startswith("turn_on_off_"),
    StateFilter(NotificationsState.viewing_notifications),
)
async def toggle_notification(callback: CallbackQuery, state: FSMContext):
    notification_id = callback.data.removeprefix("turn_on_off_")
    notification = await Notification.get(notification_id)

    if not notification:
        await callback.answer(await get_template("notif_toggle_not_found"), show_alert=True)
        return

    notification.is_active = not notification.is_active
    await notification.save()

    status = "🟢 Активне" if notification.is_active else "🔴 Вимкнене"
    cron_human = cron_to_human_readable(notification.custom_notification_cron)
    text = f"{notification.notification_text}\n" f"({cron_human})\n" f"Статус: {status}"
    turn_action = "Вимкнути" if notification.is_active else "Увімкнути"
    turn_callback = f"turn_on_off_{notification.id}"
    delete_callback = f"delete_{notification.id}"

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=turn_action, callback_data=turn_callback),
                InlineKeyboardButton(text=await get_template("button_delete"), callback_data=delete_callback),
                InlineKeyboardButton(text=await get_template("button_edit"), callback_data=f"edit_{notification.id}"),
            ]
        ]
    )

    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@notifications_router.callback_query(
    lambda c: c.data.startswith("delete_"),
    StateFilter(NotificationsState.viewing_notifications),
)
async def delete_notification(callback: CallbackQuery, state: FSMContext):
    notification_id = callback.data.removeprefix("delete_")
    notification = await Notification.get(notification_id)

    if not notification:
        await callback.answer(await get_template("notif_delete_not_found"), show_alert=True)
        return

    await notification.delete()
    await callback.answer(await get_template("notif_deleted"))

    notifications = await Notification.find(
        Notification.user_id == str(callback.from_user.id),
        Notification.notification_type == NotificationType.CUSTOM_NOTIFICATION,
    ).to_list()

    if not notifications:
        await callback.message.edit_text(await get_template("notif_none"))
        await callback.message.answer(
            text=await get_template("notif_return_to_menu"),
            reply_markup=await kb.get_notifications_menu_keyboard(),
        )
        return

    for idx, notification in enumerate(notifications, start=1):
        status = "🟢 Активне" if notification.is_active else "🔴 Вимкнене"
        cron_human = cron_to_human_readable(notification.custom_notification_cron)
        text = (
            f"{idx}. {notification.notification_text}\n"
            f"({cron_human})\n"
            f"Статус: {status}"
        )
        turn_action = "Вимкнути" if notification.is_active else "Увімкнути"
        turn_callback = f"turn_on_off_{notification.id}"
        delete_callback = f"delete_{notification.id}"

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text=turn_action, callback_data=turn_callback),
                    InlineKeyboardButton(text=await get_template("button_delete"), callback_data=delete_callback),
                    InlineKeyboardButton(text=await get_template("button_edit"), callback_data=f"edit_{notification.id}"),
                ]
            ]
        )
        await callback.message.answer(text, reply_markup=keyboard)

        await callback.message.answer(
            text=await get_template("notif_all"),
            reply_markup=await kb.go_back_button(),
        )


# process go back button
@notifications_router.message(
    StateFilter(NotificationsState.viewing_notifications), F.text == tc.BACK_BUTTON
)
async def process_go_back(message: Message, state: FSMContext) -> None:
    await message.answer(
        text=await get_template("notif_return_to_menu"),
        reply_markup=await kb.get_notifications_menu_keyboard(),
    )
    await state.clear()
    await state.set_state(MainMenuState.notifications_menu)
