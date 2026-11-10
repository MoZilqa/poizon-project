from decimal import Decimal

import pytest

from app.core.pricing import DEFAULTS, calc, parse_price, validate_setting


def test_formula():
    # 500 ¥ × 12.5 = 6250; наценка 15% = 937.50; доставка обуви 1500
    c = calc(Decimal("500"), "shoes", DEFAULTS)
    assert c == {"goods": Decimal("6250.00"), "markup": Decimal("937.50"),
                 "delivery": Decimal("1500.00"), "total": Decimal("8687.50")}


def test_rounding_is_decimal():
    c = calc(Decimal("0.01"), "accessories", {**DEFAULTS, "rate": "12.345", "markup": "10"})
    assert c["goods"] == Decimal("0.12") and c["markup"] == Decimal("0.01")


@pytest.mark.parametrize("raw,ok", [("799", Decimal(799)), ("1 299,5", Decimal("1299.5")),
                                    ("0", None), ("-5", None), ("abc", None), ("nan", None), ("1e9", None)])
def test_parse_price(raw, ok):
    assert parse_price(raw) == ok


def test_validate_setting():
    assert validate_setting("rate", " 13,1 ") == "13.1"
    for key, bad in [("rate", "0"), ("markup", "-1"), ("delivery_shoes", "x"), ("requisites", " "), ("nope", "1")]:
        with pytest.raises(ValueError):
            validate_setting(key, bad)


def test_cbr_parsers():
    from app.core.rates import effective, parse_json, parse_xml
    xml = ('<?xml version="1.0" encoding="windows-1251"?><ValCurs><Valute ID="R01375"><CharCode>CNY</CharCode>'
           '<Nominal>10</Nominal><Value>120,6800</Value></Valute></ValCurs>').encode("cp1251")
    assert parse_xml(xml) == Decimal("12.068")
    assert parse_json(b'{"Valute": {"CNY": {"Nominal": 1, "Value": 12.068}}}') == Decimal("12.068")
    assert effective(Decimal("12.068"), "3") == Decimal("12.4300")
