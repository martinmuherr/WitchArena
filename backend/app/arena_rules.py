"""Reglas del Arena tal y como estaban al salir El Bosque Embrujado (parche 11.0, abril 2018).

Fuentes:
- Notas del parche 11.0: sets Standard del Año del Cuervo, Salón de la Fama,
  "Humongous Razorleaf y Ancient Watcher dejan de aparecer en los drafts".
- Lista de cartas prohibidas en Arena publicada en febrero de 2018 (era Kóbolds).
- Parche 10.4: recogidas 1, 10, 20 y 30 con rareza garantizada rara o superior.

Todo lo que es una aproximación (probabilidades exactas que Blizzard nunca publicó)
está marcado como APROXIMADO para poder ajustarlo.
"""
from hearthstone.enums import CardClass, CardSet, Rarity

# Sets que aparecían en el draft (Arena = formato Standard en 2018)
ARENA_SETS = {
    CardSet.BASIC,         # Básico
    CardSet.EXPERT1,       # Clásico
    CardSet.UNGORO,        # Viaje a Un'Goro
    CardSet.ICECROWN,      # Caballeros del Trono Helado
    CardSet.LOOTAPALOOZA,  # Kóbolds y Catacumbas
    CardSet.GILNEAS,       # El Bosque Embrujado
}

# Set más reciente: en 2018 tenía más probabilidad de salir en el draft.
NEWEST_SET = CardSet.GILNEAS
NEWEST_SET_WEIGHT = 1.5  # APROXIMADO

# Las 9 clases jugables en 2018 y su héroe por defecto
CLASSES = {
    CardClass.DRUID: "HERO_06",
    CardClass.HUNTER: "HERO_05",
    CardClass.MAGE: "HERO_08",
    CardClass.PALADIN: "HERO_04",
    CardClass.PRIEST: "HERO_09",
    CardClass.ROGUE: "HERO_03",
    CardClass.SHAMAN: "HERO_02",
    CardClass.WARLOCK: "HERO_07",
    CardClass.WARRIOR: "HERO_01",
}

# Cartas prohibidas en el draft (se pueden seguir obteniendo con Descubrir o efectos aleatorios).
# Nombres en inglés tal y como aparecen en los datos del juego (locale enUS).
BANNED_NAMES = {
    # Druida
    "Mark of Nature", "Soul of the Forest", "Savagery", "Jungle Giants", "Malfurion the Pestilent",
    # Cazador
    "Timber Wolf", "Starving Buzzard", "Snipe", "The Marsh Queen", "Deathstalker Rexxar",
    # Mago
    "Open the Waygate", "Frost Lich Jaina",
    # Paladín
    "The Last Kaleidosaur", "Uther of the Ebon Blade",
    # Sacerdote
    "Mind Blast", "Inner Fire", "Lightwell", "Awaken the Makers", "Shadowreaper Anduin",
    # Pícaro
    "The Caverns Below", "Valeera the Hollow",
    # Chamán
    "Ancestral Healing", "Totemic Might", "Dust Devil", "Windspeaker", "Unite the Murlocs",
    "Thrall, Deathseer",
    # Brujo
    "Sacrificial Pact", "Succubus", "Sense Demons", "Lakkari Sacrifice", "Bloodreaver Gul'dan",
    # Guerrero
    "Charge", "Warsong Commander", "Rampage", "Fire Plume's Heart", "Scourgelord Garrosh",
    # Neutral
    "Vicious Fledgling",
}
# En la sala de El Bosque Embrujado se suman las dos cartas que el parche 11.0 sacó
# del draft ("Humongous Razorleaf" y "Ancient Watcher"); ver rooms.py.
BANNED_NAMES_BASE = frozenset(BANNED_NAMES)
BANNED_NAMES |= {"Humongous Razorleaf", "Ancient Watcher"}


def for_room(room):
    """Sets, set más reciente y cartas prohibidas de una sala."""
    from . import rooms
    cfg = rooms.ROOMS[rooms.normalize(room)]
    return {
        "arena_sets": cfg["arena_sets"],
        "newest_set": cfg["newest_set"],
        "banned": set(BANNED_NAMES_BASE) | set(cfg["extra_bans"]),
    }

# Las 9 cartas exclusivas de Arena del parche 10.4 se añadieron "por tiempo limitado".
# No hemos encontrado confirmación de que siguieran en la 11.0, así que por defecto NO entran.
INCLUDE_ARENA_EXCLUSIVES = False

# Probabilidad de rareza en una recogida normal. APROXIMADO (Blizzard no publicó cifras).
RARITY_WEIGHTS = {
    Rarity.COMMON: 0.78,
    Rarity.RARE: 0.17,
    Rarity.EPIC: 0.04,
    Rarity.LEGENDARY: 0.01,
}
# Recogidas con rareza rara o superior garantizada (numeradas desde 1)
GUARANTEED_RARE_PICKS = {1, 10, 20, 30}
GUARANTEED_RARITY_WEIGHTS = {
    Rarity.RARE: 0.80,
    Rarity.EPIC: 0.16,
    Rarity.LEGENDARY: 0.04,
}

# Peso de las cartas de clase frente a las neutrales. APROXIMADO.
CLASS_CARD_WEIGHT = 1.5

DECK_SIZE = 30
MAX_WINS = 12
MAX_LOSSES = 3
