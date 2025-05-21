import json
from datetime import datetime


def load_schedule_from_json(file_path='dummy_schedule.json'):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            program_records = json.load(file)
        return program_records
    except FileNotFoundError:
        print(f'Ошибка: Файл расписания {file_path} не найден.')
        return []
    except json.JSONDecodeError:
        print(f'Ошибка: Некорректный формат JSON в файле \"{file_path}\". Проверьте содержимое.')
        return []


def get_full_schedule():
    """Возвращает полное расписание мероприятия."""
    program_content = load_schedule_from_json()

    return program_content


def get_current_talk_details():
    """Определяет текущий активный доклад на основе системного времени.
     Возвращает словарь с деталями доклада или None, если активного доклада нет."""

    full_program = get_full_schedule()

    if not full_program:
        return None

    current_time_obj = datetime.now().time()

    for talk_entry in full_program:
        start_time_str = talk_entry.get('start_time')
        end_time_str = talk_entry.get('end_time')

        if not start_time_str or not end_time_str:
            print(
                f'Предупреждение: Для доклада \"{talk_entry.get("talk_title", "N/A")}\" '
                f'не указано время начала или окончания.')
            continue

        try:
            talk_start_time = datetime.strptime(start_time_str, '%H:%M').time()
            talk_end_time = datetime.strptime(end_time_str, '%H:%M').time()

            if talk_start_time <= current_time_obj < talk_end_time:
                return talk_entry
        except ValueError:
            print(f'Ошибка парсинга времени для доклада: \"{talk_entry.get("talk_title", "N/A")}\". '
                  f'Ожидался формат ЧЧ:ММ, получено: start=\"{start_time_str}\", end=\"{end_time_str}\".')
            continue

    return None
