import mimetypes

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import String, cast, func, or_, select

from ..bot.instance import bot
from ..bot.notify import notify_client, notify_receipt_rejected
from ..config import settings
from ..core import statuses as st
from ..core.pricing import SYSTEM, calc, money
from ..core.rates import apply_cached, sync_rate
from ..core.service import (TransitionError, change_status, get_cfg, load_order, reject_receipt, set_cfg,
                            set_track, status_counts)
from ..db import Session
from ..models import Order, User
from .auth import require_admin
from .schemas import CalcIn, CalcOut, OrderDetail, OrderOut, OrderPage, StatusIn, TrackIn

router = APIRouter(prefix="/api/admin", dependencies=[Depends(require_admin)])


def out(o: Order, model=OrderOut):
    return model.model_validate({
        **{c: getattr(o, c) for c in model.model_fields if hasattr(o, c)},
        "has_receipt": bool(o.receipt_id), "allowed": st.allowed(o.status),
    })


async def get_or_404(s, oid: int) -> Order:
    o = await load_order(s, oid)
    if not o:
        raise HTTPException(404, "Заказ не найден")
    return o


@router.get("/meta")
async def meta():
    return {"categories": st.CATEGORIES, "statuses": st.STATUSES, "flow": st.FLOW, "branches": st.BRANCHES,
            "final": sorted(st.FINAL), "bot_username": settings.bot_username}


@router.post("/calc", response_model=CalcOut)
async def calc_api(p: CalcIn):
    async with Session() as s:
        return calc(p.price_cny, p.category, await get_cfg(s))


@router.get("/stats")
async def stats():
    async with Session() as s:
        counts = await status_counts(s)
        paid = [x for x in st.FLOW if st.FLOW.index(x) >= st.FLOW.index(st.PAID)]
        revenue = await s.scalar(select(func.coalesce(func.sum(Order.total_rub), 0)).where(Order.status.in_(paid)))
        clients = await s.scalar(select(func.count()).select_from(User))
    return {"counts": counts, "revenue": money(revenue), "clients": clients,
            "active": sum(n for k, n in counts.items() if k not in st.FINAL)}


@router.get("/orders", response_model=OrderPage)
async def orders(status: str | None = None, q: str = "", limit: int = 50, offset: int = 0):
    query = select(Order).join(Order.user)
    if status == "active":
        query = query.where(Order.status.not_in(st.FINAL))
    elif status == "receipt":
        query = query.where(Order.status == st.AWAITING_PAYMENT, Order.receipt_id.is_not(None))
    elif status:
        query = query.where(Order.status == status)
    if q := q.strip().lstrip("#@"):
        like = f"%{q.lower()}%"
        query = query.where(or_(
            cast(Order.id, String) == q, func.lower(User.username).like(like),
            func.lower(Order.recipient).like(like), func.lower(Order.track_number).like(like),
        ))
    async with Session() as s:
        total = await s.scalar(select(func.count()).select_from(query.subquery()))
        rows = (await s.scalars(query.order_by(Order.id.desc()).limit(min(limit, 200)).offset(offset))).all()
    return {"items": [out(o) for o in rows], "total": total}


@router.get("/orders/{oid}", response_model=OrderDetail)
async def order(oid: int):
    async with Session() as s:
        return out(await get_or_404(s, oid), OrderDetail)


@router.post("/orders/{oid}/status", response_model=OrderDetail)
async def set_status(oid: int, p: StatusIn):
    async with Session() as s:
        await get_or_404(s, oid)
        try:
            o = await change_status(s, oid, p.status, actor="admin_site", track_number=p.track_number)
        except TransitionError as e:
            raise HTTPException(400, str(e))
    await notify_client(oid)  # клиент сразу получает сообщение в Telegram
    return out(o, OrderDetail)


@router.put("/orders/{oid}/track", response_model=OrderDetail)
async def put_track(oid: int, p: TrackIn):
    async with Session() as s:
        await get_or_404(s, oid)
        o = await set_track(s, oid, p.track_number)
        o = await load_order(s, oid)
    if o.status == st.SHIPPED_RU and o.track_number:
        await notify_client(oid)
    return out(o, OrderDetail)


@router.post("/orders/{oid}/reject-receipt", response_model=OrderDetail)
async def reject(oid: int):
    async with Session() as s:
        try:
            await reject_receipt(s, oid)
        except TransitionError as e:
            raise HTTPException(400, str(e))
        o = await load_order(s, oid)
    await notify_receipt_rejected(oid)
    return out(o, OrderDetail)


@router.get("/orders/{oid}/files/{kind}")
async def file(oid: int, kind: str):
    """Скриншот товара или чек — файлы хранятся в Telegram, отдаём через Bot API."""
    if kind not in ("screenshot", "receipt"):
        raise HTTPException(404)
    if not bot:
        raise HTTPException(503, "Бот не настроен (BOT_TOKEN)")
    async with Session() as s:
        o = await get_or_404(s, oid)
    file_id = o.screenshot_id if kind == "screenshot" else o.receipt_id
    if not file_id:
        raise HTTPException(404, "Файла нет")
    f = await bot.get_file(file_id)
    data = await bot.download_file(f.file_path)
    media = mimetypes.guess_type(f.file_path)[0] or "application/octet-stream"
    return Response(data.read(), media_type=media, headers={"Cache-Control": "private, max-age=3600"})


@router.get("/settings")
async def read_settings():
    async with Session() as s:
        return await get_cfg(s)


@router.put("/settings")
async def write_settings(data: dict[str, str]):
    async with Session() as s:
        auto = data.get("rate_auto", (await get_cfg(s))["rate_auto"]) == "1"
        try:
            for k, v in data.items():
                # служебные поля пишет только синхронизация; при автокурсе ручной курс игнорируем
                if k in SYSTEM or (k == "rate" and auto):
                    continue
                await set_cfg(s, k, v)
        except ValueError as e:
            raise HTTPException(400, str(e))
        await apply_cached(s)
        cfg = await get_cfg(s)
    if auto and not cfg["rate_cbr"]:  # автокурс только что включили — сразу тянем с ЦБ
        try:
            cfg = await sync_rate()
        except Exception:  # noqa: BLE001 — ошибка видна в rate_error
            async with Session() as s:
                cfg = await get_cfg(s)
    return cfg


@router.post("/rate/sync")
async def rate_sync():
    try:
        return await sync_rate(force=True)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"Не удалось получить курс ЦБ: {e}")
