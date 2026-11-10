from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.base import BaseStorage
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, BotCommandScopeChat, BotCommandScopeDefault

from ..config import settings
from . import handlers
from .middlewares import DbMiddleware


def storage() -> BaseStorage:
    if settings.redis_url:
        from aiogram.fsm.storage.redis import RedisStorage
        return RedisStorage.from_url(settings.redis_url)
    return MemoryStorage()


def build_dispatcher() -> Dispatcher:
    dp = Dispatcher(storage=storage())
    dp.message.outer_middleware(DbMiddleware())
    dp.callback_query.outer_middleware(DbMiddleware())
    dp.include_router(handlers.build())
    return dp


async def set_commands(bot: Bot):
    client = [BotCommand(command="start", description="Главное меню"),
              BotCommand(command="help", description="Помощь"),
              BotCommand(command="cancel", description="Отменить действие")]
    admin = client + [BotCommand(command="orders", description="Заказы"),
                      BotCommand(command="settings", description="Курс, наценка, тарифы"),
                      BotCommand(command="admin", description="Все команды администратора")]
    await bot.set_my_commands(client, BotCommandScopeDefault())
    for admin_id in settings.admin_ids:
        await bot.set_my_commands(admin, BotCommandScopeChat(chat_id=admin_id))
