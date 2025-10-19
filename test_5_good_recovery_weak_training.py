#!/usr/bin/env python3
"""
Генерація тестових даних для сценарію 5:
Дуже хороші показники по сну та самопочуттю, низький стрес, але слабкі тренування 
і занадто швидкий набір ваги.
Використовувати для похвали сильних сторін (сон, енергія), але критики ваги/тренувань.
"""

import asyncio
from datetime import datetime, timedelta
from app.db.database import init_db
from app.db.models import (
    User, MorningQuiz, TrainingSession, UserStatistics, 
    PeriodType, TrainingGoal
)
from zoneinfo import ZoneInfo

async def create_good_recovery_weak_training_scenario():
    """
    Сценарій 5: Хороші показники відновлення але слабкі тренування
    Відмінний сон/самопочуття, низький стрес, слабкі тренування, швидкий набір ваги
    """
    await init_db()
    
    test_user_id = "good_recovery_weak_training_user"
    
    # Користувач з ціллю схуднення (але набирає вагу)
    test_user = User(
        telegram_id=test_user_id,
        full_name="Хороше Відновлення Слабкі Тренування",
        telegram_username="good_recovery_weak_training",
        is_active=True,
        is_verified=True,
        training_goal=TrainingGoal.LOSE_WEIGHT
    )
    await test_user.save()
    print(f"✅ Створено користувача: {test_user.full_name}")
    
    # Період (22 вересня 2025, 21:36)
    start_date = datetime(2025, 6, 12, 21, 9, tzinfo=ZoneInfo("Europe/Kyiv"))
    
    # Дані для хорошого відновлення але слабких тренувань (7 днів)
    daily_data = [
        # День 1 - відмінний старт з відновленням
        {"stress": 2, "sleep": 8.5, "wellbeing": 8, "training": 4, "weight": 68.0},
        # День 2 - продовження хорошого сну, але тренування слабкі
        {"stress": 1, "sleep": 9.0, "wellbeing": 9, "training": 3, "weight": 68.4},
        # День 3 - ідеальне відновлення, мінімальні тренування
        {"stress": 2, "sleep": 8.0, "wellbeing": 8, "training": 4, "weight": 68.7},
        # День 4 - стрес мінімальний, тренування не покращуються
        {"stress": 1, "sleep": 8.5, "wellbeing": 9, "training": 3, "weight": 69.0},
        # День 5 - відпочинок відмінний, але активність низька
        {"stress": 3, "sleep": 8.0, "wellbeing": 7, "training": 5, "weight": 69.3},
        # День 6 - сон ідеальний, тренування пропускає
        {"stress": 2, "sleep": 9.0, "wellbeing": 8, "training": 2, "weight": 69.5},
        # День 7 - енергія є, але використовує погано
        {"stress": 2, "sleep": 8.5, "wellbeing": 8, "training": 4, "weight": 69.8}
    ]
    
    training_sessions_count = 0
    morning_quizzes_count = 0
    
    # Створюємо дані по днях
    for day, data in enumerate(daily_data):
        current_date = start_date + timedelta(days=day)
        
        # Ранкові квізи з швидким набором ваги
        morning_quiz = MorningQuiz(
            user_id=test_user_id,
            how_do_you_feel_today=data["wellbeing"],
            how_many_hours_of_sleep=data["sleep"],
            weight=data["weight"],
            is_going_to_gym=data["training"] > 2,
            gym_attendance_time=current_date.replace(hour=17, minute=0) if data["training"] > 2 else None,
            completed=True,
            created_at=current_date.replace(hour=8, minute=30)
        )
        await morning_quiz.save()
        morning_quizzes_count += 1
        
        # Слабкі тренувальні сесії (багато пропусків)
        if data["training"] > 2:  # Пропускає дуже слабкі дні
            training_session = TrainingSession(
                user_id=test_user_id,
                how_do_you_feel_before=data["wellbeing"],
                how_hard_was_training=data["training"],
                do_you_have_any_pain=False,
                training_started_at=current_date.replace(hour=17, minute=0),
                training_ended_at=current_date.replace(hour=17, minute=45),  # Короткі тренування
                training_duration=45,  # Тільки 45 хвилин
                stress_level=data["stress"],
                do_you_have_soreness=False,  # Немає болючості - слабкі навантаження
                completed=True,
                created_at=current_date.replace(hour=17, minute=0)
            )
            await training_session.save()
            training_sessions_count += 1
    
    print(f"✅ Створено {morning_quizzes_count} ранкових квізів")
    print(f"✅ Створено {training_sessions_count} тренувальних сесій (пропущено {7-training_sessions_count})")
    
    # Створюємо статистику
    end_date = start_date + timedelta(days=6, hours=23, minutes=59, seconds=59)
    
    # Розраховуємо метрики
    stress_avg = sum(d["stress"] for d in daily_data) / len(daily_data)  # 1.9
    sleep_avg = sum(d["sleep"] for d in daily_data) / len(daily_data)    # 8.5
    wellbeing_avg = sum(d["wellbeing"] for d in daily_data) / len(daily_data)  # 8.1
    training_avg = sum(d["training"] for d in daily_data) / len(daily_data)    # 3.6
    
    start_weight = daily_data[0]["weight"]
    end_weight = daily_data[-1]["weight"]
    weight_change = end_weight - start_weight  # +1.8
    
    user_statistics = UserStatistics(
        user_id=test_user_id,
        period_type=PeriodType.WEEKLY,
        period_start=start_date,
        period_end=end_date,
        total_training_sessions=training_sessions_count,
        total_morning_quizzes=morning_quizzes_count,
        
        # Стрес: мінімальний 1.9, ідеальний
        stress_data={
            "chart_type": "line",
            "average": 1.9,
            "trend": "excellent",
            "data_points": [
                {"date": (start_date + timedelta(days=i)).strftime("%Y-%m-%d"), "value": daily_data[i]["stress"]}
                for i in range(len(daily_data))
            ]
        },
        
        # Тренування: слабкі 3.6, багато пропусків
        warehouse_data={
            "chart_type": "bar",
            "average": 3.6,
            "trend": "weak",
            "data_points": [
                {"date": (start_date + timedelta(days=i)).strftime("%Y-%m-%d"), "value": daily_data[i]["training"]}
                for i in range(len(daily_data))
            ]
        },
        
        # Сон: ВІДМІННИЙ 8.5 годин, стабільно високий
        sleep_data={
            "chart_type": "line",
            "average": 8.5,
            "trend": "excellent",
            "total_sleep_hours": sum(d["sleep"] for d in daily_data),
            "data_points": [
                {"date": (start_date + timedelta(days=i)).strftime("%Y-%m-%d"), "value": daily_data[i]["sleep"]}
                for i in range(len(daily_data))
            ]
        },
        
        # Самопочуття: ВІДМІННЕ 8.1, стабільно високе
        wellbeing_data={
            "chart_type": "line",
            "average": 8.1,
            "trend": "excellent",
            "data_points": [
                {"date": (start_date + timedelta(days=i)).strftime("%Y-%m-%d"), "value": daily_data[i]["wellbeing"]}
                for i in range(len(daily_data))
            ]
        },
        
        # Вага: ШВИДКИЙ набір +1.8 кг (проблема при цілі схуднення)
        weight_data={
            "chart_type": "line",
            "average": round((start_weight + end_weight) / 2, 1),
            "trend": "rapid_gain",
            "start_weight": start_weight,
            "end_weight": end_weight,
            "weight_change": round(weight_change, 1),
            "data_points": [
                {"date": (start_date + timedelta(days=i)).strftime("%Y-%m-%d"), "value": daily_data[i]["weight"]}
                for i in range(len(daily_data))
            ]
        },
        
        is_complete=True,
        generated_at=datetime.now(ZoneInfo("Europe/Kyiv"))
    )
    
    await user_statistics.save()
    print(f"✅ Створено статистику для períoду {start_date.date()} - {end_date.date()}")
    
    # Виводимо підсумок
    print(f"""
📊 Сценарій 5 - Хороше відновлення але слабкі тренування:
🧘‍♂️ Середній стрес: {stress_avg:.1f} (МІНІМАЛЬНИЙ, ідеально)
💪 Складність тренувань: {training_avg:.1f} (СЛАБКІ, багато пропусків)
😴 Середній сон: {sleep_avg:.1f} годин (ВІДМІННИЙ)
😄 Загальне самопочуття: {wellbeing_avg:.1f} (ВІДМІННЕ, багато енергії)
🔥 Зміна ваги: +{weight_change:.1f} кг (ШВИДКИЙ НАБІР при цілі схуднення)
🎯 Ціль: {test_user.training_goal.value}

Очікуваний аналіз: похвала сильних сторін (сон, енергія, відсутність стресу)
+ критика слабких тренувань і швидкого набору ваги
""")

if __name__ == "__main__":
    print("Генерація тестових даних для Сценарію 5 (Хороше відновлення але слабкі тренування)...")
    asyncio.run(create_good_recovery_weak_training_scenario())
    print("✅ Сценарій 5 завершено!")