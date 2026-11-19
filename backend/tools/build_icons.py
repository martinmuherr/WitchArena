"""Asigna a cada carta un icono de game-icons.net (licencia CC BY 3.0, sin arte de Blizzard).

Busca palabras del nombre inglés de la carta en los nombres de los iconos, con un
diccionario de sinónimos para criaturas propias de Warcraft. Si no encuentra nada,
usa la raza, la clase o el tipo de carta.

Uso: python build_icons.py <carpeta_game-icons> <salida_iconos_svg> <salida_json>
"""
import json
import os
import re
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))

import app  # noqa: E402,F401
from app import arena_rules as R  # noqa: E402
from app.cards import engine_db  # noqa: E402
from hearthstone.enums import CardClass, CardType, Race  # noqa: E402

STOP = {"the", "of", "a", "an", "and", "in", "to", "on", "for", "with", "from", "by", "s", "at"}

# Palabras de Warcraft -> palabra que sí existe en game-icons
SYN = {
    "murloc": "fish-monster", "kobold": "goblin-head", "ghoul": "shambling-zombie", "geist": "ghost",
    "worgen": "werewolf", "wolfrider": "wolf-head", "imp": "imp", "ooze": "slime", "oozeling": "slime",
    "gnoll": "hyena-head", "troll": "troll", "ogre": "ogre", "elemental": "fire-silhouette",
    "naga": "snake", "raptor": "dinosaur-rex", "dinosaur": "dinosaur-rex", "devilsaur": "dinosaur-rex",
    "stegodon": "triceratops-head", "direhorn": "triceratops-head", "pterrordax": "pterodactylus",
    "lich": "lich", "necromancer": "necromancer", "ghost": "ghost", "spirit": "spectre",
    "wisp": "will-o-the-wisp", "treant": "tree-face", "ancient": "tree-face", "dryad": "dryad",
    "faerie": "fairy", "fairy": "fairy", "pixie": "fairy", "sprite": "fairy", "drake": "dragon-head",
    "whelp": "baby-face", "wyrm": "dragon-head", "dragonhawk": "griffin-symbol", "gryphon": "griffin-symbol",
    "harpy": "harpy", "yeti": "yeti", "abomination": "frankenstein-creature", "golem": "robot-golem",
    "mech": "robot-golem", "bot": "robot-golem", "gnome": "dwarf-face", "dwarf": "dwarf-face",
    "goblin": "goblin-head", "pirate": "pirate-captain", "corsair": "pirate-captain", "buccaneer": "pirate-captain",
    "parrot": "parrot-head", "deckhand": "pirate-captain", "shark": "shark-jaws", "kraken": "kraken-tentacle",
    "crab": "crab", "turtle": "turtle", "tortollan": "turtle", "lizard": "lizard-tongue",
    "bat": "bat", "boar": "boar", "raven": "raven", "crow": "raven", "owl": "owl", "hawk": "eagle-head",
    "eagle": "eagle-head", "hound": "hound", "hyena": "hyena-head", "panther": "panther", "tiger": "tiger-head",
    "lion": "lion", "bear": "bear-head", "grizzly": "bear-head", "spider": "spider-alt", "scorpid": "scorpion",
    "gorilla": "gorilla", "ape": "gorilla", "rat": "rat", "frog": "frog", "toad": "frog", "snake": "snake",
    "serpent": "sea-serpent", "fish": "fish", "squid": "squid-head", "felhound": "hound", "infernal": "flaming-claw",
    "demon": "devil-mask", "succubus": "devil-mask", "voidwalker": "spectre", "doomguard": "horned-reptile",
    "felguard": "horned-helm", "skeleton": "skeleton", "bone": "bone-gnawer", "zombie": "shambling-zombie",
    "vampire": "vampire-dracula", "witch": "witch-face", "hag": "witch-face", "scarecrow": "scarecrow",
    "pumpkin": "pumpkin-lantern", "gnome": "dwarf-face", "knight": "black-knight-helm", "paladin": "knight-banner",
    "priest": "sun-priest", "priestess": "sun-priest", "mage": "wizard-face", "magus": "wizard-face",
    "sorcerer": "wizard-face", "shaman": "totem-head", "druid": "oak-leaf", "hunter": "bow-arrow",
    "rogue": "hooded-assassin", "assassin": "hooded-assassin", "warrior": "barbarian", "berserker": "barbarian",
    "warlock": "warlock-hood", "cultist": "cultist", "acolyte": "hood", "monk": "monk-face",
    "champion": "crowned-heart", "king": "crown", "queen": "queen-crown", "prince": "crown", "lord": "crown",
    "giant": "giant", "mountain": "mountain-cave", "sea": "wave-crest", "tidecaller": "wave-crest",
    "totem": "totem", "fireball": "fireball", "fire": "fire", "flame": "fire", "frost": "ice-bolt",
    "ice": "ice-cube", "frozen": "ice-cube", "lightning": "lightning-helix", "storm": "lightning-storm",
    "thunder": "lightning-storm", "shadow": "shadow-follower", "holy": "holy-symbol", "light": "sun",
    "heal": "healing", "healing": "healing", "arcane": "magic-swirl", "missiles": "missile-swarm",
    "polymorph": "sheep", "sheep": "sheep", "potion": "potion-ball", "elixir": "potion-ball",
    "poison": "poison-bottle", "venom": "poison-bottle", "blade": "broadsword", "sword": "broadsword",
    "axe": "battle-axe", "hammer": "war-axe", "mace": "flanged-mace", "dagger": "daggers", "knife": "bone-knife",
    "shield": "shield", "armor": "breastplate", "bow": "bow-arrow", "arrow": "arrow-flights", "shot": "arrow-flights",
    "trap": "wolf-trap", "secret": "secret-door", "book": "spell-book", "tome": "spell-book", "scroll": "scroll-unfurled",
    "coin": "coins", "gold": "coins", "treasure": "chest", "chest": "chest", "candle": "candle-light",
    "egg": "dragon-egg" , "seed": "sprout", "tree": "tree-face", "grove": "tree-face", "root": "roots",
    "wrath": "lightning-bolts", "star": "star-swirl", "moon": "moon", "sun": "sun", "mana": "crystal-ball",
    "crystal": "crystal-growth", "gem": "gem-pendant", "plague": "biohazard", "blood": "blood", "rage": "enrage",
    "charge": "charging-bull", "cleave": "battle-axe", "whirlwind": "whirlwind", "execute": "executioner-hood",
    "silence": "silenced", "mind": "brain", "soul": "soul-vessel", "death": "death-skull", "doom": "death-skull",
    "curse": "cursed-star", "hex": "frog", "bolt": "lightning-bolts", "nova": "explosion-rays",
    "explosion": "explosion-rays", "bomb": "bomb", "volcano": "volcano", "lava": "lava", "rock": "rock",
    "stone": "rock", "earth": "rock", "wind": "whirlwind", "water": "water-drop", "wave": "wave-crest",
    "hand": "open-palm", "eye": "eye-target", "heart": "heart-organ", "tooth": "fangs", "claw": "claws",
    "fang": "fangs", "mark": "target-arrows", "hunter's": "bow-arrow", "kill": "skull-crack",
    "assassinate": "skull-crack", "backstab": "backstab", "sap": "pocket-bow", "sprint": "sprint",
    "vanish": "invisible", "shiv": "bone-knife", "eviscerate": "bloody-sword", "preparation": "hourglass",
    "time": "hourglass", "clock": "hourglass", "portal": "portal", "gate": "portal", "waygate": "portal",
    "banner": "knight-banner", "recruit": "swordman", "soldier": "swordman", "guard": "swordman",
    "guardian": "swordman", "footman": "swordman", "militia": "swordman", "squire": "swordman",
    "captain": "visored-helm", "commander": "visored-helm", "general": "visored-helm", "sergeant": "visored-helm",
    "chef": "chef-toque", "cook": "chef-toque", "baker": "chef-toque", "tavern": "beer-stein",
    "brewer": "beer-stein", "brewmaster": "beer-stein", "musician": "lyre", "bard": "lyre", "piper": "pan-flute",
    "doctor": "doctor-face", "apothecary": "potion-ball", "alchemist": "potion-ball", "inventor": "gears",
    "engineer": "gears", "tinker": "gears", "mechanic": "gears", "sapper": "bomb", "miner": "mining",
    "spelunker": "mining", "explorer": "compass", "ranger": "bow-arrow", "tracker": "footprint",
    "scout": "spyglass", "spy": "spyglass", "thief": "hooded-assassin", "bandit": "bandit",
    "smuggler": "bandit", "thug": "brass-knuckles", "brute": "brass-knuckles", "bully": "brass-knuckles",
    "executioner": "executioner-hood", "jailer": "prisoner", "prisoner": "prisoner", "cage": "prisoner",
    "monster": "monster-grasp", "beast": "paw", "creature": "monster-grasp", "horror": "tentacles-skull",
    "tentacle": "tentacles-skull", "faceless": "hood", "old": "elf-helmet", "elf": "elf-ear",
    "elven": "elf-ear", "druidess": "oak-leaf", "keeper": "oak-leaf", "naturalist": "oak-leaf",
}

