import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_FILE = BASE_DIR / ".env"

ROLE_ROOT = "root"
ROLE_ADMIN = "admin"
ROLE_USER = "user"
SESSION_USER_KEY = "user_id"
SESSION_LAST_SEEN_KEY = "last_seen_at"
SESSION_TIMEOUT = timedelta(minutes=30)
LOGIN_RATE_LIMIT_WINDOW = timedelta(minutes=5)
LOGIN_RATE_LIMIT_COUNT = 10
LOGIN_LOCKOUT_THRESHOLD = 5
LOGIN_LOCKOUT_DURATION = timedelta(minutes=15)


@dataclass(frozen=True)
class RootSettings:
    email: str = ""
    password: str = ""
    first_name: str = ""
    last_name: str = ""

    @property
    def is_configured(self) -> bool:
        return all((self.email, self.password, self.first_name, self.last_name))


@dataclass(frozen=True)
class Settings:
    app_title: str
    database_url: str
    session_secret_key: str
    session_same_site: str
    session_cookie_secure: bool
    session_max_age: int
    root: RootSettings


@dataclass(frozen=True)
class AppPaths:
    project_root: Path
    app_dir: Path
    web_dir: Path
    templates_dir: Path
    static_dir: Path
    postfix_dir: Path


def load_env_file() -> None:
    if not ENV_FILE.exists():
        return

    for raw_line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if value and value[0] not in {"'", '"'} and " #" in value:
            value = value.split(" #", 1)[0].rstrip()
        value = value.strip('"').strip("'")
        os.environ.setdefault(key, value)


def _env_bool(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() == "true"


def _default_database_url() -> str:
    default_sqlite_file = BASE_DIR / "app" / "database.db"
    return f"sqlite:///{default_sqlite_file.as_posix()}"


def _resolve_database_url(raw_database_url: str) -> str:
    sqlite_prefix = "sqlite:///"
    if not raw_database_url.startswith(sqlite_prefix):
        return raw_database_url

    database_path = raw_database_url.removeprefix(sqlite_prefix)
    if not database_path or database_path == ":memory:":
        return raw_database_url

    path = Path(database_path)
    if path.is_absolute():
        return raw_database_url

    return f"{sqlite_prefix}{(BASE_DIR / path).resolve().as_posix()}"


@lru_cache
def get_app_paths() -> AppPaths:
    app_dir = BASE_DIR / "app"
    web_dir = app_dir / "web"
    return AppPaths(
        project_root=BASE_DIR,
        app_dir=app_dir,
        web_dir=web_dir,
        templates_dir=web_dir / "templates",
        static_dir=web_dir / "static",
        postfix_dir=BASE_DIR / "postfix",
    )


@lru_cache
def get_settings() -> Settings:
    load_env_file()
    return Settings(
        app_title=os.getenv("APP_TITLE", "Antispam Admin Center"),
        database_url=_resolve_database_url(
            os.getenv("DATABASE_URL", _default_database_url())
        ),
        session_secret_key=os.getenv(
            "SESSION_SECRET_KEY", "replace-this-in-production"
        ),
        session_same_site=os.getenv("SESSION_SAME_SITE", "lax"),
        session_cookie_secure=_env_bool("SESSION_COOKIE_SECURE", False),
        session_max_age=int(os.getenv("SESSION_MAX_AGE_SECONDS", str(60 * 30))),
        root=RootSettings(
            email=os.getenv("ROOT_EMAIL", "").strip().lower(),
            password=os.getenv("ROOT_PASSWORD", "").strip(),
            first_name=os.getenv("ROOT_FIRST_NAME", "").strip(),
            last_name=os.getenv("ROOT_LAST_NAME", "").strip(),
        ),
    )


def utc_now() -> datetime:
    return datetime.now(UTC)
