#!/usr/bin/env python3
"""
Скрипт для парсингу HTML таблиці з часовими поясами країн.
Офсети розраховуються відносно Києва (UTC+2).
"""

from bs4 import BeautifulSoup
import re

# Київ знаходиться в UTC+2
KYIV_UTC_OFFSET = 2

def parse_utc_offset(utc_string):
    """
    Парсить рядок типу "UTC+2", "UTC-5", "UTC+5:30" і повертає числове значення офсету.
    """
    # Видаляємо всі зайві символи і залишаємо тільки UTC та офсет
    match = re.search(r'UTC([+-]?\d+(?:[.:]\d+)?)', utc_string)
    if not match:
        return None
    
    offset_str = match.group(1)
    
    # Обробляємо випадки з двокрапкою або крапкою (наприклад, +5:30 або +5.30)
    if ':' in offset_str or '.' in offset_str:
        # Замінюємо двокрапку на крапку для правильного парсингу
        offset_str = offset_str.replace(':', '.')
        return float(offset_str)
    else:
        return float(offset_str)


def calculate_kyiv_offset(utc_offset):
    """
    Розраховує офсет відносно Києва.
    Київ знаходиться в UTC+2, тому:
    - Якщо країна в UTC+4, то офсет від Києва = +4 - (+2) = +2
    - Якщо країна в UTC-5, то офсет від Києва = -5 - (+2) = -7
    """
    if utc_offset is None:
        return 0
    
    return utc_offset - KYIV_UTC_OFFSET


def parse_html_timezones(html_file_path):
    """
    Парсить HTML файл з таблицею часових поясів.
    Для країн з кількома часовими поясами створює окремі записи.
    """
    with open(html_file_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Знаходимо всі рядки таблиці
    rows = soup.find_all('tr')
    
    countries_data = []
    
    for row in rows:
        cells = row.find_all('td')
        
        # Пропускаємо рядки без достатньої кількості комірок
        if len(cells) < 3:
            continue
        
        # Перша комірка - назва країни
        country_cell = cells[0]
        country_link = country_cell.find('a', title=True)
        
        if not country_link:
            continue
        
        country_name = country_link.get('title', '').strip()
        
        # Друга комірка - кількість часових поясів
        try:
            num_timezones = int(cells[1].get_text().strip())
        except ValueError:
            continue
        
        # Третя комірка - список часових поясів
        timezones_cell = cells[2]
        
        # Розбиваємо за <br> тегами для окремих часових поясів
        # Замінюємо <br> на \n і парсимо кожен рядок
        for br in timezones_cell.find_all('br'):
            br.replace_with('\n')
        
        timezone_text = timezones_cell.get_text()
        lines = [line.strip() for line in timezone_text.split('\n') if line.strip()]
        
        # Шукаємо всі UTC зони в тексті
        utc_pattern = re.compile(r'(UTC[+-]?\d+(?:[.:]\d+)?)')
        
        # Парсимо кожну лінію з UTC окремо
        for line in lines:
            utc_match = utc_pattern.search(line)
            if not utc_match:
                continue
            
            utc_string = utc_match.group(1)
            utc_offset = parse_utc_offset(utc_string)
            
            if utc_offset is None:
                continue
            
            kyiv_offset = calculate_kyiv_offset(utc_offset)
            
            # Витягуємо опис регіону (текст після " — ")
            region_info = ""
            if ' — ' in line:
                parts = line.split(' — ', 1)
                if len(parts) > 1:
                    region_info = parts[1].strip()
                    # Видаляємо всі UTC зони з опису
                    region_info = utc_pattern.sub('', region_info).strip()
                    # Обрізаємо до 60 символів для читабельності
                    if len(region_info) > 60:
                        region_info = region_info[:57] + "..."
            
            # Якщо опису немає
            if not region_info:
                if num_timezones == 1:
                    region_info = country_name
                else:
                    # Витягуємо перше слово після UTC
                    rest_of_line = line.replace(utc_string, '').strip()
                    if rest_of_line:
                        region_info = rest_of_line[:60]
                    else:
                        region_info = f"zone {utc_string}"
            
            # Якщо це просто "на всій території" для країни з одним поясом
            if region_info == "на всій території" and num_timezones == 1:
                region_info = country_name
            
            # Округлюємо офсет до цілого числа
            kyiv_offset_int = round(kyiv_offset)
            
            # Форматуємо офсет для відображення
            if kyiv_offset_int >= 0:
                offset_display = f"+{kyiv_offset_int}"
            else:
                offset_display = f"{kyiv_offset_int}"
            
            name_display = f"{country_name} ({region_info}, {offset_display} h)"
            
            # country поле = унікальний ідентифікатор для БД
            # Для країн з одним поясом - просто назва країни
            # Для країн з кількома поясами - "Країна (регіон)"
            if num_timezones > 1:
                country_id = f"{country_name} ({region_info})"
            else:
                country_id = country_name
            
            countries_data.append({
                'name': name_display,
                'country': country_id,
                'offset': kyiv_offset_int
            })
    
    return countries_data


def format_output(countries_data):
    """
    Форматує дані у вигляді Python списку словників.
    """
    output = "COUNTRIES_WITH_TIMEZONES = [\n"
    
    for country in countries_data:
        output += f"    {country},\n"
    
    output += "]\n"
    
    return output


if __name__ == "__main__":
    html_file = "timezones_list.html"
    
    print(f"Парсинг файлу {html_file}...")
    
    countries = parse_html_timezones(html_file)
    
    print(f"Знайдено {len(countries)} країн")
    
    # Виводимо результат
    output = format_output(countries)
    
    # Зберігаємо у файл
    output_file = "parsed_timezones_output.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(output)
    
    print(f"\nРезультат збережено у файл: {output_file}")
    
    # Виводимо перші кілька записів для перевірки
    print("\nПерші 10 записів:")
    print(output.split('\n')[0])  # COUNTRIES_WITH_TIMEZONES = [
    for line in output.split('\n')[1:11]:
        print(line)
