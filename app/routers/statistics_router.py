"""
Роутер для обробки статистичних команд у Telegram боті
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command

from app.db.models import PeriodType
from app.statistics_sender import StatisticsSender

statistics_router = Router()


@statistics_router.message(Command('stats'))
async def cmd_stats(message: Message):
    """Обробник команди /stats"""
    user_id = str(message.from_user.id)
    await message.answer("Вибери тип статистики за попередній період:", reply_markup={
        "inline_keyboard": [
            [
                {"text": "За попередній тиждень", "callback_data": "stats_weekly"},
                {"text": "За попередній місяць", "callback_data": "stats_monthly"}
            ]
        ]
    })


@statistics_router.callback_query(F.data == "stats_weekly")
async def process_weekly_stats(callback: CallbackQuery):
    """Відправка тижневої статистики за запитом"""
    await callback.answer("Генерую статистику за попередній тиждень, зачекайте...")
    user_id = str(callback.from_user.id)
    
    # Відправляємо повідомлення про очікування
    await callback.message.answer("Генерую вашу статистику за попередній тиждень...")
    
    # Відправляємо статистику
    sender = StatisticsSender(callback.bot)
    result = await sender.send_weekly_statistics_to_user(user_id)
    
    if not result:
        await callback.message.answer("На жаль, не вдалося згенерувати статистику. Спробуйте пізніше.")


@statistics_router.callback_query(F.data == "stats_monthly")
async def process_monthly_stats(callback: CallbackQuery):
    """Відправка місячної статистики за запитом"""
    await callback.answer("Генерую статистику за попередній місяць, зачекайте...")
    user_id = str(callback.from_user.id)
    
    # Відправляємо повідомлення про очікування
    await callback.message.answer("Генерую вашу статистику за попередній місяць...")
    
    # Відправляємо статистику
    sender = StatisticsSender(callback.bot)
    result = await sender.send_monthly_statistics_to_user(user_id)
    
    if not result:
        await callback.message.answer("На жаль, не вдалося згенерувати місячну статистику. Спробуйте пізніше.")


# Команда для адміністратора для відправлення статистики всім користувачам
@statistics_router.message(Command('send_stats_to_all'))
async def cmd_send_stats_to_all(message: Message):
    """Обробник команди /send_stats_to_all"""
    # Перевіряємо, чи користувач є адміністратором
    admin_ids = ["379872548"]  # Додайте ID адміністраторів
    if str(message.from_user.id) not in admin_ids:
        await message.answer("У вас немає прав на використання цієї команди.")
        return
    
    await message.answer("Виберіть тип статистики для відправлення всім користувачам:", reply_markup={
        "inline_keyboard": [
            [
                {"text": "Тижнева для всіх", "callback_data": "send_weekly_all"},
                {"text": "Місячна для всіх", "callback_data": "send_monthly_all"}
            ]
        ]
    })


@statistics_router.callback_query(F.data == "send_weekly_all")
async def process_send_weekly_all(callback: CallbackQuery):
    """Відправка тижневої статистики всім користувачам"""
    admin_ids = ["379872548"]  # Додайте ID адміністраторів
    if str(callback.from_user.id) not in admin_ids:
        await callback.answer("У вас немає прав на виконання цієї дії.")
        return
    
    await callback.answer("Розпочинаю відправлення статистики всім користувачам...")
    await callback.message.answer("Розпочинаю відправлення тижневої статистики всім користувачам.\nЦе може зайняти деякий час.")
    
    from app.statistics_sender import send_weekly_statistics_to_all_users
    results = await send_weekly_statistics_to_all_users(callback.bot)
    
    await callback.message.answer(
        f"Результати відправлення тижневої статистики:\n"
        f"✅ Успішно: {results['success']}\n"
        f"❌ Невдало: {results['failed']}\n"
        f"📊 Всього: {results['total']}"
    )


@statistics_router.callback_query(F.data == "send_monthly_all")
async def process_send_monthly_all(callback: CallbackQuery):
    """Відправка місячної статистики всім користувачам"""
    admin_ids = ["379872548"]  # Додайте ID адміністраторів
    if str(callback.from_user.id) not in admin_ids:
        await callback.answer("У вас немає прав на виконання цієї дії.")
        return
    
    await callback.answer("Розпочинаю відправлення статистики всім користувачам...")
    await callback.message.answer("Розпочинаю відправлення місячної статистики всім користувачам.\nЦе може зайняти деякий час.")
    
    from app.statistics_sender import send_monthly_statistics_to_all_users
    results = await send_monthly_statistics_to_all_users(callback.bot)
    
    await callback.message.answer(
        f"Результати відправлення місячної статистики:\n"
        f"✅ Успішно: {results['success']}\n"
        f"❌ Невдало: {results['failed']}\n"
        f"📊 Всього: {results['total']}"
    )
