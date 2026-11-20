"""Salas del juego. Cada sala usa su propia colección de cartas (build de Hearthstone).

- "witchwood": El Bosque Embrujado al salir (parche 11.0, build 23966, abril 2018).
- "kobolds":   Kóbolds y Catacumbas al salir (parche 10.0, build 22611, diciembre 2017).

El motor (Fireplace) usa una base de datos de cartas global (fireplace.cards.db).
Al arrancar se carga cada build una vez y se guarda una copia; `activate(sala)`
cambia el contenido de esa base de datos global por el de la sala. El servidor
es asíncrono y de un solo hilo, así que basta con activar la sala antes de
cualquier uso del motor (acciones, vistas, temporizadores, draft).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.normpath(os.path.join(HERE, "..", "data"))
VENDOR = os.path.join(HERE, "..", "vendor")
if VENDOR not in sys.path:
    sys.path.insert(0, VENDOR)

from hearthstone.enums import CardSet, ZodiacYear  # noqa: E402

DEFAULT_ROOM = "witchwood"

_COMMON_BANS = None  # se rellena desde arena_rules para evitar importaciones circulares

ROOMS = {
    "witchwood": {
        "key": "witchwood",
        "name": "El Bosque Embrujado",
        "subtitle": "Parche 11.0 · abril de 2018",
        "description": "Año del Cuervo: Básico, Clásico, Un'Goro, Trono Helado, Kóbolds y Bosque Embrujado.",
        "build": 23966,
        "carddefs": os.path.join(DATA, "CardDefs_23966.xml"),
        "extra": os.path.join(DATA, "CardDefs_extra.xml"),
        "aliases": os.path.join(DATA, "id_aliases.json"),
        "year": ZodiacYear.RAVEN,
        "arena_sets": {
            CardSet.BASIC, CardSet.EXPERT1, CardSet.UNGORO, CardSet.ICECROWN,
            CardSet.LOOTAPALOOZA, CardSet.GILNEAS,
        },
        "newest_set": CardSet.GILNEAS,
        # En la 11.0 se sacaron del draft estas dos cartas
        "extra_bans": {"Humongous Razorleaf", "Ancient Watcher"},
        "settings": {"raza_cost": 1},
        "art": "GIL_692",  # Genn Greymane (arte de la sala)
    },
    "kobolds": {
        "key": "kobolds",
        "name": "Kóbolds y Catacumbas",
        "subtitle": "Parche 10.0 · diciembre de 2017",
        "description": "Año del Mamut: Básico, Clásico, Viejos Dioses, Karazhan, Gadgetzan, Un'Goro, Trono Helado y Kóbolds.",
        "build": 22611,
        "carddefs": os.path.join(DATA, "CardDefs_22611.xml"),
        "extra": os.path.join(DATA, "CardDefs_extra_22611.xml"),
        "aliases": os.path.join(DATA, "id_aliases_22611.json"),
        "year": ZodiacYear.MAMMOTH,
        "arena_sets": {
            CardSet.BASIC, CardSet.EXPERT1, CardSet.OG, CardSet.KARA, CardSet.GANGS,
            CardSet.UNGORO, CardSet.ICECROWN, CardSet.LOOTAPALOOZA,
        },
        "newest_set": CardSet.LOOTAPALOOZA,
        "extra_bans": set(),
        "settings": {"raza_cost": 0},
        "art": "LOOT_541",  # Rey Togwaggle
    },
}

_store = {}   # sala -> (dict de cartas, dict dbf)
_active = None


def valid(room):
    return room in ROOMS


def normalize(room):
    return room if room in ROOMS else DEFAULT_ROOM


def _load(room):
    from fireplace import cards as fp_cards
    cfg = ROOMS[room]
    db = fp_cards.db
    fp_cards.year = cfg["year"]
    fp_cards.room_settings = dict(cfg["settings"])
    db.clear()
    db.dbf = {}
    db.initialize(path=cfg["carddefs"], extra_path=cfg["extra"], alias_path=cfg["aliases"])
    # cartas propias de los scripts (@custom_card): solo se registran al importar los módulos
    from fireplace.cards.utils import register_custom_cards
    register_custom_cards()
    _store[room] = (dict(db), dict(db.dbf))


def activate(room):
    """Pone la base de datos de cartas del motor en la sala indicada."""
    global _active
    room = normalize(room)
    if _active == room:
        return
    from fireplace import cards as fp_cards
    if room not in _store:
        _load(room)
    cards, dbf = _store[room]
    cfg = ROOMS[room]
    db = fp_cards.db
    db.clear()
    db.update(cards)
    db.dbf = dbf
    db.initialized = True
    fp_cards.year = cfg["year"]
    fp_cards.room_settings = dict(cfg["settings"])
    _active = room


def active():
    return _active


def load_all():
    for room in ROOMS:
        activate(room)
    activate(DEFAULT_ROOM)


def public_info():
    return [
        {k: ROOMS[r][k] for k in ("key", "name", "subtitle", "description", "art")}
        for r in ROOMS
    ]
