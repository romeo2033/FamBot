"""
Флоу-логика: сборка текстов, inline-меню и сложная бизнес-логика
(но без декораторов и без прямых handler'ов).
"""

from __future__ import annotations

import html
from datetime import date as _date, timedelta
from urllib.parse import quote

from telebot import types

from config import BOT_USERNAME
from db import fetchone
from bot_setup import send_or_edit
from services import (
    get_or_create_user,
    get_pair_by_user,
    set_pair_start_date,
    set_pair_cloud_url,
    get_wishlist_for_owner,
    get_or_create_invite_for_user,
)


# ===== Общие элементы интерфейса =====


def add_inline_home_button(markup: types.InlineKeyboardMarkup) -> types.InlineKeyboardMarkup:
    """
    Добавляет в самый низ inline-кнопку «🏠 Главное меню».
    """
    markup.add(types.InlineKeyboardButton("🏠 Главное меню", callback_data="menu_home"))
    return markup


def build_main_inline_menu(user_id: int) -> types.InlineKeyboardMarkup:
    """
    Главный inline-меню под основным сообщением.
    Внизу всегда кнопка «🏠 Главное меню».
    """
    pair = get_pair_by_user(user_id)
    markup = types.InlineKeyboardMarkup()

    if not pair:
        markup.add(
            types.InlineKeyboardButton(
                "➕ Добавить партнёра",
                callback_data="menu_add_partner",
            )
        )
    else:
        markup.add(
            types.InlineKeyboardButton("🎁 Список желаний", callback_data="menu_wishlist")
        )
        markup.add(
            types.InlineKeyboardButton("📁 Общий диск", callback_data="menu_cloud")
        )
        markup.add(
            types.InlineKeyboardButton("❤️ Годовщина ❤️", callback_data="menu_startdate")
        )
        markup.add(
            types.InlineKeyboardButton("Удалить пару ❌", callback_data="menu_delete_pair")
        )

    add_inline_home_button(markup)
    return markup


# ===== Флоу: добавление партнёра =====


def add_partner_flow(chat_id: int, tg_user) -> None:
    """
    Флоу «Добавить партнёра»:
    - проверяет, нет ли уже пары;
    - создаёт / находит инвайт;
    - показывает deep-link.
    """
    user_id = get_or_create_user(tg_user)
    pair = get_pair_by_user(user_id)

    if pair:
        send_or_edit(
            chat_id,
            "У тебя уже есть пара 💑\n\n"
            "Если хотите сменить партнёра — сначала удалите текущую пару.",
            reply_markup=build_main_inline_menu(user_id),
        )
        return

    invite = get_or_create_invite_for_user(user_id)
    invite_token = invite["invite_token"]

    deep_link_param = "inv_" + invite_token
    deep_link = f"https://t.me/{BOT_USERNAME}?start={quote(deep_link_param)}"

    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("🔁 Обновить ссылку", callback_data="menu_add_partner")
    )
    add_inline_home_button(markup)

    send_or_edit(
        chat_id,
        "Вот ссылка для вашего партнёра:\n"
        f"{deep_link}\n\n"
        "Отправьте её тому, с кем хотите быть в паре 💌",
        reply_markup=markup,
    )


# ===== Флоу: облачный диск =====


