from datetime import datetime

from environs import Env
from telegram import (InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice,
                      Update)
from telegram.ext import CallbackContext, ConversationHandler

from bot_logic.models import (Client, Event, Question, Session, Speaker,
                              SpeakerSession, UserTg, ProspectiveSpeaker)
from bot_utils import (get_current_talk_details, get_full_schedule,
                       load_schedule_from_json)
from reply_keyboards import get_main_keyboard, get_organizer_keyboard

CHOOSE_ROLE, TYPING_ORGANIZER_PASSWORD = range(2)

ROLE_GUEST_CALLBACK = "role_guest"
ROLE_SPEAKER_CALLBACK = "role_speaker"
ROLE_ORGANIZER_CALLBACK = "role_organizer"

MANAGE_SPEAKERS_CHOOSE_EVENT, MANAGE_SPEAKERS_CHOOSE_SPEAKER, MANAGE_SPEAKERS_SESSION_DETAILS = map(str, range(10, 13))
EVENT_CHOICE_CALLBACK_PREFIX = "event_choice_"
SPEAKER_CHOICE_CALLBACK_PREFIX = "speaker_choice_"

PS_TYPING_NAME, PS_TYPING_CONTACT, PS_TYPING_NOTES = map(str, range(20, 23))

def start_command_handler(update: Update, context: CallbackContext):
    """Обрабатывает команду /start.
    Регистрирует пользователя, проверяет роль и начинает диалог выбора роли, если необходимо."""

    user = update.effective_user
    print(f"Пользователь {user.id} ({user.username or user.first_name}) запустил /start.")

    user_tg_instance, created = UserTg.objects.get_or_create(
        tg_id=user.id,
        defaults={'nic_tg': user.username}
    )
    if created:
        print(f"Создана новая запись UserTg для {user.id}.")

    is_client = Client.objects.filter(user=user_tg_instance).exists()
    is_speaker = Speaker.objects.filter(user=user_tg_instance).exists()
    is_organizer = user_tg_instance.is_organizator

    determined_role = None
    if is_organizer:
        determined_role = "Организатор"
    elif is_speaker:
        determined_role = "Спикер"
    elif is_client:  # Гость - это Client
        determined_role = "Гость"

    if determined_role:
        print(f"Роль пользователя {user.id} определена из БД как '{determined_role}'.")

        show_main_interface_for_role(update, context, role_name=determined_role,
                                     greeting_message=f"С возвращением, {user.first_name}!")
        return ConversationHandler.END
    else:
        print(f"Роль пользователя {user.id} не определена в БД. Предлагаем выбор.")

        keyboard = [
            [InlineKeyboardButton("Я Гость", callback_data=ROLE_GUEST_CALLBACK)],
            [InlineKeyboardButton("Я Спикер", callback_data=ROLE_SPEAKER_CALLBACK)],
            [InlineKeyboardButton("Я Организатор", callback_data=ROLE_ORGANIZER_CALLBACK)],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

    if update.message:
        update.message.reply_text(
            "Добро пожаловать! Пожалуйста, выберите вашу роль:",
            reply_markup=reply_markup
        )
    elif update.callback_query:
        update.callback_query.message.edit_text(  # Или reply_text, если edit_text не подходит
            "Добро пожаловать! Пожалуйста, выберите вашу роль:",
            reply_markup=reply_markup
        )
    return CHOOSE_ROLE



def show_main_interface_for_role(update: Update, context: CallbackContext, role_name: str, greeting_message: str = None):
    """Показывает основной интерфейс (кнопки и сообщение) для указанной роли."""
    chat_id = update.effective_chat.id
    user = update.effective_user

    text_to_send = greeting_message or f'С возвращением, {user.first_name}! Ваша роль: {role_name}.'

    if role_name == "Организатор":
        reply_markup = get_organizer_keyboard()
    else:
        reply_markup = get_main_keyboard()

    target_message = None
    if update.callback_query:
        target_message = update.callback_query.message
        context.bot.send_message(chat_id=chat_id, text=text_to_send, reply_markup=reply_markup)
    elif update.message:
        target_message = update.message
        target_message.reply_text(text=text_to_send, reply_markup=reply_markup)
    else:
        context.bot.send_message(chat_id=chat_id, text=text_to_send, reply_markup=reply_markup)

    context.user_data['role'] = role_name
    context.user_data['role_defined'] = True


def help_command(update:Update, context:CallbackContext):
    """Отправляет справочное сообщение пользователю."""
    user = update.effective_user

    help_text = (
        "Справка по боту PythonMeetup\n\n"
        "Я помогу вам на нашем мероприятии! Вот что я умею:\n\n"
        "Основные команды:\n"
        "- /start : Показать приветственное сообщение и основные кнопки.\n"
        "- /schedule : Показать программу мероприятия.\n"
        "- /ask <ваш вопрос> : Задать вопрос текущему докладчику.\n"
        "  (Пример: /ask Какой ваш любимый цвет?)\n"
        "- /donate : Поддержать наше мероприятие.\n"
        "- /help : Показать это справочное сообщение.\n\n"
        "Вы также можете использовать кнопки под полем ввода для быстрого доступа к основным функциям.\n\n"
        "Если у вас возникли проблемы или есть предложения, пожалуйста, обратитесь к организаторам."
    )
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=help_text
    )


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


