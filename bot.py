import os

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'meetup_bot_config.settings')
django.setup()

from environs import Env, EnvError
from telegram.ext import (CallbackQueryHandler, CommandHandler,
                          ConversationHandler, Filters, MessageHandler,
                          PreCheckoutQueryHandler, Updater)

from bot_utils import set_bot_menu_commands
from handlers import (CHOOSE_ROLE, EVENT_CHOICE_CALLBACK_PREFIX,
                      MANAGE_SPEAKERS_CHOOSE_EVENT,
                      PS_TYPING_NAME, PS_TYPING_CONTACT, PS_TYPING_NOTES,
                      MANAGE_SPEAKERS_CHOOSE_SPEAKER,
                      MANAGE_SPEAKERS_SESSION_DETAILS, ROLE_GUEST_CALLBACK,
                      ROLE_ORGANIZER_CALLBACK, ROLE_SPEAKER_CALLBACK,
                      SPEAKER_CHOICE_CALLBACK_PREFIX,
                      TYPING_ORGANIZER_PASSWORD, ask_question,
                      cancel_conversation, donate, handle_event_choice,
                      handle_guest_choice, handle_organizer_choice_init,
                      handle_organizer_password, handle_speaker_choice,
                      handle_speaker_selection, help_command,
                      manage_speakers_back_to_event_choice,
                      manage_speakers_cancel_conversation,
                      manage_speakers_start, precheckout_callback,
                      show_schedule, start_command_handler,
                      successful_payment_callback, handle_session_details_input,
                      ps_cancel_add_speaker, add_prospective_speaker_start,
                      ps_handle_name,
                      ps_handle_contact,
                      ps_handle_notes_and_save, ps_skip_notes_and_save,
                      )


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
            MANAGE_SPEAKERS_SESSION_DETAILS: [
                MessageHandler(Filters.text & ~Filters.command, handle_session_details_input),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(manage_speakers_cancel_conversation, pattern='^manage_speakers_cancel$'),
            CommandHandler('cancel', cancel_conversation)
        ],
        # per_user=True,
        # per_chat=False
        allow_reentry=True
    )

    add_prospective_speaker_conv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(Filters.regex(r'^\s*Добавить в резерв\s*$'), add_prospective_speaker_start)
        ],
        states={
            PS_TYPING_NAME: [
                MessageHandler(Filters.text & ~Filters.command, ps_handle_name)
            ],
            PS_TYPING_CONTACT: [
                MessageHandler(Filters.text & ~Filters.command, ps_handle_contact)
            ],
            PS_TYPING_NOTES: [
                CommandHandler('skip_notes', ps_skip_notes_and_save),
                MessageHandler(Filters.text & ~Filters.command, ps_handle_notes_and_save),
            ],
        },
        fallbacks=[
            CommandHandler('cancel_add_speaker', ps_cancel_add_speaker),

        ],
        allow_reentry=True
    )

    dispatcher.add_handler(role_conversation_handler)
    dispatcher.add_handler(manage_speakers_conv_handler)
    dispatcher.add_handler(add_prospective_speaker_conv_handler)

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
