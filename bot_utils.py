import json
from smtpd import program


def load_schedule_from_json(file_path='dummy_schedule.json'):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            program_records = json.load(file)
        return program_records
    except FileNotFoundError:
        print(f"Ошибка: Файл расписания {file_path} не найден.")
        return []
    except json.JSONDecodeError:
        print(f"Ошибка: Некорректный формат JSON в файле '{file_path}'. Проверьте содержимое.")
        return []


def get_full_schedule():
    """Возвращает полное расписание мероприятия."""
    program_content = load_schedule_from_json()

    return program_content