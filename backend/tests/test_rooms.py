"""Sala de Kóbolds y Catacumbas (parche 10.0) y cambio entre salas."""
import app  # noqa: F401
from app import rooms
from app.cards import arena_pool, card_view, engine_db
from fireplace.game import Game
from fireplace.player import Player
from hearthstone.enums import CardSet, GameTag


def _game(room, hero1="HERO_09", hero2="HERO_03", singleton=False):
    db = engine_db(room)
    deck = ["CS2_182"] * 30
    if singleton:  # 30 cartas distintas (para Raza)
        deck = sorted(c for c, d in db.items() if d.collectible and d.card_set == CardSet.EXPERT1
                      and d.type.name == "MINION" and d.cost <= 4)[:30]
    g = Game(players=[Player("A", list(deck), hero1), Player("B", list(deck), hero2)])
    g.start()
    for p in g.players:
        p.choice.choose()
    return g


def _pool_ids(room):
    return {cid for cls in arena_pool(room).values() for r in cls.values() for cid, _ in r}


def test_valores_de_la_10_0():
    db = engine_db("kobolds")
    assert db["LOOT_149"].atk == 5          # Reptador del pasillo antes del nerf
    assert db["ICC_705"].cost == 7          # Yegua ósea
    assert db["LOOT_306"].cost == 5
    assert db["EX1_620"].cost == 25         # Gigante fundido a 25 en la 10.0
    assert db["CFM_637"].tags.get(GameTag.CHARGE)  # Parches con Carga
    assert db["EX1_620"].card_set == CardSet.EXPERT1  # aún no está en el Salón de la Fama


def test_pool_de_kobolds():
    ids = _pool_ids("kobolds")
    db = engine_db("kobolds")
    sets = {db[c].card_set for c in ids}
    assert CardSet.OG in sets and CardSet.KARA in sets and CardSet.GANGS in sets
    assert CardSet.GILNEAS not in sets
    names = {db[c].name for c in ids}
    assert "Humongous Razorleaf" in names     # se prohibió después, en la 11.0
    assert "Vicious Fledgling" not in names
    assert "Coldlight Oracle" in names        # antes del Salón de la Fama


def test_pool_de_witchwood_no_cambia():
    _pool_ids("kobolds")
    ids = _pool_ids("witchwood")
    db = engine_db("witchwood")
    sets = {db[c].card_set for c in ids}
    assert CardSet.GILNEAS in sets and CardSet.OG not in sets
    assert "Humongous Razorleaf" not in {db[c].name for c in ids}
    assert db["LOOT_149"].atk == 2


def test_raza_poder_gratis_en_kobolds():
    for room, cost in (("kobolds", 0), ("witchwood", 1)):
        g = _game(room, singleton=True)
        p = g.player1
        p.max_mana = 10
        p.discard_hand()
        p.give("CFM_020").play()
        assert p.hero.power.cost == cost, room


def test_cambiar_de_sala_mantiene_cada_coleccion():
    rooms.activate("kobolds")
    assert card_view("LOOT_149")["atk"] == 5
    rooms.activate("witchwood")
    assert card_view("LOOT_149")["atk"] == 2
    rooms.activate("kobolds")
    assert "GIL_692" not in engine_db()
