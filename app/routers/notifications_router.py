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
from app.db.models import Notification, NotificationType
from app.utils.bot_utils import cron_to_human_readable
from app.db.templates_utils import format_template

notifications_router = Router()


@notifications_router.message(StateFilter(MainMenuState.notifications_menu))
async def process_notification_menu(message: Message, state: FSMContext) -> None:
    if message.text == tc.BACK_TO_MAIN_MENU_BUTTON:
        await message.answer(
            text=await format_template("notif_back_to_main_menu", "Ага, вертаємось до головного меню"),
            reply_markup=await kb.get_main_menu_keyboard(),
        )
        await state.set_state(MainMenuState.main_menu)

    elif message.text == tc.CREATE_NEW_NOTIFICATION_BUTTON:
        await message.answer(
            text=await format_template("notif_create_new", "Створюємо нове сповіщення. Введіть текст сповіщення."),
            reply_markup=ReplyKeyboardRemove(),
        )
        await state.set_state(NotificationsState.creating_notification_request_text)
    elif message.text == tc.VIEW_NOTIFICATIONS_BUTTON:
        notifications = await Notification.find(
            Notification.user_id == str(message.from_user.id),
            Notification.notification_type == NotificationType.CUSTOM_NOTIFICATION,
        ).to_list()
        if not notifications:
            await message.answer(await format_template("notif_none", "У вас немає сповіщень."))
            return

        for idx, notification in enumerate(notifications, start=1):
            status = (await format_template("status_active", "🟢 Активне")) if notification.is_active else (await format_template("status_disabled", "🔴 Вимкнене"))
            cron_human = cron_to_human_readable(notification.custom_notification_cron)
            text = (
                f"{idx}. {notification.notification_text}\n"
                f"({cron_human})\n"
                f"{await format_template('status_label', 'Статус: {status}', status=status)}"
            )
            turn_action = await format_template("turn_off", "Вимкнути") if notification.is_active else await format_template("turn_on", "Увімкнути")
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
                            text=await format_template("button_delete", "Видалити"), callback_data=delete_callback
                        ),
                        InlineKeyboardButton(
                            text=await format_template("button_edit", "Редагувати"), callback_data=edit_callback
                        ),
                    ]
                ]
            )
            await message.answer(text, reply_markup=keyboard)
        await message.answer(
            text=await format_template("notif_all", "Це всі ваші сповіщення."),
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
            await message.answer(await format_template("notif_none", "У вас немає сповіщень."))
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
            await message.answer(await format_template("text_empty", "Текст не може бути порожнім. Введіть новий текст:"))
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
            text=await format_template("edit_choose_frequency", "Оберіть нову частоту для сповіщення:"),
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
            await callback.message.edit_text(text + "\n" + (await format_template("choose_days_prompt", "Дні: (оберіть)")), reply_markup=keyboard)
            await state.set_state(NotificationsState.editing_notification_request_weekdays)
        elif frequency == "freq_monthly":
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text=str(day), callback_data=f"edit_monthday_{day}") for day in range(row, min(row+5, 31))] for row in range(1, 31, 5)
                ] + [[InlineKeyboardButton(text="✅ Продовжити", callback_data="edit_monthdays_done")]]
            )
            await callback.message.edit_text(text + "\n" + (await format_template("choose_days_prompt", "Дні: (оберіть)")), reply_markup=keyboard)
            await state.set_state(NotificationsState.editing_notification_request_monthdays)
        else:
            await callback.message.edit_text(text + "\n" + (await format_template("edit_choose_time", "Введіть новий час у форматі HH:MM:")))
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
                await callback.answer(await format_template("choose_at_least_one_day", "Оберіть хоча б один день"))
                return
            await callback.message.edit_text(await format_template("edit_choose_time", "Введіть новий час у форматі HH:MM:"))
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
            await callback.message.edit_text(text + "\n(оберіть ще або натисніть 'Продовжити')", reply_markup=keyboard)
            await callback.answer()
        elif callback.data == "edit_monthdays_done":
            selected = data.get("edit_monthdays", [])
            if not selected:
                await callback.answer(await format_template("choose_at_least_one_day", "Оберіть хоча б один день"))
                return
            await callback.message.edit_text(await format_template("edit_choose_time", "Введіть новий час у форматі HH:MM:"))
            await state.set_state(NotificationsState.editing_notification_request_time)
            await callback.answer()

    @notifications_router.message(
        StateFilter(NotificationsState.editing_notification_request_time)
    )
    async def edit_time_input(message: Message, state: FSMContext):
        user_input = message.text.strip()
        if not re.fullmatch(r"\d{2}:\d{2}", user_input):
            await message.answer(await format_template("notif_invalid_time_format", "Будь ласка, введіть час у форматі HH:MM (наприклад, 08:30)."))
            return
        hours, minutes = map(int, user_input.split(':'))
        if hours < 0 or hours > 23 or minutes < 0 or minutes > 59:
            await message.answer(await format_template("notif_invalid_time_range", "Невірний час. Години мають бути від 00 до 23, хвилини від 00 до 59."))
            return
        await state.update_data(edit_time=user_input)
        data = await state.get_data()
        status_text = f"Редагування сповіщення:\nТекст: {data['edit_notification_text']}\nЧастота: {tc.frequency_options.get(data['edit_frequency'])}\n"
        if data["edit_frequency"] == "freq_weekly":
            weekdays = ", ".join([day for day in data.get("edit_weekdays", [])])
            status_text += f"Дні: {weekdays}\n"
            status_text += f"Час: {user_input}\n" + await format_template("confirm_changes_prompt", "✅ Підтвердити зміни?")
        if data["edit_frequency"] == "freq_monthly":
            monthdays = ", ".join([day for day in data.get("edit_monthdays", [])])
            status_text += f"Дні: {monthdays}\n"
            status_text += f"Час: {user_input}\n" + await format_template("confirm_changes_prompt", "✅ Підтвердити зміни?")
        if data["edit_frequency"] == "freq_daily":
            status_text += f"Час: {user_input}\n" + await format_template("confirm_changes_prompt", "✅ Підтвердити зміни?")
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
            await callback.answer(await format_template("notif_not_found", "Сповіщення не знайдено"), show_alert=True)
            return
        frequency_key = data.get("edit_frequency")
        text = data.get("edit_notification_text")
        time = data.get("edit_time")
        weekdays = data.get("edit_weekdays", [])
        monthdays = data.get("edit_monthdays", [])
        if frequency_key == "freq_daily":
            cron_expr = f"{int(time.split(':')[1])} {int(time.split(':')[0])} * * *"
        elif frequency_key == "freq_weekly":
            cron_days = ",".join([
                str(["Нд", "Пн", "Вт", "Ср", "Чт", "Пт", "Сб"].index(day))
                for day in weekdays
            ])
            cron_expr = f"{int(time.split(':')[1])} {int(time.split(':')[0])} * * {cron_days}"
        elif frequency_key == "freq_monthly":
            cron_days = ",".join(monthdays)
            cron_expr = f"{int(time.split(':')[1])} {int(time.split(':')[0])} {cron_days} * *"
        else:
            await callback.answer(await format_template("error_unknown_frequency", "Помилка: невідома частота"), show_alert=True)
            return
        notification.notification_text = text
        notification.custom_notification_text = text
        notification.notification_time = time
        notification.custom_notification_cron = cron_expr
        await notification.save()
        await callback.answer(await format_template("edit_saved", "Зміни збережено ✅"))
        await callback.message.edit_text(text=await format_template("edit_saved_text", "✅ Сповіщення оновлено!"))
        await callback.message.answer(
            text=await format_template("notif_return_to_menu", "Повертаємось до меню сповіщень"),
            reply_markup=await kb.get_notifications_menu_keyboard(),
        )
        await state.clear()
        await state.set_state(MainMenuState.notifications_menu)


