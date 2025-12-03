"""
Создание экземпляра бота и общих вспомогательных утилит.
Здесь лежит всё, что связано с отправкой сообщений и общим состоянием.
"""

from __future__ import annotations

from typing import Dict, Optional, Union

import telebot
from telebot import types

try:
    from config import BOT_TOKEN
except ModuleNotFoundError:
    from tgbot.config import BOT_TOKEN


# === Экземпляр бота ===

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

# Временные действия пользователя: что он сейчас вводит
pending_actions: Dict[int, str] = {}

# ID wishlist-элементов, к которым пользователь добавляет ссылку
wishlist_link_targets: Dict[int, int] = {}

# Последнее сообщение бота в каждом чате (чтобы вести диалог в одном "блоке")
last_bot_messages: Dict[int, int] = {}


MessageOrChat = Union[types.Message, types.CallbackQuery, int]


def get_id(target: MessageOrChat) -> int:
    """
    Получить chat_id:
    - из message.chat.id
    - из callback.message.chat.id
    - либо вернуть само число, если передан chat_id.
    """
    try:
        # CallbackQuery
        chat_id = target.message.chat.id  # type: ignore[attr-defined]
    except AttributeError:
        try:
            # Обычное сообщение
            chat_id = target.chat.id  # type: ignore[attr-defined]
        except AttributeError:
            # Если это уже int
            chat_id = target  # type: ignore[assignment]

    return int(chat_id)


def get_message_id(message: types.Message) -> int:
    """
    В оригинальном коде здесь возвращался chat.id, а не message_id.
    Оставляем как есть, чтобы не менять поведение.
    """
    try:
        message_id = message.message.chat.id  # type: ignore[attr-defined]
    except AttributeError:
        message_id = message.chat.id

    return int(message_id)


def send_or_edit(
    target: MessageOrChat,
    text: str,
    reply_markup: Optional[types.InlineKeyboardMarkup] = None,
    parse_mode: str = "HTML",
    disable_web_page_preview: bool = True,
) -> types.Message:
    """
    Универсальная функция: старается отредактировать последнее сообщение бота в чате.
    Если не получается (нет сообщения или ошибка) — отправляет новое.
    Так диалог держится в одном сообщении.
    """
    chat_id = get_id(target)
    last_id = last_bot_messages.get(chat_id)
    msg: Optional[types.Message] = None

    if last_id:
        try:
            msg = bot.edit_message_text(
                chat_id=chat_id,
                message_id=last_id,
                text=text,
                parse_mode=parse_mode,
                reply_markup=reply_markup,
                disable_web_page_preview=disable_web_page_preview,
            )
            last_bot_messages[chat_id] = msg.message_id
            return msg
        except Exception:
            # Если редактирование не удалось — просто шлём новое
            pass

    msg = bot.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode=parse_mode,
        reply_markup=reply_markup,
        disable_web_page_preview=disable_web_page_preview,
    )
    last_bot_messages[chat_id] = msg.message_id
    return msg