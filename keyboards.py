from telegram import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# ======================================================================
# ===============================ЮЗЕР===================================
# ======================================================================


def get_client_initial_keyboard():
    keyboard_layout = [
        [KeyboardButton('Программы')]
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard_layout,
        resize_keyboard=True,
        one_time_keyboard=False
    )


def get_client_main_keyboard():
    keyboard_layout = [
        [KeyboardButton('Программы'),
         KeyboardButton('Актуалочка'),
         KeyboardButton("Поддержать")
         ]
    ]

    return ReplyKeyboardMarkup(
        keyboard=keyboard_layout,
        resize_keyboard=True,
        one_time_keyboard=False
    )


# ===========КЛАВЫ ЕСЛИ КЛИЕНТ В НАЧАЛЕ ТЫКНУЛ НА ---ПРОГРАММЫ--- ===========


def get_programs_section_details_keyboard():
    keyboard_layout = [
        [
            InlineKeyboardButton('Подробнее', callback_data='program_details'),
            InlineKeyboardButton(
                'Стать спикером', callback_data='become_speaker'),
            InlineKeyboardButton('Назад', callback_data='go_back')
        ]
    ]

    return InlineKeyboardMarkup(keyboard_layout)


def get_favorite_keyboard():
    keyboard_layout = [
        [KeyboardButton('BACKEND'),
         KeyboardButton('FRONTEND'),
         KeyboardButton('FULL-STACK')]
    ]

    return ReplyKeyboardMarkup(
        keyboard=keyboard_layout,
        resize_keyboard=True,
        one_time_keyboard=False
    )


# ===========КЛАВЫ ЕСЛИ КЛИЕНТ В НАЧАЛЕ ТЫКНУЛ НА ---АКТУАЛОЧКА--- ===========

def get_actual_section_details_keyboard():
    keyboard = [
        [InlineKeyboardButton("Задать вопрос", callback_data="ask_question")],
        [InlineKeyboardButton("Хронология", callback_data="timeline")],
        [InlineKeyboardButton("Найти собеседника",
                              callback_data="find_partner")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_programs_section_details_second_keyboard():
    keyboard = [
        [InlineKeyboardButton(
            "Записаться", callback_data="register_for_event")],
        [InlineKeyboardButton("Назад", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(keyboard)
# ======================================================================
# ===============================СПИКЕР===================================
# ======================================================================


def get_speaker_main_keyboard():
    keyboard_layout = [
        [KeyboardButton('НАЧАТЬ ДОКЛАД'),
         KeyboardButton('ГЛЯНУТЬ ИВЕНТЫ')]
    ]

    return ReplyKeyboardMarkup(
        keyboard=keyboard_layout,
        resize_keyboard=True,
        one_time_keyboard=False
    )


def get_speaker_in_process_keyboard():
    keyboard_layout = [
        [KeyboardButton('ГЛЯНУТЬ ВОПРОСЫ'),
         KeyboardButton('ЗАВЕРШИТЬ ВЫСТУПЛЕНИЕ')]
    ]

    return ReplyKeyboardMarkup(
        keyboard=keyboard_layout,
        resize_keyboard=True,
        one_time_keyboard=False
    )


# ======================================================================
# ===============================ОРГАНИЗАТОР============================
# ======================================================================


def get_organizator_main_keyboard():
    keyboard_layout = [
        [KeyboardButton('ИВЕНТЫ'),
         KeyboardButton('ОРГАНИЗОВАТЬ РАССЫЛКУ')]
    ]

    return ReplyKeyboardMarkup(
        keyboard=keyboard_layout,
        resize_keyboard=True,
        one_time_keyboard=False
    )

# ======================================================================
# ===============================ЮТИЛСЫ============================
# ======================================================================


def go_back():
    keyboard_layout = [
        [KeyboardButton("Назад")]
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard_layout,
        resize_keyboard=True,
        one_time_keyboard=False
    )
