"""Servidor web de HS_WitchArena (Starlette + uvicorn).

Arrancar en local:  python -m uvicorn app.main:app --port 8000
IMPORTANTE: usar un solo proceso (sin --workers), porque las partidas y la cola
de emparejamiento viven en memoria.
"""
import asyncio
import json
import os
import random
import time
from contextlib import asynccontextmanager

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import FileResponse, JSONResponse, Response, StreamingResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from . import arena_rules as R
from . import auth, db, draft, rooms
from .game_session import ActionError, GameSession

COOKIE = "wa_session"
# PUBLIC_MODE=1: la web está publicada en internet (túnel de Cloudflare o proxy).
#   - cookies solo por HTTPS
#   - la IP real del visitante se lee de la cabecera que añade Cloudflare
#   - las cuentas de prueba no pueden entrar
PUBLIC_MODE = os.environ.get("PUBLIC_MODE", "0") == "1"
COOKIE_SECURE = PUBLIC_MODE or os.environ.get("COOKIE_SECURE", "0") == "1"
FRONTEND_DIST = os.environ.get(
    "FRONTEND_DIST",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "frontend", "dist"),
)
MAX_BODY = 4096
_rng = random.SystemRandom()

# ---------------------------------------------------------------- estado en memoria
games = {}            # game_id -> GameSession
game_runs = {}        # game_id -> (run1_id, run2_id)
user_game = {}        # user_id -> game_id
queue = []            # [(user_id, run_id, desde, sala)]
presence = {r: {} for r in rooms.ROOMS}  # sala -> {user_id: última vez visto}
PRESENCE_SECONDS = 75
game_events = {}      # game_id -> asyncio.Event (se reemplaza en cada cambio)
lock = asyncio.Lock()


def err(msg, status=400):
    return JSONResponse({"error": msg}, status_code=status)


def notify(game_id):
    ev = game_events.get(game_id)
    if ev:
        ev.set()
    game_events[game_id] = asyncio.Event()


async def body_json(request):
    raw = await request.body()
    if len(raw) > MAX_BODY:
        raise ActionError("Petición demasiado grande")
    if not raw:
        return {}
    if "application/json" not in request.headers.get("content-type", ""):
        raise ActionError("Se esperaba JSON")
    try:
        data = json.loads(raw)
    except ValueError:
        raise ActionError("JSON no válido")
    if not isinstance(data, dict):
        raise ActionError("JSON no válido")
    return data


def current_user(request, require_csrf=False):
    s = auth.get_session(request.cookies.get(COOKIE))
    if s is None or (PUBLIC_MODE and s.get("is_test")):
        return None
    if require_csrf and request.headers.get("x-csrf-token") != s["csrf_token"]:
        return None
    return s


def room_of(request):
    """Sala elegida por el cliente (cabecera X-Room o parámetro ?room=)."""
    return rooms.normalize(request.headers.get("x-room") or request.query_params.get("room"))


def seen(user_id, room):
    now = time.time()
    for r, users in presence.items():
        if r == room:
            users[user_id] = now
        else:
            users.pop(user_id, None)


def online_counts():
    now = time.time()
    out = {}
    for r, users in presence.items():
        for uid, t in list(users.items()):
            if now - t > PRESENCE_SECONDS:
                users.pop(uid, None)
        out[r] = len(users)
    return out


def api(require_login=True, csrf=None):
    """Decorador: gestiona sesión, CSRF y errores."""
    def deco(fn):
        async def handler(request):
            need_csrf = csrf if csrf is not None else request.method not in ("GET", "HEAD")
            user = None
            if require_login:
                user = current_user(request, require_csrf=need_csrf)
                if user is None:
                    return err("No has iniciado sesión o la sesión no es válida", 401)
                if request.headers.get("x-room") in rooms.ROOMS:
                    seen(user["user_id"], request.headers["x-room"])
            try:
                return await fn(request, user)
            except ActionError as e:
                return err(str(e))
            except ValueError as e:
                return err(str(e))
        return handler
    return deco


def client_ip(request):
    peer = request.client.host if request.client else "?"
    # Solo nos fiamos de las cabeceras de proxy si la conexión viene del propio equipo
    # (cloudflared o Nginx corriendo en local). Desde fuera no se puede falsificar.
    if peer in ("127.0.0.1", "::1"):
        if PUBLIC_MODE and request.headers.get("cf-connecting-ip"):
            return request.headers["cf-connecting-ip"].strip()[:64]
        if os.environ.get("BEHIND_PROXY") == "1" and request.headers.get("x-real-ip"):
            return request.headers["x-real-ip"].strip()[:64]
    return peer


# ------------------------------------------------------------------------ cuentas
@api(require_login=False)
async def register(request, _):
    ip = client_ip(request)
    data = await body_json(request)
    username, password = str(data.get("username", "")), str(data.get("password", ""))
    problem = auth.validate_new_user(username, password)
    if problem:
        return err(problem)
    if not auth.register_limiter_ip.allow(ip):
        return err("Demasiados registros desde tu conexión. Prueba más tarde.", 429)
    uid = auth.create_user(username, password)
    if uid is None:
        return err("Ese nombre de usuario ya existe")
    return _login_response(uid, username)


@api(require_login=False)
async def login(request, _):
    ip = client_ip(request)
    data = await body_json(request)
    username, password = str(data.get("username", ""))[:40], str(data.get("password", ""))[:128]
    if not auth.login_limiter_ip.allow(ip) or not auth.login_limiter_user.allow(username.lower()):
        return err("Demasiados intentos. Espera unos minutos.", 429)
    row = auth.authenticate(username, password)
    if row is None or (PUBLIC_MODE and row.get("is_test")):
        return err("Usuario o contraseña incorrectos", 401)
    return _login_response(row["id"], row["username"])


def _login_response(uid, username):
    token, csrf = auth.create_session(uid)
    resp = JSONResponse({"username": username, "csrf": csrf})
    resp.set_cookie(COOKIE, token, max_age=auth.SESSION_DAYS * 86400, httponly=True,
                    samesite="strict", secure=COOKIE_SECURE, path="/")
    return resp


@api(require_login=False)
async def logout(request, _):
    s = current_user(request, require_csrf=True)
    if s:
        auth.delete_session(request.cookies.get(COOKIE))
    resp = JSONResponse({"ok": True})
    resp.delete_cookie(COOKIE, path="/")
    return resp


@api(require_login=False)
async def me(request, _):
    s = current_user(request)
    if s is None:
        return JSONResponse({"user": None})
    gid = user_game.get(s["user_id"])
    return JSONResponse({"user": {"username": s["username"]}, "csrf": s["csrf_token"],
                         "game_id": gid, "game_room": games[gid].room if gid in games else None})


@api(require_login=False)
async def room_list(request, _):
    counts = online_counts()
    out = [dict(info, online=counts.get(info["key"], 0)) for info in rooms.public_info()]
    return JSONResponse({"rooms": out})


# --------------------------------------------------------------------------- arena
def active_run(user_id, room):
    return db.query_one(
        "SELECT * FROM arena_runs WHERE user_id = ? AND room = ? AND status IN ('drafting', 'playing') "
        "ORDER BY id DESC", (user_id, room))


def run_json(run):
    if run is None:
        return {"run": None}
    st = json.loads(run["state"])
    st.setdefault("room", run.get("room") or rooms.DEFAULT_ROOM)
    rooms.activate(st["room"])
    return {"run": {"id": run["id"], "status": run["status"], "wins": run["wins"], "room": st["room"],
                    "losses": run["losses"], "draft": draft.public_state(st),
                    "max_wins": R.MAX_WINS, "max_losses": R.MAX_LOSSES}}


@api()
async def get_run(request, user):
    return JSONResponse(run_json(active_run(user["user_id"], room_of(request))))


@api()
async def new_run(request, user):
    room = room_of(request)
    if active_run(user["user_id"], room):
        return err("Ya tienes una run de Arena en curso en esta sala")
    rooms.activate(room)
    st = draft.new_run_state(_rng, room)
    db.insert("INSERT INTO arena_runs (user_id, state, room) VALUES (?, ?, ?)",
              (user["user_id"], json.dumps(st), room))
    return JSONResponse(run_json(active_run(user["user_id"], room_of(request))))


async def _draft_step(request, user, fn):
    data = await body_json(request)
    room = room_of(request)
    run = active_run(user["user_id"], room)
    if run is None or run["status"] != "drafting":
        return err("No estás haciendo un draft")
    idx = data.get("index")
    if not isinstance(idx, int):
        return err("Opción no válida")
    rooms.activate(room)
    state = json.loads(run["state"])
    state.setdefault("room", room)
    st = fn(state, idx, _rng)
    status = "playing" if st["complete"] else "drafting"
    db.execute("UPDATE arena_runs SET state = ?, status = ? WHERE id = ?",
               (json.dumps(st), status, run["id"]))
    return JSONResponse(run_json(active_run(user["user_id"], room_of(request))))


@api()
async def pick_hero(request, user):
    return await _draft_step(request, user, draft.pick_hero)


@api()
async def pick_card(request, user):
    return await _draft_step(request, user, draft.pick_card)


@api()
async def retire_run(request, user):
    run = active_run(user["user_id"], room_of(request))
    if run is None:
        return err("No tienes ninguna run activa")
    if user["user_id"] in user_game:
        return err("Termina tu partida antes de retirarte")
    _leave_queue(user["user_id"])
    db.execute("UPDATE arena_runs SET status = 'retired', finished_at = CURRENT_TIMESTAMP "
               "WHERE id = ?", (run["id"],))
    return JSONResponse({"run": None})


@api()
async def history(request, user):
    runs = db.query("SELECT id, wins, losses, status, state, created_at, room FROM arena_runs "
                    "WHERE user_id = ? AND status IN ('finished', 'retired') ORDER BY id DESC "
                    "LIMIT 20", (user["user_id"],))
    out = []
    for r in runs:
        st = json.loads(r["state"])
        out.append({"id": r["id"], "wins": r["wins"], "losses": r["losses"], "status": r["status"],
                    "class": draft.CLASS_NAMES_ES.get(st.get("card_class") or "", "?"),
                    "room": r.get("room") or rooms.DEFAULT_ROOM,
                    "room_name": rooms.ROOMS[rooms.normalize(r.get("room"))]["name"],
                    "date": str(r["created_at"])})
    return JSONResponse({"runs": out})


# ---------------------------------------------------------------- emparejamiento
def _leave_queue(user_id):
    queue[:] = [q for q in queue if q[0] != user_id]


@api()
async def queue_join(request, user):
    uid = user["user_id"]
    room = room_of(request)
    async with lock:
        if uid in user_game:
            return JSONResponse(_in_game(uid))
        run = active_run(uid, room)
        if run is None or run["status"] != "playing":
            return err("Necesitas un mazo de Arena terminado para buscar partida")
        if not any(q[0] == uid and q[3] == room for q in queue):
            _leave_queue(uid)  # solo se puede buscar partida en una sala a la vez
            queue.append((uid, run["id"], time.time(), room))
        _try_match(room)
        if uid in user_game:
            return JSONResponse(_in_game(uid))
    return JSONResponse({"status": "queued", "players_in_queue": _queued(room)})


def _queued(room):
    return sum(1 for q in queue if q[3] == room)


def _in_game(uid):
    gid = user_game[uid]
    return {"status": "in_game", "game_id": gid, "room": games[gid].room if gid in games else None}


@api()
async def queue_leave(request, user):
    async with lock:
        _leave_queue(user["user_id"])
    return JSONResponse({"status": "idle"})


@api()
async def queue_status(request, user):
    uid = user["user_id"]
    room = room_of(request)
    if uid in user_game:
        return JSONResponse(_in_game(uid))
    if any(q[0] == uid and q[3] == room for q in queue):
        return JSONResponse({"status": "queued", "players_in_queue": _queued(room)})
    return JSONResponse({"status": "idle"})


def _try_match(room):
    while True:
        waiting = [q for q in queue if q[3] == room]
        if len(waiting) < 2:
            return
        a = waiting[0]
        b = next((q for q in waiting[1:] if q[0] != a[0]), None)
        if b is None:
            return
        queue.remove(a)
        queue.remove(b)
        _start_game(a, b, room)


def _start_game(a, b, room):
    seats = []
    for uid, run_id, _, _r in (a, b):
        run = db.query_one("SELECT r.state, u.username FROM arena_runs r JOIN users u "
                           "ON u.id = r.user_id WHERE r.id = ?", (run_id,))
        st = json.loads(run["state"])
        seats.append({"user_id": uid, "username": run["username"], "hero": st["hero_card"],
                      "deck": st["deck"], "run_id": run_id})
    _rng.shuffle(seats)  # quién empieza es aleatorio
    gid = db.insert("INSERT INTO matches (run1_id, run2_id, user1_id, user2_id) VALUES (?, ?, ?, ?)",
                    (seats[0]["run_id"], seats[1]["run_id"], seats[0]["user_id"], seats[1]["user_id"]))
    games[gid] = GameSession(gid, seats, room)
    game_runs[gid] = {s["user_id"]: s["run_id"] for s in seats}
    for s in seats:
        user_game[s["user_id"]] = gid
    notify(gid)


def _finish_game(gid):
    s = games[gid]
    db.execute("UPDATE matches SET winner_user_id = ?, reason = ?, finished_at = CURRENT_TIMESTAMP "
               "WHERE id = ?", (s.winner_user_id, s.finish_reason, gid))
    for uid, run_id in game_runs[gid].items():
        if s.winner_user_id is None:
            pass  # empate: no suma nada
        elif s.winner_user_id == uid:
            db.execute("UPDATE arena_runs SET wins = wins + 1 WHERE id = ?", (run_id,))
        else:
            db.execute("UPDATE arena_runs SET losses = losses + 1 WHERE id = ?", (run_id,))
        db.execute("UPDATE arena_runs SET status = 'finished', finished_at = CURRENT_TIMESTAMP "
                   "WHERE id = ? AND (wins >= ? OR losses >= ?)", (run_id, R.MAX_WINS, R.MAX_LOSSES))
        user_game.pop(uid, None)


async def _after_change(gid):
    s = games.get(gid)
    if s and s.finished and gid in game_runs:
        _finish_game(gid)
        game_runs.pop(gid, None)
    notify(gid)


# ----------------------------------------------------------------------- partidas
def _game_for(user, gid):
    s = games.get(gid)
    if s is None or user["user_id"] not in s.user_index:
        raise ActionError("Partida no encontrada")
    return s


@api()
async def game_state(request, user):
    s = _game_for(user, int(request.path_params["gid"]))
    seen(user["user_id"], s.room)
    return JSONResponse(s.view(user["user_id"]))


@api()
async def game_action(request, user):
    gid = int(request.path_params["gid"])
    data = await body_json(request)
    uid = user["user_id"]
    async with lock:
        s = _game_for(user, gid)
        kind = data.get("type")

        def opt_int(k):
            v = data.get(k)
            if v is None:
                return None
            if not isinstance(v, int):
                raise ActionError("Parámetro no válido: %s" % k)
            return v

        if kind == "mulligan":
            ids = data.get("replace") or []
            if not isinstance(ids, list) or not all(isinstance(i, int) for i in ids):
                raise ActionError("Parámetro no válido")
            s.mulligan(uid, ids)
        elif kind == "choose":
            s.choose(uid, opt_int("eid"))
        elif kind == "play":
            s.play(uid, opt_int("eid"), target=opt_int("target"), choose=opt_int("choose"),
                   position=opt_int("position"))
        elif kind == "attack":
            s.attack(uid, opt_int("attacker"), opt_int("defender"))
        elif kind == "hero_power":
            s.hero_power(uid, target=opt_int("target"), choose=opt_int("choose"))
        elif kind == "end_turn":
            s.end_turn(uid)
        elif kind == "concede":
            s.concede(uid)
        elif kind == "chat":
            text = data.get("text")
            if not isinstance(text, str):
                raise ActionError("Mensaje no válido")
            s.say(uid, text)
        else:
            raise ActionError("Acción desconocida")
        await _after_change(gid)
        return JSONResponse(s.view(uid))


@api()
async def game_events_stream(request, user):
    gid = int(request.path_params["gid"])
    s = _game_for(user, gid)
    uid = user["user_id"]

    async def gen():
        last = -1
        while True:
            if await request.is_disconnected():
                break
            sess = games.get(gid)
            if sess is None:
                break
            seen(uid, sess.room)
            if sess.version != last:
                last = sess.version
                yield "data: %s\n\n" % json.dumps(sess.view(uid))
                if sess.finished:
                    break
            ev = game_events.setdefault(gid, asyncio.Event())
            try:
                await asyncio.wait_for(ev.wait(), timeout=15)
            except asyncio.TimeoutError:
                yield ": ping\n\n"

    del s
    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


async def ticker():
    """Aplica los temporizadores de turno y limpia partidas terminadas."""
    while True:
        await asyncio.sleep(1)
        async with lock:
            for gid, s in list(games.items()):
                try:
                    if s.tick():
                        await _after_change(gid)
                except Exception as e:  # nunca dejar morir el ticker
                    print("error en ticker", gid, e)
                if s.finished and time.time() - s.deadline > 600:
                    games.pop(gid, None)
                    game_events.pop(gid, None)


# ---------------------------------------------------------------------- frontend
async def spa(request):
    index = os.path.join(FRONTEND_DIST, "index.html")
    if os.path.exists(index):
        return FileResponse(index)
    return Response("Frontend sin compilar. Ejecuta el build del frontend.", media_type="text/plain")


class SecurityHeaders(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        resp = await call_next(request)
        resp.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' data: https://art.hearthstonejson.com; style-src 'self'; script-src 'self'; "
            "connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["Referrer-Policy"] = "same-origin"
        if request.url.path.startswith("/api/"):
            resp.headers.setdefault("Cache-Control", "no-store")
        return resp


@asynccontextmanager
async def lifespan(app):
    db.init_schema()
    from .cards import arena_pool
    for r in rooms.ROOMS:  # carga las cartas de todas las salas al arrancar
        arena_pool(r)
    rooms.activate(rooms.DEFAULT_ROOM)
    task = asyncio.create_task(ticker())
    yield
    task.cancel()


routes = [
    Route("/api/register", register, methods=["POST"]),
    Route("/api/login", login, methods=["POST"]),
    Route("/api/logout", logout, methods=["POST"]),
    Route("/api/me", me),
    Route("/api/rooms", room_list),
    Route("/api/run", get_run),
    Route("/api/run/new", new_run, methods=["POST"]),
    Route("/api/run/hero", pick_hero, methods=["POST"]),
    Route("/api/run/pick", pick_card, methods=["POST"]),
    Route("/api/run/retire", retire_run, methods=["POST"]),
    Route("/api/history", history),
    Route("/api/queue/join", queue_join, methods=["POST"]),
    Route("/api/queue/leave", queue_leave, methods=["POST"]),
    Route("/api/queue/status", queue_status),
    Route("/api/game/{gid:int}/state", game_state),
    Route("/api/game/{gid:int}/events", game_events_stream),
    Route("/api/game/{gid:int}/action", game_action, methods=["POST"]),
]
if os.path.isdir(os.path.join(FRONTEND_DIST, "assets")):
    routes.append(Mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets"))))
routes.append(Route("/{path:path}", spa))

app = Starlette(routes=routes, lifespan=lifespan, middleware=[Middleware(SecurityHeaders)])
