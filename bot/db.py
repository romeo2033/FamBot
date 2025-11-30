import psycopg2
import psycopg2.extras
from contextlib import contextmanager

from config import DATABASE_URL


@contextmanager
def get_conn():
    conn = psycopg2.connect(DATABASE_URL)
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
