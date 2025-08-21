from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from app.db.models import User, MorningQuiz, TrainingSession, UserStatistics, PeriodType
import logging

logger = logging.getLogger(__name__)

# Імпорт AI аналізатора (опціонально)
try:
    from app.ai_analyzer import StatisticsAnalyzer
    AI_ANALYZER_AVAILABLE = True
except ImportError:
    AI_ANALYZER_AVAILABLE = False
    logger.warning("AI аналізатор не доступний")


class StatisticsGenerator:
    """Клас для генерації статистики користувачів"""
    
    @staticmethod
    def get_current_week_range() -> Tuple[datetime, datetime]:
        """Повертає початок і кінець поточного тижня (понеділок-неділя)"""
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        monday = today - timedelta(days=today.weekday())
        sunday = monday + timedelta(days=6, hours=23, minutes=59, seconds=59)
        return monday, sunday
        
    @staticmethod
    def get_previous_week_range() -> Tuple[datetime, datetime]:
        """Повертає початок і кінець попереднього тижня (понеділок-неділя)"""
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        this_monday = today - timedelta(days=today.weekday())
        prev_monday = this_monday - timedelta(days=7)
        prev_sunday = prev_monday + timedelta(days=6, hours=23, minutes=59, seconds=59)
        return prev_monday, prev_sunday
    
    @staticmethod
    def get_current_month_range() -> Tuple[datetime, datetime]:
        """Повертає останні 4 тижні (28 днів)"""
        end = datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999)
        start = end - timedelta(days=27)  # 28 днів загалом включаючи поточний
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        return start, end
        
    @staticmethod
    def get_previous_month_range() -> Tuple[datetime, datetime]:
        """Повертає попередні 4 тижні (28 днів) перед поточним тижнем"""
        # Кінець періоду - неділя попереднього тижня
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        this_monday = today - timedelta(days=today.weekday())
        prev_sunday = this_monday - timedelta(days=1, microseconds=1)
        # Початок періоду - за 28 днів до кінця
        start = prev_sunday - timedelta(days=27)
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        return start, prev_sunday
    
    @staticmethod
    def generate_date_range(start_date: datetime, end_date: datetime) -> List[datetime]:
        """Створює список всіх дат у періоді"""
        dates = []
        current = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        while current <= end_date:
            dates.append(current)
            current += timedelta(days=1)
        return dates
    
    @staticmethod
    def calculate_average(values: List[float]) -> float:
        """Обчислює середнє арифметичне"""
        if not values:
            return 0.0
        return round(sum(values) / len(values), 1)
    
    @staticmethod
    def calculate_trend(values: List[float]) -> str:
        """Визначає тренд (stable/increasing/decreasing)"""
        if len(values) < 2:
            return "stable"
        
        # Порівнюємо першу і останню половини
        mid = len(values) // 2
        first_half = values[:mid] if mid > 0 else values[:1]
        second_half = values[mid:] if mid < len(values) else values[-1:]
        
        first_avg = sum(first_half) / len(first_half)
        second_avg = sum(second_half) / len(second_half)
        
        diff = second_avg - first_avg
        
        if abs(diff) < 0.5:  # Поріг для стабільності
            return "stable"
        elif diff > 0:
            return "increasing"
        else:
            return "decreasing"
    
    @staticmethod
    def format_date_for_display(date: datetime) -> str:
        """Форматує дату у формат dd.MM"""
        return date.strftime("%d.%m")
    
    async def aggregate_stress_data(self, user_id: str, start_date: datetime, end_date: datetime) -> Dict:
        """Збирає дані про стрес після тренувань"""
        training_sessions = await TrainingSession.find({
            "user_id": user_id,
            "created_at": {"$gte": start_date, "$lte": end_date},
            "stress_level": {"$ne": None},
            "completed": True
        }).to_list()
        
        # Групуємо по датах і беремо останню тренування кожного дня
        daily_stress = {}
        for session in training_sessions:
            date_key = session.created_at.date()
            if date_key not in daily_stress or session.created_at > daily_stress[date_key]['datetime']:
                daily_stress[date_key] = {
                    'value': session.stress_level,
                    'datetime': session.created_at
                }
        
        data_points = []
        values = []
        
        for date_key, stress_info in daily_stress.items():
            data_points.append({
                "date": self.format_date_for_display(stress_info['datetime']),
                "value": stress_info['value'],
                "raw_date": stress_info['datetime'].isoformat()
            })
            values.append(stress_info['value'])
        
        # Сортуємо по даті
        data_points.sort(key=lambda x: x['raw_date'])
        
        return {
            "chart_type": "scatter",
            "data_points": data_points,
            "y_axis_range": [0, 10],
            "average": self.calculate_average(values),
            "trend": self.calculate_trend(values)
        }
    
    async def aggregate_warehouse_data(self, user_id: str, start_date: datetime, end_date: datetime) -> Dict:
        """Збирає дані про складність тренувань"""
        training_sessions = await TrainingSession.find({
            "user_id": user_id,
            "created_at": {"$gte": start_date, "$lte": end_date},
            "how_hard_was_training": {"$ne": None},
            "completed": True
        }).to_list()
        
        # Групуємо по датах і беремо останню тренування кожного дня
        daily_difficulty = {}
        for session in training_sessions:
            date_key = session.created_at.date()
            if date_key not in daily_difficulty or session.created_at > daily_difficulty[date_key]['datetime']:
                daily_difficulty[date_key] = {
                    'value': session.how_hard_was_training,
                    'datetime': session.created_at
                }
        
        data_points = []
        values = []
        
        for date_key, difficulty_info in daily_difficulty.items():
            data_points.append({
                "date": self.format_date_for_display(difficulty_info['datetime']),
                "value": difficulty_info['value'],
                "raw_date": difficulty_info['datetime'].isoformat()
            })
            values.append(difficulty_info['value'])
        
        # Сортуємо по даті
        data_points.sort(key=lambda x: x['raw_date'])
        
        return {
            "chart_type": "scatter",
            "data_points": data_points,
            "y_axis_range": [0, 10],
            "average": self.calculate_average(values),
            "trend": self.calculate_trend(values)
        }
    
    async def aggregate_sleep_data(self, user_id: str, start_date: datetime, end_date: datetime) -> Dict:
        """Збирає дані про сон"""
        morning_quizzes = await MorningQuiz.find({
            "user_id": user_id,
            "created_at": {"$gte": start_date, "$lte": end_date},
            "how_many_hours_of_sleep": {"$ne": None},
            "completed": True
        }).to_list()
        
        # Групуємо по датах
        daily_sleep = {}
        for quiz in morning_quizzes:
            date_key = quiz.created_at.date()
            daily_sleep[date_key] = {
                'value': quiz.how_many_hours_of_sleep,
                'datetime': quiz.created_at
            }
        
        # Створюємо дані для всіх днів тижня
        all_dates = self.generate_date_range(start_date, end_date)
        data_points = []
        values = []
        total_sleep = 0
        
        for date in all_dates:
            date_key = date.date()
            if date_key in daily_sleep:
                sleep_hours = daily_sleep[date_key]['value']
                total_sleep += sleep_hours
                values.append(sleep_hours)
            else:
                sleep_hours = 0
            
            data_points.append({
                "date": self.format_date_for_display(date),
                "value": sleep_hours,
                "raw_date": date.isoformat()
            })
        
        return {
            "chart_type": "bar",
            "data_points": data_points,
            "y_axis_range": [0, 12],
            "average": self.calculate_average(values),
            "total_sleep_hours": round(total_sleep, 1)
        }
    
    async def aggregate_wellbeing_data(self, user_id: str, start_date: datetime, end_date: datetime) -> Dict:
        """Збирає дані про самопочуття"""
        morning_quizzes = await MorningQuiz.find({
            "user_id": user_id,
            "created_at": {"$gte": start_date, "$lte": end_date},
            "how_do_you_feel_today": {"$ne": None},
            "completed": True
        }).to_list()
        
        # Групуємо по датах
        daily_wellbeing = {}
        for quiz in morning_quizzes:
            date_key = quiz.created_at.date()
            daily_wellbeing[date_key] = {
                'value': quiz.how_do_you_feel_today,
                'datetime': quiz.created_at
            }
        
        data_points = []
        values = []
        
        # Показуємо тільки дні з даними
        for date_key, wellbeing_info in daily_wellbeing.items():
            data_points.append({
                "date": self.format_date_for_display(wellbeing_info['datetime']),
                "value": wellbeing_info['value'],
                "raw_date": wellbeing_info['datetime'].isoformat()
            })
            values.append(wellbeing_info['value'])
        
        # Сортуємо по даті
        data_points.sort(key=lambda x: x['raw_date'])
        
        return {
            "chart_type": "line",
            "data_points": data_points,
            "y_axis_range": [0, 10],
            "average": self.calculate_average(values),
            "trend": self.calculate_trend(values)
        }
    
    async def aggregate_weight_data(self, user_id: str, start_date: datetime, end_date: datetime) -> Dict:
        """Збирає дані про вагу"""
        morning_quizzes = await MorningQuiz.find({
            "user_id": user_id,
            "created_at": {"$gte": start_date, "$lte": end_date},
            "weight": {"$ne": None},
            "completed": True
        }).to_list()
        
        # Групуємо по датах
        daily_weight = {}
        for quiz in morning_quizzes:
            date_key = quiz.created_at.date()
            daily_weight[date_key] = {
                'value': quiz.weight,
                'datetime': quiz.created_at
            }
        
        data_points = []
        values = []
        
        # Показуємо тільки дні з вимірюваннями
        for date_key, weight_info in daily_weight.items():
            data_points.append({
                "date": self.format_date_for_display(weight_info['datetime']),
                "value": weight_info['value'],
                "raw_date": weight_info['datetime'].isoformat()
            })
            values.append(weight_info['value'])
        
        # Сортуємо по даті
        data_points.sort(key=lambda x: x['raw_date'])
        
        # Обчислюємо діапазон Y-осі та зміни ваги
        if values:
            min_weight = min(values)
            max_weight = max(values)
            weight_range = max_weight - min_weight
            
            # Додаємо 10% буфер до діапазону
            buffer = weight_range * 0.1 if weight_range > 0 else 0.5
            y_min = round(min_weight - buffer, 1)
            y_max = round(max_weight + buffer, 1)
            
            start_weight = values[0]
            end_weight = values[-1]
            weight_change = round(end_weight - start_weight, 1)
        else:
            y_min, y_max = 0, 100
            start_weight = end_weight = weight_change = 0
        
        return {
            "chart_type": "area",
            "data_points": data_points,
            "y_axis_range": [y_min, y_max],
            "start_weight": start_weight,
            "end_weight": end_weight,
            "weight_change": weight_change,
            "trend": self.calculate_trend(values)
        }
    
    async def generate_user_statistics(self, user_id: str, period_type: PeriodType, use_previous_period: bool = True) -> UserStatistics:
        """
        Головна функція генерації статистики користувача
        
        Args:
            user_id: ID користувача
            period_type: Тип періоду (тижневий/місячний)
            use_previous_period: Якщо True, використовується попередній період, інакше - поточний
        """
        
        # Визначаємо діапазон дат
        if period_type == PeriodType.WEEKLY:
            if use_previous_period:
                start_date, end_date = self.get_previous_week_range()
            else:
                start_date, end_date = self.get_current_week_range()
        else:  # MONTHLY
            if use_previous_period:
                start_date, end_date = self.get_previous_month_range()
            else:
                start_date, end_date = self.get_current_month_range()
        
        # Підраховуємо загальну кількість записів
        total_training_sessions = await TrainingSession.find({
            "user_id": user_id,
            "created_at": {"$gte": start_date, "$lte": end_date},
            "completed": True
        }).count()
        
        total_morning_quizzes = await MorningQuiz.find({
            "user_id": user_id,
            "created_at": {"$gte": start_date, "$lte": end_date},
            "completed": True
        }).count()
        
        # Збираємо дані для кожного типу графіка
        stress_data = await self.aggregate_stress_data(user_id, start_date, end_date)
        warehouse_data = await self.aggregate_warehouse_data(user_id, start_date, end_date)
        sleep_data = await self.aggregate_sleep_data(user_id, start_date, end_date)
        wellbeing_data = await self.aggregate_wellbeing_data(user_id, start_date, end_date)
        weight_data = await self.aggregate_weight_data(user_id, start_date, end_date)
        
        # Перевіряємо чи існує вже статистика для цього періоду
        existing_stats = await UserStatistics.find_one({
            "user_id": user_id,
            "period_type": period_type,
            "period_start": start_date,
            "period_end": end_date
        })
        
        if existing_stats:
            # Оновлюємо існуючу статистику
            existing_stats.stress_data = stress_data
            existing_stats.warehouse_data = warehouse_data
            existing_stats.sleep_data = sleep_data
            existing_stats.wellbeing_data = wellbeing_data
            existing_stats.weight_data = weight_data
            existing_stats.total_training_sessions = total_training_sessions
            existing_stats.total_morning_quizzes = total_morning_quizzes
            existing_stats.is_complete = True
            existing_stats.generated_at = datetime.now()
            
            await existing_stats.save()
            return existing_stats
        else:
            # Створюємо нову статистику
            stats = UserStatistics(
                user_id=user_id,
                period_type=period_type,
                period_start=start_date,
                period_end=end_date,
                stress_data=stress_data,
                warehouse_data=warehouse_data,
                sleep_data=sleep_data,
                wellbeing_data=wellbeing_data,
                weight_data=weight_data,
                total_training_sessions=total_training_sessions,
                total_morning_quizzes=total_morning_quizzes,
                is_complete=True
            )
            
            await stats.save()
            return stats
    
    async def generate_user_statistics_with_ai(self, user_id: str, period_type: PeriodType, 
                                   regenerate_if_exists: bool = False,
                                   use_previous_period: bool = True) -> Optional[UserStatistics]:
        """Генерує статистику користувача з AI-аналізом"""
        
        if not AI_ANALYZER_AVAILABLE:
            return None
            
        # Генеруємо базову статистику
        stats = await self.generate_user_statistics(user_id, period_type, use_previous_period)
        
        # Генеруємо AI аналіз статистики
        try:
            from app.ai_analyzer import StatisticsAnalyzer
            
            # Створюємо аналізатор з ключами з середовища
            analyzer = StatisticsAnalyzer()
            
            # Аналізуємо статистику
            analysis_success = await analyzer.analyze_statistics(stats)
            
            if not analysis_success:
                logger.warning(f"Не вдалося створити AI аналіз для користувача {user_id}")
        
        except Exception as e:
            logger.error(f"Помилка при генерації AI аналізу: {e}")
        
        return stats
    
    async def generate_statistics_for_all_users(self, period_type: PeriodType, use_previous_period: bool = True) -> List[UserStatistics]:
        """Генерує статистику для всіх активних користувачів"""
        active_users = await User.find({"is_active": True}).to_list()
        generated_statistics = []
        
        for user in active_users:
            try:
                stats = await self.generate_user_statistics(user.telegram_id, period_type, use_previous_period)
                generated_statistics.append(stats)
            except Exception as e:
                print(f"Помилка при генерації статистики для користувача {user.telegram_id}: {e}")
                continue
        
        return generated_statistics
