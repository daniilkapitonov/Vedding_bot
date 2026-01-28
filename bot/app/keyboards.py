from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def admin_kb(system_enabled: bool = False, animations_enabled: bool = True):
    label = "🔕 Отключить системные уведомления" if system_enabled else "🔔 Включить системные уведомления"
    anim_label = "✨ Анимации: ВКЛ" if animations_enabled else "✨ Анимации: ВЫКЛ"
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(KeyboardButton("Гости"), KeyboardButton("✏️ Редактировать инфо о событии"))
    kb.row(KeyboardButton("⏱ Редактировать тайминг"), KeyboardButton(label))
    kb.row(KeyboardButton(anim_label), KeyboardButton("Очистить базу"))
    kb.row(KeyboardButton("Удалить гостя"), KeyboardButton("DB Health"))
    return kb

def admin_main_kb(system_enabled: bool = False, animations_enabled: bool = True):
    label = "🔕 Отключить системные уведомления" if system_enabled else "🔔 Включить системные уведомления"
    anim_label = "✨ Анимации: ВКЛ" if animations_enabled else "✨ Анимации: ВЫКЛ"
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(KeyboardButton("Гости"), KeyboardButton("✏️ Редактировать инфо о событии"))
    kb.row(KeyboardButton("⏱ Редактировать тайминг"), KeyboardButton(label))
    kb.row(KeyboardButton(anim_label), KeyboardButton("Очистить базу"))
    kb.row(KeyboardButton("Удалить гостя"), KeyboardButton("DB Health"))
    return kb

def guests_inline_kb(page: int, rsvp: str | None, q: str | None, has_prev: bool, has_next: bool, items: list[dict] | None = None):
    kb = InlineKeyboardMarkup()
    kb.row(
        InlineKeyboardButton("Все", callback_data="guests:all"),
        InlineKeyboardButton("Приду", callback_data="guests:yes"),
        InlineKeyboardButton("Не приду", callback_data="guests:no"),
        InlineKeyboardButton("Не знаю", callback_data="guests:maybe"),
    )
    if items:
        for it in items:
            gid = it.get("guest_id")
            if gid:
                mark = "⭐" if it.get("best_friend") else "☆"
                kb.row(InlineKeyboardButton(f"{mark} #{gid}", callback_data=f"bf:{gid}"))
    nav = []
    if has_prev:
        nav.append(InlineKeyboardButton("←", callback_data=f"guests_page:{page-1}:{rsvp or ''}:{q or ''}"))
    if has_next:
        nav.append(InlineKeyboardButton("→", callback_data=f"guests_page:{page+1}:{rsvp or ''}:{q or ''}"))
    if nav:
        kb.row(*nav)
    return kb
