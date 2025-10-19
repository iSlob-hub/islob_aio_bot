#!/usr/bin/env python3
"""
Генерація тестових даних для сценарію 1:
Загалом стабільні показники з невеликими проблемами.
Стрес трохи зростає, сон стабільний але короткий, самопочуття слабке, вага трохи виросла.
Використовувати для спокійної збалансованої оцінки: похвала + легка критика + порада по відновленню.
"""

import asyncio
from datetime import datetime, timedelta
from app.db.database import init_db
from app.db.models import (
    User, MorningQuiz, TrainingSession, UserStatistics, 
    PeriodType, TrainingGoal
)
from zoneinfo import ZoneInfo

async def create_stable_with_minor_issues_scenario():
    """
    Сценарій 1: Стабільні показники з невеликими проблемами
    Стрес зростає (2→5), короткий сон (6.0), слабке самопочуття (4.8), легкий набір ваги (+0.8кг)
    """
    await init_db()
    
    test_user_id = "stable_minor_issues_user"
    
    # Користувач з ціллю схуднення
    test_user = User(
        telegram_id=test_user_id,
        full_name="Стабільні Показники З Проблемами",
        telegram_username="stable_minor_issues",
        is_active=True,
        is_verified=True,
        training_goal=TrainingGoal.LOSE_WEIGHT
    )
    await test_user.save()
    print(f"✅ Створено користувача: {test_user.full_name}")
    
    # Період (22 вересня 2025, 21:09)
    start_date = datetime(2025, 10, 6, 21, 9, tzinfo=ZoneInfo("Europe/Kyiv"))
    
    # Дані для стабільного тижня з невеликими проблемами (7 днів)
    daily_data = [
        # День 1 - стрес низький, все ок
        {"stress": 2, "sleep": 6.5, "wellbeing": 6, "training": 7, "weight": 73.0},
        # День 2 - стрес починає рости
        {"stress": 3, "sleep": 6.0, "wellbeing": 5, "training": 6, "weight": 73.2},
        # День 3 - стрес продовжує рости, сон коротшає
        {"stress": 4, "sleep": 5.5, "wellbeing": 5, "training": 7, "weight": 73.4},
        # День 4 - пік стресу
        {"stress": 5, "sleep": 6.0, "wellbeing": 4, "training": 6, "weight": 73.5},
        # День 5 - стрес стабілізується
        {"stress": 5, "sleep": 6.0, "wellbeing": 4, "training": 7, "weight": 73.6},
        # День 6 - самопочуття погіршується
        {"stress": 4, "sleep": 6.5, "wellbeing": 4, "training": 6, "weight": 73.7},
        # День 7 - легке покращення
        {"stress": 3, "sleep": 6.0, "wellbeing": 5, "training": 7, "weight": 73.8}
    ]
    
    training_sessions_count = 0
    morning_quizzes_count = 0
    
    # Створюємо дані по днях
    for day, data in enumerate(daily_data):
        current_date = start_date + timedelta(days=day)
        
        # Ранкові квізи з поступовим набором ваги
        morning_quiz = MorningQuiz(
            user_id=test_user_id,
            how_do_you_feel_today=data["wellbeing"],
            how_many_hours_of_sleep=data["sleep"],
            weight=data["weight"],
            is_going_to_gym=True,
            gym_attendance_time=current_date.replace(hour=18, minute=0),
            completed=True,
            created_at=current_date.replace(hour=8, minute=0)
        )
        await morning_quiz.save()
        morning_quizzes_count += 1
        
        # Стабільні тренувальні сесії
        training_session = TrainingSession(
            user_id=test_user_id,
            how_do_you_feel_before=data["wellbeing"],
            how_hard_was_training=data["training"],
            do_you_have_any_pain=False,
            training_started_at=current_date.replace(hour=18, minute=0),
            training_ended_at=current_date.replace(hour=19, minute=15),
            training_duration=75,
            stress_level=data["stress"],
            do_you_have_soreness=False,
            completed=True,
            created_at=current_date.replace(hour=18, minute=0)
        )
        await training_session.save()
        training_sessions_count += 1
    
    print(f"✅ Створено {morning_quizzes_count} ранкових квізів")
    print(f"✅ Створено {training_sessions_count} тренувальних сесій")
    
    # Створюємо статистику
    end_date = start_date + timedelta(days=6, hours=23, minutes=59, seconds=59)
    
    # Розраховуємо метрики
    stress_avg = sum(d["stress"] for d in daily_data) / len(daily_data)  # 3.7
    sleep_avg = sum(d["sleep"] for d in daily_data) / len(daily_data)    # 6.0
    wellbeing_avg = sum(d["wellbeing"] for d in daily_data) / len(daily_data)  # 4.8
    training_avg = sum(d["training"] for d in daily_data) / len(daily_data)    # 6.6
    
    start_weight = daily_data[0]["weight"]
    end_weight = daily_data[-1]["weight"]
    weight_change = end_weight - start_weight  # +0.8
    
    user_statistics = UserStatistics(
        user_id=test_user_id,
        period_type=PeriodType.WEEKLY,
        period_start=start_date,
        period_end=end_date,
        total_training_sessions=training_sessions_count,
        total_morning_quizzes=morning_quizzes_count,
        
        # Стрес: середній 3.7, зростає з 2 до 5
        stress_data={
            "chart_type": "line",
            "average": 3.7,
            "trend": "increasing",
            "data_points": [
                {"date": (start_date + timedelta(days=i)).strftime("%Y-%m-%d"), "value": daily_data[i]["stress"]}
                for i in range(len(daily_data))
            ]
        },
        
        # Тренування: стабільні 6.6
        warehouse_data={
            "chart_type": "bar",
            "average": 6.6,
            "trend": "stable",
            "data_points": [
                {"date": (start_date + timedelta(days=i)).strftime("%Y-%m-%d"), "value": daily_data[i]["training"]}
                for i in range(len(daily_data))
            ]
        },
        
        # Сон: короткий 6.0 годин, стабільний але недостатній
        sleep_data={
            "chart_type": "line",
            "average": 6.0,
            "trend": "stable",
            "total_sleep_hours": sum(d["sleep"] for d in daily_data),
            "data_points": [
                {"date": (start_date + timedelta(days=i)).strftime("%Y-%m-%d"), "value": daily_data[i]["sleep"]}
                for i in range(len(daily_data))
            ]
        },
        
        # Самопочуття: слабке 4.8, коливається між 4-6
        wellbeing_data={
            "chart_type": "line",
            "average": 4.8,
            "trend": "decreasing",
            "data_points": [
                {"date": (start_date + timedelta(days=i)).strftime("%Y-%m-%d"), "value": daily_data[i]["wellbeing"]}
                for i in range(len(daily_data))
            ]
        },
        
        # Вага: легкий набір +0.8 кг
        weight_data={
            "chart_type": "line",
            "average": round((start_weight + end_weight) / 2, 1),
            "trend": "increasing",
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
    print(f"✅ Створено статистику для періоду {start_date.date()} - {end_date.date()}")
    
    # Виводимо підсумок
    print(f"""
📊 Сценарій 1 - Стабільні показники з невеликими проблемами:
🧘‍♂️ Середній стрес: {stress_avg:.1f} (зростає з 2 до 5)
💪 Складність тренувань: {training_avg:.1f} (стабільні)
😴 Середній сон: {sleep_avg:.1f} годин (короткий але стабільний)
😄 Загальне самопочуття: {wellbeing_avg:.1f} (слабке, коливається)
🔥 Зміна ваги: +{weight_change:.1f} кг (легкий набір)
🎯 Ціль: {test_user.training_goal.value}

Очікуваний аналіз: спокійна збалансована оцінка з похвалою за стабільність
тренувань + легка критика стресу та сну + порада по відновленню
""")

if __name__ == "__main__":
    print("Генерація тестових даних для Сценарію 1 (Стабільні показники з невеликими проблемами)...")
    asyncio.run(create_stable_with_minor_issues_scenario())
    print("✅ Сценарій 1 завершено!")