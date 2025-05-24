from telegram import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# ======================================================================
# ===============================ЮЗЕР===================================
# ======================================================================


def get_client_main_keyboard():
    keyboard_layout = [
        [KeyboardButton('Программы'),
         KeyboardButton('Актуалочка')]
    ]

    return ReplyKeyboardMarkup(
        keyboard=keyboard_layout,
        resize_keyboard=True,
        one_time_keyboard=False
    )


# ===========КЛАВЫ ЕСЛИ КЛИЕНТ В НАЧАЛЕ ТЫКНУЛ НА ---ПРОГРАММЫ--- ===========

def get_programs_section_details_keyboard():
    keyboard_layout = [
        [KeyboardButton('Подробнее'),
         KeyboardButton('Стать спикером'),
         KeyboardButton('Назад')]
    ]

    return ReplyKeyboardMarkup(
        keyboard=keyboard_layout,
        resize_keyboard=True,
        one_time_keyboard=False
    )


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
    keyboard_layout = [
        [KeyboardButton('Задать вопрос'),
         KeyboardButton('Поддержать'),
         KeyboardButton('Хронология'),
         KeyboardButton('Найти собеседника')
         ]
    ]

    return ReplyKeyboardMarkup(
        keyboard=keyboard_layout,
        resize_keyboard=True,
        one_time_keyboard=False
    )


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
