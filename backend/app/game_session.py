"""Partida PvP sobre el motor Fireplace.

El servidor es la única autoridad: los clientes mandan intenciones
("juega la carta 34 sobre el objetivo 12") y aquí se validan contra el motor.
Cada jugador solo recibe la información que podría ver en el juego real.
"""
import functools
import logging
import time

from . import cards as C  # noqa: F401  (inicializa rutas del motor)
from . import rooms
from fireplace.exceptions import GameOver, InvalidAction
from fireplace.game import Game
from fireplace.player import Player
from hearthstone.enums import CardType, GameTag, PlayState, State, Zone

logging.getLogger("fireplace").setLevel(logging.WARNING)

TURN_SECONDS = 75
MULLIGAN_SECONDS = 45


class ActionError(Exception):
    pass


def _ids(entities):
    return [e.entity_id for e in entities]


def _in_room(fn):
    """Antes de tocar el motor, carga las cartas de la sala de esta partida."""
    @functools.wraps(fn)
    def wrapper(self, *a, **kw):
        rooms.activate(self.room)
        return fn(self, *a, **kw)
    return wrapper


TYPE_KIND = {CardType.MINION: "minion", CardType.SPELL: "spell", CardType.WEAPON: "weapon",
             CardType.HERO: "hero"}


class _Tracer:
    """Observador del motor: anota quién hace qué (daño, curación, invocaciones, hechizos
    lanzados por esbirros...) para poder animarlo y escribirlo en el registro."""

    WATCH = {"Damage", "Heal", "Destroy", "Summon", "CastSpell", "Buff", "SetTags", "Deathrattle"}

    def game_action(self, action, source, *args):
        if type(action).__name__ == "Death" and args:
            self.entries.append(("Death", None, args[0], ()))

    def __init__(self):
        self.entries = []

    def targeted_action(self, action, source, target, *args):
        name = type(action).__name__
        if name not in self.WATCH:
            return
        if name == "SetTags":
            tags = args[0] if args else ()
            if GameTag.FROZEN not in (tags if not isinstance(tags, dict) else tags.keys()):
                return
            name = "Freeze"
        self.entries.append((name, source, target, args))

    def __getattr__(self, name):  # el resto de avisos del motor no nos interesan
        return lambda *a, **k: None


MAX_CHAT = 200
LOG_KEEP = 120


