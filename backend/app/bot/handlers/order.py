"""Оформление заказа (FSM): ссылка → скриншот → размер → категория → цена → ФИО → телефон → ПВЗ → подтверждение."""
import re
from decimal import Decimal

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.pricing import calc, parse_price
from ...core.service import create_order, get_cfg
from ...core.statuses import CATEGORIES
from ...models import User
from .. import keyboards as kb
from ..notify import cards_to_admins
from ..texts import calc_text, esc
from .calc import RCAT

r = Router()
URL_RE = re.compile(r"https?://\S+")


class Form(StatesGroup):
    url = State()
    shot = State()
    size = State()
    cat = State()
    price = State()
    fio = State()
    phone = State()
    pvz = State()
    confirm = State()


# Парсеры шагов: возвращают значение или None, если ввод не подходит
def p_url(m: Message):
    # из приложения Poizon ссылка приходит вместе с текстом — достаём только URL
    found = URL_RE.search(m.text or m.caption or "")
    return found.group(0) if found else None


def p_shot(m: Message):
    if m.photo:
        return m.photo[-1].file_id
    if m.document and (m.document.mime_type or "").startswith("image/"):
        return m.document.file_id
    return None


def p_text(max_len: int):
    return lambda m: (m.text or "").strip()[:max_len] or None


def p_fio(m: Message):
    t = " ".join((m.text or "").split())
    return t[:128] if len(t.split()) >= 2 else None


def p_phone(m: Message):
    digits = re.sub(r"\D", "", m.text or "")
    if len(digits) == 11 and digits[0] in "78":
        return "+7" + digits[1:]
    return "+" + digits if 10 <= len(digits) <= 15 else None


def p_price(m: Message):
    v = parse_price(m.text)
    return str(v) if v else None


# state: (ключ в данных, вопрос, клавиатура, парсер, подсказка при ошибке)
STEPS = {
    Form.url: ("url", "Пришлите ссылку на товар на Poizon", kb.CANCEL, p_url,
               "Не вижу ссылки. Скопируйте её в приложении Poizon через «Поделиться»"),
    Form.shot: ("shot", "Пришлите скриншот товара (фото)", kb.CANCEL, p_shot, "Нужна картинка"),
    Form.size: ("size", "Укажите размер (например, 42 или M). Если размера нет — напишите «нет»",
                kb.CANCEL, p_text(64), "Укажите размер текстом"),
    Form.cat: ("cat", "Выберите категорию", kb.CATEGORIES, lambda m: RCAT.get(m.text), "Выберите категорию кнопкой"),
    Form.price: ("price", "Цена товара в юанях (¥) — как в приложении", kb.CANCEL, p_price,
                 "Введите число больше нуля, например 799"),
    Form.fio: ("fio", "ФИО получателя", kb.CANCEL, p_fio, "Укажите хотя бы фамилию и имя"),
    Form.phone: ("phone", "Телефон получателя", kb.CANCEL, p_phone, "Похоже, номер с ошибкой. Пример: +7 900 123-45-67"),
    Form.pvz: ("pvz", "Адрес пункта выдачи (СДЭК / Boxberry и т. п.)", kb.CANCEL, p_text(300), "Укажите адрес"),
}
ORDER = list(STEPS)


async def ask(m: Message, state: FSMContext, step: State):
    await state.set_state(step)
    _, question, markup, *_ = STEPS[step]
    await m.answer(question, reply_markup=markup)


@r.message(F.text == kb.BTN_ORDER)
async def order_start(m: Message, state: FSMContext):
    await state.clear()
    await ask(m, state, Form.url)


@r.message(Form.confirm, F.text == kb.BTN_CONFIRM)
async def order_confirm(m: Message, state: FSMContext, session: AsyncSession, user: User):
    d = await state.get_data()
    await state.clear()
    o = await create_order(session, user, d)
    await m.answer(f"Заказ №{o.id} оформлен ✅\nАдминистратор проверит наличие и цену и пришлёт реквизиты для оплаты.",
                   reply_markup=kb.MENU)
    await cards_to_admins(o, o.screenshot_id)


@r.message(Form.confirm, ~F.text.in_(kb.MENU_BUTTONS))
async def order_confirm_bad(m: Message):
    await m.answer("Нажмите «Подтвердить» или «Отмена»")


@r.message(StateFilter(*ORDER), ~F.text.in_(kb.MENU_BUTTONS))
async def order_step(m: Message, state: FSMContext, session: AsyncSession, raw_state: str):
    step = next(s for s in ORDER if s.state == raw_state)
    key, _, _, parse, hint = STEPS[step]
    val = parse(m)
    if val is None:
        return await m.answer(hint)
    await state.update_data({key: val})
    i = ORDER.index(step)
    if i + 1 < len(ORDER):
        return await ask(m, state, ORDER[i + 1])

    d = await state.get_data()
    c = calc(Decimal(d["price"]), d["cat"], await get_cfg(session))
    await state.update_data(total=str(c["total"]))  # цена фиксируется на момент оформления
    await state.set_state(Form.confirm)
    await m.answer_photo(
        d["shot"],
        caption=(f"<b>Проверьте заказ</b>\n{esc(d['url'][:200])}\n"
                 f"{CATEGORIES[d['cat']]}, размер {esc(d['size'])}, {d['price']} ¥\n"
                 f"Получатель: {esc(d['fio'])}, {esc(d['phone'])}\nПВЗ: {esc(d['pvz'])}\n\n{calc_text(c)}"),
        reply_markup=kb.CONFIRM)
