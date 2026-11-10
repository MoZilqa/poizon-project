from pathlib import Path
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    # .env в корне проекта; в Docker переменные приходят из env_file compose
    model_config = SettingsConfigDict(env_file=Path(__file__).resolve().parents[2] / ".env", extra="ignore")

    bot_token: str = ""
    bot_username: str = ""
    # Telegram ID администраторов через запятую: 111,222
    admin_ids: Annotated[list[int], NoDecode] = []
    admin_contact: str = ""
    # Пароль входа в админку сайта и секрет для подписи сессий
    admin_password: str = "change-me"
    secret_key: str = "change-me-too"
    session_hours: int = 24
    database_url: str = "sqlite+aiosqlite:///./poizon.db"
    # Для FSM бота; без него состояния хранятся в памяти и теряются при рестарте
    redis_url: str = ""
    # Локальная разработка: поднять polling бота внутри uvicorn (одним процессом)
    bot_in_api: bool = False

    @field_validator("admin_ids", mode="before")
    @classmethod
    def _split_ids(cls, v):
        if isinstance(v, str):
            ids = [x for x in v.replace(" ", "").split(",") if x and x != "0"]
            if bad := [x for x in ids if not x.lstrip("-").isdigit()]:
                raise ValueError(f"ADMIN_IDS — числовые Telegram ID через запятую (узнать у @userinfobot), "
                                 f"а не юзернеймы: {', '.join(bad)}")
            return [int(x) for x in ids]
        return v

    def is_admin(self, tg_id: int) -> bool:
        return tg_id in self.admin_ids


settings = Settings()
