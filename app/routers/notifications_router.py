from aiogram.filters import StateFilter
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram import Router, F
import text_constants as tc
from aiogram.types import ReplyKeyboardRemove
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
)
import re
from routers.main_router import MainMenuState
from states import NotificationsState
import keyboards as kb
from db.models import Notification, NotificationType
from utils.bot_utils import cron_to_human_readable

notifications_router = Router()


@notifications_router.message(StateFilter(MainMenuState.notifications_menu))
async def process_notification_menu(message: Message, state: FSMContext) -> None:
    if message.text == tc.BACK_TO_MAIN_MENU_BUTTON:
        await message.answer(
            text="Ага, вертаємось до головного меню",
            reply_markup=await kb.get_main_menu_keyboard(),
        )
        await state.set_state(MainMenuState.main_menu)

    elif message.text == tc.CREATE_NEW_NOTIFICATION_BUTTON:
        await message.answer(
            text="Створюємо нове сповіщення. Введіть текст сповіщення.",
            reply_markup=ReplyKeyboardRemove(),
        )
        await state.set_state(NotificationsState.creating_notification_request_text)
    elif message.text == tc.VIEW_NOTIFICATIONS_BUTTON:
        notifications = await Notification.find(
            Notification.user_id == str(message.from_user.id),
            Notification.notification_type == NotificationType.CUSTOM_NOTIFICATION,
        ).to_list()
        if not notifications:
            await message.answer("У вас немає сповіщень.")
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
                        InlineKeyboardButton(
                            text=turn_action, callback_data=turn_callback
                        ),
                        InlineKeyboardButton(
                            text="Видалити", callback_data=delete_callback
                        ),
                    ]
                ]
            )
            await message.answer(text, reply_markup=keyboard)
        await message.answer(
            text="Це всі ваші сповіщення.",
            reply_markup=await kb.go_back_button(),
        )
        await state.set_state(NotificationsState.viewing_notifications)


@notifications_router.message(
    StateFilter(NotificationsState.creating_notification_request_text)
)
async def process_notification_text(message: Message, state: FSMContext) -> None:
    notification_text = message.text.strip()

    if not notification_text:
        await message.answer(
            text="Будь ласка, введи текст сповіщення.",
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
        text=f"📌 Створення сповіщення:\nТекст: {notification_text}\nОберіть частоту:",
        reply_markup=keyboard,
    )
    await state.set_state(NotificationsState.creating_notification_request_frequency)


@notifications_router.callback_query(
    StateFilter(NotificationsState.creating_notification_request_frequency)
)
async def handle_frequency(callback: CallbackQuery, state: FSMContext):

    frequency = callback.data
    if not frequency:
        await callback.answer("Невідома частота")
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
            await callback.answer("Обери хоча б один день")
            return

        await callback.message.edit_text(
            f"📌 Створення сповіщення:\n"
            f"Текст: {data['new_notification_text']}\n"
            f"Частота: {tc.frequency_options.get(data['frequency'])}\n"
            f"Дні: {', '.join([d for d in selected])}\n"
            f"Тепер введи час у форматі HH:MM (наприклад, 08:30).",
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
            await callback.answer("Обери хоча б один день")
            return

        await callback.message.edit_text(
            f"📌 Створення сповіщення:\n"
            f"Текст: {data['new_notification_text']}\n"
            f"Частота: {tc.frequency_options.get(data['frequency'])}\n"
            f"Дні: {', '.join([d for d in selected])}\n"
            f"Тепер введи час у форматі HH:MM (наприклад, 08:30).",
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
            "Будь ласка, введи час у форматі HH:MM (наприклад, 08:30)."
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

    status_text += f"Час: {user_input}\n✅ Сповіщення готове!"
    confirm_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Підтвердити", callback_data="confirm_notification"
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
    except Exception as e:
        await message.answer("Ось підсумок:")
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
        await callback.answer("Помилка: невідома частота", show_alert=True)
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

    await callback.answer("Сповіщення збережено ✅")

    await callback.message.edit_text(text="✅ Сповіщення збережено та активоване!")

    await callback.message.answer(
        text="Повертаємось до меню сповіщень",
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
        await callback.answer("Сповіщення не знайдено", show_alert=True)
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
                InlineKeyboardButton(text="Видалити", callback_data=delete_callback),
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
        await callback.answer("Сповіщення не знайдено", show_alert=True)
        return

    await notification.delete()
    await callback.answer("Сповіщення видалено ✅")

    notifications = await Notification.find(
        Notification.user_id == str(callback.from_user.id),
        Notification.notification_type == NotificationType.CUSTOM_NOTIFICATION,
    ).to_list()

    if not notifications:
        await callback.message.edit_text("У вас немає сповіщень.")
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
                    InlineKeyboardButton(
                        text="Видалити", callback_data=delete_callback
                    ),
                ]
            ]
        )
        await callback.message.answer(text, reply_markup=keyboard)

    await callback.message.answer(
        text="Це всі ваші сповіщення.",
        reply_markup=await kb.go_back_button(),
    )


# process go back button
@notifications_router.message(
    StateFilter(NotificationsState.viewing_notifications), F.text == tc.BACK_BUTTON
)
async def process_go_back(message: Message, state: FSMContext) -> None:
    await message.answer(
        text="Повертаємось до меню сповіщень",
        reply_markup=await kb.get_notifications_menu_keyboard(),
    )
    await state.clear()
    await state.set_state(MainMenuState.notifications_menu)
