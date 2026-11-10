"""Публичная часть API — только вход: покупатели работают через бота, сайт — админка."""
from fastapi import APIRouter, HTTPException

from .auth import check_password, issue_token
from .schemas import LoginIn

router = APIRouter(prefix="/api")


@router.post("/auth/login")
async def login(p: LoginIn):
    if not check_password(p.password):
        raise HTTPException(401, "Неверный пароль")
    return {"token": issue_token()}
