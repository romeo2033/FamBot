"""
Все Telegram-хендлеры: message_handler / callback_query_handler.
Логика по максимуму вынесена в services.py и flows.py.
"""

from __future__ import annotations

import html
import re
from datetime import date

import telebot
from telebot import types

from db import fetchone, execute
from bot_setup import bot, pending_actions, wishlist_link_targets, send_or_edit, get_id
from services import (
    get_or_create_user,
    get_pair_by_user,
    add_wishlist_item,
    get_wishlist_for_owner,
)
from flows import (
    add_inline_home_button,
    build_main_inline_menu,
    add_partner_flow,
    wishlist_root_flow,
    cloud_link_flow,
    start_date_flow,
    delete_pair_flow,
    render_wishlist_for,
    show_wishlist_root,
)
from services import set_pair_start_date, set_pair_cloud_url, link_partner_to_pair


# ===== Обработка ожидаемых действий (pending_actions) =====


@bot.message_handler(func=lambda m: pending_actions.get(m.from_user.id) is not None)
def handle_pending(message: types.Message) -> None:
    """
    Универсальный хендлер для случаев, когда бот чего-то ждёт от пользователя
    (pending_actions): текст желания, дату, ссылку и т.п.
    """
    tg_id = message.from_user.id
    action = pending_actions.pop(tg_id, None)

    user_id = get_or_create_user(message.from_user)

    # 1) Добавление желания
    if action == "wishlist_add":
        pair = get_pair_by_user(user_id)
        if not pair:
            send_or_edit(
                message,
                "Сначала создайте пару через «Добавить партнёра».",
                add_inline_home_button(types.InlineKeyboardMarkup()),
            )
            return

        title = (message.text or "").strip()
        if title.lower() == "нет":
            markup = add_inline_home_button(types.InlineKeyboardMarkup())
            send_or_edit(
                message,
                "Окей не трогаю",
                reply_markup=markup,
            )
            return

        item = add_wishlist_item(pair["id"], user_id, title)

        # --- уведомление самому пользователю ---
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton(
                "➕ Добавить ссылку",
                callback_data=f"wish_link:{item['id']}",
            )
        )
        add_inline_home_button(markup)

        safe_title = html.escape(title, quote=False)
        send_or_edit(
            message,
            f"Добавил в список: <b>{safe_title}</b> 🎁",
            reply_markup=markup,
        )

        # --- уведомление партнёру о новом желании ---
        try:
            if pair["creator_user_id"] == user_id:
                partner_user_id = pair["partner_user_id"]
            else:
                partner_user_id = pair["creator_user_id"]

            if partner_user_id:
                partner = fetchone(
                    "SELECT telegram_id FROM users WHERE id = %s",
                    (partner_user_id,),
                )
            else:
                partner = None

            if partner and partner.get("telegram_id"):
                who = (
                    ("@" + message.from_user.username)
                    if message.from_user.username
                    else "Партнёр"
                )
                safe_who = html.escape(who, quote=False)
                notif_text = (
                    "🎁 <b>Новое желание в списке партнера!</b>\n\n"
                    f"<b>{safe_who}</b> добавил(а): "
                    f"<b>{safe_title}</b>"
                )

                kb = add_inline_home_button(types.InlineKeyboardMarkup())

                send_or_edit(
                    partner["telegram_id"],
                    notif_text,
                    reply_markup=kb,
                )
        except Exception as e:
            print(f"Failed to notify partner about new wishlist item: {e}")

    # 2) Установка / изменение ссылки на диск
    elif action == "cloud_set":
        pair = get_pair_by_user(user_id)
        if not pair:
            send_or_edit(
                message,
                "Сначала создайте пару через «Добавить партнёра».",
                add_inline_home_button(types.InlineKeyboardMarkup()),
            )
            return

        url = (message.text or "").strip()
        if url.lower() == "нет":
            markup = add_inline_home_button(types.InlineKeyboardMarkup())
            send_or_edit(
                message,
                "Окей не трогаю",
                reply_markup=markup,
            )
            return

        if not (url.startswith("http://") or url.startswith("https://")):
            send_or_edit(
                message,
                'Похоже, это не ссылка. Пришли полный URL, начинающийся с http или https.\n\n'
                '<i>Или, чтобы отменить пришли слово "нет"</i>',
            )
            pending_actions[tg_id] = "cloud_set"
            return

        set_pair_cloud_url(pair["id"], url)
        send_or_edit(
            message,
            f"Обновил ссылку на общий диск:\n{url}",
            add_inline_home_button(types.InlineKeyboardMarkup()),
        )

    # 3) Установка / изменение даты отношений
    elif action == "startdate_set":
        pair = get_pair_by_user(user_id)
        if not pair:
            send_or_edit(
                message,
                "Сначала создайте пару через «Добавить партнёра».",
                add_inline_home_button(types.InlineKeyboardMarkup()),
            )
            return

        text = (message.text or "").strip()

        if text.lower() == "нет":
            markup = add_inline_home_button(types.InlineKeyboardMarkup())
            send_or_edit(
                message,
                "Окей не трогаю",
                reply_markup=markup,
            )
            return

        m = re.match(r"^(\d{2})\.(\d{2})\.(\d{4})$", text)
        if not m:
            send_or_edit(
                message,
                'Формат даты должен быть <b>ДД.ММ.ГГГГ</b>.\n'
                "Пример: 14.02.2024\nПопробуй ещё раз.\n\n"
                '<i>Или, чтобы отменить, напиши слово "нет"</i>',
            )
            pending_actions[tg_id] = "startdate_set"
            return

        day, month, year = map(int, m.groups())
        from datetime import date as _date

        try:
            d = _date(year, month, day)
        except ValueError:
            send_or_edit(
                message,
                "Похоже, дата некорректна. Проверь день и месяц.",
            )
            pending_actions[tg_id] = "startdate_set"
            return

        set_pair_start_date(pair["id"], d)

        send_or_edit(
            message,
            f"Запомнил дату начала отношений: <b>{text}</b> ❤️",
            add_inline_home_button(types.InlineKeyboardMarkup()),
        )

    # 4) Удаление желания по номеру
    elif action == "wishlist_delete":
        pair = get_pair_by_user(user_id)
        if not pair:
            send_or_edit(
                message,
                "Сначала создайте пару через «Добавить партнёра».",
                add_inline_home_button(types.InlineKeyboardMarkup()),
            )
            return

        text = (message.text or "").strip()
        if text.lower() == "нет":
            markup = add_inline_home_button(types.InlineKeyboardMarkup())
            send_or_edit(
                message,
                "Окей отменяем!",
                reply_markup=markup,
            )
            return

        if not text.isdigit():
            send_or_edit(
                message,
                'Нужен номер желания (целое число). Попробуй ещё раз.\n\n'
                '<i>Или, чтобы отменить, напиши слово "нет"</i>',
            )
            pending_actions[tg_id] = "wishlist_delete"
            return

        index = int(text)

        items = get_wishlist_for_owner(pair["id"], user_id)
        if not items:
            send_or_edit(
                message,
                "Список желаний уже пуст 🙃",
                add_inline_home_button(types.InlineKeyboardMarkup()),
            )
            return

        if index < 1 or index > len(items):
            send_or_edit(
                message,
                f"Номер вне диапазона. Сейчас в списке {len(items)} желаний.\n"
                "Напиши номер из списка.",
            )
            pending_actions[tg_id] = "wishlist_delete"
            return

        item = items[index - 1]
        execute("DELETE FROM wishlist_items WHERE id = %s", (item["id"],))

        send_or_edit(
            message,
            f"Удалил желание №{index}: <b>{item['title']}</b> 🗑",
            add_inline_home_button(types.InlineKeyboardMarkup()),
        )

    # 5) Добавление ссылки к желанию
    elif action == "wishlist_link":
        pair = get_pair_by_user(user_id)
        if not pair:
            send_or_edit(
                message,
                "Сначала создайте пару через «Добавить партнёра».",
                add_inline_home_button(types.InlineKeyboardMarkup()),
            )
            return

        item_id = wishlist_link_targets.get(tg_id)
        if not item_id:
            send_or_edit(
                message,
                "Не удалось понять, к какому желанию добавить ссылку. Попробуй снова.",
                add_inline_home_button(types.InlineKeyboardMarkup()),
            )
            return

        url = (message.text or "").strip()
        if not (url.startswith("http://") or url.startswith("https://")):
            send_or_edit(
                message,
                "Похоже, это не ссылка. Пришли полный URL, начинающийся с http:// или https://.",
            )
            pending_actions[tg_id] = "wishlist_link"
            return

        execute(
            "UPDATE wishlist_items SET url = %s WHERE id = %s",
            (url, item_id),
        )

        wishlist_link_targets.pop(tg_id, None)

        send_or_edit(
            message,
            "Ссылку добавил к желанию 🔗",
            reply_markup=add_inline_home_button(types.InlineKeyboardMarkup()),
        )

    else:
        send_or_edit(
            message,
            "Я запутался в том, что ты хотел сделать. Попробуй ещё раз через меню.",
            add_inline_home_button(types.InlineKeyboardMarkup()),
        )