def cloud_link_flow(chat_id: int, tg_user) -> None:
    """
    Показ / изменение ссылки на общий диск.
    """
    user_id = get_or_create_user(tg_user)
    pair = get_pair_by_user(user_id)
    if not pair:
        send_or_edit(
            chat_id,
            "Сначала создайте пару через «Добавить партнёра».",
            reply_markup=build_main_inline_menu(user_id),
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
    add_inline_home_button(markup)

    send_or_edit(chat_id, text, reply_markup=markup)


# ===== Флоу: дата начала отношений =====


def start_date_flow(chat_id: int, tg_user) -> None:
    """
    Показ информации о дате начала отношений и прогресса до следующей годовщины.
    """
    user_id = get_or_create_user(tg_user)
    pair = get_pair_by_user(user_id)

    if not pair:
        send_or_edit(
            chat_id,
            "Сначала создайте пару через «Добавить партнёра».",
            reply_markup=build_main_inline_menu(user_id),
        )
        return

    if pair["start_date"]:
        start = pair["start_date"]
        today = _date.today()

        if start > today:
            start_fmt = start.strftime("%d.%m.%Y")
            text = (
                f"Дата начала отношений: <b>{start_fmt}</b>\n\n"
                "Похоже, эта дата ещё в будущем 🙃\n"
                "Можешь изменить её, если это ошибка."
            )
            button_text = "✏️ Изменить дату"
        else:
            start_fmt = start.strftime("%d.%m.%Y")
            days_together = (today - start).days

            years = today.year - start.year
            if (today.month, today.day) < (start.month, start.day):
                years -= 1

            last_year_anniv = _date(start.year + years, start.month, start.day)

            months = (today.year - last_year_anniv.year) * 12 + (
                today.month - last_year_anniv.month
            )
            if today.day < start.day:
                months -= 1
            if months < 0:
                months = 0

            next_anniv = _date(start.year + years + 1, start.month, start.day)
            days_until_next = (next_anniv - today).days

            total_period_days = (next_anniv - last_year_anniv).days or 1
            done_days = (today - last_year_anniv).days
            done_days = max(0, min(done_days, total_period_days))

            ratio = done_days / total_period_days
            bar_len = 10
            filled = int(round(ratio * bar_len))
            filled = min(filled, bar_len)
            bar = "█" * filled + "░" * (bar_len - filled)
            percent = int(ratio * 100)

            milestone_days = [
                100,
                200,
                300,
                400,
                500,
                600,
                700,
                800,
                900,
                1000,
                1500,
                2000,
                2500,
                3000,
            ]
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
    add_inline_home_button(markup)

    send_or_edit(chat_id, text, reply_markup=markup)


# ===== Флоу: удаление пары =====


def delete_pair_flow(chat_id: int, tg_user) -> None:
    """
    Показ диалога подтверждения удаления пары.
    """
    user_id = get_or_create_user(tg_user)
    pair = get_pair_by_user(user_id)
    if not pair:
        send_or_edit(
            chat_id,
            "У вас сейчас нет пары.",
            reply_markup=build_main_inline_menu(user_id),
        )
        return

    markup = types.InlineKeyboardMarkup()
    yes_btn = types.InlineKeyboardButton(
        "Да, удалить",
        callback_data=f"delpair_yes:{pair['id']}",
    )
    no_btn = types.InlineKeyboardButton(
        "Отмена",
        callback_data="delpair_no",
    )
    markup.add(yes_btn, no_btn)
    add_inline_home_button(markup)

    send_or_edit(
        chat_id,
        "Точно удалить пару?\n\n"
        "Будет удалён общий список желаний и настройки даты отношений.",
        reply_markup=markup,
    )


# ===== Флоу: список желаний =====


def render_wishlist_for(chat_id: int, user_id: int, mode: str) -> None:
    """
    Показ списка желаний:
    - mode == 'my' — свой список
    - mode == 'partner' — список партнёра
    """
    pair = get_pair_by_user(user_id)
    if not pair:
        send_or_edit(
            chat_id,
            "Сначала создайте пару через «Добавить партнёра».",
            reply_markup=build_main_inline_menu(user_id),
        )
        return

    if mode == "my":
        owner_id = user_id
        items = get_wishlist_for_owner(pair["id"], owner_id)
        title = "Ваш список желаний:"
        allow_edit = True
    elif mode == "partner":
        if pair["creator_user_id"] == user_id:
            owner_id = pair["partner_user_id"]
        else:
            owner_id = pair["creator_user_id"]

        if not owner_id:
            send_or_edit(
                chat_id,
                "Партнёр ещё не присоединился, его список недоступен.",
                reply_markup=build_main_inline_menu(user_id),
            )
            return

        items = get_wishlist_for_owner(pair["id"], owner_id)
        title = "Список желаний вашего партнёра:"
        allow_edit = False
    else:
        send_or_edit(
            chat_id,
            "Неизвестный режим списка.",
            reply_markup=build_main_inline_menu(user_id),
        )
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
    if allow_edit:
        markup.add(
            types.InlineKeyboardButton("➕ Добавить желание", callback_data="wishlist_add")
        )
        if items:
            markup.add(
                types.InlineKeyboardButton("🗑 Удалить желание", callback_data="wishlist_del")
            )

    markup.add(types.InlineKeyboardButton("⬅️ К выбору списков", callback_data="wishlist_back"))
    add_inline_home_button(markup)

    send_or_edit(chat_id, text, reply_markup=markup)


def show_wishlist_root(chat_id: int, user_id: int) -> None:
    """
    Корневой экран списка желаний:
    выбор между своим списком и списком партнёра.
    """
    pair = get_pair_by_user(user_id)
    if not pair:
        send_or_edit(
            chat_id,
            "Сначала создайте пару через «Добавить партнёра».",
            reply_markup=build_main_inline_menu(user_id),
        )
        return

    text = "Что показать?"
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📋 Мой список", callback_data="wishlist_my"))

    partner_id = pair["partner_user_id"] if pair["creator_user_id"] == user_id else pair[
        "creator_user_id"
    ]
    if partner_id:
        markup.add(
            types.InlineKeyboardButton("❤️ Список партнёра", callback_data="wishlist_partner")
        )
    else:
        text += "\n\nПартнёр ещё не присоединился, поэтому его список пока недоступен."

    add_inline_home_button(markup)
    send_or_edit(chat_id, text, reply_markup=markup)


def wishlist_root_flow(chat_id: int, tg_user) -> None:
    """Удобная обёртка: показать корневое меню вишлиста по tg_user."""
    user_id = get_or_create_user(tg_user)
    show_wishlist_root(chat_id, user_id)