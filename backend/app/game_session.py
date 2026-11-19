"""Partida PvP sobre el motor Fireplace.

El servidor es la única autoridad: los clientes mandan intenciones
("juega la carta 34 sobre el objetivo 12") y aquí se validan contra el motor.
Cada jugador solo recibe la información que podría ver en el juego real.
"""
import logging
import time

from . import cards as C  # noqa: F401  (inicializa rutas del motor)
from fireplace.exceptions import GameOver, InvalidAction
from fireplace.game import Game
from fireplace.player import Player
from hearthstone.enums import CardType, PlayState, State, Zone

logging.getLogger("fireplace").setLevel(logging.WARNING)

TURN_SECONDS = 75
MULLIGAN_SECONDS = 45


class ActionError(Exception):
    pass


def _ids(entities):
    return [e.entity_id for e in entities]


class GameSession:
    def __init__(self, game_id, seats):
        """seats: lista de 2 dicts {user_id, username, hero, deck}"""
        self.id = game_id
        self.seats = seats
        players = [Player(s["username"], list(s["deck"]), s["hero"]) for s in seats]
        self.game = Game(players=players)
        self.players = players
        self.user_index = {s["user_id"]: i for i, s in enumerate(seats)}
        self.version = 0
        self.log = []
        self.winner_user_id = None
        self.finished = False
        self.finish_reason = None
        self.deadline = time.time() + MULLIGAN_SECONDS
        try:
            self.game.start()
        except GameOver:
            self._check_end()
        self._bump()

    # ------------------------------------------------------------------ util
    def _bump(self, text=None):
        self.version += 1
        if text:
            self.log.append(text)
            self.log = self.log[-30:]

    def player_of(self, user_id):
        if user_id not in self.user_index:
            raise ActionError("No juegas en esta partida")
        return self.players[self.user_index[user_id]]

    def _entity(self, eid):
        if eid is None:
            return None
        for e in self.game:
            if getattr(e, "entity_id", None) == eid:
                return e
        raise ActionError("Entidad desconocida")

    def in_mulligan(self):
        return any(p.choice is not None and self.game.turn == 0 for p in self.players)

    def _check_end(self):
        if self.game.state == State.COMPLETE and not self.finished:
            self.finished = True
            states = [p.playstate for p in self.players]
            if states[0] == PlayState.WON:
                self.winner_user_id = self.seats[0]["user_id"]
            elif states[1] == PlayState.WON:
                self.winner_user_id = self.seats[1]["user_id"]
            self.finish_reason = self.finish_reason or "normal"
        return self.finished

    def _run(self, fn):
        if self.finished:
            raise ActionError("La partida ha terminado")
        try:
            fn()
        except GameOver:
            pass
        except InvalidAction as e:
            raise ActionError("Acción no válida: %s" % e)
        except AssertionError:
            raise ActionError("Acción no válida")
        self._check_end()

    def _require_turn(self, player):
        if self.in_mulligan():
            raise ActionError("Aún se está haciendo el mulligan")
        if self.game.current_player is not player:
            raise ActionError("No es tu turno")
        if player.choice is not None:
            raise ActionError("Tienes que elegir una carta primero")

    # --------------------------------------------------------------- acciones
    def mulligan(self, user_id, entity_ids):
        p = self.player_of(user_id)
        if self.game.turn != 0 or p.choice is None:
            raise ActionError("No hay mulligan pendiente")
        chosen = [c for c in p.choice.cards if c.entity_id in set(entity_ids or [])]
        self._run(lambda: p.choice.choose(*chosen))
        if not self.in_mulligan():
            self.deadline = time.time() + TURN_SECONDS
        self._bump()

    def choose(self, user_id, entity_id):
        p = self.player_of(user_id)
        if p.choice is None or self.game.turn == 0:
            raise ActionError("No hay elección pendiente")
        card = next((c for c in p.choice.cards if c.entity_id == entity_id), None)
        if card is None:
            raise ActionError("Elección no válida")
        self._run(lambda: p.choice.choose(card))
        self._bump("%s elige una carta" % p.name)

    def play(self, user_id, entity_id, target=None, choose=None, position=None):
        p = self.player_of(user_id)
        self._require_turn(p)
        card = self._entity(entity_id)
        if card not in p.hand:
            raise ActionError("Esa carta no está en tu mano")
        tgt = self._entity(target) if target is not None else None
        ch = None
        if card.must_choose_one:
            ch = next((c for c in card.choose_cards if c.entity_id == choose), None)
            if ch is None:
                raise ActionError("Debes elegir una opción")
        if not card.is_playable():
            raise ActionError("No puedes jugar esa carta ahora")
        index = None
        if card.type == CardType.MINION and position is not None:
            index = max(0, min(int(position), len(p.field)))
        name = C.card_view(card.id)["name"]
        self._run(lambda: card.play(target=tgt, index=index, choose=ch))
        self._bump("%s juega %s" % (p.name, name))

    def attack(self, user_id, attacker_id, defender_id):
        p = self.player_of(user_id)
        self._require_turn(p)
        att = self._entity(attacker_id)
        dfn = self._entity(defender_id)
        if att not in p.characters:
            raise ActionError("Ese personaje no es tuyo")
        if not att.can_attack(dfn):
            raise ActionError("No puede atacar a ese objetivo")
        self._run(lambda: att.attack(dfn))
        self._bump("%s ataca" % p.name)

    def hero_power(self, user_id, target=None, choose=None):
        p = self.player_of(user_id)
        self._require_turn(p)
        power = p.hero.power
        if not power.is_usable():
            raise ActionError("No puedes usar el poder de héroe")
        tgt = self._entity(target) if target is not None else None
        ch = None
        if power.must_choose_one:
            ch = next((c for c in power.choose_cards if c.entity_id == choose), None)
            if ch is None:
                raise ActionError("Debes elegir una opción")
        self._run(lambda: power.use(target=tgt, choose=ch))
        self._bump("%s usa su poder de héroe" % p.name)

    def end_turn(self, user_id=None, forced=False):
        p = self.game.current_player
        if user_id is not None:
            p2 = self.player_of(user_id)
            self._require_turn(p2)
        if forced and p.choice is not None and self.game.turn > 0:
            # se acabó el tiempo con una elección abierta: elegimos la primera
            self._run(lambda: p.choice.choose(p.choice.cards[0]))
        if not self.finished:
            self._run(self.game.end_turn)
        self.deadline = time.time() + TURN_SECONDS
        self._bump("%s termina su turno%s" % (p.name, " (tiempo agotado)" if forced else ""))

    def concede(self, user_id):
        p = self.player_of(user_id)
        self.finish_reason = "concede"
        self._run(p.concede)
        self._bump("%s se rinde" % p.name)

    def tick(self):
        """Llamado periódicamente: aplica los límites de tiempo."""
        if self.finished or time.time() < self.deadline:
            return False
        if self.in_mulligan():
            for p in self.players:
                if p.choice is not None:
                    self._run(lambda p=p: p.choice.choose())
            self.deadline = time.time() + TURN_SECONDS
            self._bump("Mulligan por tiempo")
            return True
        self.end_turn(forced=True)
        return True

    # ------------------------------------------------------------ vista
    def _card(self, c, viewer, hidden=False):
        if hidden:
            return {"eid": c.entity_id, "hidden": True}
        v = C.card_view(c.id)
        v = dict(v)
        v["eid"] = c.entity_id
        if c.type in (CardType.MINION, CardType.HERO):
            v["atk"] = c.atk
            v["health"] = c.health
            v["max_health"] = c.max_health
            v["damage"] = c.damage
            v["armor"] = getattr(c, "armor", 0)
        if c.type == CardType.MINION and c.zone == Zone.PLAY:
            v["flags"] = [f for f in ("taunt", "divine_shield", "stealthed", "frozen", "windfury",
                                       "poisonous", "lifesteal", "rush", "charge", "silenced",
                                       "dormant", "cant_be_targeted_by_spells")
                          if getattr(c, f, False)]
        if c.type == CardType.WEAPON:
            v["atk"] = c.atk
            v["durability"] = c.durability
        if c.zone == Zone.HAND:
            v["cost"] = c.cost
        mine = c.controller is viewer
        my_turn = (self.game.current_player is viewer and viewer.choice is None
                   and not self.in_mulligan() and not self.finished)
        if mine and my_turn:
            try:
                if c.zone == Zone.HAND:
                    v["playable"] = bool(c.is_playable())
                    if v["playable"]:
                        if c.must_choose_one:
                            v["choose"] = [
                                dict(C.card_view(o.id), eid=o.entity_id,
                                     playable=bool(o.is_playable()),
                                     targets=_ids(o.targets) if o.requires_target() else None)
                                for o in c.choose_cards
                            ]
                        elif c.requires_target():
                            v["targets"] = _ids(c.targets)
                elif c.zone == Zone.PLAY and c.type in (CardType.MINION, CardType.HERO):
                    v["can_attack"] = bool(c.can_attack())
                    if v["can_attack"]:
                        v["attack_targets"] = _ids(c.attack_targets)
            except Exception:  # un fallo en una carta no debe romper la vista
                v["playable"] = False
        return v

    def _side(self, pl, viewer):
        own = pl is viewer
        hero = pl.hero
        power = hero.power
        power_v = dict(C.card_view(power.id), eid=power.entity_id, cost=power.cost)
        my_turn = (self.game.current_player is viewer and viewer.choice is None
                   and not self.in_mulligan() and not self.finished)
        if own and my_turn:
            try:
                power_v["usable"] = bool(power.is_usable())
                if power_v["usable"] and power.requires_target():
                    power_v["targets"] = _ids(power.play_targets)
            except Exception:
                power_v["usable"] = False
        return {
            "name": pl.name,
            "hero": self._card(hero, viewer),
            "power": power_v,
            "weapon": self._card(pl.weapon, viewer) if pl.weapon else None,
            "mana": pl.mana,
            "max_mana": pl.max_mana,
            "overloaded": pl.overloaded,
            "overload_locked": getattr(pl, "overload_locked", 0),
            "deck": len(pl.deck),
            "hand": [self._card(c, viewer, hidden=not own) for c in pl.hand],
            "field": [self._card(c, viewer) for c in pl.field],
            "secrets": [self._card(c, viewer, hidden=not own) for c in pl.secrets],
        }

    def view(self, user_id):
        me = self.player_of(user_id)
        opp = me.opponent
        choice = None
        if me.choice is not None:
            choice = {
                "type": "mulligan" if self.game.turn == 0 else "discover",
                "cards": [self._card(c, me) for c in me.choice.cards],
            }
        winner = None
        if self.finished:
            winner = ("tie" if self.winner_user_id is None
                      else ("me" if self.winner_user_id == user_id else "opponent"))
        return {
            "game_id": self.id,
            "version": self.version,
            "turn": self.game.turn,
            "my_turn": self.game.current_player is me and not self.in_mulligan(),
            "mulligan": self.in_mulligan(),
            "deadline": self.deadline,
            "now": time.time(),
            "me": self._side(me, me),
            "opponent": self._side(opp, me),
            "opponent_waiting_mulligan": opp.choice is not None and self.game.turn == 0,
            "choice": choice,
            "finished": self.finished,
            "winner": winner,
            "log": self.log[-10:],
        }
