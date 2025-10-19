#!/usr/bin/env python3
"""
Генерація тестових даних для сценарію 6:
Користувач пропустив частину даних (стрес, самопочуття), тренування суперінтенсивні, 
сон недостатній, вага стабільна.
Використовувати для жартівливої критики пропусків у даних і порад по відновленню.
"""

import asyncio
from datetime import datetime, timedelta
from app.db.database import init_db
from app.db.models import (
    User, MorningQuiz, TrainingSession, UserStatistics, 
    PeriodType, TrainingGoal
)
from zoneinfo import ZoneInfo

async def create_missing_data_super_intensive_scenario():
    """
    Сценарій 6: Пропущені дані з суперінтенсивними тренуваннями
    Пропуски в стресі/самопочутті, суперінтенсивні тренування, недостатній сон, стабільна вага
    """
    await init_db()
    
    test_user_id = "missing_data_super_intensive_user"
    
    # Користувач з ціллю набору м'язової маси
    test_user = User(
        telegram_id=test_user_id,
        full_name="Пропущені Дані Суперінтенсив",
        telegram_username="missing_data_super_intensive",
        is_active=True,
        is_verified=True,
        training_goal=TrainingGoal.BUILD_MUSCLE
    )
    await test_user.save()
    print(f"✅ Створено користувача: {test_user.full_name}")
    
    # Період (22 вересня 2025, 21:44)
    start_date = datetime(2025, 10, 6, 21, 9, tzinfo=ZoneInfo("Europe/Kyiv"))
    
    # Дані з пропусками та суперінтенсивними тренуваннями (7 днів)
    daily_data = [
        # День 1 - початок, є всі дані
        {"stress": 4, "sleep": 5.5, "wellbeing": 6, "training": 10, "weight": 80.0, "has_stress": True, "has_wellbeing": True},
        # День 2 - пропустив стрес
        {"stress": None, "sleep": 6.0, "wellbeing": 5, "training": 9, "weight": 80.1, "has_stress": False, "has_wellbeing": True},
        # День 3 - пропустив самопочуття
        {"stress": 6, "sleep": 5.0, "wellbeing": None, "training": 10, "weight": 79.9, "has_stress": True, "has_wellbeing": False},
        # День 4 - пропустив обидва
        {"stress": None, "sleep": 6.5, "wellbeing": None, "training": 9, "weight": 80.0, "has_stress": False, "has_wellbeing": False},
        # День 5 - знову пропуски
        {"stress": None, "sleep": 5.5, "wellbeing": 4, "training": 10, "weight": 80.2, "has_stress": False, "has_wellbeing": True},
        # День 6 - пропустив самопочуття
        {"stress": 7, "sleep": 5.0, "wellbeing": None, "training": 9, "weight": 79.8, "has_stress": True, "has_wellbeing": False},
        # День 7 - нарешті заповнив всі дані
        {"stress": 5, "sleep": 6.0, "wellbeing": 3, "training": 10, "weight": 80.0, "has_stress": True, "has_wellbeing": True}
    ]
    
    training_sessions_count = 0
    morning_quizzes_count = 0
    
    # Створюємо дані по днях з пропусками
    for day, data in enumerate(daily_data):
        current_date = start_date + timedelta(days=day)
        
        # Ранкові квізи - завжди є вага і сон
        morning_quiz = MorningQuiz(
            user_id=test_user_id,
            how_do_you_feel_today=data["wellbeing"] if data["has_wellbeing"] else 5,  # Дефолт якщо пропущено
            how_many_hours_of_sleep=data["sleep"],
            weight=data["weight"],
            is_going_to_gym=True,  # Завжди йде тренуватися
            gym_attendance_time=current_date.replace(hour=20, minute=0),
            completed=True,
            created_at=current_date.replace(hour=8, minute=0)
        )
        await morning_quiz.save()
        morning_quizzes_count += 1
        
        # Суперінтенсивні тренувальні сесії - але пропускає дані
        training_session = TrainingSession(
            user_id=test_user_id,
            how_do_you_feel_before=data["wellbeing"] if data["has_wellbeing"] else 5,
            how_hard_was_training=data["training"],
            do_you_have_any_pain=True if data["training"] >= 10 else False,
            training_started_at=current_date.replace(hour=20, minute=0),
            training_ended_at=current_date.replace(hour=22, minute=0),  # 2 години!
            training_duration=120,  # Дуже довгі тренування
            stress_level=data["stress"] if data["has_stress"] else 5,  # Дефолт якщо пропущено
            do_you_have_soreness=True,  # Завжди болить від такої інтенсивності
            completed=True,
            created_at=current_date.replace(hour=20, minute=0)
        )
        await training_session.save()
        training_sessions_count += 1
    
    print(f"✅ Створено {morning_quizzes_count} ранкових квізів")
    print(f"✅ Створено {training_sessions_count} тренувальних сесій")
    
    # Створюємо статистику
    end_date = start_date + timedelta(days=6, hours=23, minutes=59, seconds=59)
    
    # Розраховуємо метрики тільки по наявним даним
    stress_values = [d["stress"] for d in daily_data if d["has_stress"] and d["stress"] is not None]
    wellbeing_values = [d["wellbeing"] for d in daily_data if d["has_wellbeing"] and d["wellbeing"] is not None]
    
    stress_avg = sum(stress_values) / len(stress_values) if stress_values else 5.0  # 5.5
    sleep_avg = sum(d["sleep"] for d in daily_data) / len(daily_data)    # 5.7
    wellbeing_avg = sum(wellbeing_values) / len(wellbeing_values) if wellbeing_values else 5.0  # 4.5
    training_avg = sum(d["training"] for d in daily_data) / len(daily_data)    # 9.6
    
    start_weight = daily_data[0]["weight"]
    end_weight = daily_data[-1]["weight"]
    weight_change = end_weight - start_weight  # 0.0
    
    user_statistics = UserStatistics(
        user_id=test_user_id,
        period_type=PeriodType.WEEKLY,
        period_start=start_date,
        period_end=end_date,
        total_training_sessions=training_sessions_count,
        total_morning_quizzes=morning_quizzes_count,
        
        # Стрес: середній 5.5, але БАГАТО ПРОПУСКІВ
        stress_data={
            "chart_type": "line",
            "average": stress_avg,
            "trend": "incomplete_data",
            "missing_days": len([d for d in daily_data if not d["has_stress"]]),
            "data_points": [
                {"date": (start_date + timedelta(days=i)).strftime("%Y-%m-%d"), 
                 "value": daily_data[i]["stress"] if daily_data[i]["has_stress"] else None}
                for i in range(len(daily_data))
            ]
        },
        
        # Тренування: СУПЕРІНТЕНСИВНІ 9.6, пік до 10
        warehouse_data={
            "chart_type": "bar",
            "average": 9.6,
            "trend": "super_intensive",
            "data_points": [
                {"date": (start_date + timedelta(days=i)).strftime("%Y-%m-%d"), "value": daily_data[i]["training"]}
                for i in range(len(daily_data))
            ]
        },
        
        # Сон: недостатній 5.7 годин при такій інтенсивності
        sleep_data={
            "chart_type": "line",
            "average": 5.7,
            "trend": "insufficient_for_intensity",
            "total_sleep_hours": sum(d["sleep"] for d in daily_data),
            "data_points": [
                {"date": (start_date + timedelta(days=i)).strftime("%Y-%m-%d"), "value": daily_data[i]["sleep"]}
                for i in range(len(daily_data))
            ]
        },
        
        # Самопочуття: 4.5, але БАГАТО ПРОПУСКІВ
        wellbeing_data={
            "chart_type": "line",
            "average": wellbeing_avg,
            "trend": "incomplete_data",
            "missing_days": len([d for d in daily_data if not d["has_wellbeing"]]),
            "data_points": [
                {"date": (start_date + timedelta(days=i)).strftime("%Y-%m-%d"), 
                 "value": daily_data[i]["wellbeing"] if daily_data[i]["has_wellbeing"] else None}
                for i in range(len(daily_data))
            ]
        },
        
        # Вага: стабільна ±0.4кг
        weight_data={
            "chart_type": "line",
            "average": round((start_weight + end_weight) / 2, 1),
            "trend": "stable",
            "start_weight": start_weight,
            "end_weight": end_weight,
            "weight_change": round(weight_change, 1),
            "data_points": [
                {"date": (start_date + timedelta(days=i)).strftime("%Y-%m-%d"), "value": daily_data[i]["weight"]}
                for i in range(len(daily_data))
            ]
        },
        
        is_complete=False,  # Не завершено через пропуски
        generated_at=datetime.now(ZoneInfo("Europe/Kyiv"))
    )
    
    await user_statistics.save()
    print(f"✅ Створено статистику для періoду {start_date.date()} - {end_date.date()}")
    
    # Виводимо підсумок
    stress_missing = len([d for d in daily_data if not d["has_stress"]])
    wellbeing_missing = len([d for d in daily_data if not d["has_wellbeing"]])
    
    print(f"""
📊 Сценарій 6 - Пропущені дані з суперінтенсивними тренуваннями:
🧘‍♂️ Середній стрес: {stress_avg:.1f} (ПРОПУЩЕНО {stress_missing} днів з 7!)
💪 Складність тренувань: {training_avg:.1f} (СУПЕРІНТЕНСИВНІ, пік 10)
😴 Середній сон: {sleep_avg:.1f} годин (НЕДОСТАТНЬО при такій інтенсивності)
😄 Загальне самопочуття: {wellbeing_avg:.1f} (ПРОПУЩЕНО {wellbeing_missing} днів з 7!)
🔥 Зміна ваги: {weight_change:.1f} кг (стабільна)
🎯 Ціль: {test_user.training_goal.value}

Очікуваний аналіз: жартівлива критика пропусків у даних 
+ застереження про недостатній сон при суперінтенсивних тренуваннях
""")

if __name__ == "__main__":
    print("Генерація тестових даних для Сценарію 6 (Пропущені дані з суперінтенсивними тренуваннями)...")
    asyncio.run(create_missing_data_super_intensive_scenario())
    print("✅ Сценарій 6 завершено!")