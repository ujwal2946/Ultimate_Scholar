import os

from dotenv import load_dotenv

# Load .env locally; Azure App Service environment variables take precedence.
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))


def get_env(name: str, default=None):
    return os.getenv(name, default)


class Config:
    SECRET_KEY = get_env("FLASK_SECRET_KEY", "dev-secret-change-me")

    MYSQL_HOST = get_env("MYSQL_HOST", "localhost")
    MYSQL_PORT = int(get_env("MYSQL_PORT", "3306"))
    MYSQL_USER = get_env("MYSQL_USER", "root")
    MYSQL_PASSWORD = get_env("MYSQL_PASSWORD", "")
    MYSQL_DATABASE = get_env("MYSQL_DATABASE", "student_db")

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    # Azure App Service serves the production app over HTTPS.
    SESSION_COOKIE_SECURE = get_env("SESSION_COOKIE_SECURE", "False").lower() == "true"