RACE_ICON = {
    Race.BEAST: "paw", Race.DEMON: "devil-mask", Race.DRAGON: "dragon-head", Race.ELEMENTAL: "fire-silhouette",
    Race.MECHANICAL: "robot-golem", Race.MURLOC: "fish-monster", Race.PIRATE: "pirate-captain", Race.TOTEM: "totem",
}
CLASS_ICON = {
    CardClass.DRUID: "oak-leaf", CardClass.HUNTER: "bow-arrow", CardClass.MAGE: "wizard-face",
    CardClass.PALADIN: "knight-banner", CardClass.PRIEST: "sun-priest", CardClass.ROGUE: "hooded-assassin",
    CardClass.SHAMAN: "totem-head", CardClass.WARLOCK: "warlock-hood", CardClass.WARRIOR: "barbarian",
    CardClass.NEUTRAL: "person",
}
CLASS_COLOR = {
    CardClass.DRUID: "#e0b77a", CardClass.HUNTER: "#9fdc7a", CardClass.MAGE: "#8fc6ff",
    CardClass.PALADIN: "#f3dc7c", CardClass.PRIEST: "#f1f1f1", CardClass.ROGUE: "#c9c9c9",
    CardClass.SHAMAN: "#7fb0ff", CardClass.WARLOCK: "#d29cff", CardClass.WARRIOR: "#ff9a8a",
    CardClass.NEUTRAL: "#e8d9b0",
}
TYPE_ICON = {CardType.SPELL: "magic-swirl", CardType.WEAPON: "broadsword", CardType.HERO_POWER: "sparkles"}


