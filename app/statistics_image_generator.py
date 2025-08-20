import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import io
from datetime import datetime
import os
from PIL import Image, ImageDraw, ImageFont
from app.db.models import UserStatistics, PeriodType
import matplotlib
matplotlib.use('Agg')  # Використовуємо Agg бекенд для роботи без GUI
import logging

logger = logging.getLogger(__name__)


class StatisticsImageGenerator:
    """Генератор зображень для статистики користувача"""
    
    def __init__(self):
        self.colors = {
            'stress': '#EFD02E',        # жовтий для стресу
            'complexity': '#FF0C0C',    # червоний для складності
            'sleep': '#A467DF',         # фіолетовий для сну
            'feeling': '#1EB336',       # зелений для самопочуття
            'weight': '#00BCEB'         # блакитний для ваги
        }
        
        # Створення директорії для зображень, якщо вона не існує
        self.images_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'statistics_images')
        os.makedirs(self.images_dir, exist_ok=True)
        
        # Налаштування шляху до шрифтів
        # Будемо використовувати вбудований шрифт matplotlib
        self.font_path = matplotlib.font_manager.findfont('DejaVu Sans')
            
    async def generate_and_save_statistics_image(self, stats: UserStatistics) -> str:
        """Генерує і зберігає зображення зі статистикою користувача"""
        try:
            # Формування імені файлу: user_id_period_type_date.png
            period_text = "weekly" if stats.period_type == PeriodType.WEEKLY else "monthly"
            
            # Перевіряємо, чи period_end вже є об'єктом datetime
            period_end = stats.period_end
            if isinstance(period_end, str):
                period_end = datetime.fromisoformat(period_end)
            
            filename = f"{stats.user_id}_{period_text}_{period_end.strftime('%Y%m%d')}.png"
            file_path = os.path.join(self.images_dir, filename)
            
            # Генерація зображення
            img_bytes = await self._generate_statistics_image(stats)
            
            # Збереження зображення у файл
            with open(file_path, 'wb') as f:
                f.write(img_bytes)
            
            logger.info(f"Збережено зображення статистики для користувача {stats.user_id}: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"Помилка при генерації зображення статистики: {e}")
            return None
            
    async def _generate_statistics_image(self, stats: UserStatistics) -> bytes:
        """Генерує зображення зі статистикою користувача"""
        try:
            # Створюємо основне зображення з блакитним фоном
            width, height = 800, 1200
            background_color = (158, 209, 229)  # Блакитний колір
            
            img = Image.new('RGB', (width, height), background_color)
            draw = ImageDraw.Draw(img)
            
            # Підготовка даних для графіків
            dates = []
            stress_values = []
            complexity_values = []
            sleep_values = []
            feeling_values = []
            weight_values = []
            
            # Отримуємо дані із статистики для кожного графіка
            
            # Дані про стрес
            if stats.stress_data and 'data_points' in stats.stress_data:
                for point in stats.stress_data['data_points']:
                    if 'raw_date' in point and 'value' in point:
                        date = datetime.fromisoformat(point['raw_date']) if isinstance(point['raw_date'], str) else point['raw_date']
                        dates.append(date)
                        stress_values.append(point['value'])
            
            # Дані про складність тренувань
            if stats.warehouse_data and 'data_points' in stats.warehouse_data:
                for i, point in enumerate(stats.warehouse_data['data_points']):
                    if 'raw_date' in point and 'value' in point:
                        date = datetime.fromisoformat(point['raw_date']) if isinstance(point['raw_date'], str) else point['raw_date']
                        if i >= len(dates):
                            dates.append(date)
                            complexity_values.append(point['value'])
                        elif date == dates[i]:
                            complexity_values.append(point['value'])
                        else:
                            # Знаходимо відповідний індекс або додаємо нову дату
                            if date in dates:
                                idx = dates.index(date)
                                while len(complexity_values) <= idx:
                                    complexity_values.append(None)
                                complexity_values[idx] = point['value']
                            else:
                                dates.append(date)
                                complexity_values.append(point['value'])
            
            # Дані про сон
            if stats.sleep_data and 'data_points' in stats.sleep_data:
                for point in stats.sleep_data['data_points']:
                    if 'raw_date' in point and 'value' in point:
                        date = datetime.fromisoformat(point['raw_date']) if isinstance(point['raw_date'], str) else point['raw_date']
                        if date not in dates:
                            dates.append(date)
                        idx = dates.index(date)
                        while len(sleep_values) <= idx:
                            sleep_values.append(None)
                        sleep_values[idx] = point['value']
            
            # Дані про самопочуття
            if stats.wellbeing_data and 'data_points' in stats.wellbeing_data:
                for point in stats.wellbeing_data['data_points']:
                    if 'raw_date' in point and 'value' in point:
                        date = datetime.fromisoformat(point['raw_date']) if isinstance(point['raw_date'], str) else point['raw_date']
                        if date not in dates:
                            dates.append(date)
                        idx = dates.index(date)
                        while len(feeling_values) <= idx:
                            feeling_values.append(None)
                        feeling_values[idx] = point['value']
            
            # Дані про вагу
            if stats.weight_data and 'data_points' in stats.weight_data:
                for point in stats.weight_data['data_points']:
                    if 'raw_date' in point and 'value' in point:
                        date = datetime.fromisoformat(point['raw_date']) if isinstance(point['raw_date'], str) else point['raw_date']
                        if date not in dates:
                            dates.append(date)
                        idx = dates.index(date)
                        while len(weight_values) <= idx:
                            weight_values.append(None)
                        weight_values[idx] = point['value']
            
            # Сортуємо дати і відповідні значення
            if dates:
                sorted_indices = sorted(range(len(dates)), key=lambda i: dates[i])
                dates = [dates[i] for i in sorted_indices]
                
                # Сортуємо також значення для всіх показників
                if stress_values:
                    stress_values = [stress_values[i] if i < len(stress_values) else None for i in sorted_indices]
                if complexity_values:
                    complexity_values = [complexity_values[i] if i < len(complexity_values) else None for i in sorted_indices]
                if sleep_values:
                    sleep_values = [sleep_values[i] if i < len(sleep_values) else None for i in sorted_indices]
                if feeling_values:
                    feeling_values = [feeling_values[i] if i < len(feeling_values) else None for i in sorted_indices]
                if weight_values:
                    weight_values = [weight_values[i] if i < len(weight_values) else None for i in sorted_indices]
            
            # Визначаємо розміри графіків
            chart_height = 260
            
            # Перевіряємо, чи є дані для графіків
            if not dates or len(dates) == 0:
                logger.warning(f"Немає даних для графіків статистики користувача {stats.user_id}")
                
                # Створюємо зображення з повідомленням про відсутність даних
                font = ImageFont.truetype(self.font_path, 36)
                draw.text((width // 2 - 150, height // 2), "Немає даних", font=font, fill=(0, 0, 0))
                
                buffer = io.BytesIO()
                img.save(buffer, format='PNG')
                buffer.seek(0)
                
                return buffer.getvalue()
            
            # Створюємо 5 графіків
            charts = []
            
            # 1. Графік стресу (верхній лівий)
            stress_chart = self._create_line_chart(dates, stress_values, 'СТРЕС', 
                                             self.colors['stress'], fill=False, y_range=(0, 10))
            charts.append(stress_chart)
            
            # 2. Графік складності (верхній правий)
            complexity_chart = self._create_line_chart(dates, complexity_values, 'СКЛАДНІСТЬ', 
                                             self.colors['complexity'], fill=True, y_range=(0, 10))
            charts.append(complexity_chart)
            
            # 3. Графік сну (середній лівий)
            sleep_chart = self._create_bar_chart(dates, sleep_values, 'СОН', 
                                            self.colors['sleep'], y_range=(0, 12))
            charts.append(sleep_chart)
            
            # 4. Графік самопочуття (середній правий)
            feeling_chart = self._create_line_chart(dates, feeling_values, 'САМОПОЧУТТЯ', 
                                             self.colors['feeling'], fill=False, y_range=(0, 10))
            charts.append(feeling_chart)
            
            # 5. Графік ваги (нижній на всю ширину)
            weight_chart = self._create_line_chart(dates, weight_values, 'ВАГА', 
                                              self.colors['weight'], fill=True, 
                                              width=740, height=chart_height)
            
            # Розміщення графіків на основному зображенні
            # Перший ряд (2 графіки)
            if len(charts) >= 1 and stress_chart is not None:
                img.paste(stress_chart, (30, 30))
            if len(charts) >= 2 and complexity_chart is not None:
                img.paste(complexity_chart, (410, 30))
            
            # Другий ряд (2 графіки)
            if len(charts) >= 3 and sleep_chart is not None:
                img.paste(sleep_chart, (30, 310))
            if len(charts) >= 4 and feeling_chart is not None:
                img.paste(feeling_chart, (410, 310))
            
            # Третій ряд (1 графік на всю ширину)
            if weight_chart is not None:
                img.paste(weight_chart, (30, 590))
            
            # Додаємо заголовок
            period_text = "ТИЖНЕВА" if stats.period_type == PeriodType.WEEKLY else "МІСЯЧНА"
            
            # Перевіряємо, чи період вже є об'єктом datetime
            period_start = stats.period_start
            if isinstance(period_start, str):
                period_start = datetime.fromisoformat(period_start)
                
            period_end = stats.period_end
            if isinstance(period_end, str):
                period_end = datetime.fromisoformat(period_end)
            
            period_start_str = period_start.strftime("%d.%m.%Y")
            period_end_str = period_end.strftime("%d.%m.%Y")
            
            title = f"{period_text} СТАТИСТИКА ({period_start_str} - {period_end_str})"
            
            # Добавляем заголовок с помощью PIL
            draw = ImageDraw.Draw(img)
            try:
                font = ImageFont.truetype(self.font_path, 24)
                draw.text((width // 2 - 200, 10), title, font=font, fill=(0, 0, 0))
            except Exception as e:
                logger.error(f"Помилка при додаванні заголовка: {e}")
            
            # Зберігаємо зображення у байтах
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            buffer.seek(0)
            
            return buffer.getvalue()
        except Exception as e:
            logger.error(f"Помилка при генерації зображення статистики: {e}")
            # Створюємо простий заглушку в разі помилки
            img = Image.new('RGB', (400, 300), (255, 255, 255))
            draw = ImageDraw.Draw(img)
            draw.text((10, 10), f"Помилка генерації статистики: {str(e)}", fill=(0, 0, 0))
            
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            buffer.seek(0)
            
            return buffer.getvalue()

    def _create_line_chart(self, dates, values, title, color, fill=False, width=360, height=260, y_range=None):
        """Створює графік лінії"""
        try:
            # Фільтруємо None значення
            valid_dates = []
            valid_values = []
            for d, v in zip(dates, values):
                if v is not None:
                    valid_dates.append(d)
                    valid_values.append(v)
            
            if not valid_dates or len(valid_dates) < 2:
                logger.warning(f"Недостатньо даних для графіка {title}")
                return None
            
            plt.figure(figsize=(width/100, height/100), dpi=100)
            plt.title(title, fontsize=14, fontweight='bold')
            
            # Налаштування вісей
            plt.grid(True, linestyle='--', alpha=0.7)
            if y_range:
                plt.ylim(y_range)
            
            # Малюємо лінію
            plt.plot(valid_dates, valid_values, color=color, linewidth=2.5, marker='o', markersize=5)
            
            # Заповнюємо область під лінією, якщо потрібно
            if fill:
                plt.fill_between(valid_dates, valid_values, alpha=0.3, color=color)
            
            # Форматування дат на осі X
            plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%d.%m'))
            plt.xticks(rotation=45, fontsize=9)
            plt.yticks(fontsize=10)
            
            plt.tight_layout()
            
            # Зберігаємо графік у зображення
            buf = io.BytesIO()
            plt.savefig(buf, format='png')
            plt.close()
            buf.seek(0)
            
            # Конвертуємо в зображення PIL
            chart_img = Image.open(buf)
            return chart_img
        
        except Exception as e:
            logger.error(f"Помилка при створенні лінійного графіка {title}: {e}")
            return None

    def _create_bar_chart(self, dates, values, title, color, width=360, height=260, y_range=None):
        """Створює гістограму"""
        try:
            # Фільтруємо None значення
            valid_dates = []
            valid_values = []
            for d, v in zip(dates, values):
                if v is not None:
                    valid_dates.append(d)
                    valid_values.append(v)
            
            if not valid_dates:
                logger.warning(f"Немає даних для гістограми {title}")
                return None
            
            plt.figure(figsize=(width/100, height/100), dpi=100)
            plt.title(title, fontsize=14, fontweight='bold')
            
            # Налаштування вісей
            plt.grid(True, linestyle='--', alpha=0.7)
            if y_range:
                plt.ylim(y_range)
            
            # Малюємо стовпчики
            plt.bar(valid_dates, valid_values, width=0.6, color=color, alpha=0.7, edgecolor=color, linewidth=1.5)
            
            # Форматування дат на осі X
            plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%d.%m'))
            plt.xticks(rotation=45, fontsize=9)
            plt.yticks(fontsize=10)
            
            plt.tight_layout()
            
            # Зберігаємо графік у зображення
            buf = io.BytesIO()
            plt.savefig(buf, format='png')
            plt.close()
            buf.seek(0)
            
            # Конвертуємо в зображення PIL
            chart_img = Image.open(buf)
            return chart_img
        
        except Exception as e:
            logger.error(f"Помилка при створенні гістограми {title}: {e}")
            return None
