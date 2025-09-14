"""
Модуль для відправлення статистики користувачам через Telegram
"""
import logging
import asyncio
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

from aiogram import Bot
from aiogram.types import InputFile, FSInputFile

from app.db.models import User, UserStatistics, PeriodType
from app.statistics_web_generator import WebStatisticsGenerator

logger = logging.getLogger(__name__)

# Імпортуємо AI аналізатор (опціонально)
try:
    from app.ai_analyzer import StatisticsAnalyzer
    AI_ANALYZER_AVAILABLE = True
except ImportError:
    AI_ANALYZER_AVAILABLE = False
    logger.warning("AI аналізатор не доступний")


class StatisticsSender:
    """Клас для генерації та відправки статистики користувачам"""
    
    def __init__(self, bot: Bot):
        self.bot = bot
        self.web_generator = WebStatisticsGenerator()
        
        # Ініціалізуємо AI аналізатор, якщо доступний
        self.ai_analyzer = None
        if AI_ANALYZER_AVAILABLE:
            try:
                self.ai_analyzer = StatisticsAnalyzer()
                logger.info("AI аналізатор ініціалізовано")
            except Exception as e:
                logger.error(f"Помилка ініціалізації AI аналізатора: {e}")
        
    async def send_weekly_statistics_to_user(self, user_id: str, 
                                             stats: Optional[UserStatistics] = None) -> bool:
        """
        Відправляє тижневу статистику користувачу
        
        Args:
            user_id: ID користувача
            stats: об'єкт статистики (опціонально)
            
        Returns:
            Результат відправлення (True/False)
        """
        try:
            # Якщо статистика не передана, шукаємо її в базі
            if not stats:
                from app.statistics_scheduler import get_user_statistics
                result = await get_user_statistics(
                    user_id=user_id,
                    period_type="weekly",
                    generate_if_missing=True,
                    generate_image=False,
                    use_previous_period=True
                )
                stats = result.get("statistics")
                
            if not stats:
                logger.warning(f"Не знайдено статистику для користувача {user_id}")
                return False
                
            # Запускаємо генерацію AI-аналізу, якщо доступно
            if self.ai_analyzer and not stats.ai_analysis:
                try:
                    logger.info(f"Генеруємо AI-аналіз для користувача {user_id}")
                    await self.ai_analyzer.analyze_statistics(stats)
                except Exception as ai_err:
                    logger.error(f"Помилка при генерації AI-аналізу: {ai_err}")
            
            # Генеруємо зображення за допомогою веб-генератора
            image_path = await self.web_generator.generate_image(stats)
            
            if not image_path or not os.path.exists(image_path):
                logger.error(f"Не вдалося згенерувати зображення статистики для користувача {user_id}")
                return False
                
            # Формуємо повідомлення
            caption = f"📊 <b>Ваша тижнева статистика за попередній тиждень</b>\n\n" \
                      f"Період: {stats.period_start.strftime('%d.%m.%Y')} - {stats.period_end.strftime('%d.%m.%Y')}"
            
                
            # Відправляємо зображення
            await self.bot.send_photo(
                chat_id=user_id,
                photo=FSInputFile(image_path),
                caption=caption,
                parse_mode="HTML"
            )
            
            # Якщо є AI-аналіз, відправляємо його окремим повідомленням
            if stats.ai_analysis:
                analysis_message = f"{stats.ai_analysis}"
                
                # Розбиваємо на частини, якщо повідомлення занадто довге
                if len(analysis_message) > 4000:
                    parts = [analysis_message[i:i+4000] for i in range(0, len(analysis_message), 4000)]
                    for i, part in enumerate(parts):
                        if i == 0:
                            await self.bot.send_message(
                                chat_id=user_id,
                                text=part,
                                parse_mode="HTML"
                            )
                        else:
                            await self.bot.send_message(
                                chat_id=user_id,
                                text=part,
                                parse_mode="HTML"
                            )
                        await asyncio.sleep(0.5)  # Невелика затримка між повідомленнями
                else:
                    await self.bot.send_message(
                        chat_id=user_id,
                        text=analysis_message,
                        parse_mode="HTML"
                    )
                logger.info(f"Відправлено AI-аналіз статистики користувачу {user_id}")
            
            logger.info(f"Відправлено тижневу статистику користувачу {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Помилка при відправці статистики користувачу {user_id}: {e}")
            return False
            
    async def send_monthly_statistics_to_user(self, user_id: str,
                                              stats: Optional[UserStatistics] = None) -> bool:
        """
        Відправляє місячну статистику користувачу
        
        Args:
            user_id: ID користувача
            stats: об'єкт статистики (опціонально)
            
        Returns:
            Результат відправлення (True/False)
        """
        try:
            # Якщо статистика не передана, шукаємо її в базі
            if not stats:
                from app.statistics_scheduler import get_user_statistics
                result = await get_user_statistics(
                    user_id=user_id,
                    period_type="monthly",
                    generate_if_missing=True,
                    generate_image=False,
                    use_previous_period=True
                )
                stats = result.get("statistics")
                
            if not stats:
                logger.warning(f"Не знайдено місячну статистику для користувача {user_id}")
                return False
                
            # Запускаємо генерацію AI-аналізу, якщо доступно
            if self.ai_analyzer and not stats.ai_analysis:
                try:
                    logger.info(f"Генеруємо AI-аналіз для місячної статистики користувача {user_id}")
                    await self.ai_analyzer.analyze_statistics(stats)
                except Exception as ai_err:
                    logger.error(f"Помилка при генерації AI-аналізу: {ai_err}")
            
            # Генеруємо зображення за допомогою веб-генератора
            image_path = await self.web_generator.generate_image(stats)
            
            if not image_path or not os.path.exists(image_path):
                logger.error(f"Не вдалося згенерувати зображення місячної статистики для користувача {user_id}")
                return False
                
            # Формуємо повідомлення
            caption = f"📈 <b>Ваша місячна статистика за попередній місяць</b>\n\n" \
                      f"Період: {stats.period_start.strftime('%d.%m.%Y')} - {stats.period_end.strftime('%d.%m.%Y')}"
        
                
            # Відправляємо зображення
            await self.bot.send_photo(
                chat_id=user_id,
                photo=FSInputFile(image_path),
                caption=caption,
                parse_mode="HTML"
            )
            
            # Якщо є AI-аналіз, відправляємо його окремим повідомленням
            if stats.ai_analysis:
                analysis_message = f"{stats.ai_analysis}"
                
                # Розбиваємо на частини, якщо повідомлення занадто довге
                if len(analysis_message) > 4000:
                    parts = [analysis_message[i:i+4000] for i in range(0, len(analysis_message), 4000)]
                    for i, part in enumerate(parts):
                        if i == 0:
                            await self.bot.send_message(
                                chat_id=user_id,
                                text=part,
                                parse_mode="HTML"
                            )
                        else:
                            await self.bot.send_message(
                                chat_id=user_id,
                                text=part,
                                parse_mode="HTML"
                            )
                        await asyncio.sleep(0.5)  # Невелика затримка між повідомленнями
                else:
                    await self.bot.send_message(
                        chat_id=user_id,
                        text=analysis_message,
                        parse_mode="HTML"
                    )
                logger.info(f"Відправлено AI-аналіз місячної статистики користувачу {user_id}")
            
            logger.info(f"Відправлено місячну статистику користувачу {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Помилка при відправці місячної статистики користувачу {user_id}: {e}")
            return False
    
    async def send_statistics_to_all_users(self, period_type: PeriodType) -> dict:
        """
        Відправляє статистику всім користувачам
        
        Args:
            period_type: тип періоду (тижневий/місячний)
            
        Returns:
            Результати відправлення
        """
        from app.statistics_scheduler import generate_statistics_manually
        
        results = {
            "success": 0,
            "failed": 0,
            "total": 0,
            "errors": []
        }
        
        try:
            # Отримуємо всіх користувачів
            users = await User.find().to_list()
            results["total"] = len(users)
            
            # Генеруємо статистику для всіх користувачів
            period_str = "weekly" if period_type == PeriodType.WEEKLY else "monthly"
            stats_result = await generate_statistics_manually(
                period_type=period_str,
                generate_image=False
            )
            
            all_stats = stats_result.get("statistics", [])
            stats_by_user = {stat.user_id: stat for stat in all_stats}
            
            # Відправляємо статистику кожному користувачу
            for user in users:
                try:
                    user_id = user.telegram_id
                    user_stats = stats_by_user.get(user_id)
                    
                    if period_type == PeriodType.WEEKLY:
                        success = await self.send_weekly_statistics_to_user(user_id, user_stats)
                    else:
                        success = await self.send_monthly_statistics_to_user(user_id, user_stats)
                        
                    if success:
                        results["success"] += 1
                    else:
                        results["failed"] += 1
                        results["errors"].append(f"Не вдалося відправити статистику користувачу {user_id}")
                        
                except Exception as e:
                    results["failed"] += 1
                    results["errors"].append(f"Помилка при відправці користувачу {user.telegram_id}: {str(e)}")
                    logger.error(f"Помилка при відправці статистики користувачу {user.telegram_id}: {e}")
                    
                # Затримка між повідомленнями для уникнення обмежень Telegram
                await asyncio.sleep(0.5)
                
            return results
            
        except Exception as e:
            results["errors"].append(f"Загальна помилка: {str(e)}")
            logger.error(f"Помилка при відправці статистики користувачам: {e}")
            return results

    def _clean_html_for_telegram(self, html_text: str) -> str:
        """
        Очищає HTML текст для сумісності з Telegram HTML парсером.
        Видаляє або виправляє некоректні HTML теги, які можуть спричинити помилки парсингу.
        """
        import re
        from html.parser import HTMLParser

        if not html_text:
            return html_text

        # Залишаємо тільки підтримувані Telegram теги і перевіряємо їх коректність
        supported_tags = ['b', 'i', 'u', 's', 'code', 'pre', 'a']

        # Спочатку перевіримо на незакриті теги
        class TagChecker(HTMLParser):
            def __init__(self):
                super().__init__()
                self.stack = []
                self.unclosed_tags = []

            def handle_starttag(self, tag, attrs):
                if tag in supported_tags:
                    self.stack.append(tag)

            def handle_endtag(self, tag):
                if tag in supported_tags:
                    if self.stack and self.stack[-1] == tag:
                        self.stack.pop()
                    else:
                        # Незакритий тег - запам'ятовуємо для виправлення
                        self.unclosed_tags.append(tag)

            def get_unclosed_tags(self):
                return self.stack

        # Перевіряємо структуру тегів
        checker = TagChecker()
        checker.feed(html_text)

        # Виправляємо незакриті теги, додаючи закриваючі в кінці
        for tag in reversed(checker.get_unclosed_tags()):
            html_text += f'</{tag}>'

        # Очищаємо зайві пробіли та нові рядки
        html_text = re.sub(r'\s+', ' ', html_text).strip()

        # Обмежуємо довжину повідомлення (Telegram має ліміт 4096 символів)
        if len(html_text) > 4000:
            html_text = html_text[:4000] + "..."

        return html_text


# Функції для інтеграції з планувальником

async def send_weekly_statistics_to_all_users(bot):
    """Відправляє тижневу статистику всім користувачам"""
    sender = StatisticsSender(bot)
    return await sender.send_statistics_to_all_users(PeriodType.WEEKLY)


async def send_monthly_statistics_to_all_users(bot):
    """Відправляє місячну статистику всім користувачам"""
    sender = StatisticsSender(bot)
    return await sender.send_statistics_to_all_users(PeriodType.MONTHLY)
