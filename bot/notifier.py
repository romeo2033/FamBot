import json
from datetime import date as _date, timedelta

import telebot

from config import BOT_TOKEN
from db import fetchall, fetchone, execute

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

# Красивые числа дней
BEAUTIFUL_DAYS = [100, 200, 300, 400, 500, 600, 700, 800, 900,
                  1000, 1500, 2000, 2500, 3000]


def get_all_pairs_with_start_date():
    """
    Берём все пары, у которых указана дата начала отношений.
    """
    return fetchall(
        """
        SELECT id, creator_user_id, partner_user_id, start_date
        FROM pairs
        WHERE start_date IS NOT NULL
        """
    )


def get_pair_telegram_ids(pair_row):
    """
    Получить telegram_id обоих участников пары.
    """
    ids = []
    for user_id in (pair_row["creator_user_id"], pair_row["partner_user_id"]):
        if not user_id:
            continue
        row = fetchone(
            "SELECT telegram_id FROM users WHERE id = %s",
            (user_id,)
        )
        if row and row["telegram_id"]:
            ids.append(row["telegram_id"])
    return ids


def notification_already_sent(pair_id: int, notif_type: str, payload_key: str, payload_value: str) -> bool:
    """
    Проверяем, отправляли ли уведомление с таким типом и значением.
    payload_key: ключ в JSON (например 'year' или 'days')
    payload_value: строковое значение этого поля
    """
    row = fetchone(
        f"""
        SELECT 1
        FROM notifications_log
        WHERE pair_id = %s
          AND notif_type = %s
          AND payload->>%s = %s
        """,
        (pair_id, notif_type, payload_key, payload_value)
    )
    return row is not None


def log_notification(pair_id: int, notif_type: str, payload: dict):
    execute(
        """
        INSERT INTO notifications_log (pair_id, notif_type, payload)
        VALUES (%s, %s, %s)
        """,
        (pair_id, notif_type, json.dumps(payload))
    )


def handle_anniversaries_for_pair(pair):
    """
    Обработка годовщин и напоминаний (7 дней, 1 день, в день годовщины).
    """
    pair_id = pair["id"]
    start = pair["start_date"]
    if start is None:
        return

    today = _date.today()

    # Если дата в будущем – игнорируем, что-то ввели странно
    if start > today:
        return

    # Текущая/следующая годовщина
    anniv_this_year = _date(today.year, start.month, start.day)

    if anniv_this_year >= today:
        upcoming_anniv = anniv_this_year
    else:
        upcoming_anniv = _date(today.year + 1, start.month, start.day)

    # какой это по счёту год
    year_n = upcoming_anniv.year - start.year
    if year_n <= 0:
        return  # до первой годовщины ещё не дожили

    days_to_anniv = (upcoming_anniv - today).days

    # 7 дней до годовщины
    if days_to_anniv == 7:
        if not notification_already_sent(pair_id, "year_anniversary_7d", "year", str(year_n)):
            send_year_anniversary_7d(pair, year_n, upcoming_anniv)
            log_notification(pair_id, "year_anniversary_7d", {"year": year_n})

    # 1 день до годовщины
    if days_to_anniv == 1:
        if not notification_already_sent(pair_id, "year_anniversary_1d", "year", str(year_n)):
            send_year_anniversary_1d(pair, year_n, upcoming_anniv)
            log_notification(pair_id, "year_anniversary_1d", {"year": year_n})

    # В день годовщины
    if days_to_anniv == 0 and upcoming_anniv == today:
        if not notification_already_sent(pair_id, "year_anniversary", "year", str(year_n)):
            send_year_anniversary(pair, year_n)
            log_notification(pair_id, "year_anniversary", {"year": year_n})


def handle_beautiful_days_for_pair(pair):
    """
    Обработка красивых чисел дней: 100, 200, 500, 1000 и т.д.
    """
    pair_id = pair["id"]
    start = pair["start_date"]
    if start is None:
        return

    today = _date.today()
    if start > today:
        return

    days_together = (today - start).days

    if days_together in BEAUTIFUL_DAYS:
        if not notification_already_sent(pair_id, "beautiful_day", "days", str(days_together)):
            send_beautiful_day(pair, days_together)
            log_notification(pair_id, "beautiful_day", {"days": days_together})


# ====== Функции отправки сообщений ======

def send_to_pair(pair, text: str):
    tg_ids = get_pair_telegram_ids(pair)
    for tg_id in tg_ids:
        try:
            bot.send_message(tg_id, text)
        except Exception as e:
            print(f"Failed to send to {tg_id}: {e}")


def send_year_anniversary_7d(pair, year_n: int, date_anniv: _date):
    date_str = date_anniv.strftime("%d.%m.%Y")
    text = (
        f"⏳ Через 7 дней у вас годовщина — <b>{year_n}</b> лет вместе! 💑\n\n"
        f"Дата годовщины: <b>{date_str}</b>\n"
        f"Самое время придумать что-то особенное друг для друга 💕"
    )
    send_to_pair(pair, text)


def send_year_anniversary_1d(pair, year_n: int, date_anniv: _date):
    date_str = date_anniv.strftime("%d.%m.%Y")
    text = (
        f"⏰ Завтра у вас годовщина — <b>{year_n}</b> лет вместе! 💑\n\n"
        f"Дата годовщины: <b>{date_str}</b>\n"
        f"Если ещё не придумали сюрприз — самое время 🌸"
    )
    send_to_pair(pair, text)


def send_year_anniversary(pair, year_n: int):
    text = (
        f"🎉 Сегодня ваш маленький праздник!\n\n"
        f"Вам исполнилось <b>{year_n}</b> лет вместе 💖\n"
        f"Хороший повод обняться подольше, чем обычно 🥰"
    )
    send_to_pair(pair, text)


def send_beautiful_day(pair, days_together: int):
    text = (
        f"✨ Красивое число: сегодня вы вместе уже <b>{days_together}</b> дней! 💫\n\n"
        f"Пусть этот день будет таким же особенным, как и ваше «вместе» 💕"
    )
    send_to_pair(pair, text)


def main():
    print("Notifier started")
    pairs = get_all_pairs_with_start_date()
    today = _date.today()
    print(f"Processing {len(pairs)} pairs for date {today.isoformat()}")

    for pair in pairs:
        try:
            handle_anniversaries_for_pair(pair)
            handle_beautiful_days_for_pair(pair)
        except Exception as e:
            print(f"Error processing pair {pair['id']}: {e}")

    print("Notifier finished")


if __name__ == "__main__":
    main()