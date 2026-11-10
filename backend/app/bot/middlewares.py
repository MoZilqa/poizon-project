from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from ..core.service import get_user
from ..db import Session


class DbMiddleware(BaseMiddleware):
    """Открывает сессию БД на апдейт и передаёт в хендлер `session` и `user`."""

    async def __call__(self, handler: Callable[[TelegramObject, dict], Awaitable[Any]],
                       event: TelegramObject, data: dict[str, Any]) -> Any:
        async with Session() as s:
            data["session"] = s
            if tg := data.get("event_from_user"):
                data["user"] = await get_user(s, tg.id, tg.username, tg.first_name)
            return await handler(event, data)
