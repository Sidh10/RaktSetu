"""FastAPI app factory. Run: make api (uvicorn --factory app.main:create_app). Simulated data, mock channel, not clinically validated."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.config import Settings, load_env_file
from app.db import init_db, make_engine, make_sessionmaker
from app.services.errors import DomainError

ROOT = Path(__file__).resolve().parents[2]
DIST = ROOT / "frontend" / "dist"


def _resolve_sqlite(url: str) -> str:
    """Relative SQLite paths are relative to raktsetu-app/, whatever the working directory."""
    if url.startswith("sqlite:///") and not url.endswith(":memory:"):
        p = Path(url.removeprefix("sqlite:///"))
        if not p.is_absolute():
            p = ROOT / p
            p.parent.mkdir(parents=True, exist_ok=True)
            return f"sqlite:///{p.as_posix()}"
    return url


def create_app(settings: Settings | None = None, engine=None) -> FastAPI:
    if settings is None:
        load_env_file(ROOT / ".env")      # optional; shell variables win
        settings = Settings()
    engine = engine or make_engine(_resolve_sqlite(settings.database_url))
    init_db(engine)
    app = FastAPI(title="RaktSetu prototype API",
                  description="Simulated data · mock channel · not clinically validated · demo users, not real auth")
    app.state.settings, app.state.engine, app.state.sessionmaker = settings, engine, make_sessionmaker(engine)

    @app.exception_handler(DomainError)
    async def domain_error(_: Request, exc: DomainError):
        return JSONResponse(status_code=exc.status, content=dict(error=dict(
            code=exc.code, message=exc.message, details=jsonable_encoder(exc.details))))

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError):
        errs = [dict(loc=list(e.get("loc", [])), msg=e.get("msg"), type=e.get("type")) for e in exc.errors()]
        return JSONResponse(status_code=400, content=dict(error=dict(
            code="validation_error", message="request body or parameters are invalid", details=dict(errors=errs))))

    app.include_router(router)
    if DIST.exists():   # Stage 3: built UI served from the same process
        app.mount("/", StaticFiles(directory=DIST, html=True), name="ui")
    return app
