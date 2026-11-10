import html
from decimal import Decimal

from ..core.statuses import CATEGORIES, STATUSES
from ..models import Order

esc = html.escape

HELP = (
    "<b>Как заказать</b>\n"
    "1. «Рассчитать цену» — узнайте итог в рублях.\n"
    "2. «Оформить заказ» — ссылка на Poizon, скриншот, размер, категория, цена и данные получателя.\n"
    "3. Администратор проверит заказ и пришлёт реквизиты.\n"
    "4. Оплатите, нажмите «Я оплатил» и пришлите чек.\n"
    "5. Статус смотрите в «Мои заказы» — о каждом изменении бот напишет сам.\n\n"
    "Отменить заказ можно только до оплаты, после оплаты — только возврат."
)

ADMIN_HELP = (
    "<b>Команды администратора</b>\n"
    "/orders — заказы с фильтром по статусу\n"
    "/order 5 — карточка заказа №5\n"
    "/track 5 RU123456 — трек-номер заказа\n"
    "/settings — текущие курс, наценка, тарифы\n"
    "/rate auto 3 — курс ЦБ + надбавка 3% (обновляется сам)\n"
    "/rate 12.5 — курс вручную (автокурс выключится)\n"
    "/markup 15 — наценка, %\n"
    "/delivery shoes 1500 — доставка (shoes, clothes, accessories)\n"
    "/requisites текст — реквизиты для оплаты"
)


def rub(x: Decimal) -> str:
    return f"{x:,.2f}".replace(",", " ")


def calc_text(c: dict) -> str:
    return (f"Товар: {rub(c['goods'])} ₽\nНаценка: {rub(c['markup'])} ₽\n"
            f"Доставка: {rub(c['delivery'])} ₽\n<b>Итого: {rub(c['total'])} ₽</b>")


def client_line(o: Order) -> str:
    text = f"<b>Заказ №{o.id}</b> · {rub(o.total_rub)} ₽\n{STATUSES[o.status]}"
    if o.receipt_id and o.status == "awaiting_payment":
        text += " · чек на проверке"
    if o.track_number:
        text += f"\nТрек-номер: <code>{esc(o.track_number)}</code>"
    return text


def admin_card(o: Order) -> str:
    u = o.user
    who = f"@{esc(u.username)}" if u.username else esc(u.first_name or "без имени")
    url = o.url if len(o.url) <= 300 else o.url[:300] + "…"
    text = (f"<b>Заказ №{o.id}</b> — {STATUSES[o.status]}\n"
            f"Клиент: {who} (<code>{u.tg_id}</code>)\n"
            f"{esc(url)}\n"
            f"{CATEGORIES[o.category]}, размер {esc(o.size)}: {o.price_cny} ¥ → <b>{rub(o.total_rub)} ₽</b>\n"
            f"Получатель: {esc(o.recipient)}")
    if o.track_number:
        text += f"\nТрек-номер: <code>{esc(o.track_number)}</code>"
    if o.receipt_id and o.status == "awaiting_payment":
        text += "\n🧾 Чек прислан, ждёт проверки"
    return text
