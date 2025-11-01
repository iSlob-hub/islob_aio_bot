"""
Міграційний скрипт для додавання notification_time_base до існуючих сповіщень
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings
from app.db.models import Notification, User


async def migrate_notifications():
    """Оновити всі існуючі сповіщення з notification_time_base"""
    
    # Підключаємось до бази даних
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    
    # Ініціалізуємо Beanie
    from beanie import init_beanie
    await init_beanie(
        database=client[settings.MONGODB_DB_NAME],
        document_models=[Notification, User]
    )
    
    print("Починаємо міграцію сповіщень...")
    
    # Отримуємо всі сповіщення
    notifications = await Notification.find_all().to_list()
    
    print(f"Знайдено {len(notifications)} сповіщень")
    
    updated_count = 0
    
    for notification in notifications:
        # Якщо notification_time_base вже встановлено, пропускаємо
        if notification.notification_time_base:
            print(f"Сповіщення {notification.id} вже має notification_time_base, пропускаємо")
            continue
        
        # Отримуємо користувача
        user = await User.find_one({"telegram_id": notification.user_id})
        
        if not user:
            print(f"Користувача {notification.user_id} не знайдено, встановлюємо base = time")
            notification.notification_time_base = notification.notification_time
            await notification.save()
            updated_count += 1
            continue
        
        # Розраховуємо час користувача
        timezone_offset = user.timezone_offset or 0
        
        try:
            kyiv_hour, kyiv_minute = map(int, notification.notification_time.split(':'))
            
            # Додаємо офсет для отримання часу користувача
            user_hour = kyiv_hour + timezone_offset
            
            # Обробка переходу через межу доби
            if user_hour < 0:
                user_hour += 24
            elif user_hour >= 24:
                user_hour -= 24
            
            user_time_str = f"{user_hour:02d}:{kyiv_minute:02d}"
            
            notification.notification_time_base = user_time_str
            await notification.save()
            
            print(f"✅ Оновлено сповіщення {notification.id}: Київ={notification.notification_time}, Користувач={user_time_str} (offset={timezone_offset})")
            updated_count += 1
            
        except ValueError:
            print(f"❌ Помилка парсингу часу для сповіщення {notification.id}: {notification.notification_time}")
            notification.notification_time_base = notification.notification_time
            await notification.save()
            updated_count += 1
    
    print(f"\n✅ Міграція завершена! Оновлено {updated_count} сповіщень з {len(notifications)}")
    
    client.close()


if __name__ == "__main__":
    asyncio.run(migrate_notifications())
