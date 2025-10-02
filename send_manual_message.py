import asyncio
import sys
import os
from aiogram import Bot
from app.config import settings
from app.db.database import init_db
from app.db.models import User
from dotenv import load_dotenv

load_dotenv()

def read_message_from_file(file_path: str) -> str:
    """
    Читає текст повідомлення з файлу
    
    Args:
        file_path: Шлях до файлу з текстом повідомлення
        
    Returns:
        Текст повідомлення або помилку
    """
    try:
        if not os.path.exists(file_path):
            return f"❌ Файл {file_path} не знайдено"
        
        with open(file_path, 'r', encoding='utf-8') as f:
            message = f.read().strip()
        
        if not message:
            return f"❌ Файл {file_path} порожній"
        
        print(f"📄 Завантажено повідомлення з файлу {file_path} ({len(message)} символів)")
        return message
        
    except Exception as e:
        return f"❌ Помилка читання файлу {file_path}: {e}"

async def send_message_to_user(user_id: str, message: str, parse_mode: str = "HTML"):
    """
    Відправляє повідомлення конкретному користувачу
    
    Args:
        user_id: Telegram ID користувача
        message: Текст повідомлення
        parse_mode: Режим парсингу (HTML, Markdown, None)
    """
    bot = Bot(token=os.environ.get("BOT_TOKEN"))
    
    try:
        await bot.send_message(
            chat_id=user_id,
            text=message,
            parse_mode=parse_mode
        )
        print(f"✅ Повідомлення успішно надіслано користувачу {user_id}")
        return True
    except Exception as e:
        print(f"❌ Помилка відправки повідомлення користувачу {user_id}: {e}")
        return False
    finally:
        await bot.session.close()

async def send_message_by_username(username: str, message: str, parse_mode: str = "HTML"):
    """
    Відправляє повідомлення користувачу за username
    
    Args:
        username: Username користувача (без @)
        message: Текст повідомлення
        parse_mode: Режим парсингу
    """
    await init_db()
    
    # Шукаємо користувача за username
    user = await User.find_one(User.telegram_username == username)
    
    if not user:
        print(f"❌ Користувача з username '{username}' не знайдено в базі даних")
        return False
    
    print(f"👤 Знайдено користувача: {user.full_name} (@{user.telegram_username}) - ID: {user.telegram_id}")
    
    return await send_message_to_user(user.telegram_id, message, parse_mode)

async def list_users(limit: int = 20, active_only: bool = False):
    """
    Показує список користувачів
    
    Args:
        limit: Максимальна кількість користувачів для показу
        active_only: Показувати тільки активних користувачів
    """
    await init_db()
    
    print(f"📋 Завантаження користувачів (ліміт: {limit}, тільки активні: {active_only})...")
    
    query = User.find()
    if active_only:
        query = query.find(User.is_active == True)
    
    users = await query.limit(limit).to_list()
    
    if not users:
        print("❌ Користувачів не знайдено")
        return
    
    print(f"\n👥 Знайдено {len(users)} користувачів:")
    print("-" * 80)
    
    for i, user in enumerate(users, 1):
        status = "🟢 Активний" if user.is_active else "🔴 Неактивний"
        verified = "✅ Підтверджений" if user.is_verified else "❌ Не підтверджений"
        username = f"@{user.telegram_username}" if user.telegram_username else "Немає username"
        
        print(f"{i:2d}. {user.full_name}")
        print(f"    ID: {user.telegram_id}")
        print(f"    Username: {username}")
        print(f"    Статус: {status} | {verified}")
        print("-" * 80)

async def send_broadcast_message(message: str, active_only: bool = True, parse_mode: str = "HTML"):
    """
    Відправляє повідомлення всім користувачам (розсилка)
    
    Args:
        message: Текст повідомлення
        active_only: Надсилати тільки активним користувачам
        parse_mode: Режим парсингу
    """
    await init_db()
    
    print(f"📢 Підготовка розсилки (тільки активні: {active_only})...")
    
    query = User.find()
    if active_only:
        query = query.find(User.is_active == True)
    
    users = await query.to_list()
    
    if not users:
        print("❌ Користувачів для розсилки не знайдено")
        return
    
    print(f"👥 Знайдено {len(users)} користувачів для розсилки")
    
    # Підтвердження
    confirm = input(f"⚠️ Ви дійсно хочете надіслати повідомлення {len(users)} користувачам? (yes/no): ")
    if confirm.lower() not in ['yes', 'y', 'так', 'т']:
        print("❌ Розсилку скасовано")
        return
    
    bot = Bot(token=os.environ.get("BOT_TOKEN"))
    
    success_count = 0
    failed_count = 0
    
    print("📤 Починаю розсилку...")
    
    for i, user in enumerate(users, 1):
        try:
            await bot.send_message(
                chat_id=user.telegram_id,
                text=message,
                parse_mode=parse_mode
            )
            success_count += 1
            print(f"✅ {i}/{len(users)} - {user.full_name} ({user.telegram_id})")
            
            # Невелика затримка між повідомленнями щоб не спамити
            await asyncio.sleep(0.1)
            
        except Exception as e:
            failed_count += 1
            print(f"❌ {i}/{len(users)} - {user.full_name} ({user.telegram_id}): {e}")
    
    await bot.session.close()
    
    print(f"""
📊 Розсилку завершено!
✅ Успішно: {success_count}
❌ Помилок: {failed_count}
📈 Всього: {len(users)}
""")

