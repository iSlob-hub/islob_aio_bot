#!/usr/bin/env python3
"""
Генерація тестових даних для сценарію 3:
Середній рівень: частковий прогрес, але є нестабільність у сні та тренуваннях, 
самопочуття падає. Вага в нормі.
Використовувати для акценту на баланс (сон, тренування, відновлення).
"""

import asyncio
from datetime import datetime, timedelta
from app.db.database import init_db
from app.db.models import (
    User, MorningQuiz, TrainingSession, UserStatistics, 
    PeriodType, TrainingGoal
)
from zoneinfo import ZoneInfo

async def create_unstable_medium_level_scenario():
    """
    Сценарій 3: Середній рівень з нестабільністю
    Частковий прогрес, нестабільний сон/тренування, падіння самопочуття, нормальна вага
    """
    await init_db()
    
    test_user_id = "unstable_medium_user"
    
    # Користувач з ціллю підтримки форми
    test_user = User(
        telegram_id=test_user_id,
        full_name="Нестабільний Середній Рівень",
        telegram_username="unstable_medium",
        is_active=True,
        is_verified=True,
        training_goal=TrainingGoal.MAINTAIN_FITNESS
    )
    await test_user.save()
    print(f"✅ Створено користувача: {test_user.full_name}")
    
    # Період (22 вересня 2025, 21:21)
    start_date = datetime(2025, 10, 6, 21, 9, tzinfo=ZoneInfo("Europe/Kyiv"))
    
    # Дані для нестабільного середнього рівня (7 днів)
    daily_data = [
        # День 1 - добрий старт
        {"stress": 4, "sleep": 8.0, "wellbeing": 7, "training": 7, "weight": 70.0},
        # День 2 - нестабільність сну
        {"stress": 5, "sleep": 5.0, "wellbeing": 6, "training": 8, "weight": 70.1},
        # День 3 - провал у тренуваннях
        {"stress": 3, "sleep": 7.5, "wellbeing": 6, "training": 3, "weight": 69.9},
        # День 4 - відновлення, але самопочуття падає
        {"stress": 4, "sleep": 6.5, "wellbeing": 5, "training": 7, "weight": 70.0},
        # День 5 - знову нестабільність
        {"stress": 6, "sleep": 4.5, "wellbeing": 4, "training": 6, "weight": 70.2},
        # День 6 - часткове покращення
        {"stress": 3, "sleep": 8.5, "wellbeing": 5, "training": 4, "weight": 69.8},
        # День 7 - коливання продовжуються
        {"stress": 5, "sleep": 6.0, "wellbeing": 4, "training": 6, "weight": 70.0}
    ]
    
    training_sessions_count = 0
    morning_quizzes_count = 0
    
    # Створюємо дані по днях
    for day, data in enumerate(daily_data):
        current_date = start_date + timedelta(days=day)
        
        # Ранкові квізи зі стабільною вагою
        morning_quiz = MorningQuiz(
            user_id=test_user_id,
            how_do_you_feel_today=data["wellbeing"],
            how_many_hours_of_sleep=data["sleep"],
            weight=data["weight"],
            is_going_to_gym=data["training"] > 3,
            gym_attendance_time=current_date.replace(hour=18, minute=0) if data["training"] > 3 else None,
            completed=True,
            created_at=current_date.replace(hour=8, minute=0)
        )
        await morning_quiz.save()
        morning_quizzes_count += 1
        
        # Нестабільні тренувальні сесії
        if data["training"] > 3:  # Пропускає слабкі дні
            training_session = TrainingSession(
                user_id=test_user_id,
                how_do_you_feel_before=data["wellbeing"],
                how_hard_was_training=data["training"],
                do_you_have_any_pain=False,
                training_started_at=current_date.replace(hour=18, minute=0),
                training_ended_at=current_date.replace(hour=19, minute=0 if data["training"] < 6 else 30),
                training_duration=60 if data["training"] < 6 else 90,
                stress_level=data["stress"],
                do_you_have_soreness=data["training"] > 7,
                completed=True,
                created_at=current_date.replace(hour=18, minute=0)
            )
            await training_session.save()
            training_sessions_count += 1
    
    print(f"✅ Створено {morning_quizzes_count} ранкових квізів")
    print(f"✅ Створено {training_sessions_count} тренувальних сесій (пропущено {7-training_sessions_count})")
    
    # Створюємо статистику
    end_date = start_date + timedelta(days=6, hours=23, minutes=59, seconds=59)
    
    # Розраховуємо метрики
    stress_avg = sum(d["stress"] for d in daily_data) / len(daily_data)  # 4.3
    sleep_avg = sum(d["sleep"] for d in daily_data) / len(daily_data)    # 6.6
    wellbeing_avg = sum(d["wellbeing"] for d in daily_data) / len(daily_data)  # 5.3
    training_avg = sum(d["training"] for d in daily_data) / len(daily_data)    # 5.9
    
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
        
        # Стрес: помірний 4.3, коливається 3-6
        stress_data={
            "chart_type": "line",
            "average": 4.3,
            "trend": "unstable",
            "data_points": [
                {"date": (start_date + timedelta(days=i)).strftime("%Y-%m-%d"), "value": daily_data[i]["stress"]}
                for i in range(len(daily_data))
            ]
        },
        
        # Тренування: нестабільні 5.9, є провал до 3
        warehouse_data={
            "chart_type": "bar",
            "average": 5.9,
            "trend": "unstable",
            "data_points": [
                {"date": (start_date + timedelta(days=i)).strftime("%Y-%m-%d"), "value": daily_data[i]["training"]}
                for i in range(len(daily_data))
            ]
        },
        
        # Сон: нестабільний 6.6 годин, коливання 4.5-8.5
        sleep_data={
            "chart_type": "line",
            "average": 6.6,
            "trend": "unstable",
            "total_sleep_hours": sum(d["sleep"] for d in daily_data),
            "data_points": [
                {"date": (start_date + timedelta(days=i)).strftime("%Y-%m-%d"), "value": daily_data[i]["sleep"]}
                for i in range(len(daily_data))
            ]
        },
        
        # Самопочуття: падає з 7 до 4, середнє 5.3
        wellbeing_data={
            "chart_type": "line",
            "average": 5.3,
            "trend": "decreasing",
            "data_points": [
                {"date": (start_date + timedelta(days=i)).strftime("%Y-%m-%d"), "value": daily_data[i]["wellbeing"]}
                for i in range(len(daily_data))
            ]
        },
        
        # Вага: стабільна в нормі ±0.2кг
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
        
        is_complete=True,
        generated_at=datetime.now(ZoneInfo("Europe/Kyiv"))
    )
    
    await user_statistics.save()
    print(f"✅ Створено статистику для періоду {start_date.date()} - {end_date.date()}")
    
    # Виводимо підсумок
    print(f"""
📊 Сценарій 3 - Нестабільний середній рівень:
🧘‍♂️ Середній стрес: {stress_avg:.1f} (помірний, коливається)
💪 Складність тренувань: {training_avg:.1f} (нестабільні, є провали)
😴 Середній сон: {sleep_avg:.1f} годин (нестабільний 4.5-8.5)
😄 Загальне самопочуття: {wellbeing_avg:.1f} (падає з 7 до 4)
🔥 Зміна ваги: {weight_change:.1f} кг (стабільна в нормі)
🎯 Ціль: {test_user.training_goal.value}

Очікуваний аналіз: акцент на нестабільність і потребу в балансі
між сном, тренуваннями та відновленням
""")

if __name__ == "__main__":
    print("Генерація тестових даних для Сценарію 3 (Нестабільний середній рівень)...")
    asyncio.run(create_unstable_medium_level_scenario())
    print("✅ Сценарій 3 завершено!")