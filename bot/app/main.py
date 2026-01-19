import threading
import requests
from flask import Flask, request, jsonify

import telebot
from telebot.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from .config import BOT_TOKEN, ADMIN_IDS, WEBAPP_URL, API_BASE_URL, INTERNAL_SECRET
from .keyboards import main_kb, admin_kb, admin_main_kb, guests_inline_kb

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
app = Flask(__name__)
BOT_USERNAME = None
ADMIN_STATE = {}

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

def api_headers():
    return {"x-internal-secret": INTERNAL_SECRET}

def api_get(path: str, params: dict | None = None):
    return requests.get(f"{API_BASE_URL}{path}", headers=api_headers(), params=params, timeout=8)

def api_post(path: str, payload: dict):
    return requests.post(f"{API_BASE_URL}{path}", headers=api_headers(), json=payload, timeout=8)

def api_delete(path: str):
    return requests.delete(f"{API_BASE_URL}{path}", headers=api_headers(), timeout=8)

def ensure_bot_username():
    global BOT_USERNAME
    if BOT_USERNAME:
        return BOT_USERNAME
    try:
        BOT_USERNAME = bot.get_me().username
    except Exception:
        BOT_USERNAME = ""
    return BOT_USERNAME

def render_guests(chat_id: int, page: int = 1, rsvp: str | None = None, q: str | None = None):
    params = {"page": page, "page_size": 10}
    if rsvp:
        params["rsvp"] = rsvp
    if q:
        params["q"] = q
    res = api_get("/api/admin/guests", params=params)
    if not res.ok:
        bot.send_message(chat_id, "Не удалось загрузить гостей.")
        return
    data = res.json()
    items = data.get("items", [])
    total = data.get("total", 0)
    text_lines = [f"<b>Гости</b> (стр. {data.get('page')}, всего {total})"]
    if total == 0:
        text_lines.append("В dev БД может быть пустой. В prod БД хранится в backend/data/app.db (bind-mount).")
    for it in items:
        text_lines.append(
            f"#{it['guest_id']} — {it.get('name') or '—'} | RSVP: {it.get('rsvp')}"
        )
    has_prev = page > 1
    has_next = page * data.get("page_size", 10) < total
    kb = guests_inline_kb(page, rsvp, q, has_prev, has_next)
    bot.send_message(chat_id, "\n".join(text_lines), reply_markup=kb)
    ADMIN_STATE[chat_id] = {"mode": "guests", "page": page, "rsvp": rsvp, "q": q}

@bot.message_handler(commands=["start"])
def start(m: Message):
    # Accept invite token if present
    parts = (m.text or "").split(maxsplit=1)
    if len(parts) > 1 and parts[1].startswith("inv_"):
        token = parts[1].replace("inv_", "", 1)
        res = api_post("/api/family/accept", {"token": token, "telegram_user_id": m.from_user.id})
        if res.ok:
            bot.send_message(m.chat.id, "Приглашение принято. Вы теперь вместе.")
        else:
            bot.send_message(m.chat.id, "Не удалось принять приглашение.")
    reply = admin_main_kb(WEBAPP_URL) if is_admin(m.from_user.id) else main_kb(WEBAPP_URL)
    bot.send_message(
        m.chat.id,
        "Привет! Это свадебный бот.\nОткройте приложение и заполните анкету.",
        reply_markup=reply
    )

@bot.message_handler(commands=["admin"])
def admin_help(m: Message):
    if not is_admin(m.from_user.id):
        return
    bot.send_message(m.chat.id, "Админ-меню:", reply_markup=admin_kb())

@bot.message_handler(commands=["invite"])
def invite_family(m: Message):
    ensure_bot_username()
    res = api_post("/api/family/invite", {"telegram_user_id": m.from_user.id})
    if not res.ok:
        bot.send_message(m.chat.id, "Не удалось создать приглашение.")
        return
    token = res.json().get("token")
    link = f"https://t.me/{BOT_USERNAME}?start=inv_{token}" if BOT_USERNAME else f"inv_{token}"
    bot.send_message(m.chat.id, f"Приглашение для пары:\n{link}")

@bot.message_handler(func=lambda m: is_admin(m.from_user.id) and m.text == "Гости")
def admin_guests(m: Message):
    render_guests(m.chat.id, page=1)

@bot.message_handler(func=lambda m: is_admin(m.from_user.id) and m.text == "Инфо о мероприятии")
def admin_event_info(m: Message):
    res = api_get("/api/admin/event")
    if not res.ok:
        bot.send_message(m.chat.id, "Не удалось получить информацию.")
        return
    data = res.json()
    bot.send_message(m.chat.id, f"<b>Текущее инфо:</b>\n{data.get('content','')}")
    bot.send_message(m.chat.id, "Отправьте новый текст для обновления.")
    ADMIN_STATE[m.chat.id] = {"mode": "edit_event"}

@bot.message_handler(func=lambda m: is_admin(m.from_user.id) and m.text == "Удалить гостя")
def admin_delete_guest(m: Message):
    bot.send_message(m.chat.id, "Введите ID гостя или текст для поиска.")
    ADMIN_STATE[m.chat.id] = {"mode": "delete_lookup"}

