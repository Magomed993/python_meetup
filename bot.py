import os
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

    updater.start_polling()
    print("Бот запущен и ожидает сообщений...")

    updater.idle()

if __name__ == '__main__':
    main()