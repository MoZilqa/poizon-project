from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Category = Literal["shoes", "clothes", "accessories"]


class CalcIn(BaseModel):
    category: Category
    price_cny: Decimal = Field(gt=0, lt=1_000_000)


class CalcOut(BaseModel):
    goods: Decimal
    markup: Decimal
    delivery: Decimal
    total: Decimal


class LoginIn(BaseModel):
    password: str


class HistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    status: str
    actor: str
    created_at: datetime


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    tg_id: int
    username: str | None
    first_name: str | None


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user: UserOut
    url: str
    size: str
    category: str
    price_cny: Decimal
    total_rub: Decimal
    status: str
    recipient: str
    track_number: str | None
    has_receipt: bool
    allowed: list[str]
    created_at: datetime
    updated_at: datetime


class OrderDetail(OrderOut):
    history: list[HistoryOut]


class OrderPage(BaseModel):
    items: list[OrderOut]
    total: int


class StatusIn(BaseModel):
    status: str
    track_number: str | None = Field(None, max_length=64)


class TrackIn(BaseModel):
    track_number: str | None = Field(None, max_length=64)