@bot.message_handler(func=lambda m: is_admin(m.from_user.id) and m.text == "Где БД?")
def admin_db_info(m: Message):
    bot.send_message(
        m.chat.id,
        "БД SQLite хранится в backend/data/app.db.\n"
        "В prod это файл на сервере (bind-mount), в git он не хранится.\n"
        "В dev БД может быть пустой/отсутствовать до первого запуска."
    )

@bot.message_handler(func=lambda m: is_admin(m.from_user.id) and m.text == "DB Health")
def admin_db_health(m: Message):
    res = api_get("/api/admin/db-health")
    if not res.ok:
        bot.send_message(m.chat.id, "Не удалось получить DB Health.")
        return
    data = res.json()
    tables = ", ".join(data.get("tables", [])) or "—"
    counts = data.get("counts", {})
    text = (
        "<b>DB Health</b>\n"
        f"Path: {data.get('path')}\n"
        f"Exists: {data.get('exists')} | Size: {data.get('size_bytes')} bytes\n"
        f"Tables: {tables}\n"
        f"Guests: {counts.get('guests', 0)}, Profiles: {counts.get('profiles', 0)}, "
        f"Families: {counts.get('family_groups', 0)}, Invites: {counts.get('invite_tokens', 0)}"
    )
    bot.send_message(m.chat.id, text)

@bot.message_handler(func=lambda m: is_admin(m.from_user.id) and m.text == "Очистить базу")
def admin_clear_db(m: Message):
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("Да, продолжить", callback_data="clear_db:step1"))
    kb.add(InlineKeyboardButton("Нет", callback_data="clear_db:cancel"))
    bot.send_message(m.chat.id, "Вы уверены? Это удалит всех гостей и анкеты. Продолжить?", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("clear_db:"))
def clear_db_cb(c):
    if not is_admin(c.from_user.id):
        return
    step = c.data.split(":", 1)[1]
    if step == "cancel":
        bot.send_message(c.message.chat.id, "Отменено.")
        return
    if step == "step1":
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("Удалить ВСЕ", callback_data="clear_db:step2"))
        kb.add(InlineKeyboardButton("Нет", callback_data="clear_db:cancel"))
        bot.send_message(
            c.message.chat.id,
            "Последнее подтверждение: удалить ВСЕ данные без возможности восстановления?",
            reply_markup=kb
        )
        return
    if step == "step2":
        res = api_post("/api/admin/clear-db", {})
        if res.ok:
            data = res.json()
            bot.send_message(
                c.message.chat.id,
                "База очищена.\n"
                f"guests: {data.get('guests')}\n"
                f"profiles: {data.get('profiles')}\n"
                f"groups: {data.get('groups')}\n"
                f"group_members: {data.get('group_members')}\n"
                f"family_groups: {data.get('family_groups')}\n"
                f"invite_tokens: {data.get('invite_tokens')}\n"
                f"change_log: {data.get('change_log')}"
            )
        else:
            bot.send_message(c.message.chat.id, "Не удалось очистить базу.")
        return

@bot.callback_query_handler(func=lambda c: c.data.startswith("guests:"))
def guests_filter_cb(c):
    if not is_admin(c.from_user.id):
        return
    _, flt = c.data.split(":", 1)
    rsvp = None if flt == "all" else flt
    render_guests(c.message.chat.id, page=1, rsvp=rsvp)

@bot.callback_query_handler(func=lambda c: c.data.startswith("guests_page:"))
def guests_page_cb(c):
    if not is_admin(c.from_user.id):
        return
    _, page, rsvp, q = c.data.split(":", 3)
    rsvp = rsvp or None
    q = q or None
    render_guests(c.message.chat.id, page=int(page), rsvp=rsvp, q=q)

@bot.callback_query_handler(func=lambda c: c.data.startswith("delete:"))
def delete_guest_cb(c):
    if not is_admin(c.from_user.id):
        return
    guest_id = c.data.split(":", 1)[1]
    res = api_delete(f"/api/admin/guest/{guest_id}")
    if res.ok:
        bot.send_message(c.message.chat.id, f"Гость #{guest_id} удалён.")
    else:
        bot.send_message(c.message.chat.id, "Не удалось удалить гостя.")

@bot.message_handler(func=lambda m: is_admin(m.from_user.id))
def admin_text_router(m: Message):
    state = ADMIN_STATE.get(m.chat.id, {})
    mode = state.get("mode")
    if mode == "guests":
        q = m.text.strip()
        render_guests(m.chat.id, page=1, rsvp=state.get("rsvp"), q=q)
        return
    if mode == "edit_event":
        res = api_post("/api/admin/event", {"content": m.text})
        if res.ok:
            bot.send_message(m.chat.id, "Информация обновлена.")
        else:
            bot.send_message(m.chat.id, "Не удалось обновить информацию.")
        ADMIN_STATE.pop(m.chat.id, None)
        return
    if mode == "delete_lookup":
        text = m.text.strip()
        if text.isdigit():
            guest_id = int(text)
            kb = InlineKeyboardMarkup()
            kb.add(InlineKeyboardButton("Удалить", callback_data=f"delete:{guest_id}"))
            kb.add(InlineKeyboardButton("Отмена", callback_data="cancel"))
            bot.send_message(m.chat.id, f"Удалить гостя #{guest_id}?", reply_markup=kb)
        else:
            render_guests(m.chat.id, page=1, q=text)
        return

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
