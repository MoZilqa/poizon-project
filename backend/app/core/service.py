"""Операции с БД, общие для бота и API."""
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..models import Order, Setting, StatusLog, User
from . import statuses as st
from .pricing import DEFAULTS, SYSTEM, validate_setting


class TransitionError(ValueError):
    pass


async def get_cfg(s: AsyncSession) -> dict:
    rows = (await s.scalars(select(Setting))).all()
    return {**DEFAULTS, **{k: "" for k in SYSTEM}, **{r.key: r.value for r in rows}}


async def set_cfg(s: AsyncSession, key: str, value: str, commit: bool = True) -> str:
    if key not in SYSTEM:
        value = validate_setting(key, value)
    row = await s.get(Setting, key)
    if row:
        row.value = value
    else:
        s.add(Setting(key=key, value=value))
    if commit:
        await s.commit()
    return value


async def get_user(s: AsyncSession, tg_id: int, username: str | None = None,
                   first_name: str | None = None) -> User:
    u = await s.scalar(select(User).where(User.tg_id == tg_id))
    if not u:
        u = User(tg_id=tg_id)
        s.add(u)
    fresh = (username, first_name, settings.is_admin(tg_id))
    if u.id is None or (u.username, u.first_name, u.is_admin) != fresh:
        u.username, u.first_name, u.is_admin = fresh
        await s.commit()
    return u


async def create_order(s: AsyncSession, user: User, d: dict) -> Order:
    o = Order(
        user_id=user.id, url=d["url"], screenshot_id=d["shot"], size=d["size"],
        category=d["cat"], price_cny=Decimal(d["price"]), total_rub=Decimal(d["total"]),
        status=st.NEW, recipient=f'{d["fio"]}, {d["phone"]}, {d["pvz"]}',
    )
    s.add(o)
    await s.flush()
    s.add(StatusLog(order_id=o.id, status=o.status, actor="client"))
    await s.commit()
    return await load_order(s, o.id)


async def load_order(s: AsyncSession, oid: int, lock: bool = False) -> Order | None:
    q = select(Order).where(Order.id == oid).execution_options(populate_existing=True)
    if lock:  # защита от двойного нажатия: в PostgreSQL блокируем строку
        q = q.with_for_update(of=Order)
    return await s.scalar(q)


async def change_status(s: AsyncSession, oid: int, new: str, actor: str,
                        track_number: str | None = None) -> Order:
    """Переводит заказ только в следующий статус или в ветку отмены."""
    o = await load_order(s, oid, lock=True)
    if not o:
        raise TransitionError("Заказ не найден")
    if o.status in st.FINAL:
        raise TransitionError("Заказ уже завершён")
    if actor == "client":
        if new != st.CANCELLED or o.status not in (st.NEW, st.AWAITING_PAYMENT):
            raise TransitionError("Отменить заказ можно только до оплаты")
        if o.receipt_id:
            raise TransitionError("Чек уже отправлен — напишите администратору")
    elif new not in st.allowed(o.status):
        raise TransitionError(f"Нельзя перевести из «{st.STATUSES[o.status]}» в «{st.STATUSES.get(new, new)}»")
    if track_number:
        o.track_number = track_number.strip()
    if new == st.SHIPPED_RU and not o.track_number:
        raise TransitionError("Для статуса «Отправлен в РФ» нужен трек-номер")
    o.status = new
    s.add(StatusLog(order_id=o.id, status=new, actor=actor))
    await s.commit()
    return await load_order(s, oid)


async def attach_receipt(s: AsyncSession, oid: int, user: User, file_id: str) -> Order:
    o = await load_order(s, oid, lock=True)
    if not o or o.user_id != user.id:
        raise TransitionError("Заказ не найден")
    if o.status != st.AWAITING_PAYMENT:
        raise TransitionError("Этот заказ сейчас нельзя оплатить")
    o.receipt_id = file_id
    await s.commit()
    return o


async def reject_receipt(s: AsyncSession, oid: int) -> Order:
    o = await load_order(s, oid, lock=True)
    if not o or o.status != st.AWAITING_PAYMENT or not o.receipt_id:
        raise TransitionError("Нет чека на проверке")
    o.receipt_id = None
    await s.commit()
    return o


async def set_track(s: AsyncSession, oid: int, track: str | None) -> Order:
    o = await load_order(s, oid)
    if not o:
        raise TransitionError("Заказ не найден")
    o.track_number = (track or "").strip() or None
    await s.commit()
    return o


async def status_counts(s: AsyncSession) -> dict[str, int]:
    rows = await s.execute(select(Order.status, func.count()).group_by(Order.status))
    return {k: 0 for k in st.STATUSES} | dict(rows.all())
