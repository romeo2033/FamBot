import secrets
from datetime import date
from urllib.parse import quote

import telebot
from telebot import types

from config import BOT_TOKEN, BOT_USERNAME
from db import fetchone, fetchall, execute, execute_returning_one


bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

# Временные действия пользователя: что он сейчас вводит
pending_actions: dict[int, str] = {}
wishlist_link_targets: dict[int, int] = {}


# ===== Утилиты по пользователям и парам =====

def get_or_create_user(tg_user) -> int:
    row = fetchone(
        "SELECT id FROM users WHERE telegram_id = %s",
        (tg_user.id,)
    )
    if row:
        return row["id"]

    execute(
        """
        INSERT INTO users (telegram_id, username, first_name, last_name)
        VALUES (%s, %s, %s, %s)
        """,
        (tg_user.id, tg_user.username, tg_user.first_name, tg_user.last_name)
    )
    row = fetchone("SELECT id FROM users WHERE telegram_id = %s", (tg_user.id,))
    return row["id"]


def get_pair_by_user(user_id: int):
    return fetchone(
        """
        SELECT * FROM pairs
        WHERE creator_user_id = %s OR partner_user_id = %s
        """,
        (user_id, user_id)
    )


# def create_pair_for_user(user_id: int):
#     invite_token = secrets.token_urlsafe(8)
#     execute(
#         """
#         INSERT INTO pairs (creator_user_id, invite_token)
#         VALUES (%s, %s)
#         """,
#         (user_id, invite_token)
#     )
#     return fetchone(
#         "SELECT * FROM pairs WHERE invite_token = %s",
#         (invite_token,)
#     )


def link_partner_to_pair(invite_token: str, partner_user_id: int):
    """
    Обработка перехода по ссылке-приглашению.

    Теперь пары создаются ТОЛЬКО здесь, сразу с двумя разными участниками.

    Возвращает (pair, reason):
      - pair: dict или None
      - reason:
          "ok"               – пара успешно создана
          "not_found"        – инвайт не найден / устарел
          "self"             – нельзя создать пару с самим собой
          "has_pair"         – этот пользователь уже в паре
          "creator_has_pair" – создатель инвайта уже в какой-то паре
    """
    invite = fetchone(
        "SELECT * FROM pair_invites WHERE invite_token = %s",
        (invite_token,)
    )
    if not invite:
        return None, "not_found"

    creator_user_id = invite["creator_user_id"]

    # Нельзя создать пару с самим собой
    if creator_user_id == partner_user_id:
        return None, "self"

    # Нельзя вступить в пару, если уже есть
    existing_for_partner = get_pair_by_user(partner_user_id)
    if existing_for_partner:
        return None, "has_pair"

    # На всякий случай: создатель тоже не должен уже быть в паре
    existing_for_creator = get_pair_by_user(creator_user_id)
    if existing_for_creator:
        return None, "creator_has_pair"

    # Создаём пару сразу с двумя людьми
    pair = execute_returning_one(
        """
        INSERT INTO pairs (creator_user_id, partner_user_id, invite_token)
        VALUES (%s, %s, %s)
        RETURNING *
        """,
        (creator_user_id, partner_user_id, invite_token)
    )

    # Инвайт больше не нужен
    execute("DELETE FROM pair_invites WHERE id = %s", (invite["id"],))

    return pair, "ok"


def set_pair_start_date(pair_id: int, start_date: date):
    execute(
        "UPDATE pairs SET start_date = %s WHERE id = %s",
        (start_date, pair_id)
    )


def set_pair_cloud_url(pair_id: int, url: str):
    execute(
        "UPDATE pairs SET cloud_drive_url = %s WHERE id = %s",
        (url, pair_id)
    )


# ===== Вишлисты =====

def add_wishlist_item(pair_id: int, owner_user_id: int, title: str, description: str | None = None):
    return execute_returning_one(
        """
        INSERT INTO wishlist_items (pair_id, owner_user_id, title, description, url)
        VALUES (%s, %s, %s, %s, NULL)
        RETURNING *
        """,
        (pair_id, owner_user_id, title, description)
    )


def get_wishlist_for_pair(pair_id: int):
    return fetchall(
        """
        SELECT w.*, u.first_name, u.username
        FROM wishlist_items w
        JOIN users u ON w.owner_user_id = u.id
        WHERE w.pair_id = %s
        ORDER BY w.created_at
        """,
        (pair_id,)
    )

