import asyncio
import sys
import os

# Add the project root directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.models import TextTemplate
from beanie import init_beanie
import motor.motor_asyncio
from app.config import settings

# Define all default templates
DEFAULT_TEMPLATES = {
    # Morning quiz templates
    "quiz_already_completed": "Це опитування вже завершено. Спробуй ще раз завтра вранці.",
    "quiz_starting": "Розпочинаємо опитування",
    "how_do_you_feel_today": "Як ти почуваєшся сьогодні?",
    "quiz_error_not_found": "❌ Сталась помилка. Не вдалось знайти опитування. Зв'яжіться з адміністратором.",
    "feeling_invalid_format": "❌ Невірний формат. Має бути число від 1 до 10.",
    "feeling_saved": "✅ Твій стан збережено",
    "feeling_confirmation": "Ти оцінюєш свій стан як: <b>{feeling}</b>\n\n",
    "ask_sleep_hours": "Скільки годин ти спав? \nВведи число або у форматі ГГ:ХХ (наприклад, 7:30 для 7 годин 30 хвилин)",
    "sleep_time_invalid_format": "❌ Невірний формат. Введи число або у форматі ГГ:ХХ (наприклад, 7:30 для 7 годин 30 хвилин)",
    "sleep_gym_question": "Твоє самопочуття: {feeling}\nТи спав <b>{sleep_time} годин</b>.\n\nЧи плануєш ти йти в спортзал сьогодні?",
    "yes_button": "Так",
    "no_button": "Ні",
    "gym_yes_response": "✅ Супєр, йдем в зальчік!",
    "gym_no_response": "✅ Поняв, прийняв, в зал не йдемо.",
    "ask_gym_time": "Твоє самопочуття: {feeling}\nТи спав <b>{sleep_time} годин</b>.\nТи плануєш йти в спортзал: <b>Так</b>.\nКоли ти плануєш відвідати спортзал?",
    "ask_weight_no_gym": "Твоє самопочуття: {feeling}\nТи спав <b>{sleep_time} годин</b>.\nТи плануєш йти в спортзал: <b>Ні</b>.\nТепер вкажи свою вагу (в кг):",
    "gym_time_empty": "❌ Будь ласка, введи час відвідування спортзалу.",
    "gym_time_invalid_format": "❌ Невірний формат часу. Введи час у форматі ГГ:ХХ (наприклад, 14:30 для 2:30 PM)",
    "ask_weight_with_gym": "Твоє самопочуття: {feeling}\nТи спав <b>{sleep_time} годин</b>.\nТи плануєш йти в спортзал: <b>Так</b>.\nЧас відвідування спортзалу: <b>{gym_time}</b>.\n\nТепер вкажи свою вагу (в кг):",
    "weight_invalid_format": "❌ Невірний формат ваги. Введи число.",
    "weight_out_of_range": "❌ Невірний формат ваги. Має бути число від 30 до 150.",
    "quiz_summary": "Твоє самопочуття: {feeling}\nТи спав <b>{sleep_time} годин</b>.\nТи плануєш йти в спортзал: <b>Ні</b>.\nТвоя вага: <b>{weight} кг</b>.\n\nТи красава! Гарного дня!",
    "quiz_summary_with_gym": "Твоє самопочуття: {feeling}\nТи спав <b>{sleep_time} годин</b>.\nТи плануєш йти в спортзал: <b>Так</b>.\nЧас відвідування спортзалу: <b>{gym_time}</b>.\nТвоя вага: <b>{weight} кг</b>.\n\nТи красава! Гарного дня!",
    "gym_reminder_notification_text": "Час тренування: {gym_time}"
}

async def main():
    from app.db.database import init_db
    await init_db()
    
    # Loop through all templates and add them to database
    for key, text in DEFAULT_TEMPLATES.items():
        # Check if template already exists
        existing = await TextTemplate.find_one({"template_key": key})
        if existing:
            print(f"Template '{key}' already exists, skipping...")
            continue
        
        # Create new template
        template = TextTemplate(
            template_key=key,
            template_text=text,
            description=f"Default template for {key}"
        )
        await template.save()
        print(f"Created template: {key}")
    
    print("Template population complete!")

if __name__ == "__main__":
    asyncio.run(main())