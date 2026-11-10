from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.pricing import calc, parse_price
from ...core.service import get_cfg
from ...core.statuses import CATEGORIES
from .. import keyboards as kb
from ..texts import calc_text

r = Router()
RCAT = {v: k for k, v in CATEGORIES.items()}


class Calc(StatesGroup):
    category = State()
    price = State()


@r.message(F.text == kb.BTN_CALC)
async def calc_start(m: Message, state: FSMContext):
    await state.clear()
    await state.set_state(Calc.category)
    await m.answer("Выберите категорию:", reply_markup=kb.CATEGORIES)


@r.message(Calc.category, F.text.in_(RCAT))
async def calc_category(m: Message, state: FSMContext):
    await state.update_data(cat=RCAT[m.text])
    await state.set_state(Calc.price)
    await m.answer("Цена товара в юанях (¥):", reply_markup=kb.CANCEL)


@r.message(Calc.category, ~F.text.in_(kb.MENU_BUTTONS))
async def calc_category_bad(m: Message):
    await m.answer("Выберите категорию кнопкой")


@r.message(Calc.price, ~F.text.in_(kb.MENU_BUTTONS))
async def calc_price(m: Message, state: FSMContext, session: AsyncSession):
    price = parse_price(m.text)
    if not price:
        return await m.answer("Введите число больше нуля, например 799")
    cat = (await state.get_data())["cat"]
    await state.clear()
    c = calc(price, cat, await get_cfg(session))
    await m.answer(f"{CATEGORIES[cat]}, {price} ¥\n\n{calc_text(c)}", reply_markup=kb.MENU)
