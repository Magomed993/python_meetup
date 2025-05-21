from telegram import Update
from telegram.ext import CallbackContext

from bot_utils import load_schedule_from_file


def start(update: Update, context:
CallbackContext):
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