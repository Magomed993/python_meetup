import json

def load_schedule_from_file(file_path='dummy_schedule.json'):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            schedule_list = json.load(file)
        return schedule_list
    except FileNotFoundError:
        print(f"Ошибка: Файл расписания {file_path} не найден.")
        return []