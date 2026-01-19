import threading
import requests
from flask import Flask, request, jsonify

import telebot
from telebot.types import Message

from .config import BOT_TOKEN, ADMIN_IDS, WEBAPP_URL, API_BASE_URL, INTERNAL_SECRET
from .keyboards import main_kb

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
app = Flask(__name__)

@bot.message_handler(commands=["start"])
def start(m: Message):
    bot.send_message(
        m.chat.id,
        "Привет! Это свадебный бот.\nОткройте приложение и заполните анкету.",
        reply_markup=main_kb(WEBAPP_URL)
    )

@bot.message_handler(commands=["admin"])
def admin_help(m: Message):
    if m.from_user.id not in ADMIN_IDS:
        return
    bot.send_message(m.chat.id, "Админ-команды: /start, /admin (позже добавим /broadcast и управление группами).")

@bot.message_handler(content_types=["photo"])
def photo_handler(m: Message):
    # MVP: просто подтверждаем и показываем file_id
    # Позже: можно передавать file_id в backend по initData через WebApp, а фото пусть грузят через WebApp UI и deep link в бота.
    fid = m.photo[-1].file_id
    bot.send_message(m.chat.id, f"Фото принято. file_id сохраните: <code>{fid}</code>\n(В MVP добавление фото делаем через WebApp позже.)")

@app.post("/internal/notify")
def internal_notify():
    secret = request.headers.get("x-internal-secret", "")
    if secret != INTERNAL_SECRET:
        return jsonify({"error": "forbidden"}), 403

    data = request.json or {}
    event = data.get("event")
    payload = data.get("payload", {})

    text = f"<b>Событие:</b> {event}\n<b>Данные:</b> <code>{payload}</code>"
    for admin_id in ADMIN_IDS:
        try:
            bot.send_message(admin_id, text)
        except Exception:
            pass
    return jsonify({"ok": True})

def run_flask():
    app.run(host="0.0.0.0", port=8081)

if __name__ == "__main__":
    t = threading.Thread(target=run_flask, daemon=True)
    t.start()

    bot.infinity_polling(timeout=30, long_polling_timeout=30)
