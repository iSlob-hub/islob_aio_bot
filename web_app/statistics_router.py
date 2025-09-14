from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query, Depends
from app.statistics_scheduler import get_user_statistics
from app.db.models import UserStatistics, PeriodType, User
from web_app.auth import get_current_user
from pydantic import BaseModel

router = APIRouter(prefix="/api/statistics", tags=["statistics"])

# Список адміністраторів (той самий що і в main.py)
ADMIN_IDS = [
    "591812219",
    "379872548",
    "5916038251"
]

def get_admin_user(user: User = Depends(get_current_user)) -> User:
    """Dependency to ensure only admin users can access statistics endpoints"""
    if user.telegram_id not in ADMIN_IDS:
        raise HTTPException(
            status_code=403, 
            detail="Доступ заборонено! Тільки адміністратори можуть переглядати статистику."
        )
    return user


class StatisticsResponse(BaseModel):
    user_id: str
    period_type: str
    period_start: datetime
    period_end: datetime
    stress_data: Optional[dict] = None
    warehouse_data: Optional[dict] = None
    sleep_data: Optional[dict] = None
    wellbeing_data: Optional[dict] = None
    weight_data: Optional[dict] = None
    total_training_sessions: int
    total_morning_quizzes: int
    is_complete: bool
    generated_at: datetime
    ai_analysis: Optional[str] = None
    ai_analysis_generated_at: Optional[datetime] = None