def handle_guest_choice(update: Update, context: CallbackContext):
    """Обрабатывает выбор роли 'Гость'."""

    query = update.callback_query
    query.answer()  # Обязательно отвечаем на callback
    user = query.from_user

    print(f"Пользователь {user.id} выбрал роль 'Гость'.")

    user_tg_instance = UserTg.objects.get(tg_id=user.id)
    client_instance, client_created = Client.objects.get_or_create(
        user=user_tg_instance,
        defaults={'name': user.first_name}  #Имя пользователя как имя клиента по умолчанию
    )

    if client_created:
        print(f"Создан профиль Client для пользователя {user.id}.")
    else:
        print(f"Профиль Client для пользователя {user.id} уже существует.")

    #Редактируем сообщение, убирая инлайн-кнопки
    query.edit_message_text(text="Вы выбрали: Я Гость. Добро пожаловать!")

    #Показываем основной интерфейс для гостя
    greeting = f"Добро пожаловать, {user.first_name}! Вы вошли как Гость."
    show_main_interface_for_role(update, context, role_name="Гость", greeting_message=greeting)
    return ConversationHandler.END

def handle_speaker_choice(update: Update, context: CallbackContext):
    """Обрабатывает выбор роли 'Спикер'."""

    query = update.callback_query
    query.answer()
    user = query.from_user

    print(f"Пользователь {user.id} выбрал роль 'Спикер'.")

    user_tg_instance = UserTg.objects.get(tg_id=user.id) #Пользователь UserTg должен уже существовать

    if Speaker.objects.filter(user=user_tg_instance).exists():
        speaker_profile = Speaker.objects.get(user=user_tg_instance)
        speaker_name = speaker_profile.name if speaker_profile.name else user.first_name
        print(f"Спикер {user.id} найден в БД.")

        query.edit_message_text(text="Вы подтвердили роль: Спикер. Добро пожаловать!")

        #Показываем интерфейс для спикера
        greeting = f"Добро пожаловать, {speaker_name}! Вы вошли как Спикер."
        show_main_interface_for_role(update, context, role_name="Спикер", greeting_message=greeting)
    else:
        print(f"Спикер {user.id} НЕ найден в БД.")
        query.edit_message_text(
            text="К сожалению, вы не найдены в списке спикеров.\n"
                 "Пожалуйста, обратитесь к организаторам для добавления вас в систему.\n\n"
                 "Если это ошибка, вы можете попробовать выбрать роль заново, отправив /start."
        )

    return ConversationHandler.END

def handle_organizer_choice_init(update: Update, context: CallbackContext) :
    """Инициирует запрос пароля, если пользователь выбрал 'Я Организатор'."""
    query = update.callback_query
    query.answer()
    user = query.from_user

    print(f"Пользователь {user.id} выбрал роль 'Организатор'. Запрашиваем пароль.")

    query.edit_message_text(
        text="Вы выбрали: Я Организатор.\nДля подтверждения вашей роли, пожалуйста, введите пароль организатора:")

    return TYPING_ORGANIZER_PASSWORD  #Переходим в состояние TYPING_ORGANIZER_PASSWORD (число 1)


