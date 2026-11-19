"""Cuentas y sesiones.

- Contraseñas: scrypt (biblioteca estándar) con sal aleatoria por usuario.
- Sesión: token aleatorio en cookie HttpOnly + SameSite=Strict; en la base solo se
  guarda su hash SHA-256 (si roban la base, no pueden usar las sesiones).
- CSRF: cada sesión tiene un token que el cliente debe mandar en la cabecera
  X-CSRF-Token en las peticiones que cambian cosas.
- Fuerza bruta: límite de intentos de login por IP y por usuario.
"""
import hashlib
import hmac
import os
import re
import secrets
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

from . import db

SESSION_DAYS = 7
USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,20}$")
SCRYPT = dict(n=2 ** 14, r=8, p=1, dklen=32)


def hash_password(password):
    salt = os.urandom(16)
    dk = hashlib.scrypt(password.encode(), salt=salt, **SCRYPT)
    return "scrypt$%s$%s" % (salt.hex(), dk.hex())


def verify_password(password, stored):
    try:
        _, salt_hex, dk_hex = stored.split("$")
        dk = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt_hex), **SCRYPT)
        return hmac.compare_digest(dk.hex(), dk_hex)
    except Exception:
        return False


# Hash ficticio para que el tiempo de respuesta no revele si un usuario existe
_DUMMY_HASH = hash_password(secrets.token_hex(8))


def validate_new_user(username, password):
    if not USERNAME_RE.match(username or ""):
        return "El usuario debe tener 3-20 caracteres: letras, números o _"
    if not password or len(password) < 8:
        return "La contraseña debe tener al menos 8 caracteres"
    if len(password) > 128:
        return "La contraseña es demasiado larga"
    return None


def create_user(username, password, is_test=False):
    if db.query_one("SELECT id FROM users WHERE LOWER(username) = LOWER(?)", (username,)):
        return None
    return db.insert(
        "INSERT INTO users (username, password_hash, is_test) VALUES (?, ?, ?)",
        (username, hash_password(password), is_test),
    )


def authenticate(username, password):
    row = db.query_one(
        "SELECT id, username, password_hash, is_test FROM users WHERE LOWER(username) = LOWER(?)",
        (username or "",),
    )
    if row is None:
        verify_password(password or "", _DUMMY_HASH)
        return None
    if verify_password(password or "", row["password_hash"]):
        return row
    return None


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def create_session(user_id):
    token = secrets.token_urlsafe(32)
    csrf = secrets.token_hex(32)
    expires = _now() + timedelta(days=SESSION_DAYS)
    db.execute(
        "INSERT INTO sessions (token_hash, user_id, csrf_token, expires_at) VALUES (?, ?, ?, ?)",
        (hashlib.sha256(token.encode()).hexdigest(), user_id, csrf, expires.isoformat(" ")),
    )
    return token, csrf


def get_session(token):
    if not token:
        return None
    row = db.query_one(
        "SELECT s.user_id, s.csrf_token, s.expires_at, u.username, u.is_test FROM sessions s "
        "JOIN users u ON u.id = s.user_id WHERE s.token_hash = ?",
        (hashlib.sha256(token.encode()).hexdigest(),),
    )
    if row is None:
        return None
    exp = row["expires_at"]
    if isinstance(exp, str):
        exp = datetime.fromisoformat(exp)
    if exp < _now():
        delete_session(token)
        return None
    return row


def delete_session(token):
    if token:
        db.execute("DELETE FROM sessions WHERE token_hash = ?",
                   (hashlib.sha256(token.encode()).hexdigest(),))


class RateLimiter:
    """Ventana deslizante en memoria: máx. `limit` intentos cada `window` segundos."""

    def __init__(self, limit, window):
        self.limit, self.window = limit, window
        self.hits = defaultdict(deque)

    def allow(self, key):
        now = time.time()
        q = self.hits[key]
        while q and q[0] < now - self.window:
            q.popleft()
        if len(q) >= self.limit:
            return False
        q.append(now)
        return True


login_limiter_ip = RateLimiter(10, 300)
login_limiter_user = RateLimiter(5, 300)
register_limiter_ip = RateLimiter(5, 3600)
