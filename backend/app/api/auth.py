"""Вход в админку: пароль меняется на подписанный токен с ограниченным сроком жизни."""
import hashlib
import hmac
import secrets
import time

from fastapi import Header, HTTPException

from ..config import settings


def _sign(payload: str) -> str:
    return hmac.new(settings.secret_key.encode(), payload.encode(), hashlib.sha256).hexdigest()


def check_password(password: str) -> bool:
    return secrets.compare_digest(password.encode(), settings.admin_password.encode())


def issue_token() -> str:
    exp = str(int(time.time()) + settings.session_hours * 3600)
    return f"{exp}.{_sign(exp)}"


def valid_token(token: str) -> bool:
    exp, _, sig = token.partition(".")
    return exp.isdigit() and secrets.compare_digest(sig, _sign(exp)) and int(exp) > time.time()


def require_admin(authorization: str = Header("")):
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not valid_token(token):
        raise HTTPException(401, "Нужно войти заново")
