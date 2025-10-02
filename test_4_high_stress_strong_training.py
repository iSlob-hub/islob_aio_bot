#!/usr/bin/env python3
"""
Генерація тестових даних для сценарію 4:
Стрес високий, тренування стабільні та сильні, сон майже нормальний (окрім провалу), 
самопочуття хороше але падає, вага стабільна.
Використовувати коли є сильний прогрес у тренуваннях, але фонові проблеми можуть звести нанівець результат.
"""

import asyncio
from datetime import datetime, timedelta
from app.db.database import init_db
from app.db.models import (
    User, MorningQuiz, TrainingSession, UserStatistics, 
    PeriodType, TrainingGoal
)
from zoneinfo import ZoneInfo

async def create_high_stress_strong_training_scenario():
    """
    Сценарій 4: Високий стрес але сильні тренування
    Високий стрес, стабільні сильні тренування, майже нормальний сон з провалом, падіння самопочуття, стабільна вага
    """
    await init_db()
    
    test_user_id = "high_stress_strong_training_user"
    
    # Користувач з ціллю набору м'язової маси
    test_user = User(
        telegram_id=test_user_id,
        full_name="Високий Стрес Сильні Тренування",
        telegram_username="high_stress_strong_training",
        is_active=True,
        is_verified=True,
        training_goal=TrainingGoal.BUILD_MUSCLE
    )
    await test_user.save()
    print(f"✅ Створено користувача: {test_user.full_name}")
    
    # Період (22 вересня 2025, 21:23)
    start_date = datetime(2025, 9, 22, 21, 23, tzinfo=ZoneInfo("Europe/Kyiv"))
    
    # Дані для високого стресу з сильними тренуваннями (7 днів)
    daily_data = [
        # День 1 - добрий старт але стрес
        {"stress": 6, "sleep": 7.5, "wellbeing": 7, "training": 8, "weight": 77.0},
        # День 2 - стрес зростає, тренування сильні
        {"stress": 7, "sleep": 7.0, "wellbeing": 7, "training": 8, "weight": 77.1},
        # День 3 - ПРОВАЛ У СНІ, але тренування на рівні
        {"stress": 8, "sleep": 4.0, "wellbeing": 5, "training": 8, "weight": 76.9},
        # День 4 - стрес стабільно високий
        {"stress": 7, "sleep": 7.5, "wellbeing": 6, "training": 9, "weight": 77.0},
        # День 5 - самопочуття падає
        {"stress": 8, "sleep": 7.0, "wellbeing": 5, "training": 8, "weight": 77.1},
        # День 6 - продовження стресу
        {"stress": 7, "sleep": 6.5, "wellbeing": 4, "training": 8, "weight": 76.8},
        # День 7 - пік тренувань але самопочуття низьке
        {"stress": 8, "sleep": 7.0, "wellbeing": 4, "training": 9, "weight": 77.0}
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
            is_going_to_gym=True,  # Завжди йде тренуватися
            gym_attendance_time=current_date.replace(hour=19, minute=0),
            completed=True,
            created_at=current_date.replace(hour=8, minute=0)
        )
        await morning_quiz.save()
        morning_quizzes_count += 1
        
        # Стабільно сильні тренувальні сесії
        training_session = TrainingSession(
            user_id=test_user_id,
            how_do_you_feel_before=max(data["wellbeing"], 5),  # Енергія для тренування
            how_hard_was_training=data["training"],
            do_you_have_any_pain=False,
            training_started_at=current_date.replace(hour=19, minute=0),
            training_ended_at=current_date.replace(hour=20, minute=30),  # Довгі тренування
            training_duration=90,
            stress_level=data["stress"],
            do_you_have_soreness=True if data["training"] >= 8 else False,
            completed=True,
            created_at=current_date.replace(hour=19, minute=0)
        )
        await training_session.save()
        training_sessions_count += 1
    
    print(f"✅ Створено {morning_quizzes_count} ранкових квізів")
    print(f"✅ Створено {training_sessions_count} тренувальних сесій")
    
    # Створюємо статистику
    end_date = start_date + timedelta(days=6, hours=23, minutes=59, seconds=59)
    
    # Розраховуємо метрики
    stress_avg = sum(d["stress"] for d in daily_data) / len(daily_data)  # 7.3
    sleep_avg = sum(d["sleep"] for d in daily_data) / len(daily_data)    # 6.7
    wellbeing_avg = sum(d["wellbeing"] for d in daily_data) / len(daily_data)  # 5.4
    training_avg = sum(d["training"] for d in daily_data) / len(daily_data)    # 8.3
    
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
        
        # Стрес: високий 7.3, стабільно 6-8
        stress_data={
            "chart_type": "line",
            "average": 7.3,
            "trend": "high_stable",
            "data_points": [
                {"date": (start_date + timedelta(days=i)).strftime("%Y-%m-%d"), "value": daily_data[i]["stress"]}
                for i in range(len(daily_data))
            ]
        },
        
        # Тренування: стабільно сильні 8.3, пік до 9
        warehouse_data={
            "chart_type": "bar",
            "average": 8.3,
            "trend": "stable_high",
            "data_points": [
                {"date": (start_date + timedelta(days=i)).strftime("%Y-%m-%d"), "value": daily_data[i]["training"]}
                for i in range(len(daily_data))
            ]
        },
        
        # Сон: майже нормальний 6.7 годин, але є провал до 4
        sleep_data={
            "chart_type": "line",
            "average": 6.7,
            "trend": "almost_normal_with_dip",
            "total_sleep_hours": sum(d["sleep"] for d in daily_data),
            "data_points": [
                {"date": (start_date + timedelta(days=i)).strftime("%Y-%m-%d"), "value": daily_data[i]["sleep"]}
                for i in range(len(daily_data))
            ]
        },
        
        # Самопочуття: падає з 7 до 4, середнє 5.4
        wellbeing_data={
            "chart_type": "line",
            "average": 5.4,
            "trend": "decreasing",
            "data_points": [
                {"date": (start_date + timedelta(days=i)).strftime("%Y-%m-%d"), "value": daily_data[i]["wellbeing"]}
                for i in range(len(daily_data))
            ]
        },
        
        # Вага: стабільна ±0.3кг
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
📊 Сценарій 4 - Високий стрес але сильні тренування:
🧘‍♂️ Середній стрес: {stress_avg:.1f} (ВИСОКИЙ, стабільно 6-8)
💪 Складність тренувань: {training_avg:.1f} (СТАБІЛЬНО СИЛЬНІ, пік 9)
😴 Середній сон: {sleep_avg:.1f} годин (майже норма, але є провал до 4)
😄 Загальне самопочуття: {wellbeing_avg:.1f} (ПАДАЄ з 7 до 4)
🔥 Зміна ваги: {weight_change:.1f} кг (стабільна)
🎯 Ціль: {test_user.training_goal.value}

Очікуваний аналіз: сильний прогрес у тренуваннях, але фонові проблеми
(стрес, падіння самопочуття) можуть звести нанівець результат
""")

if __name__ == "__main__":
    print("Генерація тестових даних для Сценарію 4 (Високий стрес але сильні тренування)...")
    asyncio.run(create_high_stress_strong_training_scenario())
    print("✅ Сценарій 4 завершено!")