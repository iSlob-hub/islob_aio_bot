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
    "invalid_time": "❌ Невірний формат часу. Введи час у форматі ГГ:ХХ (наприклад, 07:30)",
    "intro_message": "Ласкаво прошу до бота! (Тут має бути якийсь невеличкий опис)\nВкажіть ваше імʼя",
    "start_command": "Привіт! {full_name}!",
    "first_interraction_morning_time_message": "Дякую, {full_name}! Тепер налаштуємо сповіщення. \nВведіть бажаний час для ранкового сповіщення. Його потрібно увести в форматі '08:00'. \nВведіть будь-який зручний час в рамках від 06:00 до 12:00!",
    "training_goal_question": "Яку ціль тренувань ви перед собою встановлюєте?\n\nОберіть одну з наступних опцій:",
    "training_goal_setup_finished": "✅ Чудово! Ваша ціль тренувань: {goal}.\n\n🎉 Налаштування успішно завершено! Тепер ви будете отримувати сповіщення відповідно до ваших уподобань.",
    "menu_command": "🏠 Повертаємось до головного меню...",
    "sorry_issue_happened": "Вибачте, сталася помилка. Спробуйте ще раз.",
    "morning_notification_settings_finished": "Супер! Налаштування завершено! Тепер очікуй від бота сповіщень у вказаний час!",
    "training_menu_button": "🏅 Тренування",
    "start_training_button": "▶️ Почати тренування",
    "back_to_main_menu_button": "↩️ Головне меню",
    "notifications_menu_button": "🔔 Сповіщення",
    "report_problem_button": "❗️ Повідомити про проблему",
    "what_do_with_notifications": "Шо робимо зі сповіщеннями?",
    "describe_problem_prompt": "Опишіть свою проблему у повідомленні",
    "start_quiz_button": "Почати опитування",
    "select_option": "Виберіть опцію:",
    "what_do_with_training": "Шо робимо з тренуваннями?",
    "morning_quiz_already_completed": "Це опитування вже завершено. Спробуй ще раз завтра вранці.",
    "morning_quiz_start": "Розпочинаємо опитування",
    "how_do_you_feel_today": "Як ти почуваєшся сьогодні?",
    "how_much_sleep_last_night": "Скільки годин вдалось поспати минулої ночі?\nВведи число або у форматі ГГ:ХХ (наприклад, 7:30 для 7 годин 30 хвилин)",
    "going_to_train_today": "Чи плануєш ти тренування сьогодні?",
    "what_time_train_today": "О котрій годині ти плануєш тренування?",
    "yes": "Так",
    "no": "Ні",
    "morning_quiz_issue_happened": "❌ Сталась помилка. Не вдалось знайти опитування. Зв'яжіться з адміністратором.",
    "going_to_gym": "✅ Супєр, йдем в зальчік!",
    "not_going_to_gym": "😔 Ладно, може наступного разу.",
    "wrong_format_number_1_10": "❌ Невірний формат. Має бути число від 1 до 10.",
    "your_state_saved": "✅ Твій стан збережено",
    "morning_quiz_step1": "Ти оцінюєш свій стан як: <b>{feeling}</b>\n\n",
    "morning_quiz_step2":  "Твоє самопочуття: {how_do_you_feel_today}\nВдалось поспати <b>{sleep_time} годин</b>.\n\nЧи плануєш ти йти в спортзал сьогодні?",
    "morning_quiz_step31": "Твоє самопочуття: {how_do_you_feel_today}\nВдалось поспати <b>{sleep_time} годин</b>.\nТи плануєш йти в спортзал: <b>Так</b>.\nКоли ти плануєш відвідати спортзал?",
    "morning_quiz_step32": "Твоє самопочуття: {how_do_you_feel_today}\nВдалось поспати <b>{sleep_time} годин</b>.\nТи плануєш йти в спортзал: <b>Ні</b>.\nТепер вкажи свою вагу (в кг):",
    "enter_gym_attendance_time": "❌ Будь ласка, введи час відвідування спортзалу.",
    "morning_quiz_step41": "Твоє самопочуття: {how_do_you_feel_today}\nВдалось поспати <b>{sleep_time} годин</b>.\nТи плануєш йти в спортзал: <b>Так</b>.\nЧас відвідування спортзалу: <b>{gym_attendance_time}</b>.\n\nТепер вкажи свою вагу (в кг):",
    "invalid_weight": "❌ Невірний формат ваги. Має бути число від 30 до 150.",
    "morning_quiz_step5": "Твоє самопочуття: {how_do_you_feel_today}\nВдалось поспати <b>{sleep_time} годин</b>.\nТи плануєш йти в спортзал: <b>{is_going_to_gym}</b>.\n{gym_attendance_time_text}Твоя вага: <b>{weight} кг</b>.\n\nТи красава! Гарного дня!",
    "thanks_for_reporting_problem": "Дякуємо за повідомлення про проблему! Ми обов'язково розглянемо її.",
    # Notifications router templates
    "notif_back_to_main_menu": "Ага, вертаємось до головного меню",
    "back_to_main_menu": "Ага, вертаємось до головного меню",
    "notif_create_new": "Створюємо нове сповіщення. Введіть текст сповіщення.",
    "notif_none": "У вас немає сповіщень.",
    "notif_all": "Це всі ваші сповіщення.",
    "notif_not_found": "Сповіщення не знайдено",
    "choose_days_prompt": "Дні: (оберіть)",
    "status_active": "🟢 Активне",
    "status_disabled": "🔴 Вимкнене",
    "turn_off": "Вимкнути",
    "turn_on": "Увімкнути",
    "button_delete": "Видалити",
    "button_edit": "Редагувати",
    "error_unknown_frequency": "Помилка: невідома частота",
    "edit_saved": "Зміни збережено ✅",
    "edit_saved_text": "✅ Сповіщення оновлено!",
    "notif_enter_text_prompt": "Будь ласка, введи текст сповіщення.",
    "create_summary": "📌 Створення сповіщення:\nТекст: {text}\nОберіть частоту:",
    "notif_saved": "Сповіщення збережено ✅",
    "notif_saved_active": "✅ Сповіщення збережено та активоване!",
    "notif_return_to_menu": "Повертаємось до меню сповіщень",
    "notif_toggle_not_found": "Сповіщення не знайдено",
    "notif_delete_not_found": "Сповіщення не знайдено",
    "notif_deleted": "Сповіщення видалено ✅",
    "edit_start": "Редагування сповіщення:\nПоточний текст: {text}\nВведіть новий текст або залиште поточний:",
    "text_empty": "Текст не може бути порожнім. Введіть новий текст:",
    "edit_choose_frequency": "Оберіть нову частоту для сповіщення:",
    "choose_at_least_one_day": "Оберіть хоча б один день",
    "edit_choose_time": "Введіть новий час у форматі HH:MM:",
    "notif_invalid_time_format": "Будь ласка, введіть час у форматі HH:MM (наприклад, 08:30).",
    "notif_invalid_time_range": "Невірний час. Години мають бути від 00 до 23, хвилини від 00 до 59.",
    # (duplicates removed)
    "status_label": "Статус: {status}",
    "here_summary": "Ось підсумок:",
    "lets_start_training": "Починаємо тренування!",
    "how_do_you_feel_before_training": "Як ти себе почуваєш перед тренуванням?",
    "here_is_your_training_file": "Ось твій тренувальний план на сьогодні.",
    "training_file_unavailable": "Файл тренування недоступний, але ти можеш почати тренування.",
    "start_your_training": "Тренування розпочато! Для завершення - натисни кнопку нижче.",
    "failed_to_send_training_file": "Не вдалося надіслати файл тренування.",
    "finish_training_button": "Завершити тренування",
    "training_not_found": "Тренування не знайдено.",
    "how_hard_was_training": "Супер! Тренування завершено! \nОціни важкість тренування?",
    "do_you_have_any_pain": "Чи відчуваєш ти біль після тренування?",
    "thank_you_for_training": "Дякую за тренування!\nТренування тривало {duration}.\n",
    "do_you_have_soreness": "У тебе є крепатура?",
    "stress_level_prompt": "Оціни свій рівень стресу після тренування (1-10):",
    "thanks_for_your_training_feedback": "Дякую за відповіді! Гарного дня!",
    "morning_quiz_intro": "Ейоу, пора пройти ранкове опитування!",
    "start_morning_quiz_button": "Почати опитування",
    "after_training_quiz_intro": "Ейоу! Пора пройти опитування після тренування вчора!",
    "start_after_training_quiz_button": "Почати опитування",
    "too_long_training_notification": "Тренування триває вже більше 60 хвилин, будь ласка, заверши його, якщо забув.",
    "gym_reminder_notification_text": "🏋️‍♂️ Час для тренування! Не забудь тренувальну сесію."
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