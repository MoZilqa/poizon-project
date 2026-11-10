"""Команды и кнопки администратора. Доступ — только для ADMIN_IDS."""
from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...config import settings
from ...core import statuses as st
from ...core.rates import sync_rate
from ...core.service import (TransitionError, change_status, get_cfg, load_order, reject_receipt, set_cfg,
                             set_track, status_counts)
from ...models import Order
from .. import keyboards as kb
from ..notify import notify_client, notify_receipt_rejected, send_admin_card
from ..texts import ADMIN_HELP, admin_card, esc

r = Router()
is_admin = F.from_user.id.func(settings.is_admin)
r.message.filter(is_admin)
r.callback_query.filter(is_admin)


class AdminSt(StatesGroup):
    track = State()


async def refresh(msg: Message, o: Order):
    """Обновить карточку заказа в сообщении (подпись к фото/файлу или текст)."""
    try:
        if msg.photo or msg.document:
            await msg.edit_caption(caption=admin_card(o), reply_markup=kb.admin_order_kb(o))
        else:
            await msg.edit_text(admin_card(o), reply_markup=kb.admin_order_kb(o))
    except TelegramBadRequest:
        pass  # сообщение не изменилось или слишком старое


@r.message(Command("admin"))
async def admin_help(m: Message):
    await m.answer(ADMIN_HELP)


# ---------- заказы ----------
@r.message(Command("orders"))
async def orders(m: Message, session: AsyncSession):
    await m.answer("Фильтр по статусу:", reply_markup=kb.filter_kb(await status_counts(session)))


@r.callback_query(kb.FilterCb.filter())
async def orders_filtered(c: CallbackQuery, callback_data: kb.FilterCb, session: AsyncSession):
    q = select(Order).order_by(Order.id.desc()).limit(10)
    if callback_data.status != "all":
        q = q.where(Order.status == callback_data.status)
    rows = (await session.scalars(q)).all()
    await c.answer()
    if not rows:
        return await c.message.answer("Заказов нет")
    for o in rows:
        await c.message.answer(admin_card(o), reply_markup=kb.admin_order_kb(o))


@r.message(Command("order"))
async def order_card(m: Message, command: CommandObject, session: AsyncSession):
    if not (command.args or "").strip().isdigit():
        return await m.answer("Формат: /order 5")
    o = await load_order(session, int(command.args))
    if not o:
        return await m.answer("Заказ не найден")
    await send_admin_card(m.chat.id, o, o.screenshot_id)


@r.callback_query(kb.StatusCb.filter())
async def status_btn(c: CallbackQuery, callback_data: kb.StatusCb, state: FSMContext, session: AsyncSession):
    o = await load_order(session, callback_data.id)
    if not o:
        return await c.answer("Заказ не найден", show_alert=True)
    if callback_data.to == st.SHIPPED_RU and not o.track_number:
        # трек-номер обязателен: спрашиваем и переводим статус после ответа
        await state.set_state(AdminSt.track)
        await state.update_data(oid=o.id)
        await c.message.answer(f"Введите трек-номер для заказа №{o.id} (или /cancel)")
        return await c.answer()
    try:
        o = await change_status(session, o.id, callback_data.to, actor="admin_bot")
    except TransitionError as e:
        return await c.answer(str(e), show_alert=True)
    await refresh(c.message, o)
    await c.answer(st.STATUSES[o.status])
    await notify_client(o.id)


@r.message(AdminSt.track, F.text, ~F.text.startswith("/"))
async def track_input(m: Message, state: FSMContext, session: AsyncSession):
    oid = (await state.get_data())["oid"]
    await state.clear()
    try:
        o = await change_status(session, oid, st.SHIPPED_RU, actor="admin_bot", track_number=m.text[:64])
    except TransitionError as e:
        return await m.answer(str(e))
    await m.answer(admin_card(o), reply_markup=kb.admin_order_kb(o))
    await notify_client(o.id)