class GameSession:
    def __init__(self, game_id, seats, room=None):
        """seats: lista de 2 dicts {user_id, username, hero, deck}"""
        self.id = game_id
        self.room = rooms.normalize(room)
        rooms.activate(self.room)
        self.seats = seats
        players = [Player(s["username"], list(s["deck"]), s["hero"]) for s in seats]
        self.game = Game(players=players)
        self.players = players
        self.user_index = {s["user_id"]: i for i, s in enumerate(seats)}
        self.version = 0
        self.log = []          # cada entrada: lista de trozos {"t": texto} o {"card": vista}
        self.last_attack = None  # {"seq", "attacker", "defender"} para animar el ataque
        self._attack_seq = 0
        self.last_effect = None  # hechizo/poder/grito de batalla: a quién afectó (para animarlo)
        self.events = []         # robos, secretos, muertes, invocaciones... para animarlos en orden
        self._event_seq = 0
        self.winner_user_id = None
        self.finished = False
        self.finish_reason = None
        self.deadline = time.time() + MULLIGAN_SECONDS
        self.chat = []           # mensajes entre los dos jugadores
        self._chat_seq = 0
        self._last_said = {}
        self._tracer = _Tracer()
        self.game.manager.register(self._tracer)
        try:
            self.game.start()
        except GameOver:
            self._check_end()
        self._bump()

    # ------------------------------------------------------------------ util
    def _bump(self, text=None):
        self.version += 1
        if text:
            if isinstance(text, str):
                text = [{"t": text}]
            self.log.append(text)
            self.log = self.log[-LOG_KEEP:]

    @staticmethod
    def _ref(entity):
        """Trozo de log que enlaza a una carta (para el hover)."""
        return {"card": C.card_view(entity.id)}

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
        self._tracer.entries = []
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
        board = self._board()
        self._run(lambda: p.choice.choose(card))
        self._bump("%s elige una carta" % p.name)
        animated = self._trace_events()
        self._board_events(board, skip_hits=animated)

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
        entry = [{"t": "%s juega " % p.name}, self._ref(card)]
        if tgt is not None:
            entry += [{"t": " sobre "}, self._ref(tgt)]
        before = self._snapshot()
        board = self._board()
        source = card.entity_id if card.type == CardType.MINION else p.hero.entity_id
        cid = card.id
        # todas las cartas jugadas se muestran un momento en pantalla (las de secreto, ocultas al rival)
        self._event({"type": "cast", "player": self.players.index(p), "card": C.card_view(cid),
                     "kind": TYPE_KIND.get(card.type, "spell"),
                     "secret": bool(getattr(card, "secret", False)), "eid": card.entity_id,
                     "target": tgt.entity_id if tgt is not None else None})
        self._run(lambda: card.play(target=tgt, index=index, choose=ch))
        self._record_effect(before, source, cid, tgt)
        self._bump(entry)
        animated = self._trace_events(primary={card.entity_id, p.entity_id, p.hero.entity_id})
        self._board_events(board, played=card.entity_id, skip_hits=animated)

    def attack(self, user_id, attacker_id, defender_id):
        p = self.player_of(user_id)
        self._require_turn(p)
        att = self._entity(attacker_id)
        dfn = self._entity(defender_id)
        if att not in p.characters:
            raise ActionError("Ese personaje no es tuyo")
        if not att.can_attack(dfn):
            raise ActionError("No puede atacar a ese objetivo")
        entry = [{"t": "%s: " % p.name}, self._ref(att), {"t": " ataca a "}, self._ref(dfn)]
        self._attack_seq += 1
        self.last_attack = {"seq": self._attack_seq, "attacker": att.entity_id, "defender": dfn.entity_id}
        board = self._board()
        before = self._snapshot()
        self._run(lambda: att.attack(dfn))
        self._bump(entry)
        animated = self._trace_events(combat={att.entity_id, dfn.entity_id})
        self._board_events(board, skip_hits={att.entity_id, dfn.entity_id} | animated, before=before)

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
        entry = [{"t": "%s usa " % p.name}, self._ref(power)]
        if tgt is not None:
            entry += [{"t": " sobre "}, self._ref(tgt)]
        before = self._snapshot()
        board = self._board()
        self._run(lambda: power.use(target=tgt, choose=ch))
        self._record_effect(before, power.entity_id, power.id, tgt, is_power=True)
        self._bump(entry)
        animated = self._trace_events(primary={power.entity_id, p.entity_id, p.hero.entity_id})
        self._board_events(board, skip_hits=animated)

    # ------------------------------------------------------------ efectos visuales
    def _snapshot(self):
        snap = {}
        for pl in self.players:
            for ch in [pl.hero] + list(pl.field):
                snap[ch.entity_id] = (ch.health + getattr(ch, "armor", 0), ch.atk, ch.max_health)
        return snap

    def _record_effect(self, before, source_eid, card_id, target, is_power=False):
        after = self._snapshot()
        hits = []
        for eid, (hp, atk, mx) in before.items():
            if eid == source_eid and not is_power:
                continue
            now = after.get(eid)
            if now is None:  # murió
                hits.append({"eid": eid, "kind": "damage", "amount": hp, "died": True})
                continue
            if now[0] < hp:
                hits.append({"eid": eid, "kind": "damage", "amount": hp - now[0]})
            elif now[0] > hp and now[2] == mx:
                hits.append({"eid": eid, "kind": "heal", "amount": now[0] - hp})
            elif now[1] != atk or now[2] != mx:
                hits.append({"eid": eid, "kind": "buff", "amount": None})
        if target is not None and not any(h["eid"] == target.entity_id for h in hits):
            hits.append({"eid": target.entity_id, "kind": "touch", "amount": None})
        if not hits and is_power:
            # poderes sin objetivo (Blindaje, Llamada totémica...): brillo en el propio poder
            hits.append({"eid": source_eid, "kind": "self", "amount": None})
        if not hits:
            return
        v = C.card_view(card_id)
        self._effect_seq = getattr(self, "_effect_seq", 0) + 1
        self.last_effect = {"seq": self._effect_seq, "source": source_eid, "hits": hits[:10],
                            "icon": v.get("icon"), "class_key": v.get("class_key"), "power": is_power}

    # ------------------------------------------------------- eventos para animar
    def _event(self, ev):
        self._event_seq += 1
        ev["seq"] = self._event_seq
        self.events.append(ev)
        self.events = self.events[-40:]

    def _board(self):
        st = []
        for pl in self.players:
            st.append({
                "hand": [c.entity_id for c in pl.hand],
                "deck": len(pl.deck),
                "field": [(m.entity_id, m.id) for m in pl.field],
                "secrets": [(sc.entity_id, sc.id) for sc in pl.secrets],
                "hero": (pl.hero.entity_id, pl.hero.id),
            })
        return st

    @staticmethod
    def _has_deathrattle(card_id):
        from hearthstone.enums import GameTag
        card = C.engine_db().get(card_id)
        return bool(card is not None and card.tags.get(GameTag.DEATHRATTLE))

    def _find(self, eid):
        for e in self.game:
            if getattr(e, "entity_id", None) == eid:
                return e
        return None

    def _board_events(self, before_board, played=None, skip_hits=None, before=None):
        after = self._board()
        dying_with_dr = None
        for i, (b, a) in enumerate(zip(before_board, after)):
            # cambio de héroe (cartas de héroe, Lord Jaraxxus, Majordomo...)
            if b.get("hero") and a["hero"][0] != b["hero"][0]:
                old_v, new_v = C.card_view(b["hero"][1]), C.card_view(a["hero"][1])
                self._event({"type": "hero_change", "player": i, "eid": a["hero"][0],
                             "old": old_v, "card": new_v})
                self.log.append([{"t": "Nuevo héroe: "}, {"card": new_v}])
            # robos (del mazo) y cartas que llegan a la mano por otros medios
            new = [e for e in a["hand"] if e not in b["hand"]]
            drawn = max(0, b["deck"] - a["deck"])
            if new:
                self._event({"type": "draw", "player": i, "eids": new[:drawn] if drawn else [],
                             "gained": new[drawn:] if drawn else new})
            # secretos que saltan
            gone = [(e, cid) for e, cid in b["secrets"] if e not in [x for x, _ in a["secrets"]]]
            for e, cid in gone:
                v = C.card_view(cid)
                self._event({"type": "secret", "player": i, "card": v})
                self.log.append([{"t": "¡Secreto! "}, {"card": v}, {"t": " se activa"}])
            # muertes y esbirros que dejan la mesa
            after_ids = [e for e, _ in a["field"]]
            for e, cid in b["field"]:
                if e in after_ids:
                    continue
                ent = self._find(e)
                died = ent is not None and ent.zone == Zone.GRAVEYARD
                v = C.card_view(cid)
                dr = bool(died and self._has_deathrattle(cid))
                self._event({"type": "death" if died else "leave", "player": i, "eid": e, "card": v,
                             "deathrattle": dr})
                if dr:
                    dying_with_dr = dying_with_dr or e
            # invocaciones que no son la carta jugada
            before_ids = [e for e, _ in b["field"]]
            for e, cid in a["field"]:
                if e not in before_ids and e != played:
                    self._event({"type": "summon", "player": i, "eid": e, "card": C.card_view(cid)})
        # daño/curación causados por efectos (Últimos alientos, secretos, efectos de fin de turno...)
        if before is not None:
            now = self._snapshot()
            hits = []
            for eid, (hp, atk, mx) in before.items():
                if skip_hits and eid in skip_hits:
                    continue
                cur = now.get(eid)
                if cur is None:
                    continue
                if cur[0] < hp:
                    hits.append({"eid": eid, "kind": "damage", "amount": hp - cur[0]})
                elif cur[0] > hp and cur[2] == mx:
                    hits.append({"eid": eid, "kind": "heal", "amount": cur[0] - hp})
            if hits:
                self._event({"type": "hits", "source": dying_with_dr, "hits": hits[:10]})
        self.log = self.log[-LOG_KEEP:]

    # --------------------------------------------- efectos encadenados (registro y animación)
    @staticmethod
    def _is_card(e):
        return e is not None and getattr(e, "id", None) and hasattr(e, "zone")

    def _trace_events(self, primary=None, combat=None):
        """Convierte lo que anotó el motor en líneas del registro y animaciones.
        primary: entidades que hizo el jugador (su carta/poder): se registran pero ya se animan
        con last_effect. combat: atacante y defensor (el daño del combate ya se ve)."""
        primary = primary or set()
        combat = combat or set()
        entries, self._tracer.entries = self._tracer.entries, []
        groups = []  # [(kind, source, amount_or_card, [targets])]
        for name, src, tgt, args in entries:
            if name in ("Death", "Deathrattle"):
                if self._is_card(tgt) and tgt.type == CardType.MINION:
                    groups.append([(name, getattr(tgt, "entity_id", None), None), None, tgt, []])
                continue
            if src is None:
                continue
            # el daño que hace un jugador (p. ej. curación invertida) se atribuye a su héroe
            if not self._is_card(src) and getattr(src, "hero", None) is not None:
                src = src.hero
            if not self._is_card(src):
                continue
            if name == "Damage":
                amount = args[0] if args else 0
                if not amount:
                    continue
                if src.entity_id in combat and getattr(tgt, "entity_id", None) in combat:
                    continue
                key = ("damage", src.entity_id, amount)
            elif name == "Heal":
                amount = args[0] if args else 0
                if not amount:
                    continue
                key = ("heal", src.entity_id, amount)
            elif name == "Destroy":
                key = ("destroy", src.entity_id, None)
            elif name == "Summon":
                card = args[0] if args else None
                if not self._is_card(card) or getattr(card, "zone", None) != Zone.PLAY:
                    continue
                if src.entity_id in primary and card.entity_id in primary:
                    continue
                key = ("summon", src.entity_id, None)
                tgt = card
            elif name == "CastSpell":
                spell = tgt
                tgt = args[0] if args else None
                if not self._is_card(spell):
                    continue
                key = ("cast", src.entity_id, spell.id)
                groups.append([key, src, spell, [tgt] if self._is_card(tgt) else []])
                continue
            elif name in ("Buff", "Freeze"):
                if not self._is_card(tgt) or tgt.zone != Zone.PLAY or tgt.type not in (
                        CardType.MINION, CardType.HERO):
                    continue
                if src is tgt or src.entity_id in primary:
                    continue
                key = ("freeze" if name == "Freeze" else "buff", src.entity_id, None)
            else:
                continue
            if not self._is_card(tgt):
                continue
            if groups and groups[-1][0] == key:
                if all(t is not tgt for t in groups[-1][3]):
                    groups[-1][3].append(tgt)
            else:
                groups.append([key, src, None, [tgt]])

        animated = set()
        verbs = {"damage": " inflige %s p. de daño a ", "heal": " restaura %s p. de salud a ",
                 "destroy": " destruye a ", "summon": " invoca a ", "buff": " mejora a ",
                 "freeze": " congela a "}
        for (kind, src_eid, amount), src, extra, targets in groups[:24]:
            if kind == "Death":
                self.log.append([self._ref(extra), {"t": " muere"}])
                continue
            if kind == "Deathrattle":
                self.log.append([{"t": "Último aliento: "}, self._ref(extra)])
                continue
            src_ref = self._ref(src)
            if kind == "cast":
                v = C.card_view(extra.id)
                line = [src_ref, {"t": " lanza "}, {"card": v}]
                if targets:
                    line += [{"t": " sobre "}, self._ref(targets[0])]
                self.log.append(line)
                self._event({"type": "cast", "player": self.players.index(src.controller),
                             "card": v, "kind": "spell", "secret": False, "eid": extra.entity_id,
                             "by": C.card_view(src.id)["name"], "source": src_eid})
                continue
            line = [src_ref, {"t": verbs[kind] % amount if "%s" in verbs[kind] else verbs[kind]}]
            for i, t in enumerate(targets[:8]):
                if i:
                    line.append({"t": ", "})
                line.append(self._ref(t))
            self.log.append(line)
            # animación: el origen brilla y lanza un efecto a cada objetivo
            if src_eid in primary or kind == "summon":
                continue
            hits = []
            for t in targets[:10]:
                hk = {"damage": "damage", "heal": "heal", "destroy": "damage",
                      "buff": "buff", "freeze": "freeze"}[kind]
                hits.append({"eid": t.entity_id, "kind": hk,
                             "amount": amount if kind in ("damage", "heal") else None})
                if kind in ("damage", "heal"):
                    animated.add(t.entity_id)
            sv = C.card_view(src.id)
            self._event({"type": "trigger", "source": src_eid, "hits": hits,
                         "icon": sv.get("icon"), "class_key": sv.get("class_key"),
                         "card": sv, "player": self.players.index(src.controller)})
        self.log = self.log[-LOG_KEEP:]
        return animated

    # ------------------------------------------------------------------ chat
    def say(self, user_id, text):
        p = self.player_of(user_id)
        text = " ".join(str(text or "").split())[:MAX_CHAT]
        if not text:
            raise ActionError("Mensaje vacío")
        now = time.time()
        if now - self._last_said.get(user_id, 0) < 0.8:
            raise ActionError("Más despacio")
        self._last_said[user_id] = now
        self._chat_seq += 1
        self.chat.append({"seq": self._chat_seq, "player": self.players.index(p), "name": p.name,
                          "text": text, "t": now})
        self.chat = self.chat[-60:]
        self.version += 1

    def _events_for(self, viewer_idx):
        out = []
        for ev in self.events:
            ev = dict(ev)
            if ev["type"] == "cast" and ev.get("secret") and ev["player"] != viewer_idx:
                ev["card"] = {"hidden": True, "name": "Secreto"}
            ev["mine"] = ev.get("player") == viewer_idx
            out.append(ev)
        return out

    def end_turn(self, user_id=None, forced=False):
        p = self.game.current_player
        if user_id is not None:
            p2 = self.player_of(user_id)
            self._require_turn(p2)
        if forced and p.choice is not None and self.game.turn > 0:
            # se acabó el tiempo con una elección abierta: elegimos la primera
            self._run(lambda: p.choice.choose(p.choice.cards[0]))
        board = self._board()
        before = self._snapshot()
        if not self.finished:
            self._run(self.game.end_turn)
        self.deadline = time.time() + TURN_SECONDS
        self._bump("%s termina su turno%s" % (p.name, " (tiempo agotado)" if forced else ""))
        animated = self._trace_events()
        self._board_events(board, before=before, skip_hits=animated)

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
        # valores originales de la carta (para el hover) y mejoras que tiene encima
        v["base"] = {k: v.get(k) for k in ("cost", "atk", "health", "durability")}
        buffs = []
        for b in getattr(c, "buffs", None) or []:
            try:
                bv = C.card_view(b.id)
                src = getattr(b, "source", None)
                buffs.append({"name": bv["name"], "text": bv["text"],
                              "source": C.card_view(src.id)["name"] if src is not None and src is not c else None})
            except Exception:
                continue
        if buffs:
            v["buffs"] = buffs
        if c.type in (CardType.MINION, CardType.HERO):
            v["atk"] = c.atk
            v["health"] = c.health
            v["max_health"] = c.max_health
            v["damage"] = c.damage
            v["armor"] = getattr(c, "armor", 0)
        if c.type == CardType.MINION and c.zone == Zone.PLAY:
            v["flags"] = [f for f in ("taunt", "divine_shield", "stealthed", "frozen", "windfury",
                                       "poisonous", "lifesteal", "rush", "charge", "silenced",
                                       "dormant", "cant_be_targeted_by_spells",
                                       "cant_be_targeted_by_hero_powers", "immune")
                          if getattr(c, f, False)]
        if c.type == CardType.HERO and c.zone == Zone.PLAY:
            v["flags"] = [f for f in ("frozen", "immune", "stealthed") if getattr(c, f, False)]
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
            "log": self.log[-LOG_KEEP:],
            "chat": [dict(m, mine=m["player"] == self.players.index(me)) for m in self.chat],
            "last_attack": self.last_attack,
            "last_effect": self.last_effect,
            "events": self._events_for(self.players.index(me))[-25:],
            "event_seq": self._event_seq,
            "room": self.room,
        }


for _name in ("mulligan", "choose", "play", "attack", "hero_power", "end_turn", "concede",
              "tick", "view"):
    setattr(GameSession, _name, _in_room(getattr(GameSession, _name)))