def index_icons(root):
    files = {}
    for dp, _, fns in os.walk(root):
        for fn in fns:
            if fn.endswith(".svg"):
                files.setdefault(fn[:-4], os.path.join(dp, fn))
    by_token = defaultdict(list)
    for name in files:
        for t in name.split("-"):
            by_token[t].append(name)
    return files, by_token


def tokens(name):
    words = re.findall(r"[a-z']+", name.lower().replace("’", "'"))
    out = []
    for w in words:
        w = w.strip("'")
        if w.endswith("'s"):
            w = w[:-2]
        if w and w not in STOP:
            out.append(w)
    return out


TITLES = {"king", "queen", "prince", "lord", "captain", "commander", "general", "sergeant", "champion",
          "guard", "guardian", "keeper", "old", "mark", "light", "shadow", "holy", "blood", "time"}
SYN.update({"technician": "gears", "informant": "spyglass", "gravedigger": "spade", "weed": "vine-flower",
            "flower": "vine-flower", "bloom": "vine-flower", "vine": "vine-flower", "grunt": "orc-head",
            "orc": "orc-head", "tauren": "bull-horns", "minstrel": "lyre", "stablemaster": "horse-head",
            "horse": "horse-head", "charger": "horse-head", "steed": "horse-head", "mastiff": "hound",
            "dog": "hound", "jenkins": "chicken", "chicken": "chicken", "dragon": "dragon-head",
            "deathwing": "dragon-head", "bruiser": "brass-knuckles", "banshee": "spectre",
            "val'kyr": "angel-wings", "valkyr": "angel-wings", "angel": "angel-wings", "countess": "vampire-dracula",
            "gadgeteer": "gears", "adventurer": "compass", "fledgling": "raven", "peddler": "swap-bag"})


def pick(card, files, by_token):
    words = tokens(card.name)
    syn = lambda w: SYN.get(w) or (SYN.get(w[:-1]) if w.endswith("s") else None)
    # 1) sinónimos de criaturas/objetos (del final al principio: el sustantivo suele ir al final)
    for w in reversed(words):
        if w not in TITLES and syn(w) in files:
            return syn(w)
    # 1b) palabras compuestas (Frostwolf, Volcanosaur, Deathlord...)
    for w in reversed(words):
        subs = sorted((k for k in SYN if len(k) >= 4 and k in w and k != w and k not in TITLES),
                      key=len, reverse=True)
        for k in subs:
            if SYN[k] in files:
                return SYN[k]
    # 1c) títulos
    for w in reversed(words):
        if syn(w) in files:
            return syn(w)
    # 2) coincidencia directa con nombres de iconos
    best, score = None, 0
    for i, w in enumerate(words):
        weight = 2 if i == len(words) - 1 else 1
        for cand in {w, w[:-1] if w.endswith("s") and len(w) > 3 else w}:
            for name in by_token.get(cand, []):
                parts = name.split("-")
                s = weight * 10 - len(parts) + sum(3 for x in words if x in parts)
                if s > score:
                    best, score = name, s
    if best:
        return best
    # 3) raza, tipo, clase
    for r in getattr(card, "races", None) or []:
        if r in RACE_ICON:
            return RACE_ICON[r]
    if card.type in TYPE_ICON:
        return TYPE_ICON[card.type]
    return CLASS_ICON.get(card.card_class, "person")


def recolor(svg, color):
    svg = svg.replace('<path d="M0 0h512v512H0z"/>', "")
    return svg.replace('fill="#fff"', 'fill="%s"' % color)


def main():
    src, out_dir, out_json = sys.argv[1:4]
    files, by_token = index_icons(src)
    os.makedirs(out_dir, exist_ok=True)
    db = engine_db()
    mapping, used = {}, {}
    for cid, c in db.items():
        if c.type not in (CardType.MINION, CardType.SPELL, CardType.WEAPON, CardType.HERO, CardType.HERO_POWER):
            continue
        if c.type == CardType.HERO and c.id in R.CLASSES.values():
            icon = CLASS_ICON[c.card_class]
        else:
            icon = pick(c, files, by_token)
        if icon not in files:
            icon = "person"
        mapping[cid] = icon
        used[icon] = True
    # Un archivo por icono; el color se pone en CSS (mask-image), según la clase.
    for icon in used:
        with open(files[icon], encoding="utf-8") as f:
            svg = recolor(f.read(), "#000")
        with open(os.path.join(out_dir, icon + ".svg"), "w", encoding="utf-8") as f:
            f.write(svg)
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(mapping, f, separators=(",", ":"))
    pool = {cid for cls in __import__("app.cards", fromlist=["x"]).arena_pool().values()
            for r in cls.values() for cid, _ in r}
    generic = set(CLASS_ICON.values()) | set(TYPE_ICON.values()) | set(RACE_ICON.values())
    fallback = sum(1 for c in pool if mapping.get(c) in generic)
    print("cartas con icono:", len(mapping), "| iconos distintos:", len(used),
          "| cartas draftables con icono genérico:", fallback, "de", len(pool))


if __name__ == "__main__":
    main()
