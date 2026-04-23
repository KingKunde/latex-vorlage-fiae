from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session
from starlette.middleware.sessions import SessionMiddleware

from app.core.config import get_app_paths, get_settings
from app.core.db import create_db_and_tables, engine, ensure_root_user
from app.core.logging import setup_logging
from app.services.postfix_export import sync_all_postfix_exports
from app.web.api.router import api_router


def create_application() -> FastAPI:
    settings = get_settings()
    app_paths = get_app_paths()
    setup_logging()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        create_db_and_tables()
        with Session(engine) as session:
            ensure_root_user(session, settings.root)
            sync_all_postfix_exports(session)
        yield

    app = FastAPI(title=settings.app_title, lifespan=lifespan)
    app.mount("/static", StaticFiles(directory=str(app_paths.static_dir)), name="static")
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.session_secret_key,
        same_site=settings.session_same_site,
        https_only=settings.session_cookie_secure,
        max_age=settings.session_max_age,
    )
    app.include_router(api_router)
    return app


app = create_application()
