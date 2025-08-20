"""
Тестовий скрипт для негайного запуску відправки статистики всім користувачам
"""

import asyncio
import logging
import sys
from aiogram import Bot
from app.db.database import init_db
from app.statistics_sender import send_weekly_statistics_to_all_users
from app.config import settings

# Налаштовуємо логування
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def send_statistics_now():
    """Відправити тижневу статистику всім користувачам прямо зараз"""
    
    # Ініціалізуємо з'єднання з базою даних
    await init_db()
    
    # Ініціалізуємо бота
    bot = Bot(token=settings.BOT_TOKEN)
    
    try:
        logger.info("Запускаємо відправку тижневої статистики всім користувачам...")
        
        # Відправляємо тижневу статистику
        results = await send_weekly_statistics_to_all_users(bot)
        
        logger.info(f"Результати відправки статистики:")
        logger.info(f"✅ Успішно: {results['success']}")
        logger.info(f"❌ Невдало: {results['failed']}")
        logger.info(f"📊 Всього: {results['total']}")
        
        if results['errors']:
            logger.warning("Помилки під час відправки:")
            for error in results['errors']:
                logger.warning(f"- {error}")
    
    except Exception as e:
        logger.error(f"Загальна помилка при відправці статистики: {e}")
        
    finally:
        # Закриваємо сесію бота
        await bot.session.close()


if __name__ == "__main__":
    # Запускаємо відправку статистики
    asyncio.run(send_statistics_now())
