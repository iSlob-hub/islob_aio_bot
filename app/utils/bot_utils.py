import re

import datetime


def is_valid_morning_time(time_str: str) -> bool:
    try:
        match = re.match(r"^(0?[0-9]|1[0-9]|2[0-3]):([0-5][0-9])$", time_str)
        min_time = datetime.time(hour=6)
        max_time = datetime.time(hour=12)

        time = datetime.datetime.strptime(time_str, "%H:%M").time()
        if time < min_time or time > max_time:
            return False
        return bool(match)
    except Exception:
        return False


def cron_to_human_readable(cron_expr: str) -> str:
    parts = cron_expr.strip().split()
    if len(parts) != 5:
        return "Невірний розклад"

    minute, hour, dom, month, dow = parts
    time_part = f"{int(hour):02d}:{int(minute):02d}"

    if dow == "*" and dom != "*" and month == "*":
        days = sorted(map(int, dom.split(",")))
        days_str = ", ".join(str(day) for day in days)
        return f"Кожного місяця о {time_part} - {days_str} числа"

    elif dow != "*" and dom == "*" and month == "*":

        dow_map = {
            "0": "Неділя",
            "1": "Понеділок",
            "2": "Вівторок",
            "3": "Середа",
            "4": "Четвер",
            "5": "Пʼятниця",
            "6": "Субота",
        }
        days = [dow_map.get(d, f"день {d}") for d in dow.split(",")]
        return f"Щотижня о {time_part}, у {' та '.join(days)}"

    elif dom == "*" and dow == "*" and month == "*":
        return f"Щодня о {time_part}"

    return f"Спеціальний розклад: {cron_expr}"
