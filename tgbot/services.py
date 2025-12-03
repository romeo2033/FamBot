"""
Сервисный слой: работа с пользователями, парами и вишлистами (БД-операции).
Никакой логики Telegram — только SQL и простые функции.
"""

from __future__ import annotations

from datetime import date
import secrets
from typing import Any, Dict, List, Optional

try:
    from db import fetchone, fetchall, execute, execute_returning_one
except ModuleNotFoundError:
    from tgbot.db import fetchone, fetchall, execute, execute_returning_one


# ===== Пользователи и пары =====


def get_or_create_user(tg_user) -> int:
    """Вернуть ID пользователя в нашей БД, при необходимости создавая запись."""
    row = fetchone(
        "SELECT id FROM users WHERE telegram_id = %s",
        (tg_user.id,),
    )
    if row:
        return row["id"]

    execute(
        """
        INSERT INTO users (telegram_id, username, first_name, last_name)
        VALUES (%s, %s, %s, %s)
        """,
        (tg_user.id, tg_user.username, tg_user.first_name, tg_user.last_name),
    )

    row = fetchone("SELECT id FROM users WHERE telegram_id = %s", (tg_user.id,))
    return row["id"]


def get_pair_by_user(user_id: int) -> Optional[Dict[str, Any]]:
    """Получить пару, в которой состоит данный пользователь (если есть)."""
    return fetchone(
        """
        SELECT * FROM pairs
        WHERE creator_user_id = %s OR partner_user_id = %s
        """,
        (user_id, user_id),
    )


def link_partner_to_pair(invite_token: str, partner_user_id: int):
    """
    Обработка перехода по ссылке-приглашению.
    Пары создаются ТОЛЬКО здесь, сразу с двумя участниками.
    Возвращает (pair, reason), где reason:
      - 'ok'
      - 'not_found'
      - 'self'
      - 'has_pair'
      - 'creator_has_pair'
    """
    invite = fetchone(
        "SELECT * FROM pair_invites WHERE invite_token = %s",
        (invite_token,),
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
        (creator_user_id, partner_user_id, invite_token),
    )

    # Инвайт больше не нужен
    execute("DELETE FROM pair_invites WHERE id = %s", (invite["id"],))

    return pair, "ok"


def set_pair_start_date(pair_id: int, start_date: date) -> None:
    """Установить / обновить дату начала отношений для пары."""
    execute(
        "UPDATE pairs SET start_date = %s WHERE id = %s",
        (start_date, pair_id),
    )


def set_pair_cloud_url(pair_id: int, url: str) -> None:
    """Установить / обновить ссылку на общий диск для пары."""
    execute(
        "UPDATE pairs SET cloud_drive_url = %s WHERE id = %s",
        (url, pair_id),
    )


def get_or_create_invite_for_user(user_id: int) -> Dict[str, Any]:
    """
    Получить действующий инвайт для пользователя,
    либо создать новый, если его нет.
    """
    invite = fetchone(
        "SELECT * FROM pair_invites WHERE creator_user_id = %s",
        (user_id,),
    )
    if invite:
        return invite

    token = secrets.token_urlsafe(8)
    execute(
        """
        INSERT INTO pair_invites (creator_user_id, invite_token)
        VALUES (%s, %s)
        """,
        (user_id, token),
    )
    return fetchone(
        "SELECT * FROM pair_invites WHERE creator_user_id = %s",
        (user_id,),
    )


# ===== Вишлисты =====


def add_wishlist_item(
    pair_id: int,
    owner_user_id: int,
    title: str,
    description: Optional[str] = None,
):
    """Добавить элемент в список желаний пользователя в рамках пары."""
    return execute_returning_one(
        """
        INSERT INTO wishlist_items (pair_id, owner_user_id, title, description, url)
        VALUES (%s, %s, %s, %s, NULL)
        RETURNING *
        """,
        (pair_id, owner_user_id, title, description),
    )


def get_wishlist_for_pair(pair_id: int) -> List[Dict[str, Any]]:
    """Получить общий список желаний пары."""
    return fetchall(
        """
        SELECT w.*, u.first_name, u.username
        FROM wishlist_items w
        JOIN users u ON w.owner_user_id = u.id
        WHERE w.pair_id = %s
        ORDER BY w.created_at
        """,
        (pair_id,),
    )


def get_wishlist_for_owner(pair_id: int, owner_user_id: int) -> List[Dict[str, Any]]:
    """Получить список желаний конкретного участника пары."""
    return fetchall(
        """
        SELECT w.*, u.first_name, u.username
        FROM wishlist_items w
        JOIN users u ON w.owner_user_id = u.id
        WHERE w.pair_id = %s AND w.owner_user_id = %s
        ORDER BY w.created_at
        """,
        (pair_id, owner_user_id),
    )