from __future__ import annotations

import base64
import hashlib
import hmac
import os
import time
from dataclasses import dataclass
from typing import Iterable

from fastapi import Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from .database import get_db
from .models import User
from .settings import get_settings

ROLE_LEVEL = {
    "viewer": 10,
    "editor": 20,
    "manager": 30,
    "admin": 40,
}

ROLE_LABELS = {
    "viewer": "Просмотр",
    "editor": "Редактор",
    "manager": "Менеджер",
    "admin": "Администратор",
}

SESSION_COOKIE = "license_monitor_session"
SESSION_TTL_SECONDS = 60 * 60 * 12


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)
    return "pbkdf2_sha256$200000$" + base64.urlsafe_b64encode(salt).decode() + "$" + base64.urlsafe_b64encode(digest).decode()


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, iterations, salt_b64, digest_b64 = stored_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        salt = base64.urlsafe_b64decode(salt_b64.encode())
        expected = base64.urlsafe_b64decode(digest_b64.encode())
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(iterations))
        return hmac.compare_digest(actual, expected)
    except Exception:
        return False


def _sign(payload: str) -> str:
    secret = get_settings().session_secret.encode("utf-8")
    return hmac.new(secret, payload.encode("utf-8"), hashlib.sha256).hexdigest()


def create_session_token(user_id: int) -> str:
    payload = f"{user_id}:{int(time.time())}"
    token = f"{payload}:{_sign(payload)}"
    return base64.urlsafe_b64encode(token.encode("utf-8")).decode("utf-8")


def read_session_token(token: str | None) -> int | None:
    if not token:
        return None
    try:
        decoded = base64.urlsafe_b64decode(token.encode("utf-8")).decode("utf-8")
        user_id_str, created_str, signature = decoded.split(":", 2)
        payload = f"{user_id_str}:{created_str}"
        if not hmac.compare_digest(signature, _sign(payload)):
            return None
        if int(time.time()) - int(created_str) > SESSION_TTL_SECONDS:
            return None
        return int(user_id_str)
    except Exception:
        return None


def create_initial_admin_if_needed(db: Session) -> None:
    settings = get_settings()
    if not settings.auth_enabled:
        return
    if db.query(User).count() > 0:
        return
    admin = User(
        username=settings.initial_admin_username,
        password_hash=hash_password(settings.initial_admin_password),
        full_name="Initial Admin",
        email=settings.initial_admin_email,
        role="admin",
        is_active=True,
    )
    db.add(admin)
    db.commit()


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    settings = get_settings()
    if not settings.auth_enabled:
        return None
    user_id = read_session_token(request.cookies.get(SESSION_COOKIE))
    if user_id is None:
        return None
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        return None
    return user


def require_login(request: Request, db: Session = Depends(get_db)) -> User:
    settings = get_settings()
    if not settings.auth_enabled:
        return User(id=0, username="system", password_hash="", role="admin", is_active=True)  # type: ignore[arg-type]
    user = get_current_user(request, db)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return user


def require_role(*allowed_roles: str):
    def checker(user: User = Depends(require_login)) -> User:
        if user.role not in ROLE_LEVEL:
            raise HTTPException(status_code=403, detail="Invalid role")
        required_level = min(ROLE_LEVEL[role] for role in allowed_roles)
        if ROLE_LEVEL[user.role] < required_level:
            raise HTTPException(status_code=403, detail="Forbidden")
        return user
    return checker


def user_can(user: User | None, role: str) -> bool:
    if get_settings().auth_enabled is False:
        return True
    if user is None:
        return False
    return ROLE_LEVEL.get(user.role, 0) >= ROLE_LEVEL.get(role, 999)


def require_api_key(request: Request) -> None:
    key = get_settings().zabbix_api_key
    if not key:
        return
    provided = request.headers.get("X-API-Key") or request.query_params.get("api_key")
    if not provided or not hmac.compare_digest(provided, key):
        raise HTTPException(status_code=401, detail="Invalid API key")
