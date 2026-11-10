"""FastAPI-приложение: публичный калькулятор, админ-API и собранный фронтенд."""
import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from ..bot.instance import bot
from ..config import settings
from ..core.rates import rate_loop
from . import admin, public

log = logging.getLogger(__name__)
STATIC = Path("static")


@asynccontextmanager
async def lifespan(app: FastAPI):
    tasks = [asyncio.create_task(rate_loop())]  # автокурс юаня с ЦБ
    if settings.bot_in_api and bot:  # локальная разработка: бот в том же процессе
        from ..bot.dispatcher import build_dispatcher
        tasks.append(asyncio.create_task(build_dispatcher().start_polling(bot, handle_signals=False)))
        log.info("bot polling started inside API")
    yield
    for t in tasks:
        t.cancel()
    if bot:
        await bot.session.close()


app = FastAPI(title="Poizon admin", lifespan=lifespan, docs_url=None, redoc_url=None)
app.include_router(public.router)
app.include_router(admin.router)


@app.get("/api/health")
async def health():
    return {"ok": True}


# собранный фронтенд (в Docker лежит в ./static); SPA: неизвестные пути отдают index.html
if STATIC.exists():
    app.mount("/assets", StaticFiles(directory=STATIC / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    async def spa(path: str):
        if path.startswith("api/"):
            raise HTTPException(404)
        f = (STATIC / path).resolve()
        inside = f.is_relative_to(STATIC.resolve())
        # сайт — только админка: не индексируем
        return FileResponse(f if path and inside and f.is_file() else STATIC / "index.html",
                            headers={"X-Robots-Tag": "noindex, nofollow"})
