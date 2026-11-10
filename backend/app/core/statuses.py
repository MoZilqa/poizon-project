"""Статусы заказа по схеме из ТЗ: 8 основных + 2 завершающих."""

CATEGORIES = {"shoes": "Обувь", "clothes": "Одежда", "accessories": "Аксессуары"}

NEW = "new"
AWAITING_PAYMENT = "awaiting_payment"
PAID = "paid"
PURCHASED = "purchased"
WAREHOUSE_CN = "warehouse_cn"
SHIPPED_RU = "shipped_ru"
AT_PICKUP = "at_pickup"
RECEIVED = "received"
CANCELLED = "cancelled"
REFUND = "refund"

STATUSES = {
    NEW: "Новый",
    AWAITING_PAYMENT: "Ожидает оплаты",
    PAID: "Оплачен",
    PURCHASED: "Выкуплен",
    WAREHOUSE_CN: "На складе в Китае",
    SHIPPED_RU: "Отправлен в РФ",
    AT_PICKUP: "В пункте выдачи",
    RECEIVED: "Получен",
    CANCELLED: "Отменён",
    REFUND: "Возврат денег",
}

FLOW = [NEW, AWAITING_PAYMENT, PAID, PURCHASED, WAREHOUSE_CN, SHIPPED_RU, AT_PICKUP, RECEIVED]
NEXT = dict(zip(FLOW, FLOW[1:]))
# отменить можно только до оплаты, после оплаты — только возврат
BRANCHES = {NEW: CANCELLED, AWAITING_PAYMENT: CANCELLED, PAID: REFUND}
FINAL = {RECEIVED, CANCELLED, REFUND}


def allowed(status: str) -> list[str]:
    """Куда администратор может перевести заказ: следующий статус и/или ветка отмены."""
    return [s for s in (NEXT.get(status), BRANCHES.get(status)) if s]
