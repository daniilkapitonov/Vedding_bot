from telebot.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton

def main_kb(webapp_url: str):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("Открыть свадебное приложение", web_app=WebAppInfo(url=webapp_url)))
    return kb

def admin_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("Гости"), KeyboardButton("Инфо о мероприятии"))
    kb.add(KeyboardButton("Удалить гостя"), KeyboardButton("Где БД?"))
    kb.add(KeyboardButton("DB Health"))
    kb.add(KeyboardButton("Очистить базу"))
    return kb

def admin_main_kb(webapp_url: str):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("Открыть свадебное приложение", web_app=WebAppInfo(url=webapp_url)))
    kb.add(KeyboardButton("Гости"), KeyboardButton("Инфо о мероприятии"))
    kb.add(KeyboardButton("Удалить гостя"), KeyboardButton("Где БД?"))
    kb.add(KeyboardButton("DB Health"))
    kb.add(KeyboardButton("Очистить базу"))
    return kb

def guests_inline_kb(page: int, rsvp: str | None, q: str | None, has_prev: bool, has_next: bool):
    kb = InlineKeyboardMarkup()
    kb.row(
        InlineKeyboardButton("Все", callback_data="guests:all"),
        InlineKeyboardButton("Приду", callback_data="guests:yes"),
        InlineKeyboardButton("Не приду", callback_data="guests:no"),
        InlineKeyboardButton("Не знаю", callback_data="guests:maybe"),
    )
    nav = []
    if has_prev:
        nav.append(InlineKeyboardButton("←", callback_data=f"guests_page:{page-1}:{rsvp or ''}:{q or ''}"))
    if has_next:
        nav.append(InlineKeyboardButton("→", callback_data=f"guests_page:{page+1}:{rsvp or ''}:{q or ''}"))
    if nav:
        kb.row(*nav)
    return kb