def handle_organizer_password(update: Update, context: CallbackContext):
    """Обрабатывает введенный пароль организатора."""
    user = update.effective_user
    entered_password = update.message.text

    print(f"Пользователь {user.id} ввел пароль организатора: '{entered_password}'")

    env = Env()
    env.read_env()

    expected_password = env.str("ORGANIZER_PASSWORD", default="").strip()

    if not expected_password:
        print("ОШИБКА: Пароль организатора (ORGANIZER_PASSWORD) не задан в .env файле.")
        update.message.reply_text(
            "Произошла системная ошибка конфигурации. Пожалуйста, сообщите администратору."
        )
        return ConversationHandler.END

    user_tg_instance = UserTg.objects.get(tg_id=user.id)

    if entered_password == expected_password:
        print(f"Пароль для пользователя {user.id} верный. Подтверждаем роль Организатора.")
        user_tg_instance.is_organizator = True
        user_tg_instance.save()

        update.message.reply_text("Пароль верный! Вы вошли как Организатор.")
        show_main_interface_for_role(update, context, role_name="Организатор")
        return ConversationHandler.END
    else:
        print(f"Пароль для пользователя {user.id} неверный.")
        update.message.reply_text(
            "Неверный пароль. Пожалуйста, попробуйте ввести пароль еще раз."
        )
        return TYPING_ORGANIZER_PASSWORD

def cancel_conversation(update: Update, context: CallbackContext):
    """Отменяет текущий диалог выбора роли."""

    user = update.effective_user
    message_text = "Выбор роли отменен."

    if update.message:
        update.message.reply_text(message_text)
    elif update.callback_query:
        update.callback_query.answer() #ответ на коллбак
        update.callback_query.edit_message_text(text=message_text)

    print(f"Пользователь {user.id} отменил диалог.")

    return ConversationHandler.END


def manage_speakers_start(update: Update, context: CallbackContext):
    """
    Начинает диалог управления спикерами. Показывает список мероприятий для выбора.
    Вызывается при нажатии кнопки 'Управление Спикерами'.
    """
    user = update.effective_user

    user_tg_instance = UserTg.objects.filter(tg_id=user.id).first()
    if not (user_tg_instance and user_tg_instance.is_organizator):
        update.message.reply_text("Эта функция доступна только для организаторов.")
        return ConversationHandler.END

    print(f"Организатор {user.id} начал управление спикерами.")

    events = Event.objects.all().order_by('start_event')

    if not events:
        update.message.reply_text("Пока нет запланированных мероприятий, для которых можно управлять спикерами.")
        return ConversationHandler.END

    keyboard_rows= []
    for event in events:
        callback_data = f"{EVENT_CHOICE_CALLBACK_PREFIX}{event.id}"
        event_date_str = event.start_event.strftime('%d.%m.%Y') if event.start_event else "Дата не указана"
        button_text = f"{event.name} ({event_date_str})"

        keyboard_rows.append([InlineKeyboardButton(button_text, callback_data=callback_data)])

    keyboard_rows.append([InlineKeyboardButton("Отмена", callback_data="manage_speakers_cancel")])

    reply_markup = InlineKeyboardMarkup(keyboard_rows)
    update.message.reply_text(
        "Выберите мероприятие, на которое хотите записать спикера, или для которого хотите просмотреть/изменить состав спикеров:",
        reply_markup=reply_markup
    )

    return MANAGE_SPEAKERS_CHOOSE_EVENT


