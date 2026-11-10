"""Объект Bot общий для процесса бота и API (API через него шлёт уведомления и качает файлы)."""
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties

from ..config import settings

bot: Bot | None = (
    Bot(settings.bot_token, default=DefaultBotProperties(parse_mode="HTML")) if settings.bot_token else None
)
