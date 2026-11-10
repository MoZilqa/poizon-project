"""«Мои заказы», отмена до оплаты и отправка чека."""
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core import statuses as st
from ...core.service import TransitionError, attach_receipt, change_status, load_order
from ...models import Order, User
from .. import keyboards as kb
from ..notify import cards_to_admins, notify_admins
from ..texts import client_line

r = Router()


class Pay(StatesGroup):
    receipt = State()


@r.message(F.text == kb.BTN_MY)
async def my_orders(m: Message, state: FSMContext, session: AsyncSession, user: User):
    await state.clear()
    orders = (await session.scalars(
        select(Order).where(Order.user_id == user.id).order_by(Order.id.desc()).limit(10))).all()
    if not orders:
        return await m.answer("Заказов пока нет", reply_markup=kb.MENU)
    await m.answer(f"Последние заказы ({len(orders)}):", reply_markup=kb.MENU)
    for o in orders:
        await m.answer(client_line(o), reply_markup=kb.client_order_kb(o))


@r.callback_query(kb.CancelCb.filter())
async def cancel_order(c: CallbackQuery, callback_data: kb.CancelCb, session: AsyncSession, user: User):
    o = await load_order(session, callback_data.id)
    if not o or o.user_id != user.id:
        return await c.answer("Заказ не найден", show_alert=True)
    try:
        o = await change_status(session, o.id, st.CANCELLED, actor="client")
    except TransitionError as e:
        return await c.answer(str(e), show_alert=True)
    await c.message.edit_text(client_line(o))
    await c.answer("Заказ отменён")
    await notify_admins(f"Клиент отменил заказ №{o.id}")


@r.callback_query(kb.PaidCb.filter())
async def paid(c: CallbackQuery, callback_data: kb.PaidCb, state: FSMContext, session: AsyncSession, user: User):
    o = await load_order(session, callback_data.id)
    if not o or o.user_id != user.id or o.status != st.AWAITING_PAYMENT:
        return await c.answer("Этот заказ сейчас нельзя оплатить", show_alert=True)
    if o.receipt_id:
        return await c.answer("Чек уже на проверке", show_alert=True)
    await state.set_state(Pay.receipt)
    await state.update_data(oid=o.id)
    await c.message.answer(f"Пришлите чек по заказу №{o.id} (фото или файл)", reply_markup=kb.CANCEL)
    await c.answer()


@r.message(Pay.receipt, F.photo | F.document)
async def got_receipt(m: Message, state: FSMContext, session: AsyncSession, user: User):
    oid = (await state.get_data())["oid"]
    await state.clear()
    is_doc = m.photo is None
    file_id = m.document.file_id if is_doc else m.photo[-1].file_id
    try:
        await attach_receipt(session, oid, user, file_id)
    except TransitionError as e:
        return await m.answer(str(e), reply_markup=kb.MENU)
    await m.answer("Чек получен 👍 Администратор проверит оплату и бот сообщит результат.", reply_markup=kb.MENU)
    await cards_to_admins(await load_order(session, oid), file_id, is_doc)


@r.message(Pay.receipt, ~F.text.in_(kb.MENU_BUTTONS))
async def receipt_bad(m: Message):
    await m.answer("Пришлите фото или файл с чеком")
