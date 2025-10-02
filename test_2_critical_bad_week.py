#!/usr/bin/env python3
"""
Генерація тестових даних для сценарію 2:
Дуже поганий тиждень: високий стрес, нестабільний сон (навіть дні без сну), 
низьке самопочуття, різка втрата ваги.
Використовувати для жорсткого критичного розбору і серйозного попередження.
"""

import asyncio
from datetime import datetime, timedelta
from app.db.database import init_db
from app.db.models import (
    User, MorningQuiz, TrainingSession, UserStatistics, 
    PeriodType, TrainingGoal
)
from zoneinfo import ZoneInfo

async def create_critical_bad_week_scenario():
    """
    Сценарій 2: Критично поганий тиждень
    Високий стрес (7.5), нестабільний сон з днями без сну, низьке самопочуття (2.8), різка втрата ваги (-3.2кг)
    """
    await init_db()
    
    test_user_id = "critical_bad_week_user"
    
    # Користувач з ціллю схуднення
    test_user = User(
        telegram_id=test_user_id,
        full_name="Критично Поганий Тиждень",
        telegram_username="critical_bad_week",
        is_active=True,
        is_verified=True,
        training_goal=TrainingGoal.LOSE_WEIGHT
    )
    await test_user.save()
    print(f"✅ Створено користувача: {test_user.full_name}")
    
    # Період (22 вересня 2025, 21:16)
    start_date = datetime(2025, 9, 22, 21, 16, tzinfo=ZoneInfo("Europe/Kyiv"))
    
    # Дані для критично поганого тижня (7 днів)
    daily_data = [
        # День 1 - початок проблем
        {"stress": 6, "sleep": 4.0, "wellbeing": 4, "training": 5, "weight": 76.0},
        # День 2 - погіршення
        {"stress": 8, "sleep": 2.0, "wellbeing": 3, "training": 3, "weight": 75.2},
        # День 3 - критичний день, БЕЗ СНУ
        {"stress": 9, "sleep": 0.0, "wellbeing": 2, "training": 2, "weight": 74.5},
        # День 4 - продовження кризи
        {"stress": 8, "sleep": 1.0, "wellbeing": 2, "training": 4, "weight": 73.8},
        # День 5 - спроба відновлення не вдається
        {"stress": 7, "sleep": 3.0, "wellbeing": 3, "training": 3, "weight": 73.2},
        # День 6 - знову погано
        {"stress": 8, "sleep": 2.0, "wellbeing": 2, "training": 2, "weight": 73.0},
        # День 7 - мінімальне покращення
        {"stress": 6, "sleep": 4.0, "wellbeing": 4, "training": 4, "weight": 72.8}
    ]
    
    training_sessions_count = 0
    morning_quizzes_count = 0
    
    # Створюємо дані по днях
    for day, data in enumerate(daily_data):
        current_date = start_date + timedelta(days=day)
        
        # Ранкові квізи з різкою втратою ваги
        morning_quiz = MorningQuiz(
            user_id=test_user_id,
            how_do_you_feel_today=data["wellbeing"],
            how_many_hours_of_sleep=data["sleep"],
            weight=data["weight"],
            is_going_to_gym=data["training"] > 2,  # Не йде в зал при дуже слабких тренуваннях
            gym_attendance_time=current_date.replace(hour=18, minute=0) if data["training"] > 2 else None,
            completed=True,
            created_at=current_date.replace(hour=8, minute=0)
        )
        await morning_quiz.save()
        morning_quizzes_count += 1
        
        # Слабкі тренувальні сесії (іноді пропускає)
        if data["training"] > 2:  # Тренується тільки коли сили є
            training_session = TrainingSession(
                user_id=test_user_id,
                how_do_you_feel_before=data["wellbeing"],
                how_hard_was_training=data["training"],
                do_you_have_any_pain=True if data["stress"] > 7 else False,
                training_started_at=current_date.replace(hour=18, minute=0),
                training_ended_at=current_date.replace(hour=18, minute=30),  # Короткі тренування
                training_duration=30,  # Тільки 30 хвилин
                stress_level=data["stress"],
                do_you_have_soreness=True,
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
    stress_avg = sum(d["stress"] for d in daily_data) / len(daily_data)  # 7.4
    sleep_avg = sum(d["sleep"] for d in daily_data) / len(daily_data)    # 2.3
    wellbeing_avg = sum(d["wellbeing"] for d in daily_data) / len(daily_data)  # 2.9
    training_avg = sum(d["training"] for d in daily_data) / len(daily_data)    # 3.3
    
    start_weight = daily_data[0]["weight"]
    end_weight = daily_data[-1]["weight"]
    weight_change = end_weight - start_weight  # -3.2
    
    user_statistics = UserStatistics(
        user_id=test_user_id,
        period_type=PeriodType.WEEKLY,
        period_start=start_date,
        period_end=end_date,
        total_training_sessions=training_sessions_count,
        total_morning_quizzes=morning_quizzes_count,
        
        # Стрес: критично високий 7.4, пік до 9
        stress_data={
            "chart_type": "line",
            "average": 7.4,
            "trend": "critical",
            "data_points": [
                {"date": (start_date + timedelta(days=i)).strftime("%Y-%m-%d"), "value": daily_data[i]["stress"]}
                for i in range(len(daily_data))
            ]
        },
        
        # Тренування: слабкі 3.3, багато пропусків
        warehouse_data={
            "chart_type": "bar",
            "average": 3.3,
            "trend": "decreasing",
            "data_points": [
                {"date": (start_date + timedelta(days=i)).strftime("%Y-%m-%d"), "value": daily_data[i]["training"]}
                for i in range(len(daily_data))
            ]
        },
        
        # Сон: катастрофічно поганий 2.3 години, є день БЕЗ СНУ
        sleep_data={
            "chart_type": "line",
            "average": 2.3,
            "trend": "critical",
            "total_sleep_hours": sum(d["sleep"] for d in daily_data),
            "data_points": [
                {"date": (start_date + timedelta(days=i)).strftime("%Y-%m-%d"), "value": daily_data[i]["sleep"]}
                for i in range(len(daily_data))
            ]
        },
        
        # Самопочуття: критично низьке 2.9
        wellbeing_data={
            "chart_type": "line",
            "average": 2.9,
            "trend": "critical",
            "data_points": [
                {"date": (start_date + timedelta(days=i)).strftime("%Y-%m-%d"), "value": daily_data[i]["wellbeing"]}
                for i in range(len(daily_data))
            ]
        },
        
        # Вага: різка втрата -3.2 кг (небезпечно)
        weight_data={
            "chart_type": "line",
            "average": round((start_weight + end_weight) / 2, 1),
            "trend": "critical_decrease",
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
📊 Сценарій 2 - Критично поганий тиждень:
🧘‍♂️ Середній стрес: {stress_avg:.1f} (КРИТИЧНО ВИСОКИЙ, пік 9)
💪 Складність тренувань: {training_avg:.1f} (слабкі, багато пропусків)
😴 Середній сон: {sleep_avg:.1f} годин (КАТАСТРОФА, є день БЕЗ СНУ)
😄 Загальне самопочуття: {wellbeing_avg:.1f} (критично низьке)
🔥 Зміна ваги: {weight_change:.1f} кг (НЕБЕЗПЕЧНА втрата)
🎯 Ціль: {test_user.training_goal.value}

Очікуваний аналіз: жорсткий критичний розбір з серйозним попередженням
про здоров'я, рекомендації негайно звернутися до лікаря
""")

if __name__ == "__main__":
    print("Генерація тестових даних для Сценарію 2 (Критично поганий тиждень)...")
    asyncio.run(create_critical_bad_week_scenario())
    print("✅ Сценарій 2 завершено!")