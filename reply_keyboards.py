from telegram import ReplyKeyboardMarkup, KeyboardButton


def get_main_keyboard():
    '''Создает и возвращает основную ReplyKeyboardMarkup (клавиатуру ответов).'''

    keyboard_layout = [
        [KeyboardButton('Расписание'),
        KeyboardButton('Поддержать')]
    ]

    return ReplyKeyboardMarkup(
        keyboard=keyboard_layout,
        resize_keyboard=True,
        one_time_keyboard=False
    )

def get_organizer_keyboard():
    """Создает и возвращает ReplyKeyboardMarkup для Организатора."""
    keyboard_layout = [
    [KeyboardButton('Расписание'), KeyboardButton('Поддержать')],
    [KeyboardButton('Управление Спикерами')]
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard_layout,
        resize_keyboard=True,
        one_time_keyboard=False
    )