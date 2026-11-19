"""Extrae de una build moderna los encantamientos que no existían en la 11.0.

Fireplace (programado para el parche 17.6) usa algunos encantamientos técnicos
(p. ej. GBL_003e) que Blizzard añadió más tarde. No cambian el balance de 2018:
son "piezas internas" que el motor necesita. Los guardamos en un XML pequeño.

Uso: python build_extra_defs.py <CardDefs_23966.xml> <CardDefs_moderno.xml> <salida.xml>
"""
import sys
import xml.etree.ElementTree as ET


def main():
    old_path, new_path, out_path = sys.argv[1:4]
    old_ids = set()
    for _, el in ET.iterparse(old_path, events=("end",)):
        if el.tag == "Entity":
            old_ids.add(el.get("CardID"))
            el.clear()
    root = ET.Element("CardDefs")
    n = 0
    for _, el in ET.iterparse(new_path, events=("end",)):
        if el.tag != "Entity":
            continue
        cid = el.get("CardID")
        is_ench = any(t.get("name") == "CARDTYPE" and t.get("value") == "6" for t in el.findall("Tag"))
        if cid not in old_ids and is_ench:
            root.append(el)
            n += 1
        # no limpiamos los que añadimos
        elif el is not None:
            el.clear()
    ET.ElementTree(root).write(out_path, encoding="utf-8", xml_declaration=True)
    print("encantamientos añadidos:", n)


if __name__ == "__main__":
    main()