def print_help():
    """Показує довідку по використанню скрипта"""
    print("""
📧 Скрипт для ручної відправки повідомлень

🔧 Використання:

1. Надіслати повідомлення за Telegram ID:
   python send_manual_message.py send <telegram_id> "<message>"
   python send_manual_message.py send_file <telegram_id> <file_path>
   
2. Надіслати повідомлення за username:
   python send_manual_message.py send_by_username <username> "<message>"
   python send_manual_message.py send_file_by_username <username> <file_path>
   
3. Показати список користувачів:
   python send_manual_message.py list [limit] [active_only]
   
4. Розсилка всім користувачам:
   python send_manual_message.py broadcast "<message>" [active_only]
   python send_manual_message.py broadcast_file <file_path> [active_only]

📝 Приклади:

python send_manual_message.py send 123456789 "Привіт! Це тестове повідомлення"
python send_manual_message.py send_file 123456789 test_message.txt
python send_manual_message.py send_by_username johndoe "Привіт, Джон!"
python send_manual_message.py send_file_by_username johndoe test_message.txt
python send_manual_message.py list 10 true
python send_manual_message.py broadcast "Важливе оновлення для всіх!" true
python send_manual_message.py broadcast_file test_message.txt true

💡 Підказки:
- Повідомлення підтримують HTML форматування
- Для розсилки буде запит на підтвердження
- active_only: true/false (за замовчуванням true для розсилки)
- Файли мають бути в UTF-8 кодуванні
""")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print_help()
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "send":
        if len(sys.argv) < 4:
            print("❌ Недостатньо аргументів для команди send")
            print("Використання: python send_manual_message.py send <telegram_id> \"<message>\"")
            sys.exit(1)
        
        user_id = sys.argv[2]
        message = sys.argv[3]
        
        print(f"📤 Відправка повідомлення користувачу {user_id}...")
        asyncio.run(send_message_to_user(user_id, message))
    
    elif command == "send_file":
        if len(sys.argv) < 4:
            print("❌ Недостатньо аргументів для команди send_file")
            print("Використання: python send_manual_message.py send_file <telegram_id> <file_path>")
            sys.exit(1)
        
        user_id = sys.argv[2]
        file_path = sys.argv[3]
        
        message = read_message_from_file(file_path)
        if message.startswith("❌"):
            print(message)
            sys.exit(1)
        
        print(f"📤 Відправка повідомлення з файлу користувачу {user_id}...")
        asyncio.run(send_message_to_user(user_id, message))
    
    elif command == "send_by_username":
        if len(sys.argv) < 4:
            print("❌ Недостатньо аргументів для команди send_by_username")
            print("Використання: python send_manual_message.py send_by_username <username> \"<message>\"")
            sys.exit(1)
        
        username = sys.argv[2].replace("@", "")  # Видаляємо @ якщо є
        message = sys.argv[3]
        
        print(f"📤 Відправка повідомлення користувачу @{username}...")
        asyncio.run(send_message_by_username(username, message))
    
    elif command == "send_file_by_username":
        if len(sys.argv) < 4:
            print("❌ Недостатньо аргументів для команди send_file_by_username")
            print("Використання: python send_manual_message.py send_file_by_username <username> <file_path>")
            sys.exit(1)
        
        username = sys.argv[2].replace("@", "")  # Видаляємо @ якщо є
        file_path = sys.argv[3]
        
        message = read_message_from_file(file_path)
        if message.startswith("❌"):
            print(message)
            sys.exit(1)
        
        print(f"📤 Відправка повідомлення з файлу користувачу @{username}...")
        asyncio.run(send_message_by_username(username, message))
    
    elif command == "list":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 20
        active_only = sys.argv[3].lower() in ['true', '1', 'yes'] if len(sys.argv) > 3 else False
        
        asyncio.run(list_users(limit, active_only))
    
    elif command == "broadcast":
        if len(sys.argv) < 3:
            print("❌ Недостатньо аргументів для команди broadcast")
            print("Використання: python send_manual_message.py broadcast \"<message>\" [active_only]")
            sys.exit(1)
        
        message = sys.argv[2]
        active_only = sys.argv[3].lower() in ['true', '1', 'yes'] if len(sys.argv) > 3 else True
        
        asyncio.run(send_broadcast_message(message, active_only))
    
    elif command == "broadcast_file":
        if len(sys.argv) < 3:
            print("❌ Недостатньо аргументів для команди broadcast_file")
            print("Використання: python send_manual_message.py broadcast_file <file_path> [active_only]")
            sys.exit(1)
        
        file_path = sys.argv[2]
        active_only = sys.argv[3].lower() in ['true', '1', 'yes'] if len(sys.argv) > 3 else True
        
        message = read_message_from_file(file_path)
        if message.startswith("❌"):
            print(message)
            sys.exit(1)
        
        asyncio.run(send_broadcast_message(message, active_only))
    
    elif command == "help":
        print_help()
    
    else:
        print(f"❌ Невідома команда: {command}")
        print("Використайте 'help' для отримання довідки")
        sys.exit(1)