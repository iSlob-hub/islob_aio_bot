"""
Інтеграція з OpenAI Chat Completions API для аналізу статистики
"""

from datetime import datetime
from typing import Optional, Dict, Any
import logging
from dotenv import load_dotenv
import os
logger = logging.getLogger(__name__)

load_dotenv()

try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI пакет не встановлено. Встановіть: pip install openai")

# Конфігурація - додайте ці змінні у ваш .env файл
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4.1-mini")  # Модель за замовчуванням


class StatisticsAnalyzer:
    """Клас для аналізу статистики через OpenAI Chat Completions API"""
    
    def __init__(self, api_key: str = None, model: str = None):
        if not OPENAI_AVAILABLE:
            raise ImportError("OpenAI пакет не встановлено. Встановіть: pip install openai")
            
        self.api_key = api_key or OPENAI_API_KEY
        self.model = model or OPENAI_MODEL
        
        if not self.api_key:
            raise ValueError("Необхідно вказати OPENAI_API_KEY")
            
        self.client = AsyncOpenAI(api_key=self.api_key)
        
        # Завантажуємо інструкцію для асистента
        self.system_instruction = self._load_system_instruction()
    
    def _load_system_instruction(self) -> str:
        """Завантаження системної інструкції з файлу"""
        try:
            template_path = os.path.join(os.path.dirname(__file__), '..', 'assistant_template.txt')
            with open(template_path, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except Exception as e:
            logger.error(f"Помилка завантаження системної інструкції: {e}")
            return "Ти - AI-асистент для аналізу фітнес-статистики. Відповідай коротко та структуровано."
    
    def _calculate_data_completeness(self, stats_data: Dict[str, Any]) -> Dict[str, Any]:
        """Розраховує відсоток заповнення даних та кількість пропущених днів"""
        
        # Визначаємо очікувану кількість днів на основі типу періоду
        period_type = stats_data.get("period_type", "weekly")
        expected_days = 7 if period_type == "weekly" else 30  # базові значення
        
        # Рахуємо фактичні дні з даними
        total_quizzes = stats_data.get("total_morning_quizzes", 0)
        total_sessions = stats_data.get("total_training_sessions", 0)
        
        # Додаткова перевірка через data_points у метриках
        max_data_points = 0
        missing_days_in_metrics = 0
        
        for metric_type in ["stress_data", "warehouse_data", "sleep_data", "wellbeing_data", "weight_data"]:
            metric_data = stats_data.get(metric_type)
            if metric_data and "data_points" in metric_data:
                data_points = metric_data.get("data_points", [])
                max_data_points = max(max_data_points, len(data_points))
                
                # Рахуємо пропуски (None значення)
                null_count = sum(1 for point in data_points if point.get("value") is None)
                missing_days_in_metrics = max(missing_days_in_metrics, null_count)
        
        # Використовуємо максимальну кількість точок як базу
        if max_data_points > 0:
            expected_days = max_data_points
        
        # Рахуємо пропущені дні
        missing_days = expected_days - max(total_quizzes, total_sessions)
        if missing_days_in_metrics > 0:
            missing_days = max(missing_days, missing_days_in_metrics)
        
        # Забезпечуємо, що пропуски не можуть бути негативними
        missing_days = max(0, missing_days)
        
        # Розраховуємо відсоток заповнення
        filled_days = expected_days - missing_days
        completion_percentage = (filled_days / expected_days * 100) if expected_days > 0 else 100
        
        return {
            "expected_days": expected_days,
            "filled_days": filled_days, 
            "missing_days": missing_days,
            "completion_percentage": round(completion_percentage, 1),
            "has_missing_data": missing_days > 0
        }

    def format_statistics_for_analysis(self, stats_data: Dict[str, Any]) -> str:
        """Форматування статистики для передачі асистенту"""
        
        # Розраховуємо повноту даних
        data_completeness = self._calculate_data_completeness(stats_data)
        
        analysis_data = {
            "period": {
                "type": stats_data.get("period_type"),
                "start": stats_data.get("period_start"),
                "end": stats_data.get("period_end")
            },
            "user_profile": {
                "training_goal": stats_data.get("training_goal", "Підтримка форми")
            },
            "summary": {
                "total_training_sessions": stats_data.get("total_training_sessions", 0),
                "total_morning_quizzes": stats_data.get("total_morning_quizzes", 0)
            },
            "data_completeness": data_completeness,
            "metrics": {}
        }
        
        # Додаємо дані по кожному типу метрики
        for metric_type in ["stress_data", "warehouse_data", "sleep_data", "wellbeing_data", "weight_data"]:
            metric_data = stats_data.get(metric_type)
            if metric_data:
                analysis_data["metrics"][metric_type] = {
                    "chart_type": metric_data.get("chart_type"),
                    "average": metric_data.get("average"),
                    "trend": metric_data.get("trend"),
                    "data_points_count": len(metric_data.get("data_points", [])),
                    "data_points": metric_data.get("data_points", [])
                }
                
                # Додаємо специфічні поля для окремих метрик
                if metric_type == "sleep_data":
                    analysis_data["metrics"][metric_type]["total_sleep_hours"] = metric_data.get("total_sleep_hours")
                elif metric_type == "weight_data":
                    analysis_data["metrics"][metric_type].update({
                        "start_weight": metric_data.get("start_weight"),
                        "end_weight": metric_data.get("end_weight"),
                        "weight_change": metric_data.get("weight_change")
                    })
        
        # Формуємо текст для аналізу
        data_comp = analysis_data['data_completeness']
        formatted_text = f"""
Аналіз фітнес статистики користувача

ПЕРІОД: {analysis_data['period']['type']} ({analysis_data['period']['start']} - {analysis_data['period']['end']})

ПРОФІЛЬ КОРИСТУВАЧА:
- Ціль тренувань: {analysis_data['user_profile']['training_goal']}

ЗАГАЛЬНА ІНФОРМАЦІЯ:
- Кількість тренувань: {analysis_data['summary']['total_training_sessions']}
- Кількість ранкових квізів: {analysis_data['summary']['total_morning_quizzes']}

ПОВНОТА ДАНИХ:
- Очікувана кількість днів: {data_comp['expected_days']}
- Заповнено днів: {data_comp['filled_days']}
- Пропущено днів: {data_comp['missing_days']}
- Відсоток заповнення: {data_comp['completion_percentage']}%
- Є пропуски даних: {'ТАК' if data_comp['has_missing_data'] else 'НІ'}

ДЕТАЛЬНІ МЕТРИКИ:
"""
        
        for metric_name, metric_data in analysis_data["metrics"].items():
            metric_title = {
                "stress_data": "РІВЕНЬ СТРЕСУ",
                "warehouse_data": "СКЛАДНІСТЬ ТРЕНУВАНЬ", 
                "sleep_data": "ЯКІСТЬ СНУ",
                "wellbeing_data": "ЗАГАЛЬНЕ САМОПОЧУТТЯ",
                "weight_data": "ДИНАМІКА ВАГИ"
            }.get(metric_name, metric_name.upper())
            
            formatted_text += f"\n{metric_title}:\n"
            formatted_text += f"- Середнє значення: {metric_data.get('average')}\n"
            formatted_text += f"- Тренд: {metric_data.get('trend')}\n"
            formatted_text += f"- Кількість замірів: {metric_data.get('data_points_count')}\n"
            
            if metric_name == "sleep_data":
                formatted_text += f"- Загальні години сну: {metric_data.get('total_sleep_hours')}\n"
            elif metric_name == "weight_data":
                formatted_text += f"- Початкова вага: {metric_data.get('start_weight')} кг\n"
                formatted_text += f"- Кінцева вага: {metric_data.get('end_weight')} кг\n"
                formatted_text += f"- Зміна ваги: {metric_data.get('weight_change')} кг\n"
            
            # Додаємо останні 5 точок даних для контексту
            data_points = metric_data.get('data_points', [])
            if data_points:
                formatted_text += "- Останні заміри:\n"
                for point in data_points[-5:]:
                    formatted_text += f"  * {point.get('date')}: {point.get('value')}\n"
        
        formatted_text += "\nБудь ласка, проведи детальний аналіз цих даних, виділи ключові тренди, досягнення та рекомендації для покращення результатів."
        
        return formatted_text
    
    async def get_analysis(self, stats_data: Dict[str, Any]) -> Optional[str]:
        """Отримання аналізу від OpenAI Chat Completions API"""
        
        try:
            # Форматуємо дані для аналізу
            formatted_stats = self.format_statistics_for_analysis(stats_data)
            
            logger.info(f"Відправляємо статистику на аналіз до OpenAI Chat Completions API з моделлю {self.model}")
            
            # Створюємо запит до Chat Completions API
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_instruction},
                    {"role": "user", "content": formatted_stats}
                ],
                temperature=0.5
            )
            
            # Отримуємо відповідь
            if response.choices and len(response.choices) > 0:
                analysis_text = response.choices[0].message.content
                if analysis_text:
                    logger.info("Аналіз успішно отримано від OpenAI Chat Completions API")
                    return analysis_text.strip()
                else:
                    logger.warning("Відповідь від Chat Completions API порожня")
            else:
                logger.warning("Немає choices у відповіді від Chat Completions API")
                
        except Exception as e:
            logger.error(f"Помилка при отриманні аналізу від OpenAI Chat Completions API: {e}")
            
        return None
    
    async def analyze_statistics(self, user_statistics) -> bool:
        """Аналіз статистики та збереження результату"""
        
        try:
            # Отримуємо дані користувача для включення цілі тренування
            from app.db.models import User
            user = await User.find_one(User.telegram_id == user_statistics.user_id)
            training_goal = user.training_goal.value if user and user.training_goal else "Підтримка форми"
            
            # Конвертуємо статистику в словник
            stats_dict = {
                "period_type": user_statistics.period_type.value,
                "period_start": user_statistics.period_start.isoformat(),
                "period_end": user_statistics.period_end.isoformat(),
                "training_goal": training_goal,
                "total_training_sessions": user_statistics.total_training_sessions,
                "total_morning_quizzes": user_statistics.total_morning_quizzes,
                "stress_data": user_statistics.stress_data,
                "warehouse_data": user_statistics.warehouse_data,
                "sleep_data": user_statistics.sleep_data,
                "wellbeing_data": user_statistics.wellbeing_data,
                "weight_data": user_statistics.weight_data
            }
            
            # Отримуємо аналіз
            analysis = await self.get_analysis(stats_dict)
            
            if analysis:
                # Очищаємо та валідуємо HTML
                analysis = self._clean_html(analysis)
                
                # Зберігаємо аналіз в базі даних
                user_statistics.ai_analysis = analysis
                user_statistics.ai_analysis_generated_at = datetime.now()
                await user_statistics.save()
                
                logger.info(f"AI аналіз збережено для користувача {user_statistics.user_id}")
                return True
            else:
                logger.warning("Не вдалося отримати аналіз від OpenAI Chat Completions API")
                return False
                
        except Exception as e:
            logger.error(f"Помилка при аналізі статистики: {e}")
            return False
    
    def _clean_html(self, text: str) -> str:
        """Очищення та валідація HTML для Telegram"""
        import re
        
        # Видаляємо заборонені теги
        text = re.sub(r'<br[^>]*>', '', text, flags=re.IGNORECASE)
        text = re.sub(r'<h[1-6][^>]*>', '', text, flags=re.IGNORECASE)
        text = re.sub(r'</h[1-6]>', '', text, flags=re.IGNORECASE)
        text = re.sub(r'```html', '', text)
        text = re.sub(r'```', '', text)
        text = re.sub(r'---', '', text)
        
        # Перевіряємо парність тегів
        open_tags = []
        clean_text = ""
        i = 0
        
        while i < len(text):
            if text[i] == '<':
                # Знаходимо кінець тегу
                tag_end = text.find('>', i)
                if tag_end == -1:
                    clean_text += text[i]
                    i += 1
                    continue
                    
                tag = text[i:tag_end + 1]
                
                # Перевіряємо чи це відкриваючий тег
                if not tag.startswith('</') and tag not in ['<b>', '<i>', '<blockquote>']:
                    # Пропускаємо заборонений тег
                    i = tag_end + 1
                    continue
                elif tag.startswith('</'):
                    # Закриваючий тег
                    close_tag = tag[2:-1]  # Видаляємо </ і >
                    if open_tags and open_tags[-1] == close_tag:
                        open_tags.pop()
                        clean_text += tag
                    # Інакше пропускаємо незбалансований закриваючий тег
                else:
                    # Відкриваючий тег
                    tag_name = tag[1:-1]
                    open_tags.append(tag_name)
                    clean_text += tag
                    
                i = tag_end + 1
            else:
                clean_text += text[i]
                i += 1
        
        # Закриваємо всі незакриті теги
        while open_tags:
            tag = open_tags.pop()
            if tag in ['b', 'i', 'blockquote']:
                clean_text += f'</{tag}>'
        
        return clean_text
