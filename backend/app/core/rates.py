"""Автоматический курс юаня по данным ЦБ РФ."""
import asyncio
import json
import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal

import aiohttp

from ..db import Session
from .pricing import parse_decimal
from .service import get_cfg, set_cfg

log = logging.getLogger(__name__)

CBR_XML = "https://www.cbr.ru/scripts/XML_daily.asp"
CBR_JSON = "https://www.cbr-xml-daily.ru/daily_json.js"  # зеркало на случай недоступности cbr.ru
SYNC_EVERY = 3600  # ЦБ обновляет курс раз в день, раз в час проверяем


def parse_xml(raw: bytes) -> Decimal:
    for v in ET.fromstring(raw).iter("Valute"):
        if v.findtext("CharCode") == "CNY":
            return parse_decimal(v.findtext("Value")) / Decimal(v.findtext("Nominal"))
    raise ValueError("в ответе ЦБ нет юаня")


def parse_json(raw: bytes) -> Decimal:
    cny = json.loads(raw)["Valute"]["CNY"]
    return Decimal(str(cny["Value"])) / Decimal(cny["Nominal"])


async def fetch_cny() -> Decimal:
    errors = []
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as http:
        for url, parse in ((CBR_XML, parse_xml), (CBR_JSON, parse_json)):
            try:
                async with http.get(url) as r:
                    r.raise_for_status()
                    rate = parse(await r.read())
                if rate > 0:
                    return rate
            except Exception as e:  # noqa: BLE001 — пробуем следующий источник
                errors.append(f"{url}: {e}")
    raise RuntimeError("; ".join(errors))


def effective(cbr: Decimal, extra: str) -> Decimal:
    """Курс для расчёта = курс ЦБ × (1 + надбавка %)."""
    return (cbr * (1 + Decimal(extra) / 100)).quantize(Decimal("0.0001"), ROUND_HALF_UP)


async def apply_cached(s) -> None:
    """Пересчитать курс из последнего значения ЦБ (после смены надбавки), без запроса в сеть."""
    cfg = await get_cfg(s)
    if cfg["rate_auto"] == "1" and cfg["rate_cbr"]:
        await set_cfg(s, "rate", str(effective(Decimal(cfg["rate_cbr"]), cfg["rate_extra"])))


async def sync_rate(force: bool = False) -> dict:
    """Забрать курс с ЦБ. При ошибке старый курс остаётся, текст ошибки — в настройках."""
    async with Session() as s:
        cfg = await get_cfg(s)
        if cfg["rate_auto"] != "1" and not force:
            return cfg
        try:
            cbr = await fetch_cny()
        except Exception as e:
            log.warning("CNY rate sync failed: %s", e)
            await set_cfg(s, "rate_error", f"{datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC: {e}"[:500])
            raise
        await set_cfg(s, "rate_cbr", str(cbr.quantize(Decimal("0.0001"))), commit=False)
        await set_cfg(s, "rate_synced_at", datetime.now(timezone.utc).isoformat(timespec="seconds"), commit=False)
        await set_cfg(s, "rate_error", "", commit=False)
        await set_cfg(s, "rate", str(effective(cbr, cfg["rate_extra"])))
        log.info("CNY rate synced: CBR %s", cbr)
        return await get_cfg(s)


async def rate_loop():
    while True:
        try:
            await sync_rate()
        except Exception:  # noqa: BLE001 — ошибка уже записана, попробуем через час
            pass
        await asyncio.sleep(SYNC_EVERY)
