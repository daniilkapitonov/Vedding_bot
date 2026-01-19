from telebot.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo

def main_kb(webapp_url: str):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("Открыть свадебное приложение", web_app=WebAppInfo(url=webapp_url)))
    return kb