def get_wishlist_for_owner(pair_id: int, owner_user_id: int):
    return fetchall(
        """
        SELECT w.*, u.first_name, u.username
        FROM wishlist_items w
        JOIN users u ON w.owner_user_id = u.id
        WHERE w.pair_id = %s AND w.owner_user_id = %s
        ORDER BY w.created_at
        """,
        (pair_id, owner_user_id)
    )


# ===== Клавиатура =====

def main_menu(user_id: int):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)

    # Всегда первая кнопка — Главное меню
    kb.add(types.KeyboardButton("🏠 Главное меню"))

    pair = get_pair_by_user(user_id)

    # Если пары нет — показываем "Добавить партнера"
    if not pair:
        kb.add(types.KeyboardButton("➕ Добавить партнера"))

    # Базовые кнопки
    kb.add(types.KeyboardButton("🎁 Список желаний"))
    kb.add(types.KeyboardButton("📁 Ссылка на общий диск"))
    kb.add(types.KeyboardButton("❤️ Дата начала отношений"))

    # Если пара есть — добавляем кнопку удаления
    if pair:
        kb.add(types.KeyboardButton("Удалить пару 💔"))

    return kb


# ===== /start =====
@bot.message_handler(func=lambda m: pending_actions.get(m.from_user.id) is not None)
def handle_pending(message: types.Message):
    tg_id = message.from_user.id
    action = pending_actions.pop(tg_id, None)

    user_id = get_or_create_user(message.from_user)

    # 1) Добавление желания
    if action == "wishlist_add":
        pair = get_pair_by_user(user_id)
        if not pair:
            bot.reply_to(message, "Сначала создайте пару через «➕ Добавить партнера».",
                         reply_markup=main_menu(user_id))
            return

        title = (message.text or "").strip()
        if not title:
            bot.reply_to(message, "Пустое желание не получится, напиши текст желания.")
            pending_actions[tg_id] = "wishlist_add"
            return

        item = add_wishlist_item(pair["id"], user_id, title)

        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton(
                "➕ Добавить ссылку",
                callback_data=f"wish_link:{item['id']}"
            )
        )

        bot.reply_to(
            message,
            f"Добавил в список: <b>{title}</b> 🎁",
            reply_markup=markup
        )

    # 2) Установка / изменение ссылки на диск
    elif action == "cloud_set":
        pair = get_pair_by_user(user_id)
        if not pair:
            bot.reply_to(message, "Сначала создайте пару через «➕ Добавить партнера».",
                         reply_markup=main_menu(user_id))
            return

        url = (message.text or "").strip()
        if not (url.startswith("http://") or url.startswith("https://")):
            bot.reply_to(message, "Похоже, это не ссылка. Пришли полный URL, начинающийся с http или https.")
            pending_actions[tg_id] = "cloud_set"
            return

        set_pair_cloud_url(pair["id"], url)
        bot.reply_to(message, f"Обновил ссылку на общий диск:\n{url}",
                     reply_markup=main_menu(user_id))

    # 3) Установка / изменение даты отношений
    elif action == "startdate_set":
        pair = get_pair_by_user(user_id)
        if not pair:
            bot.reply_to(message,
                         "Сначала создайте пару через «➕ Добавить партнера».",
                         reply_markup=main_menu(user_id))
            return

        import re
        from datetime import date as _date

        text = (message.text or "").strip()

        # формат ДД.ММ.ГГГГ
        m = re.match(r"^(\d{2})\.(\d{2})\.(\d{4})$", text)
        if not m:
            bot.reply_to(
                message,
                "Формат даты должен быть <b>ДД.ММ.ГГГГ</b>.\nПример: 14.02.2024\nПопробуй ещё раз."
            )
            pending_actions[tg_id] = "startdate_set"
            return

        day, month, year = map(int, m.groups())
        try:
            d = _date(year, month, day)
        except ValueError:
            bot.reply_to(message, "Похоже, дата некорректна. Проверь день и месяц.")
            pending_actions[tg_id] = "startdate_set"
            return

        set_pair_start_date(pair["id"], d)

        bot.reply_to(
            message,
            f"Запомнил дату начала отношений: <b>{text}</b> ❤️",
            reply_markup=main_menu(user_id)
        )
        # 4) Удаление желания по номеру
    elif action == "wishlist_delete":
        pair = get_pair_by_user(user_id)
        if not pair:
            bot.reply_to(
                message,
                "Сначала создайте пару через «➕ Добавить партнера».",
                reply_markup=main_menu(user_id)
            )
            return

        text = (message.text or "").strip()
        if not text.isdigit():
            bot.reply_to(message, "Нужен номер желания (целое число). Попробуй ещё раз.")
            pending_actions[tg_id] = "wishlist_delete"
            return

        index = int(text)

        items = get_wishlist_for_owner(pair["id"], user_id)
        if not items:
            bot.reply_to(message, "Список желаний уже пуст 🙃", reply_markup=main_menu(user_id))
            return

        if index < 1 or index > len(items):
            bot.reply_to(
                message,
                f"Номер вне диапазона. Сейчас в списке {len(items)} желаний.\n"
                "Напиши номер из списка.",
            )
            pending_actions[tg_id] = "wishlist_delete"
            return

        item = items[index - 1]
        execute("DELETE FROM wishlist_items WHERE id = %s", (item["id"],))

        bot.reply_to(
            message,
            f"Удалил желание №{index}: <b>{item['title']}</b> 🗑",
            reply_markup=main_menu(user_id)
        )
    elif action == "wishlist_link":
        pair = get_pair_by_user(user_id)
        if not pair:
            bot.reply_to(
                message,
                "Сначала создайте пару через «➕ Добавить партнера».",
                reply_markup=main_menu(user_id)
            )
            return

        item_id = wishlist_link_targets.get(tg_id)
        if not item_id:
            bot.reply_to(
                message,
                "Не удалось понять, к какому желанию добавить ссылку. Попробуй снова.",
                reply_markup=main_menu(user_id)
            )
            return

        url = (message.text or "").strip()
        if not (url.startswith("http://") or url.startswith("https://")):
            bot.reply_to(
                message,
                "Похоже, это не ссылка. Пришли полный URL, начинающийся с http:// или https://."
            )
            # оставляем pending_actions и wishlist_link_targets как есть
            return

        # Привязываем ссылку к желанию
        execute(
            "UPDATE wishlist_items SET url = %s WHERE id = %s",
            (url, item_id)
        )

        # Чистим состояние
        wishlist_link_targets.pop(tg_id, None)

        bot.reply_to(
            message,
            "Ссылку добавил к желанию 🔗",
            reply_markup=main_menu(user_id)
        )
    else:
        bot.reply_to(
            message,
            "Я запутался в том, что ты хотел сделать. Попробуй ещё раз через меню.",
            reply_markup=main_menu(user_id)
        )


