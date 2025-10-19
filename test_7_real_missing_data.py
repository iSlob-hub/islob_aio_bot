#!/usr/bin/env python3
"""
Генерація тестових даних для сценарію 7:
Користувач пропускає заповнення даних по кілька днів підряд.
Використовувати для жартівливої критики за ліноту у веденні щоденника.
"""

import asyncio
from datetime import datetime, timedelta
from app.db.database import init_db
from app.db.models import (
    User, MorningQuiz, TrainingSession, UserStatistics, 
    PeriodType, TrainingGoal
)
from zoneinfo import ZoneInfo

async def create_real_missing_data_scenario():
    """
    Сценарій 7: Справжні пропущені дані
    Користувач просто не заповнює дані по кілька днів - ні квізів, ні тренувань
    """
    await init_db()
    
    test_user_id = "real_missing_data_user"
    
    # Користувач з ціллю схуднення
    test_user = User(
        telegram_id=test_user_id,
        full_name="Лінивий Користувач З Пропусками",
        telegram_username="real_missing_data",
        is_active=True,
        is_verified=True,
        training_goal=TrainingGoal.LOSE_WEIGHT
    )
    await test_user.save()
    print(f"✅ Створено користувача: {test_user.full_name}")
    
    # Період (23 вересня 2025, 10:00)
    start_date = datetime(2025, 10, 6, 10, 0, tzinfo=ZoneInfo("Europe/Kyiv"))
    
    # План на 7 днів - деякі дні взагалі пропущені
    daily_plan = [
        # День 1 - заповнив все
        {"has_data": True, "stress": 3, "sleep": 7.0, "wellbeing": 6, "training": 6, "weight": 74.0},
        # День 2 - заповнив все
        {"has_data": True, "stress": 4, "sleep": 6.5, "wellbeing": 5, "training": 7, "weight": 73.8},
        # День 3 - ПРОПУСТИВ ПОВНІСТЮ (зайнятий/забув)
        {"has_data": False},
        # День 4 - ПРОПУСТИВ ПОВНІСТЮ 
        {"has_data": False},
        # День 5 - згадав про бот, заповнив
        {"has_data": True, "stress": 6, "sleep": 5.5, "wellbeing": 4, "training": 5, "weight": 74.2},
        # День 6 - ЗНОВУ ПРОПУСТИВ
        {"has_data": False},
        # День 7 - спохватився в кінці тижня
        {"has_data": True, "stress": 5, "sleep": 6.0, "wellbeing": 5, "training": 6, "weight": 74.0}
    ]
    
    training_sessions_count = 0
    morning_quizzes_count = 0
    
    # Створюємо дані тільки для днів коли користувач не забув
    for day, data in enumerate(daily_plan):
        current_date = start_date + timedelta(days=day)
        
        if not data["has_data"]:
            print(f"❌ День {day + 1} ({current_date.date()}) - дані пропущені")
            continue
        
        # Ранкові квізи тільки коли є дані
        morning_quiz = MorningQuiz(
            user_id=test_user_id,
            how_do_you_feel_today=data["wellbeing"],
            how_many_hours_of_sleep=data["sleep"],
            weight=data["weight"],
            is_going_to_gym=True,
            gym_attendance_time=current_date.replace(hour=19, minute=0),
            completed=True,
            created_at=current_date.replace(hour=8, minute=30)
        )
        await morning_quiz.save()
        morning_quizzes_count += 1
        
        # Тренувальні сесії тільки коли є дані
        training_session = TrainingSession(
            user_id=test_user_id,
            how_do_you_feel_before=data["wellbeing"],
            how_hard_was_training=data["training"],
            do_you_have_any_pain=False,
            training_started_at=current_date.replace(hour=19, minute=0),
            training_ended_at=current_date.replace(hour=20, minute=15),
            training_duration=75,
            stress_level=data["stress"],
            do_you_have_soreness=False,
            completed=True,
            created_at=current_date.replace(hour=19, minute=0)
        )
        await training_session.save()
        training_sessions_count += 1
        
        print(f"✅ День {day + 1} ({current_date.date()}) - дані заповнені")
    
    print(f"✅ Створено {morning_quizzes_count} ранкових квізів з 7 можливих")
    print(f"✅ Створено {training_sessions_count} тренувальних сесій з 7 можливих")
    
    # Створюємо статистику
    end_date = start_date + timedelta(days=6, hours=23, minutes=59, seconds=59)
    
    # Розраховуємо метрики тільки по наявним даним
    available_data = [d for d in daily_plan if d["has_data"]]
    missing_days = len([d for d in daily_plan if not d["has_data"]])
    
    if not available_data:
        print("❌ Немає даних для створення статистики!")
        return
    
    stress_avg = sum(d["stress"] for d in available_data) / len(available_data)  # 4.5
    sleep_avg = sum(d["sleep"] for d in available_data) / len(available_data)    # 6.25
    wellbeing_avg = sum(d["wellbeing"] for d in available_data) / len(available_data)  # 5.0
    training_avg = sum(d["training"] for d in available_data) / len(available_data)    # 6.0
    
    start_weight = available_data[0]["weight"]
    end_weight = available_data[-1]["weight"]
    weight_change = end_weight - start_weight  # 0.0
    
    user_statistics = UserStatistics(
        user_id=test_user_id,
        period_type=PeriodType.WEEKLY,
        period_start=start_date,
        period_end=end_date,
        total_training_sessions=training_sessions_count,
        total_morning_quizzes=morning_quizzes_count,
        
        # Стрес: середній за наявними даними
        stress_data={
            "chart_type": "line",
            "average": stress_avg,
            "trend": "incomplete_week",
            "missing_days": missing_days,
            "data_points": [
                {"date": (start_date + timedelta(days=i)).strftime("%Y-%m-%d"), 
                 "value": daily_plan[i]["stress"] if daily_plan[i]["has_data"] else None}
                for i in range(len(daily_plan))
            ]
        },
        
        # Тренування: середнє за наявними даними
        warehouse_data={
            "chart_type": "bar",
            "average": training_avg,
            "trend": "incomplete_week",
            "missing_days": missing_days,
            "data_points": [
                {"date": (start_date + timedelta(days=i)).strftime("%Y-%m-%d"), 
                 "value": daily_plan[i]["training"] if daily_plan[i]["has_data"] else None}
                for i in range(len(daily_plan))
            ]
        },
        
        # Сон: середній за наявними даними
        sleep_data={
            "chart_type": "line",
            "average": sleep_avg,
            "trend": "incomplete_week",
            "missing_days": missing_days,
            "total_sleep_hours": sum(d["sleep"] for d in available_data),
            "data_points": [
                {"date": (start_date + timedelta(days=i)).strftime("%Y-%m-%d"), 
                 "value": daily_plan[i]["sleep"] if daily_plan[i]["has_data"] else None}
                for i in range(len(daily_plan))
            ]
        },
        
        # Самопочуття: середнє за наявними даними
        wellbeing_data={
            "chart_type": "line",
            "average": wellbeing_avg,
            "trend": "incomplete_week",
            "missing_days": missing_days,
            "data_points": [
                {"date": (start_date + timedelta(days=i)).strftime("%Y-%m-%d"), 
                 "value": daily_plan[i]["wellbeing"] if daily_plan[i]["has_data"] else None}
                for i in range(len(daily_plan))
            ]
        },
        
        # Вага: тільки дні коли є дані
        weight_data={
            "chart_type": "line",
            "average": round((start_weight + end_weight) / 2, 1),
            "trend": "incomplete_data",
            "start_weight": start_weight,
            "end_weight": end_weight,
            "weight_change": round(weight_change, 1),
            "missing_days": missing_days,
            "data_points": [
                {"date": (start_date + timedelta(days=i)).strftime("%Y-%m-%d"), 
                 "value": daily_plan[i]["weight"] if daily_plan[i]["has_data"] else None}
                for i in range(len(daily_plan))
            ]
        },
        
        is_complete=False,  # НЕ завершено через пропуски
        generated_at=datetime.now(ZoneInfo("Europe/Kyiv"))
    )
    
    await user_statistics.save()
    print(f"✅ Створено статистику для періоду {start_date.date()} - {end_date.date()}")
    
    # Виводимо підсумок
    print(f"""
📊 Сценарій 7 - Справжні пропущені дані:
🧘‍♂️ Середній стрес: {stress_avg:.1f} (тільки {len(available_data)} днів з 7!)
💪 Складність тренувань: {training_avg:.1f} (пропущено {missing_days} тренувань!)
😴 Середній сон: {sleep_avg:.1f} годин (неповні дані)
😄 Загальне самопочуття: {wellbeing_avg:.1f} (фрагментарно)
🔥 Зміна ваги: {weight_change:.1f} кг (неможливо точно оцінити)
🎯 Ціль: {test_user.training_goal.value}
❌ ПРОПУЩЕНО ДНІВ: {missing_days} з 7 ({missing_days/7*100:.0f}%)

Очікуваний аналіз: жартівлива критика за ліноту у веденні щоденника
+ нагадування про важливість регулярності даних для аналізу
""")

if __name__ == "__main__":
    print("Генерація тестових даних для Сценарію 7 (Справжні пропущені дані)...")
    asyncio.run(create_real_missing_data_scenario())
    print("✅ Сценарій 7 завершено!")