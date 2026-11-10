from aiogram import Router

from . import admin, calc, common, my_orders, order


def build() -> Router:
    root = Router()
    # admin первым: его хендлеры отфильтрованы по ID, остальным апдейты проходят дальше;
    # common до FSM-роутеров, чтобы «Отмена» и /start работали на любом шаге
    root.include_routers(admin.r, common.r, calc.r, my_orders.r, order.r)
    return root
