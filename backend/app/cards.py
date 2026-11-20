"""Base de datos de cartas: motor (Fireplace) + textos en español + pool de Arena."""
import os
import re
import sys
from functools import lru_cache

HERE = os.path.dirname(os.path.abspath(__file__))
VENDOR = os.path.join(HERE, "..", "vendor")
if VENDOR not in sys.path:
    sys.path.insert(0, VENDOR)

from fireplace import cards as fp_cards  # noqa: E402
from hearthstone import cardxml  # noqa: E402
from hearthstone.enums import CardClass, CardSet, CardType, Rarity  # noqa: E402
from hearthstone_data import get_carddefs_path  # noqa: E402

from . import arena_rules as R  # noqa: E402
from . import rooms  # noqa: E402

TYPE_ES = {
    CardType.MINION: "Esbirro", CardType.SPELL: "Hechizo", CardType.WEAPON: "Arma",
    CardType.HERO: "Héroe", CardType.HERO_POWER: "Poder de héroe", CardType.ENCHANTMENT: "Encantamiento",
}
RARITY_ES = {
    Rarity.FREE: "Básica", Rarity.COMMON: "Común", Rarity.RARE: "Rara",
    Rarity.EPIC: "Épica", Rarity.LEGENDARY: "Legendaria",
}
CLASS_ES = {
    CardClass.DRUID: "Druida", CardClass.HUNTER: "Cazador", CardClass.MAGE: "Mago",
    CardClass.PALADIN: "Paladín", CardClass.PRIEST: "Sacerdote", CardClass.ROGUE: "Pícaro",
    CardClass.SHAMAN: "Chamán", CardClass.WARLOCK: "Brujo", CardClass.WARRIOR: "Guerrero",
    CardClass.NEUTRAL: "Neutral",
}
SET_ES = {
    CardSet.BASIC: "Básico", CardSet.EXPERT1: "Clásico", CardSet.HOF: "Salón de la Fama",
    CardSet.UNGORO: "Viaje a Un'Goro", CardSet.ICECROWN: "Caballeros del Trono Helado",
    CardSet.LOOTAPALOOZA: "Kóbolds y Catacumbas", CardSet.GILNEAS: "El Bosque Embrujado",
    CardSet.OG: "Susurros de los Dioses Antiguos", CardSet.KARA: "Una Noche en Karazhan",
    CardSet.GANGS: "Mafias de Gadgetzan",
}

_ALLOWED_TAGS = re.compile(r"</?(b|i)>")


def clean_text(text):
    """Limpia el formato interno de Hearthstone. Deja solo <b> e <i>."""
    if not text:
        return ""
    t = text.replace("[x]", "")
    t = re.sub(r"[$#](\d+)", r"\1", t)          # $3 (daño con hechizo) / #3 (curación)
    t = t.replace("_", " ").replace("\n", " ")
    t = re.sub(r"@.*$", "", t)                   # textos alternativos tras '@'
    t = re.sub(r"\{\d\}", "", t)
    t = re.sub(r"<(?!/?(b|i)>)[^>]*>", "", t)    # quita cualquier otra etiqueta
    return re.sub(r"\s+", " ", t).strip()


@lru_cache(maxsize=1)
def card_icons():
    """Icono (game-icons.net, CC BY 3.0) asignado a cada carta por tools/build_icons.py."""
    import json
    path = os.path.join(HERE, "..", "data", "card_icons.json")
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except OSError:
        return {}


@lru_cache(maxsize=4)
def _spanish_db(room):
    path = rooms.ROOMS[room]["carddefs"] if room else get_carddefs_path()
    db, _ = cardxml.load(path, locale="esES")
    return db


def spanish_db(room=None):
    """Textos en español de la sala indicada (o de la sala activa)."""
    return _spanish_db(rooms.normalize(room or rooms.active()))


def engine_db(room=None):
    """Base de datos del motor con la sala indicada (o la activa) cargada."""
    rooms.activate(room or rooms.active() or rooms.DEFAULT_ROOM)
    return fp_cards.db


def card_view(card_id):
    """Datos públicos de una carta (de la sala activa) para mostrar en la web."""
    es = spanish_db().get(card_id)
    c = engine_db().get(card_id) or es
    if c is None:
        return {"id": card_id, "name": card_id, "text": ""}
    races = [r.name for r in getattr(c, "races", []) or []]
    return {
        "id": card_id,
        "name": (es.name if es else c.name),
        "text": clean_text(es.description if es else c.description),
        "type": TYPE_ES.get(c.type, str(c.type)),
        "cost": c.cost,
        "atk": c.atk,
        "health": c.health,
        "durability": c.durability,
        "rarity": RARITY_ES.get(c.rarity, ""),
        "class": CLASS_ES.get(c.card_class, ""),
        "set": SET_ES.get(c.card_set, ""),
        "races": races,
        "icon": card_icons().get(card_id),
        "class_key": c.card_class.name.lower() if c.card_class else "neutral",
    }


def _effective_rarity(c):
    return Rarity.COMMON if c.rarity == Rarity.FREE else c.rarity


def arena_pool(room=None):
    """Devuelve {clase: {rareza: [(card_id, peso), ...]}} con las cartas draftables de la sala."""
    return _arena_pool(rooms.normalize(room or rooms.active()))


@lru_cache(maxsize=4)
def _arena_pool(room):
    db = engine_db(room)
    rules = R.for_room(room)
    pool = {cls: {r: [] for r in R.RARITY_WEIGHTS} for cls in R.CLASSES}
    for cid, c in db.items():
        if not c.collectible or c.card_set not in rules["arena_sets"]:
            continue
        if c.type not in (CardType.MINION, CardType.SPELL, CardType.WEAPON, CardType.HERO):
            continue
        if c.name in rules["banned"]:
            continue
        # Los héroes básicos (Jaina, Garrosh...) son "cartas" en los datos, pero no se draftean.
        # Las cartas de héroe de verdad (p. ej. Hagatha, la Bruja) sí.
        if c.type == CardType.HERO and (c.card_set == CardSet.BASIC or cid in R.CLASSES.values()):
            continue
        rarity = _effective_rarity(c)
        weight = R.NEWEST_SET_WEIGHT if c.card_set == rules["newest_set"] else 1.0
        if c.card_class == CardClass.NEUTRAL:
            classes = list(R.CLASSES)
        elif c.card_class in R.CLASSES:
            classes = [c.card_class]
            weight *= R.CLASS_CARD_WEIGHT
        else:
            continue
        for cls in classes:
            pool[cls][rarity].append((cid, weight))
    return pool


def banned_names_missing(room=None):
    """Nombres prohibidos que no existen en los datos (para detectar erratas)."""
    room = rooms.normalize(room)
    names = {c.name for c in engine_db(room).values()}
    return sorted(n for n in R.for_room(room)["banned"] if n not in names)
