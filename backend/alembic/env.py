import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.engine import Connection

from app import models  # noqa: F401 — регистрирует таблицы в Base.metadata
from app.db import Base, engine

if context.config.config_file_name:
    fileConfig(context.config.config_file_name)


def do_run(conn: Connection):
    context.configure(connection=conn, target_metadata=Base.metadata,
                      render_as_batch=conn.dialect.name == "sqlite")
    with context.begin_transaction():
        context.run_migrations()


async def main():
    async with engine.connect() as conn:
        await conn.run_sync(do_run)
    await engine.dispose()


asyncio.run(main())
