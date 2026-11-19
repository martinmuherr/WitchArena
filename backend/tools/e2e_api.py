"""Prueba de extremo a extremo contra el servidor en marcha.

Dos usuarios de prueba hacen login, completan el draft, se emparejan y juegan
una partida con decisiones aleatorias hasta el final.
Uso: python tools/e2e_api.py http://localhost:8000 usuario1 clave1 usuario2 clave2
"""
import random
import sys

import requests


class Client:
    def __init__(self, base, user, pw):
        self.base, self.s = base, requests.Session()
        r = self.s.post(base + "/api/login", json={"username": user, "password": pw})
        r.raise_for_status()
        self.csrf = r.json()["csrf"]

    def get(self, path):
        r = self.s.get(self.base + path)
        return r.status_code, r.json()

    def post(self, path, data=None):
        r = self.s.post(self.base + path, json=data or {}, headers={"X-CSRF-Token": self.csrf})
        return r.status_code, r.json()


def draft(c, rng):
    code, run = c.get("/api/run")
    if run["run"] is None:
        code, run = c.post("/api/run/new")
    while run["run"]["status"] == "drafting":
        phase = run["run"]["draft"]["phase"]
        path = "/api/run/hero" if phase == "hero" else "/api/run/pick"
        code, run = c.post(path, {"index": rng.randrange(3)})
        assert code == 200, run
    print("mazo listo:", run["run"]["draft"]["card_class_name"], len(run["run"]["draft"]["deck"]))


def act(c, gid, v, rng):
    if v["finished"]:
        return False
    if v["choice"]:
        cards = v["choice"]["cards"]
        if v["choice"]["type"] == "mulligan":
            c.post("/api/game/%d/action" % gid, {"type": "mulligan", "replace": [cards[0]["eid"]]})
        else:
            c.post("/api/game/%d/action" % gid, {"type": "choose", "eid": rng.choice(cards)["eid"]})
        return True
    if not v["my_turn"]:
        return False
    me = v["me"]
    for card in me["hand"]:
        if card.get("playable") and not card.get("choose"):
            data = {"type": "play", "eid": card["eid"], "position": len(me["field"])}
            if card.get("targets"):
                data["target"] = rng.choice(card["targets"])
            elif card.get("targets") == []:
                continue
            code, _ = c.post("/api/game/%d/action" % gid, data)
            if code == 200:
                return True
    for m in me["field"] + [me["hero"]]:
        if m.get("can_attack") and m.get("attack_targets"):
            c.post("/api/game/%d/action" % gid, {"type": "attack", "attacker": m["eid"],
                                                 "defender": rng.choice(m["attack_targets"])})
            return True
    c.post("/api/game/%d/action" % gid, {"type": "end_turn"})
    return True


def main():
    base = sys.argv[1]
    a = Client(base, sys.argv[2], sys.argv[3])
    b = Client(base, sys.argv[4], sys.argv[5])
    rng = random.Random(3)
    # comprobaciones de seguridad básicas
    r = a.s.post(base + "/api/run/new", json={})
    assert r.status_code == 401, "sin token CSRF debería rechazarse"
    r = requests.get(base + "/api/run")
    assert r.status_code == 401, "sin sesión debería rechazarse"
    draft(a, rng)
    draft(b, rng)
    print(a.post("/api/queue/join"))
    code, st = b.post("/api/queue/join")
    print(code, st)
    gid = st["game_id"]
    code, st2 = a.get("/api/queue/status")
    assert st2["game_id"] == gid
    # el rival no ve tu mano
    code, va = a.get("/api/game/%d/state" % gid)
    assert all(h.get("hidden") for h in va["opponent"]["hand"])
    steps = 0
    while steps < 2000:
        steps += 1
        _, va = a.get("/api/game/%d/state" % gid)
        _, vb = b.get("/api/game/%d/state" % gid)
        if va["finished"]:
            break
        if not (act(a, gid, va, rng) or act(b, gid, vb, rng)):
            pass
    print("terminada:", va["finished"], "ganador para A:", va["winner"], "turno", va["turn"])
    print(a.get("/api/run"))


if __name__ == "__main__":
    main()
