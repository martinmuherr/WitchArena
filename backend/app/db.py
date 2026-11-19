"""Acceso a base de datos.

- Producción: PostgreSQL (DATABASE_URL=postgresql://usuario:clave@host/base), con psycopg 3.
- Desarrollo local: SQLite (por defecto, archivo backend/witcharena.db).

Todas las consultas usan parámetros (nunca concatenación de texto) para evitar inyección SQL.
Se escriben con marcadores '?' y se traducen a '%s' para PostgreSQL.
"""
import os
import sqlite3
import threading

DATABASE_URL = os.environ.get("DATABASE_URL", "")
IS_PG = DATABASE_URL.startswith("postgres")
_SQLITE_PATH = os.environ.get(
    "SQLITE_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "witcharena.db"),
)

SCHEMA = [
    """CREATE TABLE IF NOT EXISTS users (
        id {serial} PRIMARY KEY,
        username VARCHAR(20) NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        created_at {ts} NOT NULL DEFAULT CURRENT_TIMESTAMP,
        is_test BOOLEAN NOT NULL DEFAULT FALSE
    )""",
    """CREATE TABLE IF NOT EXISTS sessions (
        token_hash CHAR(64) PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        csrf_token CHAR(64) NOT NULL,
        created_at {ts} NOT NULL DEFAULT CURRENT_TIMESTAMP,
        expires_at {ts} NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS arena_runs (
        id {serial} PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        state TEXT NOT NULL,
        wins INTEGER NOT NULL DEFAULT 0,
        losses INTEGER NOT NULL DEFAULT 0,
        status VARCHAR(10) NOT NULL DEFAULT 'drafting',
        created_at {ts} NOT NULL DEFAULT CURRENT_TIMESTAMP,
        finished_at {ts}
    )""",
    """CREATE TABLE IF NOT EXISTS matches (
        id {serial} PRIMARY KEY,
        run1_id INTEGER NOT NULL REFERENCES arena_runs(id),
        run2_id INTEGER NOT NULL REFERENCES arena_runs(id),
        user1_id INTEGER NOT NULL REFERENCES users(id),
        user2_id INTEGER NOT NULL REFERENCES users(id),
        winner_user_id INTEGER REFERENCES users(id),
        reason VARCHAR(20),
        started_at {ts} NOT NULL DEFAULT CURRENT_TIMESTAMP,
        finished_at {ts}
    )""",
    "CREATE INDEX IF NOT EXISTS idx_runs_user ON arena_runs(user_id, status)",
    "CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id)",
]

_local = threading.local()


def _connect():
    if IS_PG:
        import psycopg  # instalado solo en el servidor

        return psycopg.connect(DATABASE_URL, autocommit=True)
    conn = sqlite3.connect(_SQLITE_PATH, check_same_thread=False, isolation_level=None)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def conn():
    c = getattr(_local, "conn", None)
    if c is None:
        c = _local.conn = _connect()
    return c


def _sql(q):
    return q.replace("?", "%s") if IS_PG else q


def execute(q, params=()):
    cur = conn().cursor()
    cur.execute(_sql(q), params)
    return cur


def query(q, params=()):
    cur = execute(q, params)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def query_one(q, params=()):
    rows = query(q, params)
    return rows[0] if rows else None


def insert(q, params=()):
    """INSERT que devuelve el id nuevo."""
    if IS_PG:
        cur = execute(q + " RETURNING id", params)
        return cur.fetchone()[0]
    cur = execute(q, params)
    return cur.lastrowid


def init_schema():
    serial = "SERIAL" if IS_PG else "INTEGER"
    ts = "TIMESTAMP" if IS_PG else "TEXT"
    for stmt in SCHEMA:
        execute(stmt.format(serial=serial, ts=ts))
