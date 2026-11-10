import pytest

from app.core import statuses as st
from app.core.service import TransitionError, attach_receipt, change_status, get_user


def test_schema_from_spec():
    assert len(st.FLOW) == 8 and {st.CANCELLED, st.REFUND} == set(st.STATUSES) - set(st.FLOW)
    assert st.allowed(st.NEW) == [st.AWAITING_PAYMENT, st.CANCELLED]
    assert st.allowed(st.PAID) == [st.PURCHASED, st.REFUND]
    assert st.allowed(st.PURCHASED) == [st.WAREHOUSE_CN]  # после выкупа — без отмены
    assert st.allowed(st.RECEIVED) == []


async def test_full_flow(session, order):
    for to in st.FLOW[1:]:
        track = "RU1" if to == st.SHIPPED_RU else None
        o = await change_status(session, order.id, to, "admin_site", track_number=track)
    assert o.status == st.RECEIVED and [h.status for h in o.history] == st.FLOW


async def test_no_skipping(session, order):
    with pytest.raises(TransitionError):
        await change_status(session, order.id, st.PAID, "admin_bot")


async def test_shipping_needs_track(session, order):
    for to in (st.AWAITING_PAYMENT, st.PAID, st.PURCHASED, st.WAREHOUSE_CN):
        await change_status(session, order.id, to, "admin_bot")
    with pytest.raises(TransitionError, match="трек"):
        await change_status(session, order.id, st.SHIPPED_RU, "admin_bot")


async def test_client_cancel_only_before_payment(session, order):
    await change_status(session, order.id, st.AWAITING_PAYMENT, "admin_bot")
    await change_status(session, order.id, st.PAID, "admin_bot")
    with pytest.raises(TransitionError, match="до оплаты"):
        await change_status(session, order.id, st.CANCELLED, "client")
    assert (await change_status(session, order.id, st.REFUND, "admin_bot")).status == st.REFUND


async def test_client_cannot_cancel_after_receipt(session, order):
    await change_status(session, order.id, st.AWAITING_PAYMENT, "admin_bot")
    user = await get_user(session, 42)
    await attach_receipt(session, order.id, user, "receipt-1")
    with pytest.raises(TransitionError, match="Чек"):
        await change_status(session, order.id, st.CANCELLED, "client")


async def test_receipt_only_own_and_awaiting(session, order):
    stranger = await get_user(session, 7)
    with pytest.raises(TransitionError):
        await attach_receipt(session, order.id, stranger, "x")
    owner = await get_user(session, 42)
    with pytest.raises(TransitionError, match="нельзя оплатить"):
        await attach_receipt(session, order.id, owner, "x")  # ещё «Новый»
