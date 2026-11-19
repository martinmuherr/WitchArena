"""Compara las cartas de dos builds de Hearthstone (CardDefs.xml).

Uso: python diff_builds.py <CardDefs_antigua.xml> <CardDefs_nueva.xml> [salida.json]

Sirve para encontrar qué cartas cambiaron entre el parche 11.0 (build 23966)
y la versión con la que se programó Fireplace (build 43246), y así saber qué
scripts de cartas hay que revisar.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "vendor"))

from hearthstone import cardxml  # noqa: E402
from hearthstone.enums import CardSet  # noqa: E402

SETS = {
    CardSet.BASIC, CardSet.EXPERT1, CardSet.HOF, CardSet.UNGORO,
    CardSet.ICECROWN, CardSet.LOOTAPALOOZA, CardSet.GILNEAS,
}


def summary(c):
    return {
        "name": c.name,
        "set": c.card_set.name,
        "cost": c.cost,
        "atk": c.atk,
        "health": c.health,
        "durability": c.durability,
        "armor": c.armor,
        "races": sorted(r.name for r in (c.races or [])) if hasattr(c, "races") else [c.race.name],
        "text": (c.description or "").replace("\n", " "),
        "collectible": c.collectible,
    }


def main():
    old_path, new_path = sys.argv[1], sys.argv[2]
    out = sys.argv[3] if len(sys.argv) > 3 else None
    old, _ = cardxml.load(old_path, locale="enUS")
    new, _ = cardxml.load(new_path, locale="enUS")
    changes = []
    for cid, oc in old.items():
        if oc.card_set not in SETS:
            continue
        nc = new.get(cid)
        if nc is None:
            changes.append({"id": cid, "old": summary(oc), "new": None})
            continue
        a, b = summary(oc), summary(nc)
        diff = {k: (a[k], b[k]) for k in a if k not in ("set",) and a[k] != b[k]}
        if diff:
            changes.append({"id": cid, "name": oc.name, "set": a["set"],
                            "collectible": oc.collectible, "diff": diff})
    changes.sort(key=lambda x: (not x.get("collectible", False), x.get("set", ""), x["id"]))
    for ch in changes:
        if ch.get("new") is None and "diff" not in ch:
            print("DESAPARECE", ch["id"], ch["old"]["name"])
            continue
        flag = "*" if ch["collectible"] else " "
        print(flag, ch["id"], ch["name"], "|", "; ".join(
            "%s: %r -> %r" % (k, v[0], v[1]) for k, v in ch["diff"].items()))
    print("total cambios:", len(changes))
    if out:
        with open(out, "w", encoding="utf-8") as f:
            json.dump(changes, f, ensure_ascii=False, indent=1, default=str)


if __name__ == "__main__":
    main()
