#!/usr/bin/env python3
"""
Скрипт для витягання AI аналізів із тестових користувачів та збереження їх у текстові файли.
Для кожного тестового користувача створює окремий файл з його AI аналізом.
"""

import asyncio
import os
from datetime import datetime
from app.db.database import init_db
from app.db.models import User, UserStatistics
from zoneinfo import ZoneInfo

async def extract_ai_analyses():
    """
    Витягує AI аналізи з усіх тестових користувачів і зберігає у текстові файли
    """
    await init_db()
    
    # Список тестових користувачів
    test_user_ids = [
        "stable_minor_issues_user",
        "critical_bad_week_user", 
        "unstable_medium_user",
        "high_stress_strong_training_user",
        "good_recovery_weak_training_user",
        "missing_data_super_intensive_user",
        "real_missing_data_user",
        # Старі тестові користувачі з попередніх сценаріїв
        "scenario_1_user",
        "scenario_2_user",
        "scenario_3_user",
        "scenario_4_user",
        "scenario_5_user",
        "test_user_123"
    ]
    
    print("🔍 Початок витягання AI аналізів...")
    
    # Створюємо папку для аналізів якщо її немає
    analyses_dir = "extracted_ai_analyses"
    if not os.path.exists(analyses_dir):
        os.makedirs(analyses_dir)
        print(f"📁 Створено папку {analyses_dir}")
    
    extracted_count = 0
    empty_count = 0
    
    # Проходимо по всіх тестових користувачах
    for user_id in test_user_ids:
        try:
            # Шукаємо користувача
            user = await User.find_one(User.telegram_id == user_id)
            if not user:
                print(f"⏭️  Користувача {user_id} не знайдено")
                continue
            
            # Шукаємо статистику для цього користувача
            statistics = await UserStatistics.find(UserStatistics.user_id == user_id).to_list()
            
            if not statistics:
                print(f"⏭️  Статистики для {user_id} не знайдено")
                empty_count += 1
                continue
            
            # Беремо останню (найновішу) статистику
            latest_stat = max(statistics, key=lambda s: s.generated_at)
            
            # Перевіряємо чи є AI аналіз
            if not latest_stat.ai_analysis:
                print(f"❌ AI аналіз для {user_id} відсутній")
                empty_count += 1
                continue
            
            # Формуємо назву файлу
            filename = f"{user_id}_analysis.txt"
            filepath = os.path.join(analyses_dir, filename)
            
            # Формуємо зміст файлу
            file_content = f"""AI Аналіз для користувача: {user.full_name}
Ціль тренування: {user.training_goal.value if user.training_goal else 'не вказано'}

{latest_stat.ai_analysis}
"""
            
            # Зберігаємо у файл
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(file_content)
            
            print(f"✅ Збережено аналіз для {user.full_name} → {filename}")
            extracted_count += 1
            
        except Exception as e:
            print(f"❌ Помилка при обробці {user_id}: {e}")
    
    print(f"""
📊 Витягання завершено!

✅ Успішно витягнуто: {extracted_count} аналізів
❌ Порожні/відсутні: {empty_count} 
📁 Збережено в папці: {analyses_dir}

Файли збережено з іменами: <user_id>_analysis.txt
""")