@notifications_router.message(
    StateFilter(NotificationsState.creating_notification_request_text)
)
async def process_notification_text(message: Message, state: FSMContext) -> None:
    notification_text = message.text.strip()

    if not notification_text:
        await message.answer(
            text=await format_template("notif_enter_text_prompt", "Будь ласка, введи текст сповіщення."),
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
        ]
    )
    await message.answer(
        text=await format_template("create_summary", "📌 Створення сповіщення:\nТекст: {text}\nОберіть частоту:", text=notification_text),
        reply_markup=keyboard,
    )
    await state.set_state(NotificationsState.creating_notification_request_frequency)


@notifications_router.callback_query(
    StateFilter(NotificationsState.creating_notification_request_frequency)
)
async def handle_frequency(callback: CallbackQuery, state: FSMContext):

    frequency = callback.data
    if not frequency:
        await callback.answer(await format_template("error_unknown_frequency", "Помилка: невідома частота"))
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
            text + "\nТепер введи час у форматі HH:MM (наприклад, 08:30).",
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
            await callback.answer(await format_template("choose_at_least_one_day", "Оберіть хоча б один день"))
            return

        await callback.message.edit_text(
            f"📌 Створення сповіщення:\n"
            f"Текст: {data['new_notification_text']}\n"
            f"Частота: {tc.frequency_options.get(data['frequency'])}\n"
            f"Дні: {', '.join([d for d in selected])}\n"
            f"" + await format_template("enter_time_prompt", "Тепер введи час у форматі HH:MM (наприклад, 08:30)."),
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
            await callback.answer(await format_template("choose_at_least_one_day", "Оберіть хоча б один день"))
            return

        await callback.message.edit_text(
            f"📌 Створення сповіщення:\n"
            f"Текст: {data['new_notification_text']}\n"
            f"Частота: {tc.frequency_options.get(data['frequency'])}\n"
            f"Дні: {', '.join([d for d in selected])}\n"
            f"" + await format_template("enter_time_prompt", "Тепер введи час у форматі HH:MM (наприклад, 08:30)."),
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
            await format_template("notif_invalid_time_format", "Будь ласка, введи час у форматі HH:MM (наприклад, 08:30).")
        )
        return
        
    # Валідація що час у межах 00:00 - 23:59
    hours, minutes = map(int, user_input.split(':'))
    if hours < 0 or hours > 23 or minutes < 0 or minutes > 59:
        await message.answer(
            await format_template("notif_invalid_time_range", "Невірний час. Години мають бути від 00 до 23, хвилини від 00 до 59.")
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

    status_text += f"Час: {user_input}\n" + await format_template("notif_ready", "✅ Сповіщення готове!")
    confirm_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=await format_template("confirm_button", "✅ Підтвердити"), callback_data="confirm_notification"
                )
            ]
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
        await message.answer(await format_template("here_summary", "Ось підсумок:"))
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
    time = data.get("time")
    weekdays = data.get("weekdays", [])
    monthdays = data.get("monthdays", [])

    if frequency == "Щодня":
        cron_expr = f"{int(time.split(':')[1])} {int(time.split(':')[0])} * * *"
    elif frequency == "Щотижня":
        cron_days = ",".join(
            [
                str(["Нд", "Пн", "Вт", "Ср", "Чт", "Пт", "Сб"].index(day))
                for day in weekdays
            ]
        )
        cron_expr = (
            f"{int(time.split(':')[1])} {int(time.split(':')[0])} * * {cron_days}"
        )
    elif frequency == "Щомісяця":
        cron_days = ",".join(monthdays)
        cron_expr = (
            f"{int(time.split(':')[1])} {int(time.split(':')[0])} {cron_days} * *"
        )
    else:
        await callback.answer(await format_template("error_unknown_frequency", "Помилка: невідома частота"), show_alert=True)
        return

    notification = Notification(
        user_id=user_id,
        notification_time=time,
        notification_text=text,
        notification_type=NotificationType.CUSTOM_NOTIFICATION,
        custom_notification_text=text,
        custom_notification_cron=cron_expr,
        custom_notification_execute_once=False,
    )
    await notification.insert()

    await callback.answer(await format_template("notif_saved", "Сповіщення збережено ✅"))

    await callback.message.edit_text(text=await format_template("notif_saved_active", "✅ Сповіщення збережено та активоване!"))

    await callback.message.answer(
        text=await format_template("notif_return_to_menu", "Повертаємось до меню сповіщень"),
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
        await callback.answer(await format_template("notif_toggle_not_found", "Сповіщення не знайдено"), show_alert=True)
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
                InlineKeyboardButton(text=await format_template("button_delete", "Видалити"), callback_data=delete_callback),
                InlineKeyboardButton(text=await format_template("button_edit", "Редагувати"), callback_data=f"edit_{notification.id}"),
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
        await callback.answer(await format_template("notif_delete_not_found", "Сповіщення не знайдено"), show_alert=True)
        return

    await notification.delete()
    await callback.answer(await format_template("notif_deleted", "Сповіщення видалено ✅"))

    notifications = await Notification.find(
        Notification.user_id == str(callback.from_user.id),
        Notification.notification_type == NotificationType.CUSTOM_NOTIFICATION,
    ).to_list()

    if not notifications:
        await callback.message.edit_text(await format_template("notif_none", "У вас немає сповіщень."))
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
                    InlineKeyboardButton(text=await format_template("button_delete", "Видалити"), callback_data=delete_callback),
                    InlineKeyboardButton(text=await format_template("button_edit", "Редагувати"), callback_data=f"edit_{notification.id}"),
                ]
            ]
        )
        await callback.message.answer(text, reply_markup=keyboard)

        await callback.message.answer(
            text=await format_template("notif_all", "Це всі ваші сповіщення."),
            reply_markup=await kb.go_back_button(),
        )


# process go back button
@notifications_router.message(
    StateFilter(NotificationsState.viewing_notifications), F.text == tc.BACK_BUTTON
)
async def process_go_back(message: Message, state: FSMContext) -> None:
    await message.answer(
        text=await format_template("notif_return_to_menu", "Повертаємось до меню сповіщень"),
        reply_markup=await kb.get_notifications_menu_keyboard(),
    )
    await state.clear()
    await state.set_state(MainMenuState.notifications_menu)
