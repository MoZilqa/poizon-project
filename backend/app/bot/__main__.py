import asyncio
import logging

from .dispatcher import build_dispatcher, set_commands
from .instance import bot


async def main():
    if not bot:
        logging.warning("BOT_TOKEN не задан — бот не запущен, сайт работает без него")
        return
    await set_commands(bot)
    await build_dispatcher().start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
