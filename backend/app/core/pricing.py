from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

DEFAULTS = {
    "rate": "12.5",  # курс юаня, ₽ — по нему считается цена
    "rate_auto": "1",  # 1 — курс берётся с ЦБ РФ автоматически
    "rate_extra": "0",  # надбавка к курсу ЦБ, %
    "markup": "15",  # наценка, %
    "delivery_shoes": "1500",
    "delivery_clothes": "1000",
    "delivery_accessories": "500",
    "requisites": "Реквизиты ещё не заданы. Администратор задаёт их командой /requisites",
}
NUMERIC = {"rate", "rate_extra", "markup", "delivery_shoes", "delivery_clothes", "delivery_accessories"}
# служебные значения синхронизации курса: пишет только сервер
SYSTEM = {"rate_cbr", "rate_synced_at", "rate_error"}
MAX_PRICE = Decimal(1_000_000)


def money(x: Decimal) -> Decimal:
    return x.quantize(Decimal("0.01"), ROUND_HALF_UP)


def parse_decimal(text: str | None) -> Decimal | None:
    try:
        v = Decimal((text or "").replace(",", ".").replace(" ", "").strip())
    except InvalidOperation:
        return None
    return v if v.is_finite() else None


def parse_price(text: str | None) -> Decimal | None:
    v = parse_decimal(text)
    return v if v is not None and 0 < v < MAX_PRICE else None


def validate_setting(key: str, value: str) -> str:
    """Нормализует значение настройки. Бросает ValueError с понятным текстом."""
    if key not in DEFAULTS:
        raise ValueError(f"Неизвестная настройка: {key}")
    value = (value or "").strip()
    if key == "rate_auto":
        if value not in ("0", "1"):
            raise ValueError("rate_auto: 0 или 1")
        return value
    if key not in NUMERIC:
        if not value:
            raise ValueError("Значение не может быть пустым")
        return value
    v = parse_decimal(value)
    if v is None:
        raise ValueError(f"{key}: нужно число")
    if key == "rate" and v <= 0:
        raise ValueError("Курс должен быть больше нуля")
    if v < 0:
        raise ValueError(f"{key}: значение не может быть отрицательным")
    return str(v)


def calc(price_cny: Decimal, category: str, cfg: dict) -> dict:
    """Итог (₽) = цена (¥) × курс × (1 + наценка) + доставка по категории."""
    goods = money(price_cny * Decimal(cfg["rate"]))
    markup = money(goods * Decimal(cfg["markup"]) / 100)
    delivery = money(Decimal(cfg[f"delivery_{category}"]))
    return {"goods": goods, "markup": markup, "delivery": delivery, "total": goods + markup + delivery}
