"""
Інтеграція з OpenAI Assistant для аналізу статистики
"""

import asyncio
from datetime import datetime
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

# Імпорт OpenAI буде додано після встановлення пакету
try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI пакет не встановлено. Встановіть: pip install openai")

# Конфігурація - додайте ці змінні у ваш .env файл
OPENAI_API_KEY = "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"  # Замініть на ваш API ключ
OPENAI_ASSISTANT_ID = "asst_kofjAVUVCR3kr7qV0NzJpfPS"  # Замініть на ID вашого асистента


class StatisticsAnalyzer:
    """Клас для аналізу статистики через OpenAI Assistant"""
    
    def __init__(self, api_key: str = None, assistant_id: str = None):
        if not OPENAI_AVAILABLE:
            raise ImportError("OpenAI пакет не встановлено. Встановіть: pip install openai")
            
        self.api_key = api_key or OPENAI_API_KEY
        self.assistant_id = assistant_id or OPENAI_ASSISTANT_ID
        
        if not self.api_key or not self.assistant_id:
            raise ValueError("Необхідно вказати OPENAI_API_KEY та OPENAI_ASSISTANT_ID")
            
        self.client = AsyncOpenAI(api_key=self.api_key)
    
    def format_statistics_for_analysis(self, stats_data: Dict[str, Any]) -> str:
        """Форматування статистики для передачі асистенту"""
        
        analysis_data = {
            "period": {
                "type": stats_data.get("period_type"),
                "start": stats_data.get("period_start"),
                "end": stats_data.get("period_end")
            },
            "summary": {
                "total_training_sessions": stats_data.get("total_training_sessions", 0),
                "total_morning_quizzes": stats_data.get("total_morning_quizzes", 0)
            },
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
        formatted_text = f"""
Аналіз фітнес статистики користувача

ПЕРІОД: {analysis_data['period']['type']} ({analysis_data['period']['start']} - {analysis_data['period']['end']})

ЗАГАЛЬНА ІНФОРМАЦІЯ:
- Кількість тренувань: {analysis_data['summary']['total_training_sessions']}
- Кількість ранкових квізів: {analysis_data['summary']['total_morning_quizzes']}

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
        """Отримання аналізу від OpenAI Assistant"""
        
        try:
            # Форматуємо дані для аналізу
            formatted_stats = self.format_statistics_for_analysis(stats_data)
            
            logger.info(f"Відправляємо статистику на аналіз до Assistant {self.assistant_id}")
            
            # Створюємо thread
            thread = await self.client.beta.threads.create()
            
            # Додаємо повідомлення з даними
            await self.client.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content=formatted_stats
            )
            
            # Запускаємо асистента
            run = await self.client.beta.threads.runs.create(
                thread_id=thread.id,
                assistant_id=self.assistant_id
            )
            
            # Чекаємо завершення
            while run.status in ['queued', 'in_progress', 'cancelling']:
                await asyncio.sleep(2)
                run = await self.client.beta.threads.runs.retrieve(
                    thread_id=thread.id,
                    run_id=run.id
                )
            
            if run.status == 'completed':
                # Отримуємо відповідь
                messages = await self.client.beta.threads.messages.list(
                    thread_id=thread.id
                )
                
                # Знаходимо останнє повідомлення від асистента
                for message in messages.data:
                    if message.role == "assistant":
                        analysis_text = ""
                        for content in message.content:
                            if content.type == "text":
                                analysis_text += content.text.value
                        
                        logger.info("Аналіз успішно отримано від OpenAI Assistant")
                        return analysis_text
                        
            else:
                logger.error(f"Помилка виконання Assistant run: {run.status}")
                if hasattr(run, 'last_error'):
                    logger.error(f"Деталі помилки: {run.last_error}")
                
        except Exception as e:
            logger.error(f"Помилка при отриманні аналізу від OpenAI Assistant: {e}")
            
        return None
    
    async def analyze_statistics(self, user_statistics) -> bool:
        """Аналіз статистики та збереження результату"""
        
        try:
            # Конвертуємо статистику в словник
            stats_dict = {
                "period_type": user_statistics.period_type.value,
                "period_start": user_statistics.period_start.isoformat(),
                "period_end": user_statistics.period_end.isoformat(),
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
                # Зберігаємо аналіз в базі даних
                user_statistics.ai_analysis = analysis
                user_statistics.ai_analysis_generated_at = datetime.now()
                await user_statistics.save()
                
                logger.info(f"AI аналіз збережено для користувача {user_statistics.user_id}")
                return True
            else:
                logger.warning("Не вдалося отримати аналіз від OpenAI Assistant")
                return False
                
        except Exception as e:
            logger.error(f"Помилка при аналізі статистики: {e}")
            return False
