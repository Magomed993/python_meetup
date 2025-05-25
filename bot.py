import os
import django
try:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE',
                          'meetup_bot_config.settings')
    django.setup()
except Exception as e:
    print(e)

from environs import Env, EnvError
from telegram.ext import (
    CommandHandler, Updater, PreCheckoutQueryHandler, MessageHandler, Filters,
    ConversationHandler, CallbackQueryHandler
)
from bot_utils import set_bot_menu_commands
from handlers import (
    ask_question, start, donate, precheckout, successful_payment,
    help, CHOOSE_ROLE, TYPING_ORGANIZER_PASSWORD, ROLE_GUEST_CALLBACK, ROLE_SPEAKER_CALLBACK,
    ROLE_ORGANIZER_CALLBACK, speaker_approval, event_details, programs_button, actual_button,
    guest_choice, speaker_choice, organizer_choice, program_details, organizer_password,
    cancel, speaker_events, start_talk, finish_talk, view_questions, cancel_question,
    question_input, QUESTION_INPUT, REGISTER_NAME, REGISTER_PHONE, REGISTER_STACK,
    register_name, register_phone, register_stack, cancel_conversation,
    timeline, find_partner, BIO_INPUT, receive_biography, cancel_partner_search,
    register_for_event, handle_event_selection, get_client_main_keyboard, EVENT_SELECTION
)


def main():
    env = Env()
    env.read_env()
    try:
        bot_token = env.str('TELEGRAM_TOKEN')
        provider_token = env.str('TELEGRAM_PROVIDER_TOKEN')
    except EnvError:
        return

    updater = Updater(bot_token, use_context=True)
    dispatcher = updater.dispatcher
    dispatcher.bot_data['provider_token'] = provider_token
    set_bot_menu_commands(updater)

    role_conversation = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CHOOSE_ROLE: [
                CallbackQueryHandler(
                    guest_choice, pattern=f"^{ROLE_GUEST_CALLBACK}$"),
                CallbackQueryHandler(
                    speaker_choice, pattern=f"^{ROLE_SPEAKER_CALLBACK}$"),
                CallbackQueryHandler(
                    organizer_choice, pattern=f"^{ROLE_ORGANIZER_CALLBACK}$"),
            ],
            TYPING_ORGANIZER_PASSWORD: [MessageHandler(Filters.text & ~Filters.command, organizer_password)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        allow_reentry=True
    )

    question_conversation = ConversationHandler(
        entry_points=[CallbackQueryHandler(
            ask_question, pattern='^ask_question$')],
        states={
            QUESTION_INPUT: [
                MessageHandler(Filters.all & ~Filters.command, question_input),
                CallbackQueryHandler(
                    cancel_question, pattern='^cancel_question$')
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel), CallbackQueryHandler(
            cancel_question, pattern='^cancel_question$')]
    )

    partner_conversation = ConversationHandler(
        entry_points=[CallbackQueryHandler(
            find_partner, pattern='^find_partner$')],
        states={
            BIO_INPUT: [
                MessageHandler(Filters.text & ~Filters.command,
                               receive_biography),
                CallbackQueryHandler(cancel_partner_search,
                                     pattern='^cancel_partner_search$')
            ],
        },
        fallbacks=[CallbackQueryHandler(cancel_partner_search, pattern='^cancel_partner_search$'),
                   CommandHandler('cancel', cancel_partner_search)]
    )

    event_registration_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(
            register_for_event, pattern='^register_for_event$')],
        states={
            EVENT_SELECTION: [
                CallbackQueryHandler(handle_event_selection,
                                     pattern=r'^register_event_\d+$'),
                CallbackQueryHandler(
                    lambda u, c: (
                        u.callback_query.answer(),
                        u.callback_query.edit_message_text(
                            "Регистрация отменена.",
                            reply_markup=get_client_main_keyboard()
                        ),
                        ConversationHandler.END
                    ),
                    pattern='^cancel_event_registration$'
                )
            ],
            REGISTER_NAME: [MessageHandler(Filters.text & ~Filters.command, register_name)],
            REGISTER_PHONE: [MessageHandler(Filters.text & ~Filters.command, register_phone)],
            REGISTER_STACK: [CallbackQueryHandler(register_stack, pattern='^stack_')],
        },
        fallbacks=[
            CommandHandler('cancel', cancel_conversation),
            CallbackQueryHandler(
                lambda u, c: (
                    u.callback_query.answer(),
                    u.callback_query.edit_message_text(
                        "Регистрация отменена.",
                        reply_markup=get_client_main_keyboard()
                    ),
                    ConversationHandler.END
                ),
                pattern='^cancel_event_registration$'
            )
        ],
        allow_reentry=True
    )

    dispatcher.add_handler(CallbackQueryHandler(
        speaker_approval, pattern=r'^(approve|reject)_speaker_\d+$'))
    dispatcher.add_handler(role_conversation)
    dispatcher.add_handler(question_conversation)
    dispatcher.add_handler(partner_conversation)
    dispatcher.add_handler(event_registration_handler)
    dispatcher.add_handler(CallbackQueryHandler(
        cancel_question, pattern='^cancel_question$'))
    dispatcher.add_handler(MessageHandler(Filters.text(
        'ГЛЯНУТЬ ИВЕНТЫ') | Filters.text('глянуть ивенты'), speaker_events))
    dispatcher.add_handler(MessageHandler(Filters.text(
        'НАЧАТЬ ДОКЛАД') | Filters.text('начать доклад'), start_talk))
    dispatcher.add_handler(MessageHandler(Filters.text(
        'ГЛЯНУТЬ ВОПРОСЫ') | Filters.text('глянуть вопросы'), view_questions))
    dispatcher.add_handler(MessageHandler(Filters.text(
        'ЗАВЕРШИТЬ ВЫСТУПЛЕНИЕ') | Filters.text('завершить выступление'), finish_talk))
    dispatcher.add_handler(CommandHandler('ask', ask_question))
    dispatcher.add_handler(CommandHandler('help', help))
    dispatcher.add_handler(CallbackQueryHandler(
        ask_question, pattern='^ask_question$'))
    dispatcher.add_handler(CallbackQueryHandler(
        timeline, pattern='^timeline$'))
    dispatcher.add_handler(CallbackQueryHandler(
        find_partner, pattern='^find_partner$'))
    dispatcher.add_handler(PreCheckoutQueryHandler(precheckout))
    dispatcher.add_handler(MessageHandler(
        Filters.successful_payment, successful_payment))
    dispatcher.add_handler(MessageHandler(Filters.text('Поддержать'), donate))
    dispatcher.add_handler(MessageHandler(
        Filters.text('Программы'), programs_button))
    dispatcher.add_handler(MessageHandler(
        Filters.text('Актуалочка'), actual_button))
    dispatcher.add_handler(MessageHandler(
        Filters.text('Подробнее'), event_details))
    dispatcher.add_handler(CallbackQueryHandler(
        program_details, pattern='^program_details$'))
    dispatcher.add_handler(MessageHandler(Filters.all, lambda u, c: None))

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