@bot.message_handler(commands=["start"])
def start_cmd(message: types.Message):
    from datetime import date as _date

    user_id = get_or_create_user(message.from_user)
    parts = message.text.split()

    # === deep-link: подключение партнёра ===
    if len(parts) > 1 and parts[1].startswith("inv_"):
        invite_token = parts[1][4:]
        pair, reason = link_partner_to_pair(invite_token, user_id)

        if not pair:
            if reason == "not_found":
                text = "Похоже, эта ссылка устарела или неверна 🙁"
            elif reason == "self":
                text = (
                    "Хитро 😏\n\n"
                    "Но пару с самим собой создать нельзя.\n"
                    "Отправь ссылку своему настоящему партнёру 💌"
                )
            elif reason == "has_pair":
                text = (
                    "У тебя уже есть пара 💑\n\n"
                    "Нельзя одновременно состоять в двух парах.\n"
                    "Сначала удали текущую пару, если хочешь создать новую."
                )
            elif reason == "creator_has_pair":
                text = (
                    "Создатель этой ссылки уже состоит в паре.\n\n"
                    "Пусть он удалит текущую пару или создаст новую ссылку позже."
                )
            else:
                text = "Не удалось присоединиться по этой ссылке 🙁"

            bot.reply_to(message, text, reply_markup=main_menu(user_id))
            return

        # успешное присоединение
        bot.send_message(
            message.chat.id,
            "🎉 Вы успешно стали парой!\nТеперь вам доступен общий список желаний и напоминания 💑",
            reply_markup=main_menu(user_id)
        )

        # Уведомляем создателя пары
        creator = fetchone("SELECT telegram_id FROM users WHERE id = %s", (pair["creator_user_id"],))
        if creator:
            bot.send_message(
                creator["telegram_id"],
                f"💌 Ваш партнёр @{message.from_user.username or message.from_user.id} присоединился!",
                reply_markup=main_menu(pair["creator_user_id"])
            )
        return

    # === обычный /start ===
    pair = get_pair_by_user(user_id)

    # Если пары нет ИЛИ партнёр ещё не присоединился — ведём себя как "партнёра нет"
    if not pair:
        bot.send_message(
            message.chat.id,
            "Привет! Я бот для пар 💑\n\n"
            "Нажми «➕ Добавить партнера», чтобы создать пару и получить ссылку-приглашение.",
            reply_markup=main_menu(user_id)
        )
        return

    # === Пара есть и у неё есть оба участника ===

    # Определяем, кто партнёр
    if pair["creator_user_id"] == user_id:
        partner_id = pair["partner_user_id"]
    else:
        partner_id = pair["creator_user_id"]

    partner = fetchone("SELECT username, first_name FROM users WHERE id = %s", (partner_id,))

    partner_name = (
        f"@{partner['username']}" if partner and partner["username"] else
        partner["first_name"] if partner and partner["first_name"] else
        "ваш партнёр"
    )

    # Время вместе, если есть дата
    if pair["start_date"]:
        start = pair["start_date"]
        today = _date.today()

        years = today.year - start.year
        if (today.month, today.day) < (start.month, start.day):
            years -= 1

        last_anniv = _date(start.year + years, start.month, start.day)

        months = (today.year - last_anniv.year) * 12 + (today.month - last_anniv.month)
        if today.day < start.day:
            months -= 1
        if months < 0:
            months = 0

        together_text = f"Вы вместе уже <b>{years}</b> г. <b>{months}</b> м. 💞"
    else:
        together_text = "Вы ещё не указали дату начала отношений 💌"

    text = (
        "Привет! Я бот для пар 💑\n\n"
        f"Твой партнёр: <b>{partner_name}</b>\n"
        f"{together_text}\n\n"
        "Вы крутышки! Продолжайте радовать друг друга 💕"
    )

    bot.send_message(
        message.chat.id,
        text,
        reply_markup=main_menu(user_id),
        parse_mode="HTML"
    )


# ===== Добавить партнёра =====

@bot.message_handler(func=lambda m: m.text == "➕ Добавить партнера")
def add_partner(message: types.Message):
    user_id = get_or_create_user(message.from_user)

    # Если уже есть пара – новых создавать нельзя
    pair = get_pair_by_user(user_id)
    if pair:
        bot.reply_to(
            message,
            "У тебя уже есть пара 💑\n\n"
            "Если хотите сменить партнёра — сначала удалите текущую пару.",
            reply_markup=main_menu(user_id)
        )
        return

    # Создаём / берём существующее приглашение
    invite = get_or_create_invite_for_user(user_id)
    invite_token = invite["invite_token"]

    deep_link_param = "inv_" + invite_token
    deep_link = f"https://t.me/{BOT_USERNAME}?start={quote(deep_link_param)}"

    bot.reply_to(
        message,
        "Вот ссылка для вашего партнёра:\n"
        f"{deep_link}\n\n"
        "Отправьте её тому, с кем хотите быть в паре 💌",
        reply_markup=main_menu(user_id)
    )

def get_or_create_invite_for_user(user_id: int):
    invite = fetchone(
        "SELECT * FROM pair_invites WHERE creator_user_id = %s",
        (user_id,)
    )
    if invite:
        return invite

    token = secrets.token_urlsafe(8)
    execute(
        """
        INSERT INTO pair_invites (creator_user_id, invite_token)
        VALUES (%s, %s)
        """,
        (user_id, token)
    )
    return fetchone(
        "SELECT * FROM pair_invites WHERE creator_user_id = %s",
        (user_id,)
    )

@bot.message_handler(func=lambda m: m.text == "🏠 Главное меню")
def go_main_menu(message: types.Message):
    # просто вызываем /start как функцию
    start_cmd(message)


# ===== Список желаний =====

@bot.message_handler(func=lambda m: m.text == "🎁 Список желаний")
def wishlist_entry(message: types.Message):
    user_id = get_or_create_user(message.from_user)
    show_wishlist_root(message.chat.id, user_id)