# ===== /start и главное меню =====


@bot.message_handler(commands=["start"])
def start_cmd(message: types.Message) -> None:
    """
    Обработка /start:
    - deep-link с инвайтом (start inv_xxx)
    - обычный старт (главный экран).
    """
    from datetime import date as _date

    user_id = get_or_create_user(message.from_user)

    # === deep-link: подключение партнёра ===
    try:
        parts = message.text.split()

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

                send_or_edit(
                    message,
                    text,
                    add_inline_home_button(types.InlineKeyboardMarkup()),
                )
                return

            send_or_edit(
                message.chat.id,
                "🎉 Вы успешно стали парой!\nТеперь вам доступен общий список желаний и напоминания 💑",
                reply_markup=build_main_inline_menu(user_id),
            )
            return
    except Exception:
        # Не ломаем /start, если что-то пошло не так при парсинге deep-link.
        pass

    # === обычный /start ===
    pair = get_pair_by_user(user_id)

    if not pair:
        text = (
            "Привет! Я бот для пар 💑\n\n"
            "Нажми кнопку ниже, чтобы создать пару и получить ссылку-приглашение.\n\n"
            "Если что-то пошло не так — просто жми «🏠 Главное меню» внизу, "
            "это отменит текущие действия и вернёт тебя сюда."
        )
    else:
        if pair["creator_user_id"] == user_id:
            partner_id = pair["partner_user_id"]
        else:
            partner_id = pair["creator_user_id"]

        partner = fetchone(
            "SELECT username, first_name FROM users WHERE id = %s", (partner_id,)
        )

        partner_name = (
            f"@{partner['username']}"
            if partner and partner["username"]
            else partner["first_name"]
            if partner and partner["first_name"]
            else "ваш партнёр"
        )

        if pair["start_date"]:
            start = pair["start_date"]
            today = date.today()

            years = today.year - start.year
            if (today.month, today.day) < (start.month, start.day):
                years -= 1

            last_anniv = date(start.year + years, start.month, start.day)

            months = (today.year - last_anniv.year) * 12 + (
                today.month - last_anniv.month
            )
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
            "Вы крутышки! Продолжайте радовать друг друга 💕\n\n"
            "Используй кнопки ниже, чтобы управлять списком желаний, "
            "датой отношений и другими настройками.\n\n"
            "Если что-то запуталось — жми «🏠 Главное меню» внизу."
        )

    send_or_edit(
        get_id(message),
        text,
        reply_markup=build_main_inline_menu(user_id),
        parse_mode="HTML",
    )


# ===== Навигация через inline-меню (menu_*) =====


@bot.callback_query_handler(func=lambda c: c.data == "menu_add_partner")
def menu_add_partner_callback(call: types.CallbackQuery) -> None:
    bot.answer_callback_query(call.id)
    add_partner_flow(call.message.chat.id, call.from_user)


@bot.callback_query_handler(func=lambda c: c.data == "menu_wishlist")
def menu_wishlist_callback(call: types.CallbackQuery) -> None:
    bot.answer_callback_query(call.id)
    wishlist_root_flow(call.message.chat.id, call.from_user)


@bot.callback_query_handler(func=lambda c: c.data == "menu_cloud")
def menu_cloud_callback(call: types.CallbackQuery) -> None:
    bot.answer_callback_query(call.id)
    cloud_link_flow(call.message.chat.id, call.from_user)


@bot.callback_query_handler(func=lambda c: c.data == "menu_startdate")
def menu_startdate_callback(call: types.CallbackQuery) -> None:
    bot.answer_callback_query(call.id)
    start_date_flow(call.message.chat.id, call.from_user)


@bot.callback_query_handler(func=lambda c: c.data == "menu_delete_pair")
def menu_delete_pair_callback(call: types.CallbackQuery) -> None:
    bot.answer_callback_query(call.id)
    delete_pair_flow(call.message.chat.id, call.from_user)


@bot.callback_query_handler(func=lambda c: c.data == "menu_home")
def menu_home_callback(call: types.CallbackQuery) -> None:
    """
    Inline-кнопка «🏠 Главное меню»:
    очищает pending-стейт и запускает /start.
    """
    bot.answer_callback_query(call.id)
    pending_actions.pop(call.from_user.id, None)
    wishlist_link_targets.pop(call.from_user.id, None)

    start_cmd(call)


# ===== Старые текстовые message-обработчики (для совместимости) =====


@bot.message_handler(func=lambda m: m.text == "➕ Добавить партнера")
def add_partner_message_handler(message: types.Message) -> None:
    add_partner_flow(message.chat.id, message.from_user)


@bot.message_handler(func=lambda m: m.text == "🎁 Список желаний")
def wishlist_entry(message: types.Message) -> None:
    wishlist_root_flow(message.chat.id, message.from_user)


@bot.message_handler(func=lambda m: m.text == "📁 Ссылка на общий диск")
def cloud_link(message: types.Message) -> None:
    cloud_link_flow(message.chat.id, message.from_user)


@bot.message_handler(func=lambda m: m.text == "❤️ Дата начала отношений")
def ask_start_date(message: types.Message) -> None:
    start_date_flow(message.chat.id, message.from_user)


@bot.message_handler(func=lambda m: m.text == "Удалить пару 💔")
def ask_delete_pair(message: types.Message) -> None:
    delete_pair_flow(message.chat.id, message.from_user)


# ===== Список желаний (callbacks wishlist_*) =====


@bot.callback_query_handler(func=lambda c: c.data == "wishlist_my")
def wishlist_my_callback(call: types.CallbackQuery) -> None:
    user_id = get_or_create_user(call.from_user)
    bot.answer_callback_query(call.id)
    render_wishlist_for(call.message.chat.id, user_id, mode="my")


@bot.callback_query_handler(func=lambda c: c.data == "wishlist_partner")
def wishlist_partner_callback(call: types.CallbackQuery) -> None:
    user_id = get_or_create_user(call.from_user)
    bot.answer_callback_query(call.id)
    render_wishlist_for(call.message.chat.id, user_id, mode="partner")


@bot.callback_query_handler(func=lambda c: c.data == "wishlist_back")
def wishlist_back_callback(call: types.CallbackQuery) -> None:
    user_id = get_or_create_user(call.from_user)
    bot.answer_callback_query(call.id)
    show_wishlist_root(call.message.chat.id, user_id)


@bot.callback_query_handler(func=lambda c: c.data == "wishlist_add")
def wishlist_add_callback(call: types.CallbackQuery) -> None:
    user_id = get_or_create_user(call.from_user)
    pair = get_pair_by_user(user_id)
    if not pair:
        bot.answer_callback_query(call.id, "Сначала создайте пару.")
        send_or_edit(
            call.message.chat.id,
            "Сначала создайте пару через «Добавить партнёра».",
            reply_markup=build_main_inline_menu(user_id),
        )
        return

    pending_actions[call.from_user.id] = "wishlist_add"
    bot.answer_callback_query(call.id)
    send_or_edit(
        call.message.chat.id,
        'Напиши текст желания одной строкой.\nНапример: «новый плед».\n\n'
        '<i>Или, чтобы отменить создание, напиши слово "нет"</i>',
    )


@bot.callback_query_handler(func=lambda c: c.data.startswith("wish_link:"))
def wishlist_link_callback(call: types.CallbackQuery) -> None:
    user_id = get_or_create_user(call.from_user)
    pair = get_pair_by_user(user_id)
    if not pair:
        bot.answer_callback_query(call.id, "Сначала создайте пару.")
        send_or_edit(
            call.message.chat.id,
            "Сначала создайте пару через «Добавить партнёра».",
            reply_markup=build_main_inline_menu(user_id),
        )
        return

    _, item_id_str = call.data.split(":", 1)
    try:
        item_id = int(item_id_str)
    except ValueError:
        bot.answer_callback_query(call.id, "Некорректный идентификатор желания.")
        return

    wishlist_link_targets[call.from_user.id] = item_id
    pending_actions[call.from_user.id] = "wishlist_link"

    bot.answer_callback_query(call.id)
    send_or_edit(
        call.message.chat.id,
        "Пришли ссылку на товар целиком.\n"
        "Например: https://example.com/...",
    )


@bot.callback_query_handler(func=lambda c: c.data == "wishlist_del")
def wishlist_delete_callback(call: types.CallbackQuery) -> None:
    user_id = get_or_create_user(call.from_user)
    pair = get_pair_by_user(user_id)
    if not pair:
        bot.answer_callback_query(call.id, "Сначала создайте пару.")
        send_or_edit(
            call.message.chat.id,
            "Сначала создайте пару через «Добавить партнёра».",
            reply_markup=build_main_inline_menu(user_id),
        )
        return

    items = get_wishlist_for_owner(pair["id"], user_id)
    if not items:
        bot.answer_callback_query(call.id, "Список уже пуст.")
        send_or_edit(
            call.message.chat.id,
            "В списке сейчас нет желаний.",
            reply_markup=build_main_inline_menu(user_id),
        )
        return

    pending_actions[call.from_user.id] = "wishlist_delete"
    bot.answer_callback_query(call.id)
    send_or_edit(
        call.message.chat.id,
        "Напиши номер желания, которое хочешь удалить.\n"
        "Например: 1",
    )


# ===== Ссылка на диск (callback cloud_set) =====


@bot.callback_query_handler(func=lambda c: c.data == "cloud_set")
def cloud_set_callback(call: types.CallbackQuery) -> None:
    user_id = get_or_create_user(call.from_user)
    pair = get_pair_by_user(user_id)
    if not pair:
        bot.answer_callback_query(call.id, "Сначала создайте пару.")
        send_or_edit(
            call.message.chat.id,
            "Сначала создайте пару через «Добавить партнёра».",
            reply_markup=build_main_inline_menu(user_id),
        )
        return

    pending_actions[call.from_user.id] = "cloud_set"
    bot.answer_callback_query(call.id)
    send_or_edit(
        call.message.chat.id,
        "Пришли ссылку на общий диск одной строкой.\nНапример: https://drive.google.com/...",
    )


# ===== Дата начала отношений (callback startdate_set) =====


@bot.callback_query_handler(func=lambda c: c.data == "startdate_set")
def startdate_set_callback(call: types.CallbackQuery) -> None:
    user_id = get_or_create_user(call.from_user)
    pair = get_pair_by_user(user_id)
    if not pair:
        bot.answer_callback_query(call.id, "Сначала создайте пару.")
        send_or_edit(
            call.message.chat.id,
            "Сначала создайте пару через «Добавить партнёра».",
            reply_markup=build_main_inline_menu(user_id),
        )
        return

    pending_actions[call.from_user.id] = "startdate_set"
    bot.answer_callback_query(call.id)
    send_or_edit(
        call.message.chat.id,
        "Напиши дату начала отношений в формате <b>ДД.ММ.ГГГГ</b>\n"
        "Например: 14.02.2024",
    )


# ===== Удаление пары (delpair_*) =====


@bot.callback_query_handler(func=lambda c: c.data.startswith("delpair_"))
def process_delete_pair_callback(call: types.CallbackQuery) -> None:
    data = call.data

    if data == "delpair_no":
        bot.answer_callback_query(call.id, "Отмена")
        try:
            bot.edit_message_reply_markup(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=None,
            )
        except Exception:
            pass

        send_or_edit(
            call.message.chat.id,
            "Слава богу!\n\nПару не трогаю 🔥",
            reply_markup=add_inline_home_button(types.InlineKeyboardMarkup()),
        )
        return

    _, pair_id_str = data.split(":", 1)
    try:
        pair_id = int(pair_id_str)
    except ValueError:
        bot.answer_callback_query(call.id, "Ошибка идентификатора пары")
        return

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
        (pair_id,),
    )

    if not pair:
        bot.answer_callback_query(call.id, "Пара уже удалена")
        try:
            bot.edit_message_reply_markup(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=None,
            )
        except Exception:
            pass
        return

    execute("DELETE FROM pairs WHERE id = %s", (pair_id,))

    bot.answer_callback_query(call.id, "Пара удалена")

    try:
        bot.edit_message_reply_markup(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=None,
        )
    except Exception:
        pass

    text = (
        "Пара была удалена.\n\n"
        "Если захотите — можно создать новую через кнопку "
        "«Добавить партнёра» в главном меню."
    )

    # Уведомляем обоих участников
    for tg_id in [pair["t1"], pair["t2"]]:
        if tg_id:
            try:
                u_id = get_or_create_user(
                    telebot.types.User(
                        id=tg_id,
                        is_bot=False,
                        first_name="",
                        last_name="",
                        username=None,
                    )
                )
            except Exception:
                u_id = None

            try:
                if u_id:
                    kb = build_main_inline_menu(u_id)
                else:
                    kb = None
                send_or_edit(tg_id, text, reply_markup=kb)
            except Exception:
                pass

    # Обновляем меню в текущем чате
    try:
        user_id = get_or_create_user(call.from_user)
        send_or_edit(
            call.message.chat.id,
            "Пара удалена. Главное меню обновлено.",
            reply_markup=build_main_inline_menu(user_id),
        )
    except Exception:
        pass


# ===== Кнопка «🏠 Главное меню» из reply-keyboard =====


@bot.message_handler(func=lambda m: m.text == "🏠 Главное меню")
def go_main_menu(message: types.Message) -> None:
    """
    Кнопка из reply-keyboard:
    - отменяет все ожидания (pending_actions, wishlist_link_targets),
    - и запускает /start.
    """
    pending_actions.pop(message.from_user.id, None)
    wishlist_link_targets.pop(message.from_user.id, None)
    start_cmd(message)


# ===== Fallback =====


@bot.message_handler(content_types=["text"])
def fallback(message: types.Message) -> None:
    """
    Фолбэк на произвольный текст, если он не подошёл ни под один хендлер.
    """
    get_or_create_user(message.from_user)
    send_or_edit(
        message,
        "Я тебя понял, но не знаю, что с этим сделать 😅\n"
        "Пользуйся, пожалуйста, кнопкой «🏠 Главное меню» внизу — "
        "она отменит текущие действия и покажет главное меню с кнопками.",
        add_inline_home_button(types.InlineKeyboardMarkup()),
    )