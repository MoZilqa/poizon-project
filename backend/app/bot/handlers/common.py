from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from ...config import settings
from .. import keyboards as kb
from ..texts import HELP, esc

r = Router()


@r.message(CommandStart())
async def start(m: Message, state: FSMContext):
    await state.clear()
    await m.answer("Привет! Помогу заказать одежду и обувь с Poizon. Выберите действие:", reply_markup=kb.MENU)


@r.message(F.text == kb.BTN_CANCEL)
@r.message(Command("cancel"))
async def cancel(m: Message, state: FSMContext):
    await state.clear()
    await m.answer("Отменено", reply_markup=kb.MENU)


@r.message(F.text == kb.BTN_HELP)
@r.message(Command("help"))
async def help_(m: Message, state: FSMContext):
    await state.clear()
    await m.answer(f"{HELP}\n\nАдминистратор: {esc(settings.admin_contact or 'не указан')}", reply_markup=kb.MENU)
