import psycopg2
import psycopg2.extras
from contextlib import contextmanager
import os
from tgbot.config import DATABASE_URL


@contextmanager
def get_conn():
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", "5432")),
        dbname=os.getenv("DB_NAME", "lovebot"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD"),
    )
    try:
        yield conn
    finally:
        conn.close()


def fetchone(query, params=None):
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, params or ())
            return cur.fetchone()


def fetchall(query, params=None):
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, params or ())
            return cur.fetchall()


def execute(query, params=None):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params or ())
        conn.commit()

def execute_returning_one(query, params=None):
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, params or ())
            row = cur.fetchone()
        conn.commit()
    return row