def handle_event_choice(update:Update, context:CallbackContext):
    """
       Обрабатывает выбор мероприятия организатором.
       Сохраняет ID мероприятия и запрашивает выбор спикера.
    """

    query = update.callback_query
    query.answer()
    user = query.from_user

    try:
        event_id_str = query.data.replace(EVENT_CHOICE_CALLBACK_PREFIX, "")
        event_id = int(event_id_str)
    except (ValueError, TypeError):
        print(f"ОШИБКА: Не удалось извлечь event_id из callback_data: {query.data}")
        query.edit_message_text("Произошла ошибка при выборе мероприятия. Попробуйте снова.")
        return ConversationHandler.END

    context.user_data['selected_event_id'] = event_id

    try:
        selected_event = Event.objects.get(id=event_id)
        event_name = selected_event.name
        print(f"Организатор {user.id} выбрал мероприятие ID: {event_id} ({event_name}).")
        query.edit_message_text(f"Выбрано мероприятие: {event_name}.\nТеперь выберите спикера из списка:")
    except Event.DoesNotExist:
        print(f"ОШИБКА: Мероприятие с ID {event_id} не найдено в БД.")
        query.edit_message_text("Выбранное мероприятие не найдено. Пожалуйста, начните заново.")
        return ConversationHandler.END

    speakers = Speaker.objects.all().order_by('name')

    if not speakers.exists():
        query.message.reply_text( #reply_text, так как edit_message_text уже был вызван
            "В системе пока нет зарегистрированных спикеров.\n"
            "Сначала добавьте спикеров, затем вы сможете их записывать на мероприятия."
        )
        return ConversationHandler.END

    keyboard = []
    for speaker_profile in speakers:
        display_name = speaker_profile.name if speaker_profile.name else \
            (speaker_profile.user.nic_tg if speaker_profile.user and speaker_profile.user.nic_tg else \
                 (f"User ID: {speaker_profile.user.tg_id}" if speaker_profile.user else "Имя не указано"))

        callback_data = f"{SPEAKER_CHOICE_CALLBACK_PREFIX}{speaker_profile.id}"
        button_text = f"{display_name}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])

    keyboard.append([InlineKeyboardButton("<< Назад к выбору мероприятия",
                                              callback_data="manage_speakers_back_to_event_choice")])
    keyboard.append([InlineKeyboardButton("Отмена", callback_data="manage_speakers_cancel")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        query.edit_message_reply_markup(reply_markup=reply_markup)
    except Exception as e:
        print(f"Ошибка при попытке изменить клавиатуру: {e}. Отправляем новое сообщение.")
        query.message.reply_text("Выберите спикера:", reply_markup=reply_markup)

    return MANAGE_SPEAKERS_CHOOSE_SPEAKER


def manage_speakers_back_to_event_choice(update: Update, context: CallbackContext):
    """Возвращает пользователя к выбору мероприятия."""

    query = update.callback_query
    query.answer()

    if 'selected_event_id' in context.user_data:
        del context.user_data['selected_event_id']

    events = Event.objects.all().order_by('start_event')
    if not events.exists():
        query.edit_message_text("Нет мероприятий для выбора.")
        return ConversationHandler.END

    keyboard = []
    for event in events:
        callback_data = f"{EVENT_CHOICE_CALLBACK_PREFIX}{event.id}"
        event_date_str = event.start_event.strftime('%d.%m.%Y') if event.start_event else "Дата не указана"
        button_text = f"{event.name} ({event_date_str})"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])

    keyboard.append([InlineKeyboardButton("Отмена", callback_data="manage_speakers_cancel")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    query.edit_message_text(
        "Выберите мероприятие снова:",
        reply_markup=reply_markup
    )
    return MANAGE_SPEAKERS_CHOOSE_EVENT


def manage_speakers_cancel_conversation(update: Update, context: CallbackContext):
    """Отменяет диалог управления спикерами."""
    query = update.callback_query
    query.answer()
    user = query.from_user

    message_text = "Управление спикерами отменено."
    query.edit_message_text(text=message_text)
    print(f"Организатор {user.id} отменил диалог управления спикерами.")

    # Очищаем user_data, если там что-то было сохранено для этого диалога
    if 'selected_event_id' in context.user_data:
        del context.user_data['selected_event_id']
    if 'selected_speaker_id' in context.user_data:  # на будущее
        del context.user_data['selected_speaker_id']

    return ConversationHandler.END


def handle_speaker_selection(update: Update, context: CallbackContext):
    """
        Обрабатывает выбор спикера организатором.
        Сохраняет ID спикера и запрашивает детали сессии/доклада.
    """
    query = update.callback_query
    query.answer()
    user = query.from_user # сейчас орг

    try:
        speaker_id_str = query.data.replace(SPEAKER_CHOICE_CALLBACK_PREFIX, "")
        speaker_id = int(speaker_id_str)
    except (ValueError, TypeError):
        print(f"ОШИБКА: Не удалось извлечь speaker_id из callback_data: {query.data}")
        query.edit_message_text("Произошла ошибка при выборе спикера. Попробуйте снова.")
        return ConversationHandler.END

    context.user_data['selected_speaker_id'] = speaker_id

    try:
        selected_speaker = Speaker.objects.get(id=speaker_id)

        speaker_display_name = selected_speaker.name if selected_speaker.name else \
            (selected_speaker.user.nic_tg if selected_speaker.user and selected_speaker.user.nic_tg else \
                 (f"User ID: {selected_speaker.user.tg_id}" if selected_speaker.user else "Имя не указано"))

        # Получаем ID ранее выбранного мероприятия из user_data
        selected_event_id = context.user_data.get('selected_event_id')
        if not selected_event_id:
            print(f"ОШИБКА: selected_event_id не найден в user_data для организатора {user.id}")
            query.edit_message_text("Произошла ошибка: не найдено выбранное мероприятие. Начните заново.")
            return ConversationHandler.END

        selected_event = Event.objects.get(id=selected_event_id)  # Предполагаем, что мероприятие существует

        print(
            f"Организатор {user.id} выбрал спикера ID: {speaker_id} ({speaker_display_name}) для мероприятия '{selected_event.name}'.")

        message_text = (
            f'Выбран спикер: {speaker_display_name}\n'
            f'Для мероприятия: {selected_event.name}\n\n'
            'Теперь, пожалуйста, введите детали для его выступления.\n'
            'Отправьте ОДНО сообщение, где каждая деталь на новой строке, в следующем формате:\n\n'
            'Тема доклада: [Полное название темы]\n'
            'Начало: [ДД.ММ.ГГГГ ЧЧ:ММ]\n'
            'Окончание: [ДД.ММ.ГГГГ ЧЧ:ММ]\n\n'
            'Пример:\n'
            'Тема доклада: Введение в асинхронный Python\n'
            'Начало: 25.12.2024 10:00\n'
            'Окончание: 25.12.2024 10:45'
        )
        query.edit_message_text(text=message_text)

    except Speaker.DoesNotExist:
        print(f"ОШИБКА: Спикер с ID {speaker_id} не найден в БД.")
        query.edit_message_text("Выбранный спикер не найден. Пожалуйста, начните заново.")
        return ConversationHandler.END
    except Event.DoesNotExist:
        print(
            f"ОШИБКА: Мероприятие с ID {context.user_data.get('selected_event_id')} не найдено в БД при выборе спикера.")
        query.edit_message_text("Произошла ошибка с выбранным мероприятием. Начните заново.")
        return ConversationHandler.END

    return MANAGE_SPEAKERS_SESSION_DETAILS


def handle_session_details_input(update: Update, context: CallbackContext):
    """
        Обрабатывает введенные организатором детали сессии (тема, начало, окончание).
        Создает записи Session и SpeakerSession в БД.
    """

    user = update.effective_user
    text_input = update.message.text

    print(f"Организатор {user.id} ввел детали сессии: \n{text_input}")

    try:
        lines = text_input.strip().split('\n')
        details = {}
        for line in lines:
            if ':' in line:
                key, value = line.split(':', 1)
                processed_key = key.strip().lower()
                details[processed_key] = value.strip()
                details[key.strip().lower()] = value.strip()
            else:
                pass

        # Ожидаемые ключи
        topic_key = 'тема доклада'
        start_key = 'начало'
        end_key = 'окончание'

        session_topic = details.get(topic_key)
        start_time_str = details.get(start_key)
        end_time_str = details.get(end_key)

        if not (session_topic and start_time_str and end_time_str):
            missing_parts = []
            if not session_topic: missing_parts.append("'Тема доклада'")
            if not start_time_str: missing_parts.append("'Начало'")
            if not end_time_str: missing_parts.append("'Окончание'")

            error_detail = f"Не найдены следующие обязательные части: {', '.join(missing_parts)}." \
                if missing_parts else "Формат ввода неверный."

            raise ValueError(f"{error_detail}\n"
                             "Пожалуйста, используйте формат:\n"
                             "Тема доклада: [Название]\n"
                             "Начало: [ДД.ММ.ГГГГ ЧЧ:ММ]\n"  
                             "Окончание: [ДД.ММ.ГГГГ ЧЧ:ММ]")

        datetime_format = "%d.%m.%Y %H:%M"
        start_datetime = datetime.strptime(start_time_str, datetime_format)
        end_datetime = datetime.strptime(end_time_str, datetime_format)

        if start_datetime >= end_datetime:
            raise ValueError("Время начала должно быть раньше времени окончания.")

    except ValueError as e:
        error_message = f"Ошибка в данных: {e}\n\nПожалуйста, попробуйте ввести детали снова, соблюдая формат."
        update.message.reply_text(error_message)
        return MANAGE_SPEAKERS_SESSION_DETAILS
    except Exception as e:
        print(f"Непредвиденная ошибка парсинга деталей сессии: {e}")
        update.message.reply_text(
            "Произошла ошибка при обработке введенных данных. "
            "Пожалуйста, проверьте формат и попробуйте снова.\n\n"
            "Тема доклада: [Название]\n"
            "Начало (ДД.ММ.ГГГГ ЧЧ:ММ): [Дата и время]\n"
            "Окончание (ДД.ММ.ГГГГ ЧЧ:ММ): [Дата и время]"
        )
        return MANAGE_SPEAKERS_SESSION_DETAILS

    selected_event_id = context.user_data.get('selected_event_id')
    selected_speaker_id = context.user_data.get('selected_speaker_id')

    if not selected_event_id or not selected_speaker_id:
        print("ОШИБКА: selected_event_id или selected_speaker_id не найдены в user_data.")
        update.message.reply_text(
            "Произошла внутренняя ошибка (потерян контекст). Пожалуйста, начните процесс записи спикера заново с помощью команды /start и выбора роли организатора.")

        context.user_data.pop('selected_event_id', None)
        context.user_data.pop('selected_speaker_id', None)
        return ConversationHandler.END

    try:
        event_instance = Event.objects.get(id=selected_event_id)
        speaker_instance = Speaker.objects.get(id=selected_speaker_id)

        new_session = Session.objects.create(
            event=event_instance,
            title=session_topic,
            start_session=start_datetime,
            finish_session=end_datetime
        )
        print(f"Создана сессия: ID={new_session.id}, Тема='{new_session.title}'")



        speaker_session_instance = SpeakerSession.objects.create(
            session=new_session,
            speaker=speaker_instance,
            topic=session_topic,
            start_session=start_datetime,
            finish_session=end_datetime
        )
        print(
            f"Создана SpeakerSession: ID={speaker_session_instance.id} для спикера {speaker_instance.id} и сессии {new_session.id}")

        speaker_display_name = speaker_instance.name or \
                               (speaker_instance.user.nic_tg if speaker_instance.user else None) or \
                               f"ID {speaker_instance.user.tg_id}"

        success_message = (
            f"Успешно! Спикер '{speaker_display_name}' записан на мероприятие '{event_instance.name}'.\n"
            f"Доклад: '{session_topic}'\n"
            f"Время: с {start_datetime.strftime(datetime_format)} по {end_datetime.strftime(datetime_format)}"
        )
        update.message.reply_text(success_message)


        context.user_data.pop('selected_event_id', None)
        context.user_data.pop('selected_speaker_id', None)


        show_main_interface_for_role(update, context, role_name="Организатор",
                                     greeting_message="Вы вернулись в меню организатора.")
        return ConversationHandler.END

    except Event.DoesNotExist:
        update.message.reply_text("Ошибка: выбранное ранее мероприятие не найдено. Начните заново.")
    except Speaker.DoesNotExist:
        update.message.reply_text("Ошибка: выбранный ранее спикер не найден. Начните заново.")
    except Exception as e:
        print(f"Ошибка при создании записей в БД: {e}")
        update.message.reply_text(
            "Произошла ошибка при сохранении данных. Попробуйте снова или обратитесь к администратору.")


    context.user_data.pop('selected_event_id', None)
    context.user_data.pop('selected_speaker_id', None)
    return ConversationHandler.END


def add_prospective_speaker_start(update: Update, context: CallbackContext):
    '''Начинает диалог добавления нового потенциального спикера. Запрашивает имя'''

    user = update.effective_user

    user_tg_instance = UserTg.objects.filter(tg_id=user.id).first()
    if not (user_tg_instance and user_tg_instance.is_organizator):
        update.message.reply_text("Эта функция доступна только для организаторов.")
        return ConversationHandler.END

    update.message.reply_text(
        "Вы собираетесь добавить нового потенциального спикера в резерв.\n"
        "Пожалуйста, введите Имя (или ФИО) спикера.\n\n"
        "Чтобы отменить, введите /cancel_add_speaker"
    )
    return PS_TYPING_NAME


def ps_handle_contact(update: Update, context: CallbackContext):
    """Сохраняет контакты и запрашивает заметки/темы."""

    user = update.effective_user
    entered_contact = update.message.text.strip()

    if not entered_contact:
        update.message.reply_text(
            'Контактная информация не может быть пустой. Введите контакты или /cancel_add_speaker.')
        return PS_TYPING_CONTACT

    context.user_data['prospective_speaker_contact'] = entered_contact
    speaker_name = context.user_data.get('prospective_speaker_name', 'спикера')
    print(f'Организатор {user.id} ввел контакты для {speaker_name}: {entered_contact}')

    update.message.reply_text(
        f'Контактная информация сохранена: {entered_contact}.\n'
        'Теперь, пожалуйста, введите любые заметки о спикере или темы, которые он мог бы осветить (можно оставить пустым, нажав /skip_notes).\n\n'
        'Чтобы отменить весь процесс, введите /cancel_add_speaker'
    )
    return PS_TYPING_NOTES


def ps_handle_notes_and_save(update: Update, context: CallbackContext):
    """Сохраняет заметки (если есть) и создает запись ProspectiveSpeaker в БД."""

    user = update.effective_user
    entered_notes = update.message.text.strip()

    if not entered_notes:
        update.message.reply_text(
            "Заметки не могут быть пустым сообщением. Введите текст или /skip_notes для пропуска, или /cancel_add_speaker для отмены.")
        return PS_TYPING_NOTES

    print(f"Организатор {user.id} ввел заметки: {entered_notes}")
    context.user_data['prospective_speaker_notes'] = entered_notes

    name = context.user_data.get('prospective_speaker_name')
    contact = context.user_data.get('prospective_speaker_contact')
    notes = context.user_data.get('prospective_speaker_notes')

    if not name or not contact:
        print("ОШИБКА: Потеряны имя или контакты в user_data при добавлении потенциального спикера.")
        update.message.reply_text("Произошла внутренняя ошибка. Пожалуйста, начните заново.")
        # Очистка user_data
        context.user_data.pop('prospective_speaker_name', None)
        context.user_data.pop('prospective_speaker_contact', None)
        context.user_data.pop('prospective_speaker_notes', None)
        return ConversationHandler.END

    try:
        new_prospective_speaker = ProspectiveSpeaker.objects.create(
            name=name,
            contact_info=contact,
            notes=notes
        )
        print(f"Создана запись ProspectiveSpeaker: ID={new_prospective_speaker.id}, Имя='{name}'")
        update.message.reply_text(
            f"Успешно! Потенциальный спикер '{name}' добавлен в резерв.\n"
            f"Контакты: {contact}\n"
            f"Заметки: {notes if notes else 'Нет'}"
        )
    except Exception as e:
        print(f"ОШИБКА при создании ProspectiveSpeaker: {e}")
        update.message.reply_text("Произошла ошибка при сохранении данных. Попробуйте снова.")

        context.user_data.pop('prospective_speaker_name', None)
        context.user_data.pop('prospective_speaker_contact', None)
        context.user_data.pop('prospective_speaker_notes', None)
        return ConversationHandler.END

    context.user_data.pop('prospective_speaker_name', None)
    context.user_data.pop('prospective_speaker_contact', None)
    context.user_data.pop('prospective_speaker_notes', None)

    show_main_interface_for_role(update, context, role_name="Организатор",
                                 greeting_message="Вы вернулись в меню организатора.")
    return ConversationHandler.END


def ps_cancel_add_speaker(update: Update, context: CallbackContext) -> int:
    """Отменяет диалог добавления потенциального спикера."""
    user = update.effective_user
    print(f'Организатор {user.id} отменил добавление потенциального спикера.')
    update.message.reply_text('Добавление нового потенциального спикера отменено.')


    context.user_data.pop('prospective_speaker_name', None)
    context.user_data.pop('prospective_speaker_contact', None)
    context.user_data.pop('prospective_speaker_notes', None)

    show_main_interface_for_role(update, context, role_name='Организатор',
                                 greeting_message='Вы вернулись в меню организатора.')
    return ConversationHandler.END

def ps_handle_name(update: Update, context: CallbackContext):
    '''Сохраняет имя потенциального спикера и запрашивает контактную информацию'''

    user = update.effective_user
    entered_name = update.message.text.strip()

    if not entered_name:
        update.message.reply_text("Имя не может быть пустым. Пожалуйста, введите имя или /cancel_add_speaker.")
        return PS_TYPING_NAME

    context.user_data['prospective_speaker_name'] = entered_name
    print(f"Организатор {user.id} ввел имя для нового спикера: {entered_name}")

    update.message.reply_text(
        f'Отлично, имя: {entered_name}.\n'
        'Теперь введите контактную информацию (например, email, ссылка на Telegram/LinkedIn, или телефон).\n\n'
        'Чтобы отменить, введите /cancel_add_speaker'
    )
    return PS_TYPING_CONTACT


def ps_skip_notes_and_save(update: Update, context: CallbackContext):
    '''Обрабатывает команду /skip_notes, сохраняет спикера без заметок.'''

    user = update.effective_user
    print(f"Организатор {user.id} использовал /skip_notes.")

    context.user_data['prospective_speaker_notes'] = None

    name = context.user_data.get('prospective_speaker_name')
    contact = context.user_data.get('prospective_speaker_contact')
    notes = context.user_data.get('prospective_speaker_notes')

    if not name or not contact:
        print("ОШИБКА: Потеряны имя или контакты в user_data при добавлении (пропуск заметок).")
        update.message.reply_text("Произошла внутренняя ошибка. Пожалуйста, начните заново.")
        context.user_data.pop('prospective_speaker_name', None)
        context.user_data.pop('prospective_speaker_contact', None)
        context.user_data.pop('prospective_speaker_notes', None)
        return ConversationHandler.END

    try:
        new_prospective_speaker = ProspectiveSpeaker.objects.create(
            name=name,
            contact_info=contact,
            notes=notes
        )
        print(f"Создана запись ProspectiveSpeaker (без заметок): ID={new_prospective_speaker.id}, Имя='{name}'")
        update.message.reply_text(
            f"Успешно! Потенциальный спикер '{name}' добавлен в резерв (без дополнительных заметок).\n"
            f"Контакты: {contact}"
        )
    except Exception as e:
        print(f"ОШИБКА при создании ProspectiveSpeaker (пропуск заметок): {e}")
        update.message.reply_text("Произошла ошибка при сохранении данных. Попробуйте снова.")
        context.user_data.pop('prospective_speaker_name', None)
        context.user_data.pop('prospective_speaker_contact', None)
        context.user_data.pop('prospective_speaker_notes', None)
        return ConversationHandler.END

    context.user_data.pop('prospective_speaker_name', None)
    context.user_data.pop('prospective_speaker_contact', None)
    context.user_data.pop('prospective_speaker_notes', None)

    show_main_interface_for_role(update, context, role_name="Организатор",
                                 greeting_message="Вы вернулись в меню организатора.")
    return ConversationHandler.END


