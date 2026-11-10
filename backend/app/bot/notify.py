"""Исходящие сообщения: клиенту о смене статуса, администраторам о заказах и чеках.

Вызывается и из бота, и из API сайта.
"""
import logging

from aiogram.exceptions import TelegramAPIError
from aiogram.types import InlineKeyboardMarkup

from ..config import settings
from ..core import statuses as st
from ..core.service import get_cfg, load_order
from ..db import Session
from ..models import Order
from . import keyboards as kb
from .instance import bot
from .texts import admin_card, esc, rub

log = logging.getLogger(__name__)


async def send(chat_id: int, text: str, markup: InlineKeyboardMarkup | None = None):
    if not bot:
        return
    try:
        await bot.send_message(chat_id, text, reply_markup=markup)
    except TelegramAPIError as e:  # клиент мог заблокировать бота
        log.warning("send to %s failed: %s", chat_id, e)


async def notify_client(oid: int):
    """Сообщение клиенту о текущем статусе заказа."""
    async with Session() as s:
        o = await load_order(s, oid)
        requisites = (await get_cfg(s))["requisites"]
    text = f"Заказ №{o.id}: <b>{st.STATUSES[o.status]}</b>"
    markup = None
    if o.status == st.AWAITING_PAYMENT:
        text = (f"Заказ №{o.id} подтверждён. К оплате: <b>{rub(o.total_rub)} ₽</b>\n\n"
                f"Реквизиты:\n{esc(requisites)}\n\nПосле оплаты нажмите «Я оплатил» и пришлите чек.")
        markup = kb.paid_kb(o.id)
    elif o.status == st.SHIPPED_RU:
        text += f"\nТрек-номер: <code>{esc(o.track_number or '—')}</code>"
    elif o.status == st.REFUND:
        text += "\nТовара нет в наличии или цена выросла. Администратор свяжется с вами для возврата денег."
    elif o.status == st.CANCELLED:
        text = f"Заказ №{o.id} отменён"
    await send(o.user.tg_id, text, markup)


async def notify_receipt_rejected(oid: int):
    async with Session() as s:
        o = await load_order(s, oid)
    await send(o.user.tg_id, f"Чек по заказу №{o.id} не принят. Проверьте оплату и пришлите чек ещё раз.",
               kb.paid_kb(o.id))


async def notify_admins(text: str):
    for admin in settings.admin_ids:
        await send(admin, text)


async def send_admin_card(chat_id: int, o: Order, file_id: str | None = None, is_doc: bool = False):
    """Карточка заказа с кнопками; file_id — скриншот товара или чек."""
    if not bot:
        return
    try:
        if file_id and is_doc:
            await bot.send_document(chat_id, file_id, caption=admin_card(o), reply_markup=kb.admin_order_kb(o))
        elif file_id:
            await bot.send_photo(chat_id, file_id, caption=admin_card(o), reply_markup=kb.admin_order_kb(o))
        else:
            await bot.send_message(chat_id, admin_card(o), reply_markup=kb.admin_order_kb(o))
    except TelegramAPIError as e:
        log.warning("admin card to %s failed: %s", chat_id, e)


async def cards_to_admins(o: Order, file_id: str | None = None, is_doc: bool = False):
    for admin in settings.admin_ids:
        await send_admin_card(admin, o, file_id, is_doc)
