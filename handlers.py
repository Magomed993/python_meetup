from datetime import datetime

from telegram import Update
from telegram.ext import CallbackContext

from bot_utils import (get_current_talk_details, get_full_schedule,
                       load_schedule_from_json)


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
    welcome_message = (
        f'Привет, {user.first_name}!\n\n'
        'Я бот для PythonMeetup. Здесь ты сможешь:\n'
        '- Узнать программу мероприятия (/schedule)\n'
        '- Задать вопрос текущему докладчику (/ask)\n'
        # "- Познакомиться с другими участниками (скоро)\n"
        # "- Поддержать организаторов (скоро)\n\n"
        'Пока это основное. Приятного митапа!'
    )
    update.message.reply_text(welcome_message)
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
