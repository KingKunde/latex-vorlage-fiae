from pathlib import Path

from app.core import config as settings_module


def test_resolve_database_url_converts_relative_sqlite_path_to_absolute():
    resolved = settings_module._resolve_database_url("sqlite:///app/database.db")

    assert resolved == (
        f"sqlite:///{(settings_module.BASE_DIR / 'app' / 'database.db').resolve().as_posix()}"
    )


def test_resolve_database_url_keeps_memory_and_absolute_sqlite_paths():
    absolute_database_path = (Path.cwd() / "database.db").resolve().as_posix()

    assert settings_module._resolve_database_url("sqlite:///:memory:") == "sqlite:///:memory:"
    assert settings_module._resolve_database_url(
        f"sqlite:///{absolute_database_path}"
    ) == f"sqlite:///{absolute_database_path}"
