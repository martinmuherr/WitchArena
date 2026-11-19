import { useEffect, useRef, useState } from "react";
import { api } from "./api.js";
import { Art, Card, CardBack, RichText } from "./Card.jsx";

const FLAG_ES = {
  taunt: "Provocar", divine_shield: "Escudo divino", stealthed: "Sigilo", frozen: "Congelado",
  windfury: "Viento furioso", poisonous: "Veneno", lifesteal: "Robo de vida", rush: "Embestir",
  charge: "Cargar", silenced: "Silenciado", dormant: "Latente", cant_be_targeted_by_spells: "Elusivo",
};

function plain(t) {
  return (t || "").replace(/<[^>]+>/g, "");
}

function Minion({ m, onClick, targetable, active, canAct }) {
  const flags = m.flags || [];
  const cls = ["minion", ...flags.map((f) => "f-" + f), targetable ? "targetable" : "",
    active ? "active" : "", canAct ? "can-act" : "", onClick ? "clickable" : ""].join(" ");
  const tip = m.name + (m.text ? " — " + plain(m.text) : "") + (flags.length ? " [" + flags.map((f) => FLAG_ES[f]).join(", ") + "]" : "");
  return (
    <div className={cls} onClick={onClick} title={tip}>
      <Art icon={m.icon} cls={m.class_key} className="m-art" />
      <div className="m-name">{m.name}</div>
      {m.text && <div className="m-text"><RichText text={m.text} /></div>}
      <div className="stat atk">{m.atk}</div>
      <div className={"stat hp" + (m.damage ? " hurt" : "")}>{m.health}</div>
    </div>
  );
}

function Hero({ side, onClick, targetable, active, canAct, mine, onPower, powerActive, powerUsable }) {
  const h = side.hero;
  return (
    <div className="hero-row">
      <div className="mana mana-left">
        <span className="mana-n">{side.mana}/{side.max_mana}</span>
        {side.overloaded > 0 && <span className="overload">Sobrecarga {side.overloaded}</span>}
        <span className="deck-n">Mazo: {side.deck}</span>
      </div>
      <div className="weapon-slot">
        {side.weapon && (
          <div className="weapon" title={side.weapon.name + " — " + plain(side.weapon.text)}>
            <Art icon={side.weapon.icon} cls={side.weapon.class_key} className="w-art" />
            <span className="w-name">{side.weapon.name}</span>
            <span className="stat atk" title="Daño">{side.weapon.atk}</span>
            <span className="stat dur" title="Durabilidad">{side.weapon.durability}</span>
          </div>
        )}
      </div>
      <div className={"hero " + (targetable ? "targetable " : "") + (active ? "active " : "") + (canAct ? "can-act " : "") + (onClick ? "clickable" : "")}
        onClick={onClick} title={h.name}>
        <Art icon={h.icon} cls={h.class_key} className="h-art" />
        <div className="h-name">{side.name}</div>
        <div className="h-class">{h.name}</div>
        {h.atk > 0 && <div className="stat atk">{h.atk}</div>}
        <div className={"stat hp" + (h.damage ? " hurt" : "")}>{h.health}</div>
        {h.armor > 0 && <div className="stat armor">{h.armor}</div>}
        {side.secrets.length > 0 && (
          <div className="secrets" title={mine ? side.secrets.map((s) => s.name).join(", ") : "Secretos del rival"}>
            {side.secrets.length} ?
          </div>
        )}
      </div>
      <div className={"power " + (powerUsable ? "usable " : "used ") + (powerActive ? "active" : "")}
        onClick={mine && powerUsable ? onPower : undefined}
        title={side.power.name + " — " + plain(side.power.text)}>
        <span className="cost">{side.power.cost}</span>
        <Art icon={side.power.icon} cls={side.power.class_key} className="p-art" />
        <span className="p-name">{side.power.name}</span>
      </div>
    </div>
  );
}

function useCountdown(view) {
  const [left, setLeft] = useState(0);
  useEffect(() => {
    if (!view) return;
    const offset = view.now - Date.now() / 1000;
    const t = setInterval(() => setLeft(Math.max(0, Math.round(view.deadline - (Date.now() / 1000 + offset)))), 500);
    return () => clearInterval(t);
  }, [view && view.deadline, view && view.now]);
  return left;
}

