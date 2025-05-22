import os
from typing import ContextManager

import django
from environs import Env, EnvError
from telegram.ext import (CommandHandler, Updater, PreCheckoutQueryHandler, MessageHandler, Filters)

from handlers import (ask_question, show_schedule,
                      start, donate, precheckout_callback, successful_payment_callback)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'meetup_bot_config.settings')
django.setup()


def main():
    """Запускает бота."""
    env = Env()
    env.read_env()

    try:
        bot_token = env.str('TELEGRAM_TOKEN')
        provider_token = env.str('TELEGRAM_PROVIDER_TOKEN')
    except EnvError as e:
        print(f'В bot.py не удалось прочитать TELEGRAM_TOKEN или TELEGRAM_PROVIDER_TOKEN. Ошибка {e}')
        return

    updater = Updater(bot_token, use_context=True)

    dispatcher = updater.dispatcher

    dispatcher.bot_data['provider_token'] = provider_token

    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(CommandHandler('schedule', show_schedule))
    dispatcher.add_handler(CommandHandler('ask', ask_question))
    dispatcher.add_handler(CommandHandler('donate', donate))

    dispatcher.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    dispatcher.add_handler(MessageHandler(Filters.successful_payment,
                                          successful_payment_callback
                                          )
                           )
    updater.start_polling()
    print('Бот запущен и ожидает сообщений...')

    updater.idle()


if __name__ == '__main__':
    main()
