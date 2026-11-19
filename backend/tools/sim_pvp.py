"""Simula partidas PvP entre dos "clientes" aleatorios usando SOLO la vista y las
acciones públicas de GameSession (lo mismo que hará la web). Sirve de test de estrés."""
import os
import random
import sys
import traceback

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from app import draft  # noqa: E402
from app.game_session import ActionError, GameSession  # noqa: E402


def random_deck(rng):
    st = draft.new_run_state(rng)
    st = draft.pick_hero(st, rng.randrange(3), rng)
    while not st["complete"]:
        st = draft.pick_card(st, rng.randrange(3), rng)
    return st["hero_card"], st["deck"]


def bot_step(s, uid, rng):
    v = s.view(uid)
    if v["finished"]:
        return False
    if v["choice"]:
        cards = v["choice"]["cards"]
        if v["choice"]["type"] == "mulligan":
            s.mulligan(uid, [c["eid"] for c in cards if rng.random() < 0.4])
        else:
            s.choose(uid, rng.choice(cards)["eid"])
        return True
    if not v["my_turn"]:
        return False
    me = v["me"]
    opts = []
    for c in me["hand"]:
        if c.get("playable"):
            opts.append(("play", c))
    for c in me["field"] + [me["hero"]]:
        if c.get("can_attack") and c.get("attack_targets"):
            opts.append(("attack", c))
    if me["power"].get("usable"):
        opts.append(("power", me["power"]))
    if not opts or rng.random() < 0.15:
        s.end_turn(uid)
        return True
    kind, c = rng.choice(opts)
    try:
        if kind == "play":
            choose = target = None
            if c.get("choose"):
                o = rng.choice([o for o in c["choose"] if o["playable"]] or c["choose"])
                choose = o["eid"]
                if o.get("targets"):
                    target = rng.choice(o["targets"])
                elif o.get("targets") == []:
                    return True
            elif c.get("targets"):
                target = rng.choice(c["targets"])
            elif c.get("targets") == []:
                s.end_turn(uid)
                return True
            s.play(uid, c["eid"], target=target, choose=choose,
                   position=rng.randint(0, len(me["field"])))
        elif kind == "attack":
            s.attack(uid, c["eid"], rng.choice(c["attack_targets"]))
        else:
            s.hero_power(uid, target=rng.choice(c["targets"]) if c.get("targets") else None)
    except ActionError:
        pass
    return True


def run(n, seed):
    rng = random.Random(seed)
    stats = {"ok": 0, "crash": 0, "stuck": 0}
    for g in range(n):
        h1, d1 = random_deck(rng)
        h2, d2 = random_deck(rng)
        s = GameSession(g, [
            {"user_id": 1, "username": "A", "hero": h1, "deck": d1},
            {"user_id": 2, "username": "B", "hero": h2, "deck": d2},
        ])
        try:
            steps = 0
            while not s.finished and steps < 3000:
                moved = bot_step(s, 1, rng) or bot_step(s, 2, rng)
                steps += 1
                if not moved:
                    break
                s.view(1), s.view(2)
            if s.finished:
                stats["ok"] += 1
            else:
                stats["stuck"] += 1
                print("partida", g, "atascada en turno", s.game.turn)
        except Exception:
            stats["crash"] += 1
            print("CRASH partida", g)
            traceback.print_exc(limit=6)
    print(stats)


if __name__ == "__main__":
    run(int(sys.argv[1]) if len(sys.argv) > 1 else 5, int(sys.argv[2]) if len(sys.argv) > 2 else 1)