export function GameBoard({ gameId, onExit }) {
  const [view, setView] = useState(null);
  const [sel, setSel] = useState(null); // {kind, eid, targets, choose}
  const [chooseFor, setChooseFor] = useState(null);
  const [mull, setMull] = useState([]);
  const [error, setError] = useState(null);
  const [mouse, setMouse] = useState(null);
  const left = useCountdown(view);
  const esRef = useRef(null);

  useEffect(() => {
    let closed = false;
    api.get(`/api/game/${gameId}/state`).then(setView).catch((e) => setError(e.message));
    // Tiempo real por SSE. Algunos túneles (p. ej. Quick Tunnels de Cloudflare) no dejan pasar
    // SSE, así que si no llega nada en 2,5 s preguntamos el estado cada segundo.
    let lastEvent = 0;
    let lastVersion = -1;
    const apply = (v) => {
      if (v && v.version !== lastVersion) {
        lastVersion = v.version;
        setView(v);
      }
    };
    const connect = () => {
      const es = new EventSource(`/api/game/${gameId}/events`);
      esRef.current = es;
      es.onmessage = (ev) => {
        lastEvent = Date.now();
        apply(JSON.parse(ev.data));
      };
      es.onerror = () => {
        es.close();
        if (!closed) setTimeout(connect, 3000);
      };
    };
    connect();
    let polling = false;
    const poll = setInterval(async () => {
      if (polling || Date.now() - lastEvent < 2500) return;
      polling = true;
      try {
        apply(await api.get(`/api/game/${gameId}/state`));
      } catch {
        /* reintentamos en el siguiente ciclo */
      } finally {
        polling = false;
      }
    }, 1000);
    return () => {
      closed = true;
      clearInterval(poll);
      esRef.current && esRef.current.close();
    };
  }, [gameId]);

  // La flecha sigue al ratón mientras eliges objetivo
  useEffect(() => {
    if (!sel) return;
    const move = (e) => setMouse({ x: e.clientX, y: e.clientY });
    window.addEventListener("mousemove", move);
    return () => window.removeEventListener("mousemove", move);
  }, [sel]);

  useEffect(() => {
    const esc = (e) => e.key === "Escape" && (setSel(null), setChooseFor(null));
    window.addEventListener("keydown", esc);
    return () => window.removeEventListener("keydown", esc);
  }, []);

  if (!view) return <div className="loading">Conectando con la partida…{error && <p className="error">{error}</p>}</div>;

  const send = async (data) => {
    setError(null);
    setSel(null);
    setChooseFor(null);
    try {
      setView(await api.post(`/api/game/${gameId}/action`, data));
    } catch (e) {
      setError(e.message);
    }
  };

  const me = view.me;
  const opp = view.opponent;
  const myTurn = view.my_turn && !view.choice && !view.finished;
  const isTarget = (eid) => sel && sel.targets && sel.targets.includes(eid);
  const origin = (e) => {
    const r = e.currentTarget.getBoundingClientRect();
    setMouse({ x: e.clientX, y: e.clientY });
    return { x: r.left + r.width / 2, y: r.top + r.height / 2 };
  };

  const clickTarget = (eid) => {
    if (!sel || !isTarget(eid)) return false;
    if (sel.kind === "play") send({ type: "play", eid: sel.eid, target: eid, choose: sel.choose, position: me.field.length });
    else if (sel.kind === "attack") send({ type: "attack", attacker: sel.eid, defender: eid });
    else if (sel.kind === "power") send({ type: "hero_power", target: eid, choose: sel.choose });
    return true;
  };

  const clickHand = (c, e) => {
    if (!myTurn || !c.playable) return;
    if (c.choose) return setChooseFor({ ...c, from: origin(e) });
    if (c.targets) {
      if (c.targets.length === 0) return setError("No hay objetivos válidos");
      return setSel({ kind: "play", eid: c.eid, targets: c.targets, from: origin(e) });
    }
    send({ type: "play", eid: c.eid, position: me.field.length });
  };

  const pickChoose = (o) => {
    const c = chooseFor;
    setChooseFor(null);
    if (!o.playable) return setError("Esa opción no se puede jugar ahora");
    if (o.targets) {
      if (o.targets.length === 0) return setError("No hay objetivos válidos");
      return setSel({ kind: "play", eid: c.eid, targets: o.targets, choose: o.eid, from: c.from });
    }
    send({ type: "play", eid: c.eid, choose: o.eid, position: me.field.length });
  };

  const clickMine = (ent, e) => {
    if (clickTarget(ent.eid)) return;
    if (!myTurn) return;
    if (sel && sel.eid === ent.eid) return setSel(null);
    if (ent.can_attack && ent.attack_targets && ent.attack_targets.length) {
      setSel({ kind: "attack", eid: ent.eid, targets: ent.attack_targets, from: origin(e) });
    } else if (ent.atk > 0 && !ent.can_attack) {
      setError("Ese personaje no puede atacar ahora");
    }
  };

  const clickPower = (e) => {
    if (!myTurn) return;
    const p = me.power;
    if (p.targets) return setSel({ kind: "power", eid: p.eid, targets: p.targets, from: origin(e) });
    send({ type: "hero_power" });
  };

  return (
    <div className="board" onClick={(e) => {
      const c = e.target.classList;
      if (c.contains("board") || c.contains("side") || c.contains("field") || c.contains("hand") || c.contains("midline") || c.contains("hero-row")) setSel(null);
    }}>
      <div className="side opp">
        <div className="hand opp-hand">{opp.hand.map((c) => <CardBack key={c.eid} />)}</div>
        <Hero side={opp} targetable={isTarget(opp.hero.eid)} onClick={sel ? () => clickTarget(opp.hero.eid) : undefined} />
        <div className="field">
          {opp.field.map((m) => (
            <Minion key={m.eid} m={m} targetable={isTarget(m.eid)} onClick={sel ? () => clickTarget(m.eid) : undefined} />
          ))}
        </div>
      </div>

      <div className="midline">
        <div className="log">{view.log.slice(-4).map((l, i) => <div key={i}>{l}</div>)}</div>
        <div className="turn-info">
          {view.mulligan ? "Mulligan" : view.finished ? "Fin de la partida" : myTurn ? "Tu turno" : "Turno del rival"}
          {!view.finished && <span className={"timer" + (left <= 15 ? " low" : "")}>{left}s</span>}
        </div>
        <button className="primary end-turn" disabled={!myTurn} onClick={() => send({ type: "end_turn" })}>Terminar turno</button>
      </div>

      <div className="side mine">
        <div className="field">
          {me.field.map((m) => (
            <Minion key={m.eid} m={m} canAct={myTurn && m.can_attack} active={sel && sel.eid === m.eid}
              targetable={isTarget(m.eid)} onClick={(e) => clickMine(m, e)} />
          ))}
        </div>
        <Hero side={me} mine targetable={isTarget(me.hero.eid)} active={sel && sel.eid === me.hero.eid}
          canAct={myTurn && me.hero.can_attack} onClick={(e) => clickMine(me.hero, e)}
          onPower={clickPower} powerUsable={myTurn && me.power.usable} powerActive={sel && sel.kind === "power"} />
        <div className="hand">
          {me.hand.map((c) => (
            <Card key={c.eid} card={c} small onClick={(e) => clickHand(c, e)} dim={myTurn && !c.playable}
              selected={sel && sel.eid === c.eid} />
          ))}
        </div>
      </div>

      {sel && <div className="sel-hint">Elige un objetivo resaltado (Esc o clic fuera para cancelar)</div>}
      {sel && sel.from && mouse && (
        <svg className="arrow-layer" width="100%" height="100%">
          <defs>
            <marker id="arrowhead" markerWidth="5" markerHeight="5" refX="2.5" refY="2.5" orient="auto">
              <path d="M0,0 L5,2.5 L0,5 Z" className="arrow-head" />
            </marker>
          </defs>
          <path className="arrow-line" markerEnd="url(#arrowhead)"
            d={`M${sel.from.x},${sel.from.y} Q${(sel.from.x + mouse.x) / 2},${Math.min(sel.from.y, mouse.y) - 60} ${mouse.x},${mouse.y}`} />
        </svg>
      )}
      {error && <div className="toast error" onClick={() => setError(null)}>{error}</div>}

      {chooseFor && (
        <div className="modal">
          <h3>Elige una opción</h3>
          <div className="offer">
            {chooseFor.choose.map((o) => <Card key={o.eid} card={o} onClick={() => pickChoose(o)} dim={!o.playable} />)}
          </div>
          <button onClick={() => setChooseFor(null)}>Cancelar</button>
        </div>
      )}

      {view.choice && view.choice.type === "mulligan" && (
        <div className="modal">
          <h3>Mulligan: marca las cartas que quieres cambiar</h3>
          <div className="offer">
            {view.choice.cards.map((c) => (
              <Card key={c.eid} card={c} selected={mull.includes(c.eid)}
                onClick={() => setMull(mull.includes(c.eid) ? mull.filter((x) => x !== c.eid) : [...mull, c.eid])} />
            ))}
          </div>
          <button className="primary" onClick={() => { send({ type: "mulligan", replace: mull }); setMull([]); }}>Confirmar</button>
          <p className="timer-text">{left}s</p>
        </div>
      )}
      {!view.choice && view.mulligan && (
        <div className="modal small"><p>Esperando a que el rival termine el mulligan…</p></div>
      )}
      {view.choice && view.choice.type === "discover" && (
        <div className="modal">
          <h3>Elige una carta</h3>
          <div className="offer">
            {view.choice.cards.map((c) => <Card key={c.eid} card={c} onClick={() => send({ type: "choose", eid: c.eid })} />)}
          </div>
        </div>
      )}
      {view.finished && (
        <div className="modal">
          <h2 className={"result " + view.winner}>
            {view.winner === "me" ? "¡Victoria!" : view.winner === "opponent" ? "Derrota" : "Empate"}
          </h2>
          <button className="primary" onClick={onExit}>Volver al Arena</button>
        </div>
      )}
      {!view.finished && (
        <button className="concede" onClick={() => window.confirm("¿Seguro que quieres rendirte?") && send({ type: "concede" })}>
          Rendirse
        </button>
      )}
    </div>
  );
}
