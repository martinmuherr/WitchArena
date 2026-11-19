"""Draft de Arena: elección de héroe y 30 elecciones de 1 entre 3 cartas.

El estado de la run es un dict serializable a JSON que se guarda en la base de datos.
El cliente nunca decide qué cartas se ofrecen: solo envía el índice (0, 1 o 2).
"""
import random

from hearthstone.enums import CardClass, Rarity

from . import arena_rules as R
from .cards import arena_pool, card_view


def _weighted_choice(rng, items):
    total = sum(w for _, w in items)
    x = rng.random() * total
    for item, w in items:
        x -= w
        if x <= 0:
            return item
    return items[-1][0]


def _roll_rarity(rng, pick_number):
    table = R.GUARANTEED_RARITY_WEIGHTS if pick_number in R.GUARANTEED_RARE_PICKS else R.RARITY_WEIGHTS
    return _weighted_choice(rng, list(table.items()))


def offer_cards(card_class, pick_number, rng):
    pool = arena_pool()[card_class]
    rarity = _roll_rarity(rng, pick_number)
    candidates = list(pool[rarity])
    offer = []
    while len(offer) < 3 and candidates:
        cid = _weighted_choice(rng, candidates)
        offer.append(cid)
        candidates = [(c, w) for c, w in candidates if c != cid]
    return offer


def new_run_state(rng=None):
    rng = rng or random.SystemRandom()
    classes = rng.sample(list(R.CLASSES), 3)
    return {
        "phase": "hero",
        "hero_options": [c.name for c in classes],
        "card_class": None,
        "hero_card": None,
        "deck": [],
        "offer": [],
        "complete": False,
    }


def pick_hero(state, index, rng=None):
    rng = rng or random.SystemRandom()
    if state["phase"] != "hero":
        raise ValueError("Ya has elegido héroe")
    if index not in (0, 1, 2):
        raise ValueError("Opción no válida")
    cls = CardClass[state["hero_options"][index]]
    state = dict(state)
    state.update(phase="cards", card_class=cls.name, hero_card=R.CLASSES[cls], deck=[],
                 offer=offer_cards(cls, 1, rng))
    return state


def pick_card(state, index, rng=None):
    rng = rng or random.SystemRandom()
    if state["phase"] != "cards":
        raise ValueError("No estás eligiendo cartas")
    if index not in range(len(state["offer"])):
        raise ValueError("Opción no válida")
    state = dict(state)
    state["deck"] = state["deck"] + [state["offer"][index]]
    if len(state["deck"]) >= R.DECK_SIZE:
        state.update(phase="done", offer=[], complete=True)
    else:
        state["offer"] = offer_cards(CardClass[state["card_class"]], len(state["deck"]) + 1, rng)
    return state


CLASS_NAMES_ES = {
    "DRUID": "Druida", "HUNTER": "Cazador", "MAGE": "Mago", "PALADIN": "Paladín",
    "PRIEST": "Sacerdote", "ROGUE": "Pícaro", "SHAMAN": "Chamán", "WARLOCK": "Brujo",
    "WARRIOR": "Guerrero",
}


def public_state(state):
    """Lo que ve el jugador de su draft."""
    return {
        "phase": state["phase"],
        "hero_options": [{"key": k, "name": CLASS_NAMES_ES[k]} for k in state["hero_options"]],
        "card_class": state["card_class"],
        "card_class_name": CLASS_NAMES_ES.get(state["card_class"] or "", None),
        "deck": [card_view(c) for c in state["deck"]],
        "offer": [card_view(c) for c in state["offer"]],
        "pick_number": len(state["deck"]) + 1,
        "complete": state["complete"],
    }