@router.get("/user/{user_id}")
async def get_user_statistics_endpoint(
    user_id: str,
    period_type: str = Query("weekly", regex="^(weekly|monthly)$"),
    generate_if_missing: bool = Query(True),
    current_period: bool = Query(False, description="Отримати статистику за поточний період (тільки для адміністраторів)"),
    admin_user: User = Depends(get_admin_user)
) -> StatisticsResponse:
    """Отримати статистику користувача
    
    Якщо параметр current_period=True, повертає статистику за поточний період.
    За замовчуванням повертає статистику за попередній період.
    """
    try:
        # Використовуємо параметр current_period для визначення типу періоду
        # Для current_period=True: use_previous_period=False (поточний період)
        # Для current_period=False: use_previous_period=True (попередній період)
        stats = await get_user_statistics(
            user_id=user_id,
            period_type=period_type,
            generate_if_missing=generate_if_missing,
            use_previous_period=not current_period
        )
        
        if not stats or not stats.get("statistics"):
            period_desc = "поточний" if current_period else "попередній"
            raise HTTPException(
                status_code=404,
                detail=f"Статистика для користувача {user_id} за {period_desc} {period_type} період не знайдена"
            )

        stats = stats["statistics"]
        return StatisticsResponse(
            user_id=stats.user_id,
            period_type=stats.period_type.value,
            period_start=stats.period_start,
            period_end=stats.period_end,
            stress_data=stats.stress_data,
            warehouse_data=stats.warehouse_data,
            sleep_data=stats.sleep_data,
            wellbeing_data=stats.wellbeing_data,
            weight_data=stats.weight_data,
            total_training_sessions=stats.total_training_sessions,
            total_morning_quizzes=stats.total_morning_quizzes,
            is_complete=stats.is_complete,
            generated_at=stats.generated_at,
            ai_analysis=stats.ai_analysis,
            ai_analysis_generated_at=stats.ai_analysis_generated_at
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate/{user_id}")
async def generate_user_statistics_endpoint(
    user_id: str,
    period_type: str = Query("weekly", regex="^(weekly|monthly)$"),
    current_period: bool = Query(False, description="Генерувати статистику за поточний період"),
    admin_user: User = Depends(get_admin_user)
) -> StatisticsResponse:
    """Згенерувати статистику для користувача вручну
    
    Якщо параметр current_period=True, генерує статистику за поточний період.
    За замовчуванням генерує статистику за попередній період.
    """
    try:
        from app.statistics import StatisticsGenerator
        from app.db.models import PeriodType
        
        # Перевіряємо чи існує користувач
        user = await User.find_one({"telegram_id": user_id})
        if not user:
            raise HTTPException(status_code=404, detail="Користувача не знайдено")
            
        # Тепер замість generate_statistics_manually викликаємо напряму StatisticsGenerator,
        # щоб мати можливість передати параметр use_previous_period
        period_enum = PeriodType.WEEKLY if period_type == "weekly" else PeriodType.MONTHLY
        generator = StatisticsGenerator()
        
        # Генеруємо статистику з вказаним параметром use_previous_period
        stats = await generator.generate_user_statistics(
            user_id=user_id, 
            period_type=period_enum, 
            use_previous_period=not current_period
        )
        
        return StatisticsResponse(
            user_id=stats.user_id,
            period_type=stats.period_type.value,
            period_start=stats.period_start,
            period_end=stats.period_end,
            stress_data=stats.stress_data,
            warehouse_data=stats.warehouse_data,
            sleep_data=stats.sleep_data,
            wellbeing_data=stats.wellbeing_data,
            weight_data=stats.weight_data,
            total_training_sessions=stats.total_training_sessions,
            total_morning_quizzes=stats.total_morning_quizzes,
            is_complete=stats.is_complete,
            generated_at=stats.generated_at,
            ai_analysis=stats.ai_analysis,
            ai_analysis_generated_at=stats.ai_analysis_generated_at
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate/all")
async def generate_all_statistics_endpoint(
    period_type: str = Query("weekly", regex="^(weekly|monthly)$"),
    current_period: bool = Query(False, description="Генерувати статистику за поточний період"),
    admin_user: User = Depends(get_admin_user)
) -> List[StatisticsResponse]:
    """Згенерувати статистику для всіх користувачів
    
    Якщо параметр current_period=True, генерує статистику за поточний період.
    За замовчуванням генерує статистику за попередній період.
    """
    try:
        from app.statistics import StatisticsGenerator
        from app.db.models import PeriodType
        
        # Замість generate_statistics_manually викликаємо напряму StatisticsGenerator,
        # щоб мати можливість передати параметр use_previous_period
        period_enum = PeriodType.WEEKLY if period_type == "weekly" else PeriodType.MONTHLY
        generator = StatisticsGenerator()
        
        # Генеруємо статистику з вказаним параметром use_previous_period
        stats_list = await generator.generate_statistics_for_all_users(
            period_type=period_enum, 
            use_previous_period=not current_period
        )
        
        if not stats_list:
            period_desc = "поточний" if current_period else "попередній"
            raise HTTPException(
                status_code=404, 
                detail=f"Статистика за {period_desc} {period_type} період не знайдена"
            )

        return [
            StatisticsResponse(
                user_id=stats.user_id,
                period_type=stats.period_type.value,
                period_start=stats.period_start,
                period_end=stats.period_end,
                stress_data=stats.stress_data,
                warehouse_data=stats.warehouse_data,
                sleep_data=stats.sleep_data,
                wellbeing_data=stats.wellbeing_data,
                weight_data=stats.weight_data,
                total_training_sessions=stats.total_training_sessions,
                total_morning_quizzes=stats.total_morning_quizzes,
                is_complete=stats.is_complete,
                generated_at=stats.generated_at,
                ai_analysis=stats.ai_analysis,
                ai_analysis_generated_at=stats.ai_analysis_generated_at
            )
            for stats in stats_list
        ]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{user_id}")
async def get_user_statistics_history(
    user_id: str,
    period_type: str = Query("weekly", regex="^(weekly|monthly)$"),
    limit: int = Query(10, ge=1, le=100),
    current_period: bool = Query(False, description="Включати статистику за поточний період"),
    admin_user: User = Depends(get_admin_user)
) -> List[StatisticsResponse]:
    """Отримати історію статистики користувача
    
    Якщо параметр current_period=True, буде включена також статистика за поточний період
    (якщо вона існує). За замовчуванням повертаються тільки завершені періоди.
    """
    try:
        period = PeriodType.WEEKLY if period_type.lower() == "weekly" else PeriodType.MONTHLY
        from app.statistics import StatisticsGenerator
        
        # Визначаємо діапазон дат для поточного періоду
        stats_generator = StatisticsGenerator()
        if period == PeriodType.WEEKLY:
            current_start, current_end = stats_generator.get_current_week_range()
        else:
            current_start, current_end = stats_generator.get_current_month_range()
        
        # Будуємо запит в базу даних
        query = [UserStatistics.user_id == user_id, UserStatistics.period_type == period]
        
        # Якщо не потрібно включати поточний період, додаємо фільтр
        if not current_period:
            query.append(UserStatistics.period_start < current_start)
        
        # Виконуємо запит до бази
        stats_list = await UserStatistics.find(*query).sort([("period_start", -1)]).limit(limit).to_list()
        
        return [
            StatisticsResponse(
                user_id=stats.user_id,
                period_type=stats.period_type.value,
                period_start=stats.period_start,
                period_end=stats.period_end,
                stress_data=stats.stress_data,
                warehouse_data=stats.warehouse_data,
                sleep_data=stats.sleep_data,
                wellbeing_data=stats.wellbeing_data,
                weight_data=stats.weight_data,
                total_training_sessions=stats.total_training_sessions,
                total_morning_quizzes=stats.total_morning_quizzes,
                is_complete=stats.is_complete,
                generated_at=stats.generated_at,
                ai_analysis=stats.ai_analysis,
                ai_analysis_generated_at=stats.ai_analysis_generated_at
            )
            for stats in stats_list
        ]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/scheduler/status")
async def get_scheduler_status_endpoint(admin_user: User = Depends(get_admin_user)):
    """Отримати статус планувальника статистики"""
    from app.statistics_scheduler import statistics_scheduler
    return statistics_scheduler.get_scheduler_status()


@router.get("/ai-config")
async def get_ai_config(admin_user: User = Depends(get_admin_user)):
    """Отримання конфігурації AI для фронтенду"""
    from app.config import settings
    
    return {
        "has_api_key": bool(settings.OPENAI_API_KEY),
        "has_model": bool(settings.OPENAI_MODEL),
        # Більше не відправляємо ключі на фронтенд
        "api_key": None,
        "model": settings.OPENAI_MODEL
    }


@router.post("/generate-with-ai/{user_id}")
async def generate_statistics_with_ai_endpoint(
    user_id: str,
    period_type: str = Query("weekly", regex="^(weekly|monthly)$"),
    current_period: bool = Query(False, description="Генерувати статистику за поточний період"),
    admin_user: User = Depends(get_admin_user)
):
    """Генерація статистики з AI аналізом
    
    Якщо параметр current_period=True, генерує статистику за поточний період.
    За замовчуванням генерує статистику за попередній період.
    """
    
    try:
        from app.statistics import StatisticsGenerator
        from app.db.models import PeriodType
        
        # Перевіряємо чи існує користувач
        user = await User.find_one({"telegram_id": user_id})
        if not user:
            raise HTTPException(status_code=404, detail="Користувача не знайдено")
        
        # Конвертуємо тип періоду
        period_enum = PeriodType.WEEKLY if period_type == "weekly" else PeriodType.MONTHLY
        
        # Генеруємо статистику з AI
        generator = StatisticsGenerator()
        stats = await generator.generate_user_statistics_with_ai(
            user_id=user_id,
            period_type=period_enum,
            use_previous_period=not current_period
        )
        
        if not stats:
            period_desc = "поточний" if current_period else "попередній"
            raise HTTPException(
                status_code=404, 
                detail=f"Не вдалося згенерувати AI аналіз для {period_desc} {period_type} періоду"
            )
            
        return StatisticsResponse(
            user_id=stats.user_id,
            period_type=stats.period_type.value,
            period_start=stats.period_start,
            period_end=stats.period_end,
            stress_data=stats.stress_data,
            warehouse_data=stats.warehouse_data,
            sleep_data=stats.sleep_data,
            wellbeing_data=stats.wellbeing_data,
            weight_data=stats.weight_data,
            total_training_sessions=stats.total_training_sessions,
            total_morning_quizzes=stats.total_morning_quizzes,
            is_complete=stats.is_complete,
            generated_at=stats.generated_at,
            ai_analysis=stats.ai_analysis,
            ai_analysis_generated_at=stats.ai_analysis_generated_at
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/test/monday-check")
async def test_monday_check(admin_user: User = Depends(get_admin_user)):
    """Тестовий ендпоінт для перевірки логіки 4-го понеділка"""
    from app.statistics_scheduler import StatisticsScheduler
    from datetime import datetime
    
    return {
        "current_date": datetime.now().strftime("%Y-%m-%d %A"),
        "is_monday": datetime.now().weekday() == 0,
        "is_fourth_monday_or_later": StatisticsScheduler.is_fourth_monday_or_later(),
        "weekday_number": datetime.now().weekday(),  # 0 = Monday
    }
