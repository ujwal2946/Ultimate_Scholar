import os

from dotenv import load_dotenv

# Load .env from project root (this file lives in the same directory)
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))



def get_env(name: str, default=None):
    v = os.getenv(name, default)
    return v


class Config:
    SECRET_KEY = get_env("FLASK_SECRET_KEY", "dev-secret-change-me")

    MYSQL_HOST = get_env("MYSQL_HOST", "localhost")
    MYSQL_PORT = int(get_env("MYSQL_PORT", "3306"))
    MYSQL_USER = get_env("MYSQL_USER", "root")
    MYSQL_PASSWORD = get_env("MYSQL_PASSWORD", "")
    MYSQL_DATABASE = get_env("MYSQL_DATABASE", "student_db")

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = False  # set True behind HTTPS

