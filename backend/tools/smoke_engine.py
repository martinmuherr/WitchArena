"""Prueba rápida: carga el motor con los datos 11.0 y juega partidas aleatorias."""
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "vendor"))

from fireplace import cards  # noqa: E402

t = time.time()
cards.db.initialize()
print("cartas cargadas:", len(cards.db), "en %.1fs" % (time.time() - t))

for cid in ["EX1_308", "ICC_701", "LOOT_520", "EX1_620", "GIL_825", "UNG_067"]:
    if cid in cards.db:
        c = cards.db[cid]
        print(cid, c.name, "coste", c.cost, "ataque", c.atk, "vida", c.health)

from fireplace.utils import play_full_game  # noqa: E402

ok = 0
for i in range(int(sys.argv[1]) if len(sys.argv) > 1 else 3):
    try:
        play_full_game()
        ok += 1
    except Exception as e:  # GameOver se considera éxito
        if type(e).__name__ == "GameOver":
            ok += 1
        else:
            print("error en partida", i, type(e).__name__, e)
print("partidas completadas:", ok)
