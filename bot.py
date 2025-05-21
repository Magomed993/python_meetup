import os
import django

from environs import Env, EnvError
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

from handlers import start, show_schedule

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'meetup_bot_config.settings')
django.setup()




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