@r.callback_query(kb.ReceiptRejectCb.filter())
async def receipt_reject(c: CallbackQuery, callback_data: kb.ReceiptRejectCb, session: AsyncSession):
    try:
        o = await reject_receipt(session, callback_data.id)
    except TransitionError as e:
        return await c.answer(str(e), show_alert=True)
    await refresh(c.message, await load_order(session, o.id))
    await c.answer("Чек отклонён, клиент получит уведомление")
    await notify_receipt_rejected(o.id)


@r.message(Command("track"))
async def cmd_track(m: Message, command: CommandObject, session: AsyncSession):
    oid, _, num = (command.args or "").strip().partition(" ")
    if not oid.isdigit() or not num.strip():
        return await m.answer("Формат: /track 5 RU123456")
    try:
        o = await set_track(session, int(oid), num[:64])
    except TransitionError as e:
        return await m.answer(str(e))
    await m.answer(f"Трек-номер заказа №{o.id} сохранён")
    if o.status == st.SHIPPED_RU:
        await notify_client(o.id)


# ---------- настройки ----------
@r.message(Command("settings"))
async def cmd_settings(m: Message, session: AsyncSession):
    c = await get_cfg(session)
    if c["rate_auto"] == "1":
        rate = (f"Курс: {c['rate']} ₽/¥ — авто, ЦБ {c['rate_cbr'] or '—'} + {c['rate_extra']}%"
                f"\nОбновлён: {c['rate_synced_at'][:16].replace('T', ' ') or '—'} UTC")
        if c["rate_error"]:
            rate += f"\n⚠️ Ошибка синхронизации: {esc(c['rate_error'][:200])}"
    else:
        rate = f"Курс: {c['rate']} ₽/¥ — вручную (/rate auto — брать с ЦБ)"
    await m.answer(f"{rate}\nНаценка: {c['markup']}%\n"
                   f"Доставка: обувь {c['delivery_shoes']} ₽, одежда {c['delivery_clothes']} ₽, "
                   f"аксессуары {c['delivery_accessories']} ₽\n\nРеквизиты:\n{esc(c['requisites'])}")


async def put(m: Message, session: AsyncSession, key: str, val: str | None):
    try:
        val = await set_cfg(session, key, val or "")
    except ValueError as e:
        return await m.answer(str(e))
    await m.answer(f"Сохранено: {key} = {esc(val)}")


@r.message(Command("rate"))
async def cmd_rate(m: Message, command: CommandObject, session: AsyncSession):
    """/rate 12.5 — вручную (автокурс выключается); /rate auto [надбавка %] — курс ЦБ."""
    word, _, extra = (command.args or "").strip().partition(" ")
    if word.lower() != "auto":
        try:
            rate = await set_cfg(session, "rate", command.args or "")
        except ValueError as e:
            return await m.answer(str(e))
        await set_cfg(session, "rate_auto", "0")
        return await m.answer(f"Курс {rate} ₽/¥ задан вручную, автокурс выключен (/rate auto — включить)")
    try:
        if extra.strip():
            await set_cfg(session, "rate_extra", extra)
        await set_cfg(session, "rate_auto", "1")
        c = await sync_rate()
    except ValueError as e:
        return await m.answer(str(e))
    except Exception as e:  # noqa: BLE001
        return await m.answer(f"Автокурс включён, но ЦБ сейчас не ответил: {esc(str(e)[:200])}. Попробую через час.")
    await m.answer(f"Автокурс включён: ЦБ {c['rate_cbr']} + {c['rate_extra']}% = <b>{c['rate']} ₽/¥</b>")


@r.message(Command("markup"))
async def cmd_markup(m: Message, command: CommandObject, session: AsyncSession):
    await put(m, session, "markup", command.args)


@r.message(Command("requisites"))
async def cmd_requisites(m: Message, command: CommandObject, session: AsyncSession):
    await put(m, session, "requisites", command.args)


@r.message(Command("delivery"))
async def cmd_delivery(m: Message, command: CommandObject, session: AsyncSession):
    cat, _, val = (command.args or "").strip().partition(" ")
    if cat not in st.CATEGORIES:
        return await m.answer("Формат: /delivery shoes 1500 (shoes, clothes, accessories)")
    await put(m, session, f"delivery_{cat}", val)
