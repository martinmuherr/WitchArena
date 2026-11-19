"""Comprueba que las cartas tienen los valores del parche 11.0 (abril 2018)."""
import app  # noqa: F401  (rutas del motor)
from app.cards import arena_pool, engine_db
from fireplace.game import Game
from fireplace.player import Player
from hearthstone.enums import CardClass, Race


def _game(hero1="HERO_07", hero2="HERO_03"):
    engine_db()
    deck = ["CS2_182"] * 30  # Yeti de invierno
    g = Game(players=[Player("A", list(deck), hero1), Player("B", list(deck), hero2)])
    g.start()
    for p in g.players:
        p.choice.choose()
    return g


def test_costes_y_stats_de_la_11_0():
    db = engine_db()
    assert db["EX1_620"].cost == 20      # Gigante fundido (vuelve a 20 en la 11.0)
    assert db["LOOT_539"].cost == 6      # Invocadora rencorosa (nerf a 7 en la 11.1)
    assert db["LOOT_306"].cost == 5      # Lacayo poseído
    assert db["LOOT_093"].cost == 4      # Llamada a las armas
    assert db["NEW1_012"].cost == 1      # Wyrm de maná
    assert db["CS2_073"].cost == 1       # Sangre fría
    assert db["EX1_619"].cost == 2       # Igualdad
    assert db["EX1_164"].cost == 5       # Nutrir
    assert db["ICC_221"].cost == 2       # Veneno sanguijuela
    assert Race.ELEMENTAL not in (db["EX1_105"].races or [])  # Gigante de montaña


def test_pacto_oscuro_cura_8():
    g = _game()
    p = g.player1
    p.hero.set_current_health(10)
    p.max_mana = 10
    p.discard_hand()
    minion = p.give("CS2_182").play()
    p.give("LOOT_017").play(target=minion)
    assert p.hero.health == 18


def test_preparacion_reduce_3():
    g = _game()
    p = g.player1
    p.max_mana = 10
    p.discard_hand()
    spell = p.give("CS2_032")  # Flamestrike (7)
    p.give("EX1_145").play()
    assert spell.cost == 4


def test_nucleo_de_cristal_5_5():
    g = _game()
    p = g.player1
    p.max_mana = 10
    p.discard_hand()
    p.give("UNG_067t1").play()
    minion = p.give("CS2_182").play()
    assert (minion.atk, minion.health) == (5, 5)


def test_portal_de_mana_6_hechizos():
    from fireplace.cards.ungoro.mage import UNG_028
    assert UNG_028.progress_total == 6


def test_pool_sin_salon_de_la_fama_ni_prohibidas():
    pool = arena_pool()
    ids = {cid for r in pool[CardClass.MAGE].values() for cid, _ in r}
    db = engine_db()
    names = {db[c].name for c in ids}
    assert "Ice Block" not in names        # Salón de la Fama en la 11.0
    assert "Frost Lich Jaina" not in names  # prohibida en Arena
    assert "Fireball" in names


def test_castigo_sagrado_2_a_cualquier_objetivo():
    g = _game()
    p = g.player1
    p.max_mana = 10
    p.discard_hand()
    hp = p.opponent.hero.health
    p.give("CS1_130").play(target=p.opponent.hero)
    assert p.opponent.hero.health == hp - 2


def test_palabra_de_poder_escudo_roba():
    g = _game()
    p = g.player1
    p.max_mana = 10
    p.discard_hand()
    minion = p.give("CS2_182").play()
    p.give("CS2_004").play(target=minion)
    assert minion.health == 7
    assert len(p.hand) == 1


def test_poderes_de_heroe_basicos_funcionan():
    # En la 11.0 los poderes se llamaban CS2_083b, CS2_034...; Fireplace usa HERO_03bp...
    g = _game(hero1="HERO_03")
    p = g.player1
    p.max_mana = 10
    p.hero.power.use()
    assert p.weapon is not None and p.weapon.atk == 1 and p.weapon.durability == 2
    assert p.hero.can_attack()
    p.hero.attack(p.opponent.hero)
    assert p.opponent.hero.health == 29
    assert p.weapon.durability == 1


def test_arma_de_carta_permite_atacar():
    g = _game(hero1="HERO_01")
    p = g.player1
    p.max_mana = 10
    p.discard_hand()
    p.give("CS2_106").play()  # Hacha de guerra ígnea 3/2
    assert p.hero.can_attack()
    p.hero.attack(p.opponent.hero)
    assert p.opponent.hero.health == 27


def test_coleccionista_de_bibelots_crece_al_robar():
    g = _game(hero1="HERO_08")
    p = g.player1
    p.max_mana = 10
    p.discard_hand()
    curio = p.give("GIL_640").play()
    base = (curio.atk, curio.health)
    p.draw()
    assert (curio.atk, curio.health) == (base[0] + 1, base[1] + 1)
    assert all(not c.buffs for c in p.hand)


def test_heroes_basicos_no_salen_en_el_draft():
    from hearthstone.enums import CardType
    db = engine_db()
    ids = {cid for cls in arena_pool().values() for r in cls.values() for cid, _ in r}
    heroes = {db[c].name for c in ids if db[c].type == CardType.HERO}
    assert "Jaina Proudmoore" not in heroes and "Garrosh Hellscream" not in heroes
    assert "Hagatha the Witch" in heroes


def test_arugal_y_dorian_reaccionan_al_robar_esbirro():
    g = _game(hero1="HERO_08")
    p = g.player1
    p.max_mana = 20
    p.discard_hand()
    p.give("GIL_691").play()   # Archimago Arugal
    p.give("GIL_620").play()   # Maestro de muñecas Dorian
    field_before = len(p.field)
    p.draw()  # el mazo es de Yetis
    assert len(p.hand) == 2            # el Yeti + copia de Arugal
    assert len(p.field) == field_before + 1   # copia 1/1 de Dorian
