"""
Скрипт для генерації тестових даних для користувача
"""

import asyncio
from datetime import datetime, timedelta
from app.db.database import init_db
from app.db.models import User, MorningQuiz, TrainingSession
import random


async def generate_test_data_for_user(user_id: str, days: int = 35):
    """Генерація тестових даних для користувача за вказану кількість днів"""
    
    print(f"Генерація тестових даних для користувача {user_id} за {days} днів...")
    
    # Видаляємо старі дані
    await MorningQuiz.find({"user_id": user_id}).delete()
    await TrainingSession.find({"user_id": user_id}).delete()
    print("Видалено старі дані")
    
    # Базові параметри
    base_weight = 72.5  # реалістична вага
    base_wellbeing = 7
    quiz_count = 0
    training_count = 0
    
    # Генеруємо ранкові квізи (майже кожен день)
    for i in range(days):
        date = datetime.now() - timedelta(days=i)
        
        # 90% ймовірність заповнення квізу
        if random.random() < 0.9:
            # Реалістичні зміни з цілими або простими числами
            weight_change = round(random.uniform(-0.5, 0.5) + (i * 0.02), 1)  # поступове зниження ваги
            wellbeing = max(1, min(10, base_wellbeing + random.randint(-2, 3)))
            sleep_hours = round(random.uniform(6.0, 9.5), 1)  # округлюємо до 1 знака
            
            # Варіації залежно від дня тижня
            day_of_week = date.weekday()
            if day_of_week in [5, 6]:  # вихідні
                sleep_hours = round(sleep_hours + random.uniform(0.5, 1.5), 1)
                wellbeing += random.randint(0, 1)
            
            morning_quiz = MorningQuiz(
                user_id=user_id,
                how_do_you_feel_today=wellbeing,
                how_many_hours_of_sleep=max(4.0, min(12.0, sleep_hours)),
                weight=round(max(65.0, min(80.0, base_weight + weight_change)), 1),  # округлюємо вагу
                is_going_to_gym=random.choice([True, False]),
                completed=True,
                created_at=date
            )
            await morning_quiz.save()
            quiz_count += 1
    
    # Генеруємо тренування (3-4 рази на тиждень)
    for i in range(days):
        date = datetime.now() - timedelta(days=i)
        day_of_week = date.weekday()
        
        # Більше тренувань у будні
        training_probability = 0.6 if day_of_week < 5 else 0.3
        
        if random.random() < training_probability:
            # Прогрес у тренуваннях
            progress = (days - i) / days
            
            difficulty = max(1, min(10, 5 + int(progress * 3) + random.randint(-2, 2)))
            stress = max(1, min(10, 6 - int(progress * 2) + random.randint(-2, 2)))
            feeling_before = random.randint(6, 10)
            
            # Більш реалістичні тривалості тренувань (округлені до 5 хвилин)
            base_duration = random.choice([45, 50, 55, 60, 65, 70, 75, 80, 85, 90])
            duration = base_duration
            
            training_session = TrainingSession(
                user_id=user_id,
                how_do_you_feel_before=feeling_before,
                how_hard_was_training=difficulty,
                do_you_have_any_pain=random.choice([True, False, False, False]),
                training_started_at=date,
                training_ended_at=date + timedelta(minutes=duration),
                training_duration=duration,
                stress_level=stress,
                completed=True,
                created_at=date
            )
            await training_session.save()
            training_count += 1
    
    print(f"✅ Згенеровано {quiz_count} ранкових квізів")
    print(f"✅ Згенеровано {training_count} тренувань")
    print(f"✅ Дані створено за період: {(datetime.now() - timedelta(days=days-1)).strftime('%Y-%m-%d')} - {datetime.now().strftime('%Y-%m-%d')}")


async def create_test_user(telegram_id: str):
    """Створення тестового користувача"""
    
    # Видаляємо існуючого користувача
    existing_user = await User.find_one({"telegram_id": telegram_id})
    if existing_user:
        await existing_user.delete()
        print(f"Видалено існуючого користувача {telegram_id}")
    
    # Створюємо нового
    test_user = User(
        telegram_id=telegram_id,
        full_name="Тестовий Користувач",
        telegram_username="test_user",
        is_active=True,
        is_verified=True
    )
    await test_user.save()
    print(f"✅ Створено користувача {telegram_id}")


async def main():
    """Головна функція"""
    print("🚀 Запуск генерації тестових даних...")
    
    # Ініціалізація бази даних
    await init_db()
    
    # ID тестового користувача
    test_user_id = "test_user_123"
    
    # Створюємо користувача
    await create_test_user(test_user_id)
    
    # Генеруємо дані за 35 днів (5 тижнів)
    await generate_test_data_for_user(test_user_id, days=35)
    
    # Генеруємо статистику для користувача
    print("\n📊 Генерація статистики на основі створених даних...")
    from app.statistics import StatisticsGenerator
    from app.db.models import PeriodType
    
    stats_generator = StatisticsGenerator()
    
    # Генеруємо тижневу статистику
    weekly_stats = await stats_generator.generate_user_statistics(test_user_id, PeriodType.WEEKLY)
    print(f"✅ Згенеровано тижневу статистику для користувача {test_user_id}")
    print("   Дані у тижневій статистиці:")
    print(f"   - Точок даних у stress_data: {len(weekly_stats.stress_data.get('data_points', [])) if weekly_stats.stress_data else 0}")
    print(f"   - Точок даних у warehouse_data: {len(weekly_stats.warehouse_data.get('data_points', [])) if weekly_stats.warehouse_data else 0}")
    print(f"   - Точок даних у sleep_data: {len(weekly_stats.sleep_data.get('data_points', [])) if weekly_stats.sleep_data else 0}")
    print(f"   - Точок даних у wellbeing_data: {len(weekly_stats.wellbeing_data.get('data_points', [])) if weekly_stats.wellbeing_data else 0}")
    print(f"   - Точок даних у weight_data: {len(weekly_stats.weight_data.get('data_points', [])) if weekly_stats.weight_data else 0}")
    
    # Генеруємо місячну статистику
    monthly_stats = await stats_generator.generate_user_statistics(test_user_id, PeriodType.MONTHLY)
    print(f"✅ Згенеровано місячну статистику для користувача {test_user_id}")
    print("   Дані у місячній статистиці:")
    print(f"   - Точок даних у stress_data: {len(monthly_stats.stress_data.get('data_points', [])) if monthly_stats.stress_data else 0}")
    print(f"   - Точок даних у warehouse_data: {len(monthly_stats.warehouse_data.get('data_points', [])) if monthly_stats.warehouse_data else 0}")
    print(f"   - Точок даних у sleep_data: {len(monthly_stats.sleep_data.get('data_points', [])) if monthly_stats.sleep_data else 0}")
    print(f"   - Точок даних у wellbeing_data: {len(monthly_stats.wellbeing_data.get('data_points', [])) if monthly_stats.wellbeing_data else 0}")
    print(f"   - Точок даних у weight_data: {len(monthly_stats.weight_data.get('data_points', [])) if monthly_stats.weight_data else 0}")
    
    print("\n🎉 Генерація тестових даних та статистики завершена!")
    print(f"Користувач: {test_user_id}")
    print("Тепер можна тестувати систему статистики і візуалізацію")


if __name__ == "__main__":
    asyncio.run(main())
