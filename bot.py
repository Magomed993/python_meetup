import os
import json
import django

from telegram import Update, Bot
from environs import Env, EnvError
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'meetup_bot_config.settings')
django.setup()


def start(update: Update, context: CallbackContext):
    """Отправляет приветственное сообщение при команде /start."""
    user = update.effective_user
    welcome_message = (
        f"Привет, {user.first_name}!\n\n"
        "Я бот для PythonMeetup. Здесь ты сможешь:\n"
        "- Узнать программу мероприятия (/schedule)\n"
        "- Задать вопрос текущему докладчику (/ask)\n"
        # "- Познакомиться с другими участниками (скоро)\n"
        # "- Поддержать организаторов (скоро)\n\n"
        "Пока это основное. Приятного митапа!"
    )
    update.message.reply_text(welcome_message)
    print(f"Пользователь "
          f"{user.id} ({user.username or user.first_name})"
          f" запустил бота."
    )

def load_schedule_from_file(file_path='dummy_schedule.json'):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            schedule_list = json.load(file)
        return schedule_list
    except FileNotFoundError:
        print(f"Ошибка: Файл расписания {file_path} не найден.")
        return []

def show_schedule(update:Update, context: CallbackContext):
    """Отправляет пользователю программу мероприятия, загруженную из файла."""
    loaded_schedule = load_schedule_from_file()

    if not loaded_schedule:
        reply_text = "К сожалению, программа мероприятия пока не загружена или возникла ошибка при её чтении. Попробуйте позже."
        update.message.reply_text(reply_text)
        return

    schedule_entries = ["Программа мероприятия:\n"]
    for entry_details in loaded_schedule:
        speaker = entry_details.get("speaker_name", "Не указан")
        title = entry_details.get("talk_title", "Без названия")
        start = entry_details.get("start_time", "Время не указано")
        end = entry_details.get("end_time", "Время не указано")

        schedule_entries.append(
            f"Время доклада : {start} - {end}\n"
            f"Имя докладчика: {speaker}\n"
            f"Тема: {title}\n"
            "----------------------------------"
        )
    full_schedule_text = "\n".join(schedule_entries)
    update.message.reply_text(full_schedule_text)

def main():
    """Запускает бота."""
    env = Env()
    env.read_env()

    try:
        bot_token = env.str('TELEGRAM_TOKEN')
    except EnvError as e:
        print(f'В bot.py не удалось прочитать TELEGRAM_TOKEN. Ошибка {e}')
        return

    updater = Updater(bot_token, use_context=True)


    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(CommandHandler('schedule', show_schedule))

    updater.start_polling()
    print("Бот запущен и ожидает сообщений...")

    updater.idle()

if __name__ == '__main__':
    main()