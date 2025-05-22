from datetime import datetime

from telegram import Update, LabeledPrice
from telegram.ext import CallbackContext

from bot_utils import (get_current_talk_details, get_full_schedule,
                       load_schedule_from_json)


def successful_payment_callback(update: Update, context: CallbackContext):
    """Обрабатывает успешный платеж."""
    payment_details = update.message.successful_payment
    user = update.effective_user

    currency = payment_details.currency
    total_amount = payment_details.total_amount
    invoice_payload = payment_details.invoice_payload
    readable_amount = total_amount / 100

    user_representation = (f'{user.first_name} (ID: {user.id}, Username:'
                           f' {user.username or "N/A"})') if user else 'Неизвестный пользователь'
    print('\n--- УСПЕШНЫЙ ПЛАТЕЖ ---')
    print(f'Пользователь: {user_representation}')
    print('-------------------------------------')

    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=(
            f'Спасибо большое, {user.first_name if user else "дорогой друг"}, за вашу поддержку в размере {readable_amount} {currency}!\n'
            f'Ваш вклад очень важен для нас. Payload вашего платежа: {invoice_payload}.'
        )
    )


def precheckout_callback(update:Update, context: CallbackContext):
    """Обрабатывает PreCheckoutQuery, отправленный Telegram."""
    query = update.pre_checkout_query
    print(f"Получен PreCheckoutQuery: id={query.id}, payload={query.invoice_payload}, user_id={query.from_user.id}")

    if query.invoice_payload != f'meetup_donation_{query.from_user.id}_{query.invoice_payload.split("_")[-1]}':
        expected_prefix = f'meetup_donation_{query.from_user.id}'

        if not query.invoice_payload.startswith(expected_prefix):
            print(f'ОШИБКА: PreCheckoutQuery с неожиданным payload: {query.invoice_payload}')
            context.bot.answer_pre_checkout_query(
                pre_checkout_query_id=query.id,
                ok=False,
                error_message='Произошла ошибка при проверке платежа. Пожалуйста, попробуйте снова.'
            )
            return

    context.bot.answer_pre_checkout_query(pre_checkout_query_id=query.id, ok=True)
    print(f"Ответили ok=True на PreCheckoutQuery id={query.id}")


def donate(update:Update, context: CallbackContext):
    """Отправляет счет для доната."""
    chat_id = update.effective_chat.id
    user = update.effective_user

    title = 'Поддержка Python Meetup'
    description = "Ваш вклад поможет сделать наши митапы еще лучше! Спасибо!"

    payload_user_part = user.id if user else 'Unknown_user'
    payload_time_part = int(datetime.now().timestamp())
    payload = f'meetup_donation_{payload_user_part}_{payload_time_part}'

    if 'provider_token' not in context.bot_data:
        update.message.reply_text(
            "Извините, функция донатов временно недоступна. (Ошибка конфигурации провайдера)"
        )
        print("ОШИБКА: provider_token не найден в context.bot_data при вызове /donate")
        return

    provider_token = context.bot_data['provider_token']
    currency = 'RUB'

    prices = [LabeledPrice("Донат на развитие митапа", 100 * 100)]

    if context.bot:
        context.bot.send_invoice(
            chat_id=chat_id,
            title=title,
            description=description,
            payload=payload,
            provider_token=provider_token,
            currency=currency,
            prices=prices,
        )
    else:
        update.message.reply_text(
            "Произошла ошибка при попытке отправить счет. Пожалуйста, попробуйте позже. (Бот не доступен)")
        print("ОШИБКА: context.bot не был доступен при вызове send_invoice")


def get_current_speaker_for_question():
    """ MVP: Возвращает имя "текущего" спикера для вопросов."""
    program_listing = load_schedule_from_json()

    if program_listing:
        first_presentation = program_listing[0] if program_listing else {}
        return first_presentation.get('speaker_name', 'speaker-Not found')
    return 'Неизвестный Спикер'


def ask_question(update: Update, context: CallbackContext):
    """Обрабатывает команду /ask для отправки вопроса 'текущему' докладчику."""
    user = update.effective_user

    if not context.args:
        update.message.reply_text(
            'Пожалуйста, напишите ваш вопрос после команды /ask.\n'
            'Например: /ask Какой ваш любимый фреймворк?'
        )
        return

    question_text = ' '.join(context.args)
    active_talk_details = get_current_talk_details()
    if active_talk_details:
        speaker_name = active_talk_details.get('speaker_name', 'Неизвестный Спикер')
        talk_title = active_talk_details.get('talk_title', 'Текущий доклад')

        response_to_user = (
            f'Спасибо за ваш вопрос к докладу «{talk_title}» (спикер: {speaker_name})!\n'
            f'Ваш вопрос: «{question_text}» был \"отправлен\".'
        )

        print(f'\n--- Новый вопрос ({datetime.now().strftime("%Y-%m-%d %H:%M:%S")}) ---')
        print(f'Для доклада: «{talk_title}» (Спикер: {speaker_name})')
        print(f'От пользователя: {user.first_name} (ID: {user.id}, Username: {user.username or "N/A"})')
        print(f'Текст вопроса: {question_text}')
        print('-----------------\n')
    else:
        response_to_user = (
            'В данный момент нет активных докладов, которым можно было бы задать вопрос.\n'
            'Пожалуйста, проверьте расписание (/schedule) и попробуйте позже.'
        )
        print(f'\n--- Попытка задать вопрос вне активного доклада ({datetime.now().strftime("%Y-%m-%d %H:%M:%S")}) ---')
        print(f'От пользователя: {user.first_name} (ID: {user.id}, Username: {user.username or "N/A"})')
        print(f'Текст предполагаемого вопроса: {question_text}')
        print('-----------------\n')
    update.message.reply_text(
        response_to_user
    )


def start(update: Update, context: CallbackContext):
    """Отправляет приветственное сообщение при команде /start."""
    user = update.effective_user
    chat_id =update.effective_chat.id
    welcome_message = (
        f"Привет, {user.first_name}!\n\n"
        f"Добро пожаловать на PythonMeetup! Я ваш бот-помощник.\n\n"
        f"Здесь вы можете:\n"
        f"-Узнать программу мероприятия (команда /schedule или кнопка 'Расписание').\n"
        f"-Задать вопрос текущему докладчику (команда /ask <ваш вопрос>).\n"
        f"-Поддержать наше мероприятие (команда /donate или кнопка 'Поддержать').\n"
        f"-Получить эту справку (команда /help).\n\n"
        f"Используйте команды из меню или кнопки ниже для навигации."
    )
    context.bot.send_message(
        chat_id=chat_id,
        text=welcome_message
    )
    print(f'Пользователь '
          f'{user.id} ({user.username or user.first_name})'
          f' запустил бота.'
          )


def show_schedule(update: Update, context: CallbackContext):
    """Отправляет пользователю программу мероприятия, загруженную из файла."""
    program_listing = get_full_schedule()

    if not program_listing:
        reply_text = ('К сожалению, программа мероприятия пока не загружена'
                      ' или возникла ошибка при её чтении. Попробуйте позже.')
        update.message.reply_text(reply_text)
        return

    schedule_entries_text = ['Программа мероприятия:\n']
    for entry_details in program_listing:
        speaker = entry_details.get('speaker_name', 'Не указан')
        title = entry_details.get('talk_title', 'Без названия')
        start = entry_details.get('start_time', 'Время не указано')
        end = entry_details.get('end_time', 'Время не указано')

        schedule_entries_text.append(
            f'Время доклада : {start} - {end}\n'
            f'Имя докладчика: {speaker}\n'
            f'Тема: {title}\n'
            '----------------------------------'
        )
    full_schedule_text = '\n'.join(schedule_entries_text)
    update.message.reply_text(full_schedule_text)
