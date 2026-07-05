import os
import pymysql

from config import Config


def _db_config_sanity_check():
    # Fail fast with actionable info; do not print the actual password.
    missing = [
        name
        for name, val in [
            ("MYSQL_HOST", Config.MYSQL_HOST),
            ("MYSQL_PORT", str(Config.MYSQL_PORT)),
            ("MYSQL_USER", Config.MYSQL_USER),
            ("MYSQL_DATABASE", Config.MYSQL_DATABASE),
        ]
        if val is None or str(val).strip() == ""
    ]
    if missing:
        raise RuntimeError(f"DB config missing values: {', '.join(missing)}")

    # If password is empty, the MySQL error matches: using password: NO
    if Config.MYSQL_PASSWORD is None or str(Config.MYSQL_PASSWORD) == "":
        raise RuntimeError(
            "DB password is empty. Set MYSQL_PASSWORD in .env (or environment) for this project. "
            "Do not rely on default empty password for MySQL 'root'."
        )


def get_connection():
    _db_config_sanity_check()
    return pymysql.connect(
        host=Config.MYSQL_HOST,
        port=Config.MYSQL_PORT,
        user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD,
        database=Config.MYSQL_DATABASE,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
    )



def fetch_one(query: str, params: tuple = None):
    params = params or ()
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(query, params)
            return cur.fetchone()
    finally:
        conn.close()


def execute(query: str, params: tuple = None):
    params = params or ()
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(query, params)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

