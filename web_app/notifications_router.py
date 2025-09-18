from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query, Depends, Form
from app.db.models import Notification, NotificationType, User
from web_app.auth import get_current_user
from pydantic import BaseModel
import re
from croniter import croniter

router = APIRouter(prefix="/api/notifications", tags=["notifications"])

# Список адміністраторів
ADMIN_IDS = [
    "591812219",
    "379872548",
    "5916038251"
]

def get_admin_user(user: User = Depends(get_current_user)) -> User:
    """Dependency to ensure only admin users can access notifications endpoints"""
    if user.telegram_id not in ADMIN_IDS:
        raise HTTPException(
            status_code=403, 
            detail="Доступ заборонено! Тільки адміністратори можуть керувати сповіщеннями."
        )
    return user


class NotificationResponse(BaseModel):
    id: str
    user_id: str
    notification_time: str
    notification_text: str
    notification_type: str
    custom_notification_text: Optional[str] = None
    custom_notification_cron: Optional[str] = None
    custom_notification_execute_once: Optional[bool] = False
    system_data: Optional[dict] = None
    is_active: bool
    created_at: datetime
    cron_human_readable: Optional[str] = None
    user_info: Optional[dict] = None


class CreateNotificationRequest(BaseModel):
    user_id: str
    notification_text: str
    notification_type: str
    notification_time: str
    custom_notification_cron: Optional[str] = None
    custom_notification_execute_once: Optional[bool] = False
    
    
class UpdateNotificationRequest(BaseModel):
    notification_text: str
    notification_time: str
    custom_notification_cron: Optional[str] = None
    custom_notification_execute_once: Optional[bool] = False


def cron_to_human_readable(cron_expr: str) -> str:
    """Конвертує cron вираз в читабельний формат"""
    if not cron_expr:
        return ""
    
    try:
        parts = cron_expr.split()
        if len(parts) != 5:
            return cron_expr
        
        minute, hour, day, month, weekday = parts
        
        # Щодня
        if day == "*" and month == "*" and weekday == "*":
            return f"Щодня о {hour}:{minute.zfill(2)}"
        
        # Щотижня
        if day == "*" and month == "*" and weekday != "*":
            weekdays = {
                "0": "Нд", "1": "Пн", "2": "Вт", "3": "Ср", 
                "4": "Чт", "5": "Пт", "6": "Сб"
            }
            days = []
            for w in weekday.split(','):
                days.append(weekdays.get(w, w))
            return f"Щотижня ({', '.join(days)}) о {hour}:{minute.zfill(2)}"
        
        # Щомісяця
        if day != "*" and month == "*" and weekday == "*":
            days = day.split(',')
            if len(days) == 1:
                return f"Щомісяця {days[0]} числа о {hour}:{minute.zfill(2)}"
            else:
                return f"Щомісяця ({', '.join(days)}) о {hour}:{minute.zfill(2)}"
        
        return cron_expr
        
    except Exception:
        return cron_expr


@router.get("/user/{user_id}")
async def get_user_notifications(
    user_id: str,
    notification_type: Optional[str] = Query(None),
    admin_user: User = Depends(get_admin_user)
) -> List[NotificationResponse]:
    """Отримати всі сповіщення користувача або всіх користувачів"""
    try:
        # Спеціальна обробка для "all" - повернути сповіщення всіх користувачів
        if user_id.lower() == "all":
            # Фільтр для запиту - тільки по типу сповіщення, якщо вказано
            query_filter = {}
            if notification_type:
                query_filter["notification_type"] = notification_type
                
            # Отримуємо дані користувачів для додавання імен
            users = {user.telegram_id: user.full_name for user in await User.find().to_list()}
        else:
            # Перевіряємо чи існує користувач
            user = await User.find_one({"telegram_id": user_id})
            if not user:
                raise HTTPException(status_code=404, detail="Користувача не знайдено")
            
            # Фільтр для запиту
            query_filter = {"user_id": user_id}
            if notification_type:
                query_filter["notification_type"] = notification_type
        
        # Отримуємо сповіщення з сортуванням
        notifications = await Notification.find(query_filter).sort([("created_at", -1)]).to_list()
        
        result = []
        for notification in notifications:
            # Додаємо інформацію про користувача якщо запит був для всіх користувачів
            user_info = None
            if user_id.lower() == "all" and notification.user_id in users:
                user_info = {"name": users[notification.user_id]}
                
            notification_data = NotificationResponse(
                id=str(notification.id),
                user_id=notification.user_id,
                notification_time=notification.notification_time,
                notification_text=notification.notification_text,
                notification_type=notification.notification_type.value,
                custom_notification_text=notification.custom_notification_text,
                custom_notification_cron=notification.custom_notification_cron,
                custom_notification_execute_once=notification.custom_notification_execute_once,
                system_data=notification.system_data,
                is_active=notification.is_active,
                created_at=notification.created_at,
                cron_human_readable=cron_to_human_readable(notification.custom_notification_cron) if notification.custom_notification_cron else None,
                user_info=user_info  # Додаємо інформацію про користувача
            )
            result.append(notification_data)
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/create")
async def create_notification(
    request: CreateNotificationRequest,
    admin_user: User = Depends(get_admin_user)
) -> NotificationResponse:
    """Створити нове сповіщення"""
    try:
        # Перевіряємо чи існує користувач
        user = await User.find_one({"telegram_id": request.user_id})
        if not user:
            raise HTTPException(status_code=404, detail="Користувача не знайдено")
        
        # Валідація типу сповіщення
        try:
            notification_type_enum = NotificationType(request.notification_type)
        except ValueError:
            raise HTTPException(status_code=400, detail="Невідомий тип сповіщення")
        
        # Валідація часу
        if not re.match(r"^\d{2}:\d{2}$", request.notification_time):
            raise HTTPException(status_code=400, detail="Невірний формат часу. Використовуйте HH:MM")
        
        # Валідація cron виразу якщо він вказаний
        if request.custom_notification_cron:
            try:
                croniter(request.custom_notification_cron)
            except Exception:
                raise HTTPException(status_code=400, detail="Невірний cron вираз")
        
        # Створення сповіщення
        notification = Notification(
            user_id=request.user_id,
            notification_time=request.notification_time,
            notification_text=request.notification_text,
            notification_type=notification_type_enum,
            custom_notification_text=request.notification_text if notification_type_enum == NotificationType.CUSTOM_NOTIFICATION else None,
            custom_notification_cron=request.custom_notification_cron,
            custom_notification_execute_once=request.custom_notification_execute_once or False,
            system_data={}
        )
        
        await notification.insert()
        
        return NotificationResponse(
            id=str(notification.id),
            user_id=notification.user_id,
            notification_time=notification.notification_time,
            notification_text=notification.notification_text,
            notification_type=notification.notification_type.value,
            custom_notification_text=notification.custom_notification_text,
            custom_notification_cron=notification.custom_notification_cron,
            custom_notification_execute_once=notification.custom_notification_execute_once,
            system_data=notification.system_data,
            is_active=notification.is_active,
            created_at=notification.created_at,
            cron_human_readable=cron_to_human_readable(notification.custom_notification_cron) if notification.custom_notification_cron else None
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{notification_id}/toggle")
async def toggle_notification(
    notification_id: str,
    admin_user: User = Depends(get_admin_user)
) -> NotificationResponse:
    """Увімкнути/вимкнути сповіщення"""
    try:
        notification = await Notification.get(notification_id)
        if not notification:
            raise HTTPException(status_code=404, detail="Сповіщення не знайдено")
        
        notification.is_active = not notification.is_active
        await notification.save()
        
        return NotificationResponse(
            id=str(notification.id),
            user_id=notification.user_id,
            notification_time=notification.notification_time,
            notification_text=notification.notification_text,
            notification_type=notification.notification_type.value,
            custom_notification_text=notification.custom_notification_text,
            custom_notification_cron=notification.custom_notification_cron,
            custom_notification_execute_once=notification.custom_notification_execute_once,
            system_data=notification.system_data,
            is_active=notification.is_active,
            created_at=notification.created_at,
            cron_human_readable=cron_to_human_readable(notification.custom_notification_cron) if notification.custom_notification_cron else None
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: str,
    admin_user: User = Depends(get_admin_user)
):
    """Видалити сповіщення"""
    try:
        notification = await Notification.get(notification_id)
        if not notification:
            raise HTTPException(status_code=404, detail="Сповіщення не знайдено")
        
        await notification.delete()
        return {"message": "Сповіщення видалено"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/types")
async def get_notification_types(admin_user: User = Depends(get_admin_user)):
    """Отримати список доступних типів сповіщень"""
    return {
        "types": [
            {
                "value": NotificationType.DAILY_MORNING_NOTIFICATION.value,
                "label": "Ранкове сповіщення",
                "description": "Щоденне ранкове сповіщення для проходження опитування"
            },
            {
                "value": NotificationType.AFTER_TRAINING_NOTIFICATION.value,
                "label": "Після тренування",
                "description": "Сповіщення після завершення тренування"
            },
            {
                "value": NotificationType.CUSTOM_NOTIFICATION.value,
                "label": "Власне сповіщення",
                "description": "Налаштовуване сповіщення з власним розкладом"
            }
        ]
    }


@router.put("/{notification_id}")
async def update_notification(
    notification_id: str,
    request: UpdateNotificationRequest,
    admin_user: User = Depends(get_admin_user)
) -> NotificationResponse:
    """Оновити існуюче сповіщення"""
    try:
        notification = await Notification.get(notification_id)
        if not notification:
            raise HTTPException(status_code=404, detail="Сповіщення не знайдено")
        
        # Валідація часу
        if not re.match(r"^\d{2}:\d{2}$", request.notification_time):
            raise HTTPException(status_code=400, detail="Невірний формат часу. Використовуйте HH:MM")
        
        # Валідація cron виразу якщо він вказаний
        if request.custom_notification_cron:
            try:
                croniter(request.custom_notification_cron)
            except Exception:
                raise HTTPException(status_code=400, detail="Невірний cron вираз")
        
        # Оновлення полів сповіщення
        notification.notification_time = request.notification_time
        notification.notification_text = request.notification_text
        
        # Оновлення додаткових полів для користувацьких сповіщень
        if notification.notification_type == NotificationType.CUSTOM_NOTIFICATION:
            notification.custom_notification_text = request.notification_text
            notification.custom_notification_cron = request.custom_notification_cron
            notification.custom_notification_execute_once = request.custom_notification_execute_once
        
        await notification.save()
        
        return NotificationResponse(
            id=str(notification.id),
            user_id=notification.user_id,
            notification_time=notification.notification_time,
            notification_text=notification.notification_text,
            notification_type=notification.notification_type.value,
            custom_notification_text=notification.custom_notification_text,
            custom_notification_cron=notification.custom_notification_cron,
            custom_notification_execute_once=notification.custom_notification_execute_once,
            system_data=notification.system_data,
            is_active=notification.is_active,
            created_at=notification.created_at,
            cron_human_readable=cron_to_human_readable(notification.custom_notification_cron) if notification.custom_notification_cron else None
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users")
async def get_all_users(admin_user: User = Depends(get_admin_user)):
    """Отримати список всіх користувачів для адміністративного інтерфейсу"""
    try:
        users = await User.find().sort([("full_name", 1)]).to_list()
        
        return [{
            "telegram_id": user.telegram_id,
            "full_name": user.full_name,
            "telegram_username": user.telegram_username,
            "is_active": user.is_active,
            "created_at": user.created_at
        } for user in users]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cron-presets")
async def get_cron_presets(admin_user: User = Depends(get_admin_user)):
    """Отримати готові шаблони cron виразів"""
    return {
        "presets": [
            {
                "label": "Щодня о 08:00",
                "cron": "0 8 * * *"
            },
            {
                "label": "Щотижня у понеділок о 09:00",
                "cron": "0 9 * * 1"
            },
            {
                "label": "Щотижня у п'ятницю о 18:00",
                "cron": "0 18 * * 5"
            },
            {
                "label": "Щомісяця 1 числа о 10:00",
                "cron": "0 10 1 * *"
            },
            {
                "label": "Кожні 2 години",
                "cron": "0 */2 * * *"
            },
            {
                "label": "Робочі дні о 12:00 (Пн-Пт)",
                "cron": "0 12 * * 1-5"
            },
            {
                "label": "Вихідні о 10:00 (Сб-Нд)",
                "cron": "0 10 * * 0,6"
            }
        ]
    }