def render_wishlist_for(chat_id: int, user_id: int, mode: str):
    pair = get_pair_by_user(user_id)
    if not pair:
        bot.send_message(
            chat_id,
            "Сначала создайте пару через «➕ Добавить партнера».",
            reply_markup=main_menu(user_id)
        )
        return

    if mode == "my":
        owner_id = user_id
        items = get_wishlist_for_owner(pair["id"], owner_id)
        title = "Ваш список желаний:"
        allow_edit = True
    elif mode == "partner":
        # Определяем ID партнёра
        if pair["creator_user_id"] == user_id:
            owner_id = pair["partner_user_id"]
        else:
            owner_id = pair["creator_user_id"]

        if not owner_id:
            bot.send_message(
                chat_id,
                "Партнёр ещё не присоединился, его список недоступен.",
                reply_markup=main_menu(user_id)
            )
            return

        items = get_wishlist_for_owner(pair["id"], owner_id)
        title = "Список желаний вашего партнёра:"
        allow_edit = False
    else:
        bot.send_message(chat_id, "Неизвестный режим списка.", reply_markup=main_menu(user_id))
        return

    if not items:
        text = title + "\n\nПока тут пусто."
    else:
        lines = []
        for i, item in enumerate(items, start=1):
            prefix = "✅" if item["is_done"] else f"{i}."
            link_part = ""
            if item.get("url"):
                link_part = f' (<a href="{item["url"]}">ссылка</a>)'

            lines.append(f"{prefix} <b>{item['title']}</b>{link_part}")

        text = title + "\n\n" + "\n".join(lines)

    markup = types.InlineKeyboardMarkup()
    # Кнопки редактирования только для своего списка
    if allow_edit:
        markup.add(types.InlineKeyboardButton("➕ Добавить желание", callback_data="wishlist_add"))
        if items:
            markup.add(types.InlineKeyboardButton("🗑 Удалить желание", callback_data="wishlist_del"))

    # Общая кнопка "Назад к выбору"
    markup.add(types.InlineKeyboardButton("⬅️ К выбору списков", callback_data="wishlist_back"))

    bot.send_message(chat_id, text, reply_markup=markup, disable_web_page_preview=True)

def show_wishlist_root(chat_id: int, user_id: int):
    pair = get_pair_by_user(user_id)
    if not pair:
        bot.send_message(
            chat_id,
            "Сначала создайте пару через «➕ Добавить партнера».",
            reply_markup=main_menu(user_id)
        )
        return

    text = "Что показать?"
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📋 Мой список", callback_data="wishlist_my"))

    # Определяем, есть ли партнёр
    partner_id = pair["partner_user_id"] if pair["creator_user_id"] == user_id else pair["creator_user_id"]
    if partner_id:
        markup.add(types.InlineKeyboardButton("❤️ Список партнёра", callback_data="wishlist_partner"))
    else:
        text += "\n\nПартнёр ещё не присоединился, поэтому его список пока недоступен."

    bot.send_message(chat_id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data == "wishlist_my")
def wishlist_my_callback(call: types.CallbackQuery):
    user_id = get_or_create_user(call.from_user)
    bot.answer_callback_query(call.id)
    render_wishlist_for(call.message.chat.id, user_id, mode="my")


@bot.callback_query_handler(func=lambda c: c.data == "wishlist_partner")
def wishlist_partner_callback(call: types.CallbackQuery):
    user_id = get_or_create_user(call.from_user)
    bot.answer_callback_query(call.id)
    render_wishlist_for(call.message.chat.id, user_id, mode="partner")


@bot.callback_query_handler(func=lambda c: c.data == "wishlist_back")
def wishlist_back_callback(call: types.CallbackQuery):
    user_id = get_or_create_user(call.from_user)
    bot.answer_callback_query(call.id)
    show_wishlist_root(call.message.chat.id, user_id)

@bot.callback_query_handler(func=lambda c: c.data == "wishlist_add")
def wishlist_add_callback(call: types.CallbackQuery):
    user_id = get_or_create_user(call.from_user)
    pair = get_pair_by_user(user_id)
    if not pair:
        bot.answer_callback_query(call.id, "Сначала создайте пару.")
        bot.send_message(
            call.message.chat.id,
            "Сначала создайте пару через «➕ Добавить партнера».",
            reply_markup=main_menu(user_id)
        )
        return

    pending_actions[call.from_user.id] = "wishlist_add"
    bot.answer_callback_query(call.id)
    bot.send_message(
        call.message.chat.id,
        "Напиши текст желания одной строкой.\nНапример: «новый плед»."
    )

@bot.callback_query_handler(func=lambda c: c.data.startswith("wish_link:"))
def wishlist_link_callback(call: types.CallbackQuery):
    user_id = get_or_create_user(call.from_user)
    pair = get_pair_by_user(user_id)
    if not pair:
        bot.answer_callback_query(call.id, "Сначала создайте пару.")
        bot.send_message(
            call.message.chat.id,
            "Сначала создайте пару через «➕ Добавить партнера».",
            reply_markup=main_menu(user_id)
        )
        return

    _, item_id_str = call.data.split(":", 1)
    try:
        item_id = int(item_id_str)
    except ValueError:
        bot.answer_callback_query(call.id, "Некорректный идентификатор желания.")
        return

    # Запоминаем, к какому желанию будем привязывать ссылку
    wishlist_link_targets[call.from_user.id] = item_id
    pending_actions[call.from_user.id] = "wishlist_link"

    bot.answer_callback_query(call.id)
    bot.send_message(
        call.message.chat.id,
        "Пришли ссылку на товар целиком.\n"
        "Например: https://example.com/...",
    )

@bot.callback_query_handler(func=lambda c: c.data == "wishlist_del")
def wishlist_delete_callback(call: types.CallbackQuery):
    user_id = get_or_create_user(call.from_user)
    pair = get_pair_by_user(user_id)
    if not pair:
        bot.answer_callback_query(call.id, "Сначала создайте пару.")
        bot.send_message(
            call.message.chat.id,
            "Сначала создайте пару через «➕ Добавить партнера».",
            reply_markup=main_menu(user_id)
        )
        return

    items = get_wishlist_for_owner(pair["id"], user_id)
    if not items:
        bot.answer_callback_query(call.id, "Список уже пуст.")
        bot.send_message(
            call.message.chat.id,
            "В списке сейчас нет желаний.",
            reply_markup=main_menu(user_id)
        )
        return

    pending_actions[call.from_user.id] = "wishlist_delete"
    bot.answer_callback_query(call.id)
    bot.send_message(
        call.message.chat.id,
        "Напиши номер желания, которое хочешь удалить.\n"
        "Например: 1"
    )

# ===== Ссылка на диск =====

@bot.message_handler(func=lambda m: m.text == "📁 Ссылка на общий диск")
def cloud_link(message: types.Message):
    user_id = get_or_create_user(message.from_user)
    pair = get_pair_by_user(user_id)
    if not pair:
        bot.reply_to(
            message,
            "Сначала создайте пару через «➕ Добавить партнера».",
            reply_markup=main_menu(user_id)
        )
        return

    if pair["cloud_drive_url"]:
        text = f"Текущая ссылка на общий диск:\n{pair['cloud_drive_url']}"
        button_text = "✏️ Изменить ссылку"
    else:
        text = "Сейчас ссылка на общий диск не настроена."
        button_text = "➕ Добавить ссылку"

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(button_text, callback_data="cloud_set"))

    bot.reply_to(message, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data == "cloud_set")
def cloud_set_callback(call: types.CallbackQuery):
    user_id = get_or_create_user(call.from_user)
    pair = get_pair_by_user(user_id)
    if not pair:
        bot.answer_callback_query(call.id, "Сначала создайте пару.")
        bot.send_message(
            call.message.chat.id,
            "Сначала создайте пару через «➕ Добавить партнера».",
            reply_markup=main_menu(user_id)
        )
        return

    pending_actions[call.from_user.id] = "cloud_set"
    bot.answer_callback_query(call.id)
    bot.send_message(
        call.message.chat.id,
        "Пришли ссылку на общий диск одной строкой.\nНапример: https://drive.google.com/..."
    )


# ===== Дата начала отношений =====

