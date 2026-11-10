from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton as IB
from aiogram.types import InlineKeyboardMarkup as IM
from aiogram.types import KeyboardButton as KB
from aiogram.types import ReplyKeyboardMarkup as RM

from ..core import statuses as st
from ..models import Order

BTN_CALC, BTN_ORDER, BTN_MY, BTN_HELP = "Рассчитать цену", "Оформить заказ", "Мои заказы", "Помощь"
BTN_CANCEL, BTN_CONFIRM = "Отмена", "Подтвердить"
MENU_BUTTONS = {BTN_CALC, BTN_ORDER, BTN_MY, BTN_HELP, BTN_CANCEL}


class StatusCb(CallbackData, prefix="st"):
    id: int
    to: str


class ReceiptRejectCb(CallbackData, prefix="rr"):
    id: int


class PaidCb(CallbackData, prefix="paid"):
    id: int


class CancelCb(CallbackData, prefix="cancel"):
    id: int


class FilterCb(CallbackData, prefix="flt"):
    status: str  # "all" — без фильтра


def reply(*rows) -> RM:
    return RM(keyboard=[[KB(text=t) for t in row] for row in rows], resize_keyboard=True)


MENU = reply([BTN_CALC, BTN_ORDER], [BTN_MY, BTN_HELP])
CANCEL = reply([BTN_CANCEL])
CATEGORIES = reply(list(st.CATEGORIES.values()), [BTN_CANCEL])
CONFIRM = reply([BTN_CONFIRM], [BTN_CANCEL])


def paid_kb(oid: int) -> IM:
    return IM(inline_keyboard=[[IB(text="Я оплатил", callback_data=PaidCb(id=oid).pack())]])


def client_order_kb(o: Order) -> IM | None:
    row = []
    if o.status == st.AWAITING_PAYMENT and not o.receipt_id:
        row.append(IB(text="Я оплатил", callback_data=PaidCb(id=o.id).pack()))
    if o.status in (st.NEW, st.AWAITING_PAYMENT) and not o.receipt_id:
        row.append(IB(text="Отменить заказ", callback_data=CancelCb(id=o.id).pack()))
    return IM(inline_keyboard=[row]) if row else None


def admin_order_kb(o: Order) -> IM | None:
    rows = []
    for to in st.allowed(o.status):
        if to == st.PAID and o.receipt_id:
            text = "✅ Подтвердить оплату"
        elif to in st.BRANCHES.values():
            text = f"✖ {st.STATUSES[to]}"
        else:
            text = f"→ {st.STATUSES[to]}"
        rows.append([IB(text=text, callback_data=StatusCb(id=o.id, to=to).pack())])
    if o.status == st.AWAITING_PAYMENT and o.receipt_id:
        rows.append([IB(text="❌ Отклонить чек", callback_data=ReceiptRejectCb(id=o.id).pack())])
    return IM(inline_keyboard=rows) if rows else None


def filter_kb(counts: dict[str, int]) -> IM:
    buttons = [IB(text=f"{st.STATUSES[k]} ({n})", callback_data=FilterCb(status=k).pack())
               for k, n in counts.items() if n]
    rows = [buttons[i:i + 2] for i in range(0, len(buttons), 2)]
    rows.append([IB(text=f"Все ({sum(counts.values())})", callback_data=FilterCb(status="all").pack())])
    return IM(inline_keyboard=rows)
