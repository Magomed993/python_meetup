from telegram.error import TelegramError
from django.db.models import Q
from datetime import datetime
from django.utils import timezone
from environs import Env
from telegram import Update, LabeledPrice, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, ConversationHandler
from telegram import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from phonenumber_field.modelfields import PhoneNumberField
from bot_utils import get_current_talk_details, get_full_schedule, load_schedule_from_json
from keyboards import (
    get_client_main_keyboard, get_speaker_main_keyboard, get_organizator_main_keyboard,
    get_favorite_keyboard, get_actual_section_details_keyboard, get_speaker_in_process_keyboard,
    get_programs_section_details_keyboard, get_programs_section_details_second_keyboard,
    get_actual_section_details_keyboard, get_client_initial_keyboard
)
from bot_logic.models import UserTg, Client, Speaker, Question, Event, Session, SpeakerSession, EventRegistration

registered_users = set()
CHOOSE_ROLE, TYPING_ORGANIZER_PASSWORD = range(2)
REGISTER_NAME, REGISTER_PHONE, REGISTER_STACK = range(3, 6)
ROLE_GUEST_CALLBACK = "role_guest"
ROLE_SPEAKER_CALLBACK = "role_speaker"
ROLE_ORGANIZER_CALLBACK = "role_organizer"
QUESTION_INPUT = 7
BIO_INPUT = 8
PARTNER_CHOICE = 9
EVENT_SELECTION = 10


def start(update: Update, context: CallbackContext):
    user = update.effective_user
    user_tg, created = UserTg.objects.get_or_create(
        tg_id=user.id, defaults={'nic_tg': user.username})
    is_client = Client.objects.filter(user=user_tg).exists()
    is_speaker = user_tg.is_speaker
    is_organizer = user_tg.is_organizator

    determined_role = "Организатор" if is_organizer else "Спикер" if is_speaker else "Гость" if is_client else None

    if determined_role:
        show_main_interface(update, context, determined_role,
                            f"С возвращением, {user.first_name}!")
        return ConversationHandler.END

    keyboard = [
        [InlineKeyboardButton("Я Гость", callback_data=ROLE_GUEST_CALLBACK)],
        [InlineKeyboardButton(
            "Я Спикер", callback_data=ROLE_SPEAKER_CALLBACK)],
        [InlineKeyboardButton(
            "Я Организатор", callback_data=ROLE_ORGANIZER_CALLBACK)],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    message = update.message or update.callback_query.message
    message.reply_text(
        "Добро пожаловать! Пожалуйста, выберите вашу роль:", reply_markup=reply_markup)
    return CHOOSE_ROLE


def show_main_interface(update: Update, context: CallbackContext, role_name: str, greeting_message: str = None):
    user = update.effective_user
    text = greeting_message or f'С возвращением, {user.first_name}! Ваша роль: {role_name}.'

    if role_name == "Гость":
        try:
            user_tg = UserTg.objects.get(tg_id=user.id)
            reply_markup = get_client_main_keyboard() if Client.objects.filter(
                user=user_tg, is_registered=True).exists() else get_client_initial_keyboard()
        except UserTg.DoesNotExist:
            reply_markup = get_client_initial_keyboard()
    elif role_name == "Спикер":
        reply_markup = get_speaker_main_keyboard()
    else:
        reply_markup = get_organizator_main_keyboard()

    message = update.callback_query.message if update.callback_query else update.message
    message.reply_text(text=text, reply_markup=reply_markup)
    context.user_data['role'] = role_name
    context.user_data['role_defined'] = True


def help(update: Update, context: CallbackContext):
    help_text = (
        "Справка по боту PythonMeetup\n\n"
        "Основные команды:\n"
        "- /start : Показать приветственное сообщение и основные кнопки.\n"
        "- /schedule : Показать программу мероприятия.\n"
        "- /ask <ваш вопрос> : Задать вопрос текущему докладчику.\n"
        "- /donate : Поддержать наше мероприятие.\n"
        "- /help : Показать это справочное сообщение.\n\n"
        "Если у вас возникли проблемы, обратитесь к организаторам."
    )
    context.bot.send_message(chat_id=update.effective_chat.id, text=help_text)


def successful_payment(update: Update, context: CallbackContext):
    payment = update.message.successful_payment
    user = update.effective_user
    readable_amount = payment.total_amount / 100
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f'Спасибо, {user.first_name}, за поддержку в размере {readable_amount} {payment.currency}! Ваш вклад важен.'
    )


def precheckout(update: Update, context: CallbackContext):
    query = update.pre_checkout_query
    expected_prefix = f'meetup_donation_{query.from_user.id}'
    if not query.invoice_payload.startswith(expected_prefix):
        context.bot.answer_pre_checkout_query(
            pre_checkout_query_id=query.id, ok=False, error_message='Ошибка при проверке платежа.')
        return
    context.bot.answer_pre_checkout_query(
        pre_checkout_query_id=query.id, ok=True)


def donate(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    user = update.effective_user
    title = 'Поддержка Python Meetup'
    description = "Ваш вклад поможет сделать наши митапы еще лучше! Спасибо!"
    payload = f'meetup_donation_{user.id}_{int(datetime.now().timestamp())}'

    if 'provider_token' not in context.bot_data:
        update.message.reply_text("Функция донатов временно недоступна.")
        return

    context.bot.send_invoice(
        chat_id=chat_id,
        title=title,
        description=description,
        payload=payload,
        provider_token=context.bot_data['provider_token'],
        currency='RUB',
        prices=[LabeledPrice("Донат на развитие митапа", 100 * 100)]
    )


def get_current_speaker():
    program = load_schedule_from_json()
    return program[0].get('speaker_name', 'Неизвестный Спикер') if program else 'Неизвестный Спикер'


def ask(update: Update, context: CallbackContext):
    user = update.effective_user
    if not context.args:
        update.message.reply_text(
            'Напишите вопрос после команды /ask. Например: /ask Какой ваш любимый фреймворк?')
        return

    question_text = ' '.join(context.args)
    active_talk = get_current_talk_details()
    if active_talk:
        speaker_name = active_talk.get('speaker_name', 'Неизвестный Спикер')
        talk_title = active_talk.get('talk_title', 'Текущий доклад')
        response = f'Спасибо за вопрос к докладу «{talk_title}» (спикер: {speaker_name})!\nВаш вопрос: «{question_text}» отправлен.'
    else:
        response = 'Нет активных докладов. Проверьте расписание (/schedule).'
    update.message.reply_text(response)


def schedule(update: Update, context: CallbackContext):
    program = get_full_schedule()
    if not program:
        update.message.reply_text('Программа мероприятия пока не загружена.')
        return

    schedule_text = ['Программа мероприятия:\n']
    for entry in program:
        schedule_text.append(
            f'Время: {entry.get("start_time", "Не указано")} - {entry.get("end_time", "Не указано")}\n'
            f'Докладчик: {entry.get("speaker_name", "Не указан")}\n'
            f'Тема: {entry.get("talk_title", "Без названия")}\n'
            '----------------------------------'
        )
    update.message.reply_text('\n'.join(schedule_text))


def guest_choice(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    user = query.from_user
    user_tg = UserTg.objects.get(tg_id=user.id)
    client, created = Client.objects.get_or_create(
        user=user_tg, defaults={'name': user.first_name})
    query.edit_message_text("Вы выбрали: Я Гость. Добро пожаловать!")
    show_main_interface(update, context, "Гость",
                        f"Добро пожаловать, {user.first_name}!")
    return ConversationHandler.END


def speaker_choice(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    user = query.from_user
    user_tg = UserTg.objects.get(tg_id=user.id)

    if user_tg.is_speaker:
        query.edit_message_text(
            "Вы уже подтвержденный спикер. Добро пожаловать!")
        show_main_interface(update, context, "Спикер",
                            f"Добро пожаловать, {user.first_name}!")
        return ConversationHandler.END

    if Speaker.objects.filter(user=user_tg).exists():
        query.edit_message_text(
            "Ваша заявка на роль спикера ожидает подтверждения.")
        return ConversationHandler.END

    Speaker.objects.create(user=user_tg, name=user.first_name)
    for organizer in UserTg.objects.filter(is_organizator=True):
        try:
            keyboard = [[
                InlineKeyboardButton(
                    "Принять", callback_data=f"approve_speaker_{user.id}"),
                InlineKeyboardButton(
                    "Отказать", callback_data=f"reject_speaker_{user.id}")
            ]]
            context.bot.send_message(
                chat_id=organizer.tg_id,
                text=f"Пользователь {user.first_name} хочет стать спикером. Подтвердить?",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception as e:
            print(e)

    query.edit_message_text(
        "Заявка на роль спикера отправлена на подтверждение.")
    return ConversationHandler.END


def organizer_choice(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    query.edit_message_text("Введите пароль организатора:")
    return TYPING_ORGANIZER_PASSWORD


def organizer_password(update: Update, context: CallbackContext):
    user = update.effective_user
    password = update.message.text
    env = Env()
    env.read_env()
    expected_password = env.str("ORGANIZER_PASSWORD", "").strip()

    if not expected_password:
        update.message.reply_text(
            "Системная ошибка конфигурации. Сообщите администратору.")
        return ConversationHandler.END

    user_tg = UserTg.objects.get(tg_id=user.id)
    if password == expected_password:
        user_tg.is_organizator = True
        user_tg.save()
        update.message.reply_text("Пароль верный! Вы вошли как Организатор.")
        show_main_interface(update, context, "Организатор")
        return ConversationHandler.END

    update.message.reply_text("Неверный пароль. Попробуйте еще раз.")
    return TYPING_ORGANIZER_PASSWORD


def cancel(update: Update, context: CallbackContext):
    message_text = "Выбор роли отменен."
    if update.message:
        update.message.reply_text(message_text)
    elif update.callback_query:
        update.callback_query.answer()
        update.callback_query.edit_message_text(message_text)
    return ConversationHandler.END


def speaker_approval(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    action, _, speaker_id = query.data.split('_')
    speaker_id = int(speaker_id)

    try:
        speaker_user = UserTg.objects.get(tg_id=speaker_id)
        speaker_profile = Speaker.objects.get(user=speaker_user)

        if action == "approve":
            speaker_user.is_speaker = True
            speaker_user.save()
            context.bot.send_message(
                chat_id=speaker_id,
                text="Ваша заявка на роль спикера одобрена!",
                reply_markup=get_speaker_main_keyboard()
            )
            query.edit_message_text(
                f"Вы одобрили заявку пользователя {speaker_user.nic_tg}.")
        elif action == "reject":
            speaker_profile.delete()
            context.bot.send_message(
                chat_id=speaker_id,
                text="Ваша заявка на роль спикера отклонена."
            )
            query.edit_message_text(
                f"Вы отклонили заявку пользователя {speaker_user.nic_tg}.")
    except Exception as e:
        query.edit_message_text("Ошибка при обработке выбора.")
        print(e)


def speaker_events(update: Update, context: CallbackContext):
    user = update.effective_user
    user_tg = UserTg.objects.get(tg_id=user.id)
    now = timezone.now()
    sessions = SpeakerSession.objects.filter(speaker__user=user_tg).select_related(
        'session__event').order_by('start_session')

    if not sessions.exists():
        update.message.reply_text(
            "У вас нет запланированных выступлений.", reply_markup=get_speaker_main_keyboard())
        return

    message = ["Ваши предстоящие выступления:\n"]
    for session in sessions:
        event = session.session.event
        message.append(
            f"📅 {event.name}\n"
            f"📍 {event.address or 'уточняется'}\n"
            f"🕒 {event.start_event.strftime('%d.%m.%Y') if event.start_event else 'дата уточняется'}\n"
            f"🎤 {session.session.title or 'без названия'}\n"
            f"⏱ {session.start_session.strftime('%H:%M') if session.start_session else 'время уточняется'} - "
            f"{session.finish_session.strftime('%H:%M') if session.finish_session else 'время уточняется'}\n"
            "────────────────────"
        )
    update.message.reply_text(
        "\n".join(message), reply_markup=get_speaker_main_keyboard())


def start_talk(update: Update, context: CallbackContext):
    user = update.effective_user
    user_tg = UserTg.objects.get(tg_id=user.id)
    now = timezone.now()
    current_session = SpeakerSession.objects.filter(
        speaker__user=user_tg, start_session__lte=now, finish_session__gte=now, is_finish=False
    ).select_related('session__event').first()

    if not current_session:
        update.message.reply_text(
            "Нет запланированного выступления.", reply_markup=get_speaker_main_keyboard())
        return

    if SpeakerSession.objects.filter(session__event=current_session.session.event, finish_session__lt=current_session.start_session, is_finish=False).exists():
        update.message.reply_text(
            "Предыдущий спикер еще выступает.", reply_markup=get_speaker_main_keyboard())
        return

    update.message.reply_text(
        f"Вы начали выступление: {current_session.session.title}\n"
        f"Время: {current_session.start_session.strftime('%H:%M')} - {current_session.finish_session.strftime('%H:%M')}",
        reply_markup=get_speaker_in_process_keyboard()
    )


def view_questions(update: Update, context: CallbackContext):
    user = update.effective_user
    user_tg = UserTg.objects.get(tg_id=user.id)
    now = timezone.now()
    current_session = SpeakerSession.objects.filter(
        speaker__user=user_tg, start_session__lte=now, finish_session__gte=now, is_finish=False
    ).first()

    if not current_session:
        update.message.reply_text(
            "Нет активного выступления.", reply_markup=get_speaker_in_process_keyboard())
        return

    questions = Question.objects.filter(
        speaker=current_session.speaker,
        created_at__gte=current_session.start_session,
        created_at__lte=current_session.finish_session
    ).select_related('client').order_by('created_at')

    if not questions.exists():
        update.message.reply_text(
            "Пока нет вопросов.", reply_markup=get_speaker_in_process_keyboard())
        return

    message = ["❓ Вопросы к вашему выступлению:\n"]
    for i, question in enumerate(questions, 1):
        message.append(
            f"{i}. {question.text}\n"
            f"   👤 {question.client.name if question.client.name else 'Аноним'}\n"
            f"   ⏱ {question.created_at.strftime('%H:%M')}\n"
            "────────────────────"
        )
    update.message.reply_text(
        "\n".join(message), reply_markup=get_speaker_in_process_keyboard())


def finish_talk(update: Update, context: CallbackContext):
    user = update.effective_user
    user_tg = UserTg.objects.get(tg_id=user.id)
    now = timezone.now()
    current_session = SpeakerSession.objects.filter(
        speaker__user=user_tg,
        start_session__lte=now,
        finish_session__gte=now,
        is_finish=False
    ).first()

    if not current_session:
        update.message.reply_text(
            "Нет активного выступления.", reply_markup=get_speaker_main_keyboard())
        return

    current_session.is_finish = True
    current_session.save()
    update.message.reply_text(
        "Выступление завершено! Спасибо за участие!", reply_markup=get_speaker_main_keyboard())


def programs_button(update: Update, context: CallbackContext):
    now = timezone.now()
    events = Event.objects.all().order_by('start_event')
    if not events.exists():
        message = update.message or update.callback_query.message
        message.reply_text("Нет запланированных мероприятий.",
                           reply_markup=get_programs_section_details_keyboard())
        return

    message = ["📅 Все предстоящие мероприятия:\n"]
    for event in events:
        start_time = event.start_event.strftime(
            "%d.%m.%Y %H:%M") if event.start_event else "дата уточняется"
        message.append(
            f"🔹 {event.name}\n"
            f"📌 {event.address or 'уточняется'}\n"
            f"🕒 {start_time}\n"
            "────────────────────"
        )
    reply_markup = get_programs_section_details_keyboard()
    if update.message:
        update.message.reply_text(
            "\n".join(message), reply_markup=reply_markup)
    elif update.callback_query:
        update.callback_query.message.edit_text(
            text="\n".join(message), reply_markup=reply_markup)


def actual_button(update: Update, context: CallbackContext):
    now = timezone.now()
    current_event = Event.objects.filter(
        start_event__lte=now, finish_event__gte=now).first()
    if not current_event:
        message = update.message or update.callback_query.message
        message.reply_text("Нет активных мероприятий.",
                           reply_markup=get_actual_section_details_keyboard())
        return

    current_speaker_session = SpeakerSession.objects.filter(
        session__event=current_event, start_session__lte=now, finish_session__gte=now
    ).select_related('session', 'speaker').first()

    message = [
        "🎤 Сейчас в эфире:\n",
        f"📌 {current_event.name}",
        f"📍 {current_event.address or 'уточняется'}",
        f"🕒 {current_event.start_event.strftime('%H:%M') if current_event.start_event else ''} - "
        f"{current_event.finish_event.strftime('%H:%M') if current_event.finish_event else ''}",
        f"ℹ️ {current_event.description or 'нет описания'}"
    ]
    if current_speaker_session:
        message.extend([
            "\n🎤 Текущий доклад:",
            f"📢 {current_speaker_session.session.title if current_speaker_session.session else 'Без названия'}",
            f"👤 {current_speaker_session.speaker.name if current_speaker_session.speaker else 'уточняется'}",
            f"🕒 {current_speaker_session.start_session.strftime('%H:%M') if current_speaker_session.start_session else ''} - "
            f"{current_speaker_session.finish_session.strftime('%H:%M') if current_speaker_session.finish_session else ''}"
        ])
    reply_markup = get_actual_section_details_keyboard()
    if update.message:
        update.message.reply_text(
            "\n".join(message), reply_markup=reply_markup)
    elif update.callback_query:
        update.callback_query.message.edit_text(
            text="\n".join(message), reply_markup=reply_markup)


def event_details(update: Update, context: CallbackContext):
    events = Event.objects.all()
    if not events.exists():
        update.message.reply_text("Нет запланированных мероприятий.",
                                  reply_markup=get_programs_section_details_keyboard())
        return

    message = ["Актуальные мероприятия:\n"]
    for event in events:
        start_time = event.start_event.strftime(
            "%d.%m.%Y %H:%M") if event.start_event else "время уточняется"
        end_time = event.finish_event.strftime(
            "%H:%M") if event.finish_event else "время уточняется"
        message.append(
            f"📅 {event.name}\n"
            f"📌 {event.address or 'место уточняется'}\n"
            f"🕒 {start_time} - {end_time}\n"
            f"ℹ️ {event.description or 'описание отсутствует'}\n"
            "────────────────────"
        )
    update.message.reply_text(
        "\n".join(message), reply_markup=get_programs_section_details_keyboard())


def ask_question(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    user = update.effective_user
    now = timezone.now()

    try:
        current_session = SpeakerSession.objects.filter(
            is_finish=False,
            start_session__lte=now,
            finish_session__gte=now).select_related('speaker', 'session__event').first()
        if not current_session:
            query.edit_message_text(
                "Нет активных выступлений.", reply_markup=get_client_main_keyboard())
            return ConversationHandler.END

        if not current_session.speaker.user.tg_id or not current_session.session.event:
            query.edit_message_text(
                "Ошибка: данные спикера или мероприятия недоступны.", reply_markup=get_client_main_keyboard())
            return ConversationHandler.END

        context.user_data['speaker_id'] = current_session.speaker.id
        context.user_data['session_id'] = current_session.id
        query.edit_message_text(
            text=f"""Задайте вопрос спикеру {current_session.speaker.name}:\nТема: 
            {current_session.session.title}\n\nВведите ваш вопрос:""",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("Отмена", callback_data="cancel_question")]])
        )
        return QUESTION_INPUT
    except Exception as e:
        print(e)
        return ConversationHandler.END


def question_input(update: Update, context: CallbackContext):
    user = update.effective_user
    question_text = update.message.text

    try:
        if 'speaker_id' not in context.user_data or 'session_id' not in context.user_data:
            return ConversationHandler.END

        speaker = Speaker.objects.get(id=context.user_data['speaker_id'])
        session = SpeakerSession.objects.get(
            id=context.user_data['session_id'])
        now = timezone.now()

        if session.is_finish or now < session.start_session or now > session.finish_session:
            update.message.reply_text(
                "Выступление завершено или еще не началось.", reply_markup=get_client_main_keyboard())
            return ConversationHandler.END

        user_tg, _ = UserTg.objects.get_or_create(
            tg_id=user.id, defaults={'nic_tg': user.username})
        client, _ = Client.objects.get_or_create(
            user=user_tg, defaults={'name': user.first_name})
        Question.objects.create(speaker=speaker, client=client, text=question_text.strip(
        ), event=session.session.event, created_at=now)
        update.message.reply_text(
            f"✅ Вопрос отправлен спикеру {speaker.name}!", reply_markup=get_client_main_keyboard())
    except Exception as e:
        print(e)

    context.user_data.pop('speaker_id', None)
    context.user_data.pop('session_id', None)
    return ConversationHandler.END


def cancel_question(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    query.edit_message_text(
        "Вопрос отменен.", reply_markup=get_actual_section_details_keyboard())
    return ConversationHandler.END


def timeline(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    events = Event.objects.all().order_by('start_event')

    if not events.exists():
        query.edit_message_text("Нет информации о мероприятиях.")
        return ConversationHandler.END

    message = ["⏳ Все мероприятия:\n"]
    for event in events:
        message.append(
            f"📅 {event.name}\n"
            f"🕒 {event.start_event.strftime('%d.%m.%Y %H:%M') if event.start_event else 'Дата уточняется'}\n"
            f"📍 {event.address or 'Место уточняется'}\n"
            "────────────────────"
        )
    query.edit_message_text("\n".join(message))
    return ConversationHandler.END


def find_partner(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    user = update.effective_user
    user_tg, _ = UserTg.objects.get_or_create(
        tg_id=user.id, defaults={'nic_tg': user.username})
    client, _ = Client.objects.get_or_create(user=user_tg)

    if not client.biography:
        query.edit_message_text(
            text="Расскажите о себе (чем занимаетесь, технологии):",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("Отмена", callback_data="cancel_partner_search")]])
        )
        return BIO_INPUT
    return show_partner_options(update, context)


def receive_biography(update: Update, context: CallbackContext):
    user = update.effective_user
    biography = update.message.text
    user_tg = UserTg.objects.get(tg_id=user.id)
    client = Client.objects.get(user=user_tg)
    client.biography = biography
    client.save()
    update.message.reply_text(
        "Спасибо! Теперь мы можем подобрать вам собеседника.")
    return show_partner_options(update, context)


def show_partner_options(update: Update, context: CallbackContext):
    user = update.effective_user
    user_tg = UserTg.objects.get(tg_id=user.id)
    other_clients = Client.objects.exclude(user=user_tg).select_related('user')

    if not other_clients.exists():
        reply_text = "Пока нет других участников для общения."
    else:
        message = ["Доступные собеседники:\n"]
        for i, client in enumerate(other_clients, 1):
            message.append(
                f"{i}. {client.name or 'Без имени'}\n"
                f"   Стек: {client.get_favorite_stack_display() or 'Не указан'}\n"
                f"   О себе: {client.biography or 'Не указано'}\n"
                f"   Телеграм: {'@' + str(client.user.nic_tg) if client.user.nic_tg else str(client.contact_phone)}\n"
                "────────────────────"
            )
        reply_text = "\n".join(message)

    if update.message:
        update.message.reply_text(reply_text)
    elif update.callback_query:
        update.callback_query.edit_message_text(
            text=reply_text, reply_markup=None)
    else:
        context.bot.send_message(chat_id=user.id, text=reply_text)
    return ConversationHandler.END


def cancel_partner_search(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    query.edit_message_text("Поиск собеседника отменен.",
                            reply_markup=get_client_main_keyboard())
    return ConversationHandler.END


def register_for_event(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    user = update.effective_user
    try:
        user_tg = UserTg.objects.get(tg_id=user.id)
        client = Client.objects.get(user=user_tg)
    except (UserTg.DoesNotExist, Client.DoesNotExist):
        query.edit_message_text(
            "Сначала нужно зарегистрироваться в системе.",
            reply_markup=get_client_initial_keyboard()
        )
        return ConversationHandler.END
    upcoming_events = Event.objects.filter(
        finish_event__gte=timezone.now()
    ).order_by('start_event')

    if not upcoming_events.exists():
        query.edit_message_text(
            "Нет предстоящих мероприятий для регистрации.",
            reply_markup=get_client_main_keyboard()
        )
        return ConversationHandler.END
    keyboard = []
    for event in upcoming_events:
        event_date = event.start_event.strftime(
            '%d.%m.%Y') if event.start_event else 'Дата уточняется'
        keyboard.append([
            InlineKeyboardButton(
                f"{event.name} ({event_date})",
                callback_data=f"register_event_{event.id}"
            )
        ])
    keyboard.append([
        InlineKeyboardButton(
            "Отмена", callback_data="cancel_event_registration")
    ])

    query.edit_message_text(
        "Выберите мероприятие для регистрации:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return EVENT_SELECTION


def handle_event_selection(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    if query.data == "cancel_event_registration":
        query.edit_message_text(
            "Регистрация отменена.",
            reply_markup=get_programs_section_details_keyboard()  #
        )
        return ConversationHandler.END

    try:
        event_id = int(query.data.split('_')[2])
        context.user_data['event_id'] = event_id
        event = Event.objects.get(id=event_id)

        user = update.effective_user
        user_tg, _ = UserTg.objects.get_or_create(
            tg_id=user.id, defaults={'nic_tg': user.username}
        )
        client, created = Client.objects.get_or_create(user=user_tg)

        if created or not client.is_registered:
            context.bot.send_message(
                chat_id=query.message.chat_id,
                text="Введите ваше ФИО:",
                reply_markup=ReplyKeyboardMarkup(
                    [[KeyboardButton("Отмена")]], resize_keyboard=True)
            )
            return REGISTER_NAME
        else:
            if EventRegistration.objects.filter(client=client, event=event).exists():
                context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=f"Вы уже зарегистрированы на мероприятие: {event.name}",
                    reply_markup=get_client_main_keyboard()  # Reply keyboard
                )
                return ConversationHandler.END
            EventRegistration.objects.create(client=client, event=event)
            event_date = event.start_event.strftime(
                '%d.%m.%Y %H:%M') if event.start_event else 'дата уточняется'
            confirmation_message = (
                f"✅ Вы успешно зарегистрированы на:\n"
                f"Мероприятие: {event.name}\n"
                f"Дата: {event_date}\n"
                f"Место: {event.address or 'уточняется'}"
            )
            context.bot.send_message(
                chat_id=query.message.chat_id,
                text=confirmation_message,
                reply_markup=get_client_main_keyboard()
            )
            return ConversationHandler.END

    except Exception as e:
        print(e)
        return ConversationHandler.END


def back_to_programs(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    return programs_button(update, context)


def back_to_main(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    user = update.effective_user
    show_main_interface(update, context, "Гость",
                        f"Добро пожаловать, {user.first_name}!")
    return ConversationHandler.END


def program_details(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    now = timezone.now()
    events = Event.objects.all()

    if not events.exists():
        query.edit_message_text("Нет запланированных мероприятий.",
                                reply_markup=get_programs_section_details_second_keyboard())
        return

    message = ["📅 Подробная информация о предстоящих мероприятиях:\n"]
    for event in events:
        start_time = event.start_event.strftime(
            "%d.%m.%Y %H:%M") if event.start_event else "дата уточняется"
        end_time = event.finish_event.strftime(
            "%H:%M") if event.finish_event else "время уточняется"
        message.append(
            f"🔹 {event.name}\n"
            f"📌 {event.address or 'уточняется'}\n"
            f"🕒 {start_time} - {end_time}\n"
            f"ℹ️ {event.description or 'нет описания'}\n"
        )
        speaker_sessions = SpeakerSession.objects.filter(
            session__event=event).select_related('session', 'speaker')
        if speaker_sessions.exists():
            message.append("📢 Программа мероприятия:")
            for ss in speaker_sessions:
                session_start = ss.start_session.strftime(
                    "%H:%M") if ss.start_session else "время уточняется"
                session_end = ss.finish_session.strftime(
                    "%H:%M") if ss.finish_session else "время уточняется"
                message.append(
                    f"  • {ss.session.title if ss.session else 'Без названия'}\n"
                    f"    👤 {ss.speaker.name if ss.speaker else 'Спикер уточняется'}\n"
                    f"    🕒 {session_start} - {session_end}\n"
                )
        else:
            message.append("ℹ️ Программа мероприятия пока не опубликована\n")
        message.append("────────────────────")
    query.edit_message_text("\n".join(
        message), reply_markup=get_programs_section_details_second_keyboard())


def start_registration(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    query.edit_message_text("Введите ваше ФИО:")
    return REGISTER_NAME


def register_name(update: Update, context: CallbackContext):
    context.user_data['full_name'] = update.message.text
    update.message.reply_text("Введите ваш номер телефона:")
    return REGISTER_PHONE


def register_phone(update: Update, context: CallbackContext):
    phone = update.message.text
    try:
        parsed_phone = PhoneNumberField().clean(phone, None)
        context.user_data['phone'] = str(parsed_phone)
        keyboard = [
            [InlineKeyboardButton("Бэкенд", callback_data="stack_backend")],
            [InlineKeyboardButton("Фронтенд", callback_data="stack_frontend")],
            [InlineKeyboardButton(
                "Фулл-стэк", callback_data="stack_full_stack")],
        ]
        update.message.reply_text(
            "Выберите ваш любимый стэк:", reply_markup=InlineKeyboardMarkup(keyboard))
        return REGISTER_STACK
    except Exception:
        update.message.reply_text(
            "Некорректный номер телефона. Введите в формате +71234567890:")
        return REGISTER_PHONE


def register_stack(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    stack = query.data.split('_')[1]
    user = update.effective_user

    try:
        full_name = context.user_data.get('full_name')
        phone = context.user_data.get('phone')
        event_id = context.user_data.get('event_id')

        if not all([full_name, phone, event_id]):
            raise ValueError("ошибка")

        user_tg, _ = UserTg.objects.get_or_create(
            tg_id=user.id,
            defaults={'nic_tg': user.username}
        )
        event = Event.objects.get(id=event_id)
        client, _ = Client.objects.update_or_create(
            user=user_tg,
            defaults={
                'name': full_name,
                'contact_phone': phone,
                'favorite_stack': stack,
                'is_registered': True
            }
        )
        EventRegistration.objects.create(client=client, event=event)
        event_date = event.start_event.strftime(
            '%d.%m.%Y %H:%M') if event.start_event else 'дата уточняется'
        confirmation_message = (
            f"✅ Регистрация завершена!\n"
            f"Мероприятие: {event.name}\n"
            f"Дата: {event_date}\n"
            f"Место: {event.address or 'уточняется'}\n"
            f"Ваше имя: {full_name}\n"
            f"Телефон: {phone}"
        )
        context.bot.send_message(
            chat_id=query.message.chat_id,
            text=confirmation_message,
            reply_markup=get_client_main_keyboard()
        )

        query.message.delete()

    except Event.DoesNotExist:
        context.bot.send_message(
            chat_id=query.message.chat_id,
            text="Мероприятие не найдено. Пожалуйста, попробуйте выбрать другое.",
            reply_markup=get_client_main_keyboard()
        )
    except Exception as e:
        print(str(e))
        context.bot.send_message(
            chat_id=query.message.chat_id,
            text="Произошла ошибка при регистрации. Пожалуйста, попробуйте позже.",
            reply_markup=get_client_main_keyboard()
        )

    for key in ['event_id', 'full_name', 'phone']:
        context.user_data.pop(key, None)

    return ConversationHandler.END


def cancel_registration(update: Update, context: CallbackContext):
    update.message.reply_text(
        "Регистрация отменена.", reply_markup=get_programs_section_details_keyboard())
    return ConversationHandler.END


def cancel_conversation(update: Update, context: CallbackContext):
    """Отменяет текущий диалог выбора роли."""

    user = update.effective_user
    message_text = "Выбор роли отменен."

    if update.message:
        update.message.reply_text(message_text)
    elif update.callback_query:
        update.callback_query.answer()  # ответ на коллбак
        update.callback_query.edit_message_text(text=message_text)

    print(f"Пользователь {user.id} отменил диалог.")

    return ConversationHandler.END