@bot.message_handler(func=lambda m: m.text == "❤️ Дата начала отношений")
def ask_start_date(message: types.Message):
    from datetime import date as _date, timedelta

    user_id = get_or_create_user(message.from_user)
    pair = get_pair_by_user(user_id)

    if not pair:
        bot.reply_to(
            message,
            "Сначала создайте пару через «➕ Добавить партнера».",
            reply_markup=main_menu(user_id)
        )
        return

    if pair["start_date"]:
        start = pair["start_date"]
        today = _date.today()

        # защита от будущей даты (если вдруг так ввели)
        if start > today:
            start_fmt = start.strftime("%d.%m.%Y")
            text = (
                f"Дата начала отношений: <b>{start_fmt}</b>\n\n"
                "Похоже, эта дата ещё в будущем 🙃\n"
                "Можешь изменить её, если это ошибка."
            )
            button_text = "✏️ Изменить дату"
        else:
            # формат ДД.ММ.ГГГГ
            start_fmt = start.strftime("%d.%m.%Y")

            # 1) Дни вместе
            days_together = (today - start).days

            # 2) Годы и месяцы вместе
            # полные годы
            years = today.year - start.year
            if (today.month, today.day) < (start.month, start.day):
                years -= 1

            # дата последней годовщины
            last_year_anniv = _date(start.year + years, start.month, start.day)

            # полные месяцы после последней годовщины
            months = (today.year - last_year_anniv.year) * 12 + (today.month - last_year_anniv.month)
            if today.day < start.day:
                months -= 1
            if months < 0:
                months = 0

            # 3) Следующая годовщина
            next_anniv = _date(start.year + years + 1, start.month, start.day)
            days_until_next = (next_anniv - today).days

            # 4) Прогресс до следующей годовщины (бар)
            total_period_days = (next_anniv - last_year_anniv).days or 1
            done_days = (today - last_year_anniv).days
            if done_days < 0:
                done_days = 0
            if done_days > total_period_days:
                done_days = total_period_days

            ratio = done_days / total_period_days
            bar_len = 10
            filled = int(round(ratio * bar_len))
            if filled > bar_len:
                filled = bar_len
            bar = "█" * filled + "░" * (bar_len - filled)
            percent = int(ratio * 100)

            # 5) Красивая дата (100, 200, 500, 1000, 1500, 2000...)
            milestone_days = [100, 200, 300, 400, 500, 600, 700, 800, 900,
                              1000, 1500, 2000, 2500, 3000]
            next_milestone = None
            for d in milestone_days:
                if d > days_together:
                    next_milestone = d
                    break

            milestone_block = ""
            if next_milestone is not None:
                days_to_milestone = next_milestone - days_together
                milestone_date = start + timedelta(days=next_milestone)
                milestone_block = (
                    f"\n\n✨ <b>Ближайшая «красивая» дата:</b>\n"
                    f"– <b>{next_milestone}</b> дней вместе — "
                    f"<b>{milestone_date.strftime('%d.%m.%Y')}</b>\n"
                    f"– Осталось: <b>{days_to_milestone}</b> дней"
                )

            # 6) Большой юбилей (кратный 5 годам: 5, 10, 15, ...)
            if years < 0:
                years = 0
            next_big_year = ((years // 5) + 1) * 5
            big_anniv_date = _date(start.year + next_big_year, start.month, start.day)
            days_to_big = (big_anniv_date - today).days

            big_block = (
                f"\n\n🎉 <b>Следующий большой юбилей:</b>\n"
                f"– <b>{next_big_year}</b> лет — "
                f"<b>{big_anniv_date.strftime('%d.%m.%Y')}</b>\n"
                f"– Осталось: <b>{days_to_big}</b> дней"
            )

            # Итоговый текст
            text = (
                f"Дата начала отношений: <b>{start_fmt}</b>\n\n"
                f"❤️ <b>Вместе уже:</b>\n"
                f"– <b>{days_together}</b> дней\n"
                f"– <b>{years}</b> г. <b>{months}</b> м.\n\n"
                f"⏳ До следующей годовщины: <b>{days_until_next}</b> дней\n"
                f"📊 Прогресс: {bar} (<b>{percent}%</b>)"
                f"{milestone_block}"
                f"{big_block}"
            )

            button_text = "✏️ Изменить дату"

    else:
        text = "Дата начала отношений пока не указана."
        button_text = "➕ Указать дату"

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(button_text, callback_data="startdate_set"))
    bot.reply_to(message, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data == "startdate_set")
def startdate_set_callback(call: types.CallbackQuery):
    user_id = get_or_create_user(call.from_user)
    pair = get_pair_by_user(user_id)
    if not pair:
        bot.answer_callback_query(call.id, "Сначала создайте пару.")
        bot.send_message(
            call.message.chat.id,
            "Сначала создайте пару через «➕ Добавить партнера».",
            reply_markup=main_menu(user_id)
        )
        return

    pending_actions[call.from_user.id] = "startdate_set"
    bot.answer_callback_query(call.id)
    bot.send_message(
        call.message.chat.id,
        "Напиши дату начала отношений в формате <b>ДД.ММ.ГГГГ</b>\n"
        "Например: 14.02.2024"
    )


# ===== Удаление пары =====

@bot.message_handler(func=lambda m: m.text == "Удалить пару 💔")
def ask_delete_pair(message: types.Message):
    user_id = get_or_create_user(message.from_user)
    pair = get_pair_by_user(user_id)
    if not pair:
        bot.reply_to(
            message,
            "У вас сейчас нет пары.",
            reply_markup=main_menu(user_id)
        )
        return

    markup = types.InlineKeyboardMarkup()
    yes_btn = types.InlineKeyboardButton(
        "Да, удалить",
        callback_data=f"delpair_yes:{pair['id']}"
    )
    no_btn = types.InlineKeyboardButton(
        "Отмена",
        callback_data="delpair_no"
    )
    markup.add(yes_btn, no_btn)

    bot.reply_to(
        message,
        "Точно удалить пару?\n\n"
        "Будет удалён общий список желаний и настройки даты отношений.",
        reply_markup=markup
    )


@bot.callback_query_handler(func=lambda c: c.data.startswith("delpair_"))
def process_delete_pair_callback(call: types.CallbackQuery):
    data = call.data

    if data == "delpair_no":
        bot.answer_callback_query(call.id, "Отмена")
        # убираем inline-кнопки под сообщением
        try:
            bot.edit_message_reply_markup(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=None
            )
        except Exception:
            pass
        bot.send_message(call.message.chat.id, "Слава богу!\n\nПару не трогаю 🔥")
        return

    # тут точно delpair_yes:<id>
    _, pair_id_str = data.split(":", 1)
    try:
        pair_id = int(pair_id_str)
    except ValueError:
        bot.answer_callback_query(call.id, "Ошибка идентификатора пары")
        return

    # достаём пару и телеграм-id обоих
    pair = fetchone(
        """
        SELECT p.id, p.creator_user_id, p.partner_user_id,
               u1.telegram_id AS t1,
               u2.telegram_id AS t2
        FROM pairs p
        JOIN users u1 ON u1.id = p.creator_user_id
        LEFT JOIN users u2 ON u2.id = p.partner_user_id
        WHERE p.id = %s
        """,
        (pair_id,)
    )

    if not pair:
        bot.answer_callback_query(call.id, "Пара уже удалена")
        try:
            bot.edit_message_reply_markup(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=None
            )
        except Exception:
            pass
        return

    # Удаляем пару (wishlist_items и notifications_log удалятся каскадно)
    execute("DELETE FROM pairs WHERE id = %s", (pair_id,))

    bot.answer_callback_query(call.id, "Пара удалена")

    # убираем кнопки под сообщением
    try:
        bot.edit_message_reply_markup(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=None
        )
    except Exception:
        pass

    # Оповещаем обоих
    text = (
        "Пара была удалена.\n\n"
        "Если захотите — можно создать новую через кнопку "
        "«➕ Добавить партнера»."
    )

    for tg_id in [pair["t1"], pair["t2"]]:
        if tg_id:
            try:
                u_id = get_or_create_user(telebot.types.User(id=tg_id, is_bot=False, first_name="", last_name="", username=None))  # грубый хак, можно убрать если не нужен main_menu
            except Exception:
                u_id = None

            try:
                if u_id:
                    kb = main_menu(u_id)
                else:
                    kb = None
                bot.send_message(tg_id, text, reply_markup=kb)
            except Exception:
                pass

    # Обновим меню тому, кто нажал кнопку (на всякий случай)
    try:
        user_id = get_or_create_user(call.from_user)
        bot.send_message(
            call.message.chat.id,
            "Пара удалена. Главное меню обновлено.",
            reply_markup=main_menu(user_id)
        )
    except Exception:
        pass

# ===== Fallback =====

@bot.message_handler(content_types=["text"])
def fallback(message: types.Message):
    user_id = get_or_create_user(message.from_user)
    bot.reply_to(
        message,
        "Я тебя понял, но не знаю, что с этим сделать 😅\n"
        "Пользуйся, пожалуйста, кнопками в меню снизу.",
        reply_markup=main_menu(user_id)
    )


if __name__ == "__main__":
    print("Bot started...")
    bot.infinity_polling()