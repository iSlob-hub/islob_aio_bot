from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from app.statistics import StatisticsGenerator
from app.db.models import PeriodType
import logging

logger = logging.getLogger(__name__)


class StatisticsScheduler:
    """Клас для планування автоматичної генерації статистики"""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.stats_generator = StatisticsGenerator()
    
    @staticmethod
    def is_fourth_monday_or_later():
        """Перевіряє, чи поточний понеділок є 4-м або пізнішим в місяці"""
        from datetime import datetime, timedelta
        
        current_date = datetime.now()
        
        # Перевіряємо, чи сьогодні понеділок
        if current_date.weekday() != 0:
            return False
        
        # Знаходимо перший день місяця
        first_day = current_date.replace(day=1)
        
        # Знаходимо перший понеділок місяця
        days_until_monday = (7 - first_day.weekday()) % 7
        if first_day.weekday() == 0:  # Якщо 1-е число - понеділок
            days_until_monday = 0
        
        first_monday = first_day + timedelta(days=days_until_monday)
        
        # Рахуємо кількість понеділків від початку місяця до поточної дати
        weeks_diff = (current_date - first_monday).days // 7
        
        # Повертаємо True, якщо це 4-й понеділок або пізніше
        return weeks_diff >= 3
    
    async def generate_weekly_statistics(self):
        """Генерація тижневої статистики кожного понеділка"""
        try:
            logger.info("Початок генерації тижневої статистики")
            generated_stats = await self.stats_generator.generate_statistics_for_all_users(
                PeriodType.WEEKLY
            )
            logger.info(f"Згенеровано тижневу статистику для {len(generated_stats)} користувачів")
        except Exception as e:
            logger.error(f"Помилка при генерації тижневої статистики: {e}")
    
    async def generate_monthly_statistics(self):
        """Генерація місячної статистики кожен 4-й понеділок"""
        try:
            # Перевіряємо, чи це 4-й понеділок або пізніше
            if self.is_fourth_monday_or_later():
                logger.info("Початок генерації місячної статистики (4-й понеділок або пізніше)")
                generated_stats = await self.stats_generator.generate_statistics_for_all_users(
                    PeriodType.MONTHLY
                )
                logger.info(f"Згенеровано місячну статистику для {len(generated_stats)} користувачів")
            else:
                logger.info("Не 4-й понеділок місяця, місячна статистика не генерується")
                
        except Exception as e:
            logger.error(f"Помилка при генерації місячної статистики: {e}")
    
    def start_scheduler(self):
        """Запуск планувальника"""
        # Тижнева статистика: кожного понеділка о 08:00
        self.scheduler.add_job(
            self.generate_weekly_statistics,
            trigger=CronTrigger(day_of_week=0, hour=8, minute=0),  # Понеділок = 0
            id='weekly_statistics',
            name='Генерація тижневої статистики (кожен понеділок)',
            replace_existing=True
        )
        
        # Місячна статистика: кожного понеділка о 08:30 (перевірка всередині функції)
        self.scheduler.add_job(
            self.generate_monthly_statistics,
            trigger=CronTrigger(day_of_week=0, hour=8, minute=30),  # Понеділок = 0
            id='monthly_statistics',
            name='Генерація місячної статистики (4-й понеділок)',
            replace_existing=True
        )
        
        self.scheduler.start()
        logger.info("Планувальник статистики запущено")
    
    def stop_scheduler(self):
        """Зупинка планувальника"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Планувальник статистики зупинено")
    
    def get_scheduler_status(self) -> dict:
        """Отримання статусу планувальника"""
        from datetime import datetime
        
        if not self.scheduler.running:
            return {"status": "stopped", "jobs": []}
        
        jobs_info = []
        for job in self.scheduler.get_jobs():
            next_run = job.next_run_time
            jobs_info.append({
                "id": job.id,
                "name": job.name,
                "next_run": next_run.isoformat() if next_run else None,
                "trigger": str(job.trigger)
            })
        
        # Додаємо інформацію про поточний статус 4-го понеділка
        current_monday_info = {
            "is_fourth_monday_or_later": self.is_fourth_monday_or_later(),
            "current_date": datetime.now().strftime("%Y-%m-%d %A"),
            "current_weekday": datetime.now().weekday(),
        }
        
        return {
            "status": "running",
            "jobs": jobs_info,
            "monday_check": current_monday_info
        }


# Глобальний екземпляр планувальника
statistics_scheduler = StatisticsScheduler()


# Функції для ручного запуску статистики (для тестування та адміністрування)
async def generate_statistics_manually(user_id: str = None, period_type: str = "weekly"):
    """Ручна генерація статистики для користувача або всіх користувачів"""
    stats_generator = StatisticsGenerator()
    
    period = PeriodType.WEEKLY if period_type.lower() == "weekly" else PeriodType.MONTHLY
    
    if user_id:
        # Генерація для конкретного користувача
        try:
            stats = await stats_generator.generate_user_statistics(user_id, period)
            logger.info(f"Згенеровано {period_type} статистику для користувача {user_id}")
            return stats
        except Exception as e:
            logger.error(f"Помилка при генерації статистики для користувача {user_id}: {e}")
            raise
    else:
        # Генерація для всіх користувачів
        try:
            generated_stats = await stats_generator.generate_statistics_for_all_users(period)
            logger.info(f"Згенеровано {period_type} статистику для {len(generated_stats)} користувачів")
            return generated_stats
        except Exception as e:
            logger.error(f"Помилка при генерації {period_type} статистики: {e}")
            raise


async def get_user_statistics(user_id: str, period_type: str = "weekly", generate_if_missing: bool = True):
    """Отримання статистики користувача з можливістю автоматичної генерації"""
    from app.db.models import UserStatistics
    
    period = PeriodType.WEEKLY if period_type.lower() == "weekly" else PeriodType.MONTHLY
    stats_generator = StatisticsGenerator()
    
    # Визначаємо діапазон дат
    if period == PeriodType.WEEKLY:
        start_date, end_date = stats_generator.get_current_week_range()
    else:
        start_date, end_date = stats_generator.get_current_month_range()
    
    # Шукаємо існуючу статистику
    existing_stats = await UserStatistics.find_one({
        "user_id": user_id,
        "period_type": period,
        "period_start": start_date,
        "period_end": end_date
    })
    
    if existing_stats:
        return existing_stats
    elif generate_if_missing:
        # Генеруємо нову статистику
        logger.info(f"Статистика для користувача {user_id} не знайдена, генеруємо нову")
        return await stats_generator.generate_user_statistics(user_id, period)
    else:
        return None
