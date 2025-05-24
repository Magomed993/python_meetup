import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'meetup_bot_config.settings')
django.setup()

from environs import Env, EnvError
from telegram.ext import (CommandHandler, Updater, PreCheckoutQueryHandler, MessageHandler, Filters,
                          ConversationHandler, CallbackQueryHandler)

from handlers import (ask_question, show_schedule, handle_event_choice, manage_speakers_back_to_event_choice,
                      manage_speakers_cancel_conversation,
                      start_command_handler, donate, precheckout_callback, successful_payment_callback,
                      help_command, CHOOSE_ROLE, TYPING_ORGANIZER_PASSWORD,
                      ROLE_GUEST_CALLBACK, ROLE_SPEAKER_CALLBACK, ROLE_ORGANIZER_CALLBACK,
                      handle_guest_choice, handle_speaker_choice, handle_organizer_choice_init,
                      handle_organizer_password, cancel_conversation,
                      manage_speakers_start,
                      MANAGE_SPEAKERS_CHOOSE_EVENT, MANAGE_SPEAKERS_CHOOSE_SPEAKER, MANAGE_SPEAKERS_SESSION_DETAILS,
                      EVENT_CHOICE_CALLBACK_PREFIX, EVENT_CHOICE_CALLBACK_PREFIX, SPEAKER_CHOICE_CALLBACK_PREFIX,
                      handle_speaker_selection,
                      )
from bot_utils import set_bot_menu_commands


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

    set_bot_menu_commands(updater)

    role_conversation_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start_command_handler)],
        states={
            CHOOSE_ROLE: [
                CallbackQueryHandler(handle_guest_choice, pattern=f"^{ROLE_GUEST_CALLBACK}$"),
                CallbackQueryHandler(handle_speaker_choice, pattern=f"^{ROLE_SPEAKER_CALLBACK}$"),
                CallbackQueryHandler(handle_organizer_choice_init, pattern=f"^{ROLE_ORGANIZER_CALLBACK}$"),
            ],
            TYPING_ORGANIZER_PASSWORD: [
                MessageHandler(Filters.text & ~Filters.command, handle_organizer_password)
            ],
        },
        fallbacks=[
            CommandHandler('cancel', cancel_conversation)
        ],
        allow_reentry=True
    )

    manage_speakers_conv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(Filters.regex(r'^\s*Управление Спикерами\s*$'), manage_speakers_start)
        ],
        states={
            MANAGE_SPEAKERS_CHOOSE_EVENT: [CallbackQueryHandler(handle_event_choice,
                                           pattern=f"^{EVENT_CHOICE_CALLBACK_PREFIX}"),
                                           ],
            MANAGE_SPEAKERS_CHOOSE_SPEAKER: [CallbackQueryHandler(handle_speaker_selection,
                                                                  pattern=f"^{SPEAKER_CHOICE_CALLBACK_PREFIX}"),
                                            CallbackQueryHandler(manage_speakers_back_to_event_choice,
                                                                  pattern='^manage_speakers_back_to_event_choice$'),
                                             ],
            MANAGE_SPEAKERS_SESSION_DETAILS: [ ],
        },
        fallbacks=[
            CallbackQueryHandler(manage_speakers_cancel_conversation, pattern='^manage_speakers_cancel$'),
            CommandHandler('cancel', cancel_conversation)
        ],
        # per_user=True,
        # per_chat=False
        allow_reentry=True
    )

    dispatcher.add_handler(role_conversation_handler)
    dispatcher.add_handler(manage_speakers_conv_handler)

    dispatcher.add_handler(CommandHandler('schedule', show_schedule))
    dispatcher.add_handler(CommandHandler('ask', ask_question))
    dispatcher.add_handler(CommandHandler('donate', donate))
    dispatcher.add_handler(CommandHandler('help', help_command))

    dispatcher.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    dispatcher.add_handler(MessageHandler(Filters.successful_payment,
                                          successful_payment_callback
                                          )
                           )

    dispatcher.add_handler(MessageHandler(Filters.text('Расписание'), show_schedule))
    dispatcher.add_handler(MessageHandler(Filters.text('Поддержать'), donate))
    updater.start_polling()
    print('Бот запущен и ожидает сообщений...')

    updater.idle()


if __name__ == '__main__':
    main()