async def extract_specific_user_analysis(user_id: str):
    """
    Витягує AI аналіз конкретного користувача
    """
    await init_db()
    
    print(f"🔍 Шукаю аналіз для користувача {user_id}...")
    
    # Шукаємо користувача
    user = await User.find_one(User.telegram_id == user_id)
    if not user:
        print(f"❌ Користувача {user_id} не знайдено")
        return
    
    # Шукаємо статистику
    statistics = await UserStatistics.find(UserStatistics.user_id == user_id).to_list()
    
    if not statistics:
        print(f"❌ Статистики для {user_id} не знайдено")
        return
    
    # Беремо останню статистику
    latest_stat = max(statistics, key=lambda s: s.generated_at)
    
    if not latest_stat.ai_analysis:
        print(f"❌ AI аналіз для {user_id} відсутній")
        return
    
    # Створюємо папку якщо її немає
    analyses_dir = "extracted_ai_analyses"
    if not os.path.exists(analyses_dir):
        os.makedirs(analyses_dir)
    
    # Зберігаємо файл
    filename = f"{user_id}_analysis.txt"
    filepath = os.path.join(analyses_dir, filename)
    
    file_content = f"""AI Аналіз для користувача: {user.full_name}
Telegram ID: {user_id}
Username: @{user.telegram_username or 'немає'}
Ціль тренування: {user.training_goal.value if user.training_goal else 'не вказано'}

Період аналізу: {latest_stat.period_type.value} 
Дати: {latest_stat.period_start.strftime('%Y-%m-%d')} - {latest_stat.period_end.strftime('%Y-%m-%d')}

{'='*50}
AI АНАЛІЗ:
{'='*50}

{latest_stat.ai_analysis}
"""
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(file_content)
    
    print(f"✅ Аналіз збережено: {filepath}")
    
    # Також виводимо в консоль
    print(f"\n{'='*50}")
    print("АНАЛІЗ:")
    print('='*50)
    print(latest_stat.ai_analysis)
    print('='*50)

async def list_users_with_analyses():
    """
    Показує список користувачів, у яких є AI аналізи
    """
    await init_db()
    
    print("🔍 Шукаю користувачів з AI аналізами...")
    
    # Шукаємо всі статистики з AI аналізом
    statistics_with_ai = await UserStatistics.find(
        UserStatistics.ai_analysis != None
    ).to_list()
    
    if not statistics_with_ai:
        print("❌ AI аналізів не знайдено")
        return
    
    # Групуємо по користувачах
    users_analyses = {}
    for stat in statistics_with_ai:
        if stat.user_id not in users_analyses:
            users_analyses[stat.user_id] = []
        users_analyses[stat.user_id].append(stat)
    
    print(f"\n📋 Знайдено {len(users_analyses)} користувачів з AI аналізами:")
    print("-" * 80)
    
    for i, (user_id, analyses) in enumerate(users_analyses.items(), 1):
        # Отримуємо дані користувача
        user = await User.find_one(User.telegram_id == user_id)
        user_name = user.full_name if user else "Невідомий користувач"
        
        # Остання статистика
        latest = max(analyses, key=lambda s: s.generated_at)
        
        print(f"{i:2d}. {user_name}")
        print(f"    ID: {user_id}")
        print(f"    Аналізів: {len(analyses)}")
        print(f"    Останній: {latest.generated_at.strftime('%Y-%m-%d %H:%M')}")
        print(f"    Період: {latest.period_start.strftime('%Y-%m-%d')} - {latest.period_end.strftime('%Y-%m-%d')}")
        print("-" * 80)

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "list":
            print("📋 Показ користувачів з AI аналізами...")
            asyncio.run(list_users_with_analyses())
            
        elif command == "user" and len(sys.argv) > 2:
            user_id = sys.argv[2]
            print(f"🔍 Витягання аналізу користувача {user_id}...")
            asyncio.run(extract_specific_user_analysis(user_id))
            
        elif command == "help":
            print("""
🔧 Використання скрипта:

python extract_ai_analyses.py           - Витягнути всі AI аналізи тестових користувачів
python extract_ai_analyses.py list      - Показати список користувачів з AI аналізами
python extract_ai_analyses.py user <id> - Витягнути аналіз конкретного користувача
python extract_ai_analyses.py help      - Показати цю довідку

Приклади:
python extract_ai_analyses.py list
python extract_ai_analyses.py user stable_minor_issues_user

Файли зберігаються в папці: extracted_ai_analyses/
""")
        else:
            print("❌ Невідома команда. Використай 'help' для довідки")
    else:
        print("🔍 Витягання AI аналізів усіх тестових користувачів...")
        asyncio.run(extract_ai_analyses())
        print("✅ Готово!")