"""Detecta cartas que Blizzard renombró (mismo dbfId, distinto CardID) entre la 11.0
y la build moderna con la que se programó Fireplace.

Ejemplo: el poder de héroe del Pícaro era CS2_083b en 2018 y ahora es HERO_03bp.
Fireplace solo tiene el script con el nombre nuevo, así que sin este alias el poder no hacía nada.

Uso: python build_id_aliases.py <CardDefs_23966.xml> <CardDefs_moderno.xml> <salida.json>
"""
import json
import sys
import xml.etree.ElementTree as ET


def dbf_map(path):
    out = {}
    for _, el in ET.iterparse(path, events=("end",)):
        if el.tag == "Entity":
            out[el.get("ID")] = el.get("CardID")
            el.clear()
    return out


def main():
    old, new, out = sys.argv[1:4]
    a, b = dbf_map(old), dbf_map(new)
    aliases = {a[d]: b[d] for d in a if d in b and a[d] != b[d]}
    with open(out, "w", encoding="utf-8") as f:
        json.dump(aliases, f, indent=1, sort_keys=True)
    print("alias:", len(aliases))
    for k in sorted(aliases)[:40]:
        print(" ", k, "->", aliases[k])


if __name__ == "__main__":
    main()
