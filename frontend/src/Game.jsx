import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { api } from "./api.js";
import { Art, Card, CardArt, CardBack, RichText } from "./Card.jsx";

const FLAG_ES = {
  taunt: "Provocar", divine_shield: "Escudo divino", stealthed: "Sigilo", frozen: "Congelado",
  windfury: "Viento furioso", poisonous: "Veneno", lifesteal: "Robo de vida", rush: "Embestir",
  charge: "Cargar", silenced: "Silenciado", dormant: "Latente", cant_be_targeted_by_spells: "Elusivo",
};

const DRAG_THRESHOLD = 6; // px antes de considerar que empiezas a arrastrar

// ---------------------------------------------------------------- vista previa al pasar el ratón
// Muestra la carta ORIGINAL (coste y estadísticas base) y, al lado, las mejoras que tiene.
export function HoverPreview({ hover }) {
  const ref = useRef(null);
  const [pos, setPos] = useState({ left: -9999, top: -9999 });
  useLayoutEffect(() => {
    if (!hover || !ref.current) return;
    const w = ref.current.offsetWidth;
    const h = ref.current.offsetHeight;
    const gap = 18;
    const W = window.innerWidth;
    const H = window.innerHeight;
    // siempre hacia el centro de la pantalla
    let left = hover.x < W / 2 ? hover.x + gap : hover.x - gap - w;
    let top = hover.y < H / 2 ? hover.y + gap : hover.y - gap - h;
    left = Math.max(8, Math.min(left, W - w - 8));
    top = Math.max(8, Math.min(top, H - h - 8));
    setPos({ left, top });
  }, [hover && hover.x, hover && hover.y, hover && hover.card && hover.card.eid, hover && hover.card && hover.card.id]);
  if (!hover || !hover.card || hover.card.hidden) return null;
  const c = hover.card;
  const base = { ...c, ...(c.base || {}) };
  const buffs = c.buffs || [];
  const flags = c.flags || [];
  return (
    <div className="hover-preview" ref={ref} style={{ left: pos.left + "px", top: pos.top + "px" }}>
      <Card card={base} />
      {(buffs.length > 0 || flags.length > 0) && (
        <div className="hover-buffs">
          {buffs.length > 0 && <h4>Mejoras</h4>}
          {buffs.map((b, i) => (
            <div key={i} className="buff">
              <b>{b.name}</b>
              {b.text && <span>: <RichText text={b.text} /></span>}
              {b.source && b.source !== b.name && <div className="buff-src">de {b.source}</div>}
            </div>
          ))}
          {flags.length > 0 && <div className="hover-flags">{flags.map((f) => FLAG_ES[f] || f).join(" · ")}</div>}
          {c.atk !== undefined && c.base && (c.atk !== c.base.atk || c.health !== c.base.health) && c.type === "Esbirro" && (
            <div className="hover-now">Ahora: {c.atk}/{c.health}</div>
          )}
        </div>
      )}
    </div>
  );
}

// Hielo: rombos azules repartidos sin orden fijo por el borde del marco
const SHARDS = (() => {
  let seed = 7;
  const rnd = () => ((seed = (seed * 9301 + 49297) % 233280) / 233280);
  const out = [];
  const n = 22;
  for (let i = 0; i < n; i++) {
    const t = i / n;
    // recorre el borde: arriba, derecha, abajo, izquierda
    let x, y;
    if (t < 0.25) { x = t * 4; y = 0; } else if (t < 0.5) { x = 1; y = (t - 0.25) * 4; }
    else if (t < 0.75) { x = 1 - (t - 0.5) * 4; y = 1; } else { x = 0; y = 1 - (t - 0.75) * 4; }
    out.push({
      left: (x * 100 + (rnd() - 0.5) * 14).toFixed(1) + "%",
      top: (y * 100 + (rnd() - 0.5) * 14).toFixed(1) + "%",
      w: (9 + rnd() * 14).toFixed(0), h: (16 + rnd() * 22).toFixed(0),
      rot: (rnd() * 70 - 35).toFixed(0), op: (0.65 + rnd() * 0.35).toFixed(2), d: (rnd() * 0.25).toFixed(2),
    });
  }
  return out;
})();

export function Frozen() {
  return (
    <div className="ice">
      {SHARDS.map((sh, i) => (
        <span key={i} className="shard" style={{
          left: sh.left, top: sh.top, width: sh.w + "px", height: sh.h + "px", opacity: sh.op,
          transform: `translate(-50%,-50%) rotate(${sh.rot}deg) scaleX(.62) rotate(45deg)`, animationDelay: sh.d + "s",
        }} />
      ))}
    </div>
  );
}

function Minion({ m, onClick, targetable, active, canAct, hoverProps }) {
  const flags = m.flags || [];
  const cls = ["minion", ...flags.map((f) => "f-" + f), targetable ? "targetable" : "",
    active ? "active" : "", canAct ? "can-act" : "", onClick ? "clickable" : ""].join(" ");
  const buffed = m.base && m.base.atk !== undefined;
  return (
    <div className={cls} onClick={onClick} data-eid={m.eid} {...hoverProps(m)}>
      {flags.includes("taunt") && <div className="taunt-shield" />}
      <CardArt id={m.id} icon={m.icon} cls={m.class_key} className="m-art" />
      <div className="m-body">
        <div className="m-name">{m.name}</div>
        {m.text && <div className="m-text"><RichText text={m.text} /></div>}
      </div>
      <div className={"stat atk" + (buffed && m.atk > m.base.atk ? " up" : "")}>{m.atk}</div>
      <div className={"stat hp" + (m.damage ? " hurt" : buffed && m.health > m.base.health ? " up" : "")}>{m.health}</div>
      {flags.includes("frozen") && <Frozen />}
    </div>
  );
}

function Hero({ side, onClick, targetable, active, canAct, mine, onPower, powerActive, powerUsable, hoverProps }) {
  const h = side.hero;
  return (
    <div className="hero-row">
      <div className="mana mana-left">
        <span className="mana-n">{side.mana}/{side.max_mana}</span>
        {side.overloaded > 0 && <span className="overload">Sobrecarga {side.overloaded}</span>}
      </div>
      <div className="weapon-slot">
        {side.weapon && (
          <div className="weapon" data-eid={side.weapon.eid} {...hoverProps(side.weapon)}>
            <CardArt id={side.weapon.id} icon={side.weapon.icon} cls={side.weapon.class_key} className="w-art" />
            <span className="w-name">{side.weapon.name}</span>
            <span className="stat atk" title="Daño">{side.weapon.atk}</span>
            <span className="stat dur" title="Durabilidad">{side.weapon.durability}</span>
          </div>
        )}
      </div>
      <div className={"hero " + (targetable ? "targetable " : "") + (active ? "active " : "") + (canAct ? "can-act " : "") + (onClick ? "clickable" : "")}
        onClick={onClick} data-eid={h.eid}>
        <CardArt id={h.id} icon={h.icon} cls={h.class_key} className="h-art" />
        <div className="h-name">{side.name}</div>
        <div className="h-class">{h.name}</div>
        {h.atk > 0 && <div className="stat atk">{h.atk}</div>}
        <div className={"stat hp" + (h.damage ? " hurt" : "")}>{h.health}</div>
        {h.armor > 0 && <div className="stat armor">{h.armor}</div>}
        {(h.flags || []).includes("frozen") && <Frozen />}
        {side.secrets.length > 0 && (
          <div className="secrets" title={mine ? side.secrets.map((s) => s.name).join(", ") : "Secretos del rival"}>
            {side.secrets.length} ?
          </div>
        )}
      </div>
      <div className={"power " + (powerUsable ? "usable " : "used ") + (powerActive ? "active" : "")}
        onClick={mine && powerUsable ? onPower : undefined} data-eid={side.power.eid} {...hoverProps(side.power)}>
        <span className="cost">{side.power.cost}</span>
        <CardArt id={side.power.id} icon={side.power.icon} cls={side.power.class_key} className="p-art" />
        <span className="p-name">{side.power.name}</span>
      </div>
      <div className="deck-pile" data-deck={mine ? "me" : "opp"} title={`Mazo: ${side.deck} cartas`}>
        {[...Array(Math.min(5, Math.ceil(side.deck / 6)))].map((_, i) => (
          <div key={i} className="deck-layer" style={{ transform: `translate(${i * 2}px, ${-i * 2}px)` }} />
        ))}
        <span className="deck-count">{side.deck}</span>
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

function center(r) {
  return { x: r.left + r.width / 2, y: r.top + r.height / 2 };
}

// Proyectil de un hechizo o poder de héroe: sale del origen, vuela al objetivo y estalla.
function Projectile({ fx, onDone }) {
  const ref = useRef(null);
  useLayoutEffect(() => {
    const el = ref.current;
    const dx = fx.to.x - fx.from.x;
    const dy = fx.to.y - fx.from.y;
    const travel = fx.kind === "self" || fx.noFly ? 0 : 750;
    if (el && el.animate && travel) {
      el.animate(
        [
          { transform: "translate(-50%,-50%) translate(0px,0px) scale(.7)", opacity: 0.2 },
          { transform: `translate(-50%,-50%) translate(${dx * 0.5}px,${dy * 0.5 - 40}px) scale(1.15)`, opacity: 1, offset: 0.5 },
          { transform: `translate(-50%,-50%) translate(${dx}px,${dy}px) scale(1)`, opacity: 1 },
        ],
        { duration: travel, easing: "ease-in", fill: "forwards", delay: fx.delay || 0 },
      );
    }
    const t = setTimeout(onDone, (fx.delay || 0) + travel + 1100);
    return () => clearTimeout(t);
  }, []);
  const travel = (fx.kind === "self" || fx.noFly ? 0 : 750) + (fx.delay || 0);
  const url = fx.icon ? `url(/assets/icons/${fx.icon}.svg)` : null;
  return (
    <>
      {fx.kind !== "self" && !fx.noFly && (
        <div ref={ref} className={"projectile k-" + fx.kind} style={{ left: fx.from.x + "px", top: fx.from.y + "px", opacity: fx.delay ? 0 : undefined }}>
          {url && <div className={"proj-icon c-" + (fx.cls || "neutral")} style={{ maskImage: url, WebkitMaskImage: url }} />}
        </div>
      )}
      <div className={"impact k-" + fx.kind} style={{ left: fx.to.x + "px", top: fx.to.y + "px", animationDelay: travel + "ms" }}>
        {fx.amount ? <span className="impact-n">{fx.kind === "heal" ? "+" : "-"}{fx.amount}</span> : null}
      </div>
    </>
  );
}

// Carta que vuela del mazo a la mano al robar
function DrawFlyer({ f, onDone }) {
  const ref = useRef(null);
  useLayoutEffect(() => {
    const el = ref.current;
    const dx = f.to.x - f.from.x;
    const dy = f.to.y - f.from.y;
    if (el && el.animate) {
      el.animate(
        [
          { transform: "translate(-50%,-50%) translate(0,0) rotate(0deg) scale(.8)", opacity: 0 },
          { transform: `translate(-50%,-50%) translate(${dx * 0.4}px,${dy * 0.4 - 60}px) rotate(-8deg) scale(1.15)`, opacity: 1, offset: 0.4 },
          { transform: `translate(-50%,-50%) translate(${dx}px,${dy}px) rotate(0deg) scale(1)`, opacity: 1 },
        ],
        { duration: 750, delay: f.delay, easing: "ease-in-out", fill: "forwards" },
      );
    }
    const t = setTimeout(onDone, f.delay + 800);
    return () => clearTimeout(t);
  }, []);
  return <div ref={ref} className="draw-flyer" style={{ left: f.from.x + "px", top: f.from.y + "px", opacity: 0 }} />;
}

// Carta jugada, secreto revelado o nuevo héroe, en grande unos instantes
const OVERLAY_MS = { secret: 2000, hero_change: 2600, spell: 1700, minion: 1150, weapon: 1300, hidden: 1400 };

function overlayMs(ev) {
  if (ev.type === "secret") return OVERLAY_MS.secret;
  if (ev.type === "hero_change") return OVERLAY_MS.hero_change;
  if (ev.secret) return OVERLAY_MS.hidden;
  return OVERLAY_MS[ev.kind] || OVERLAY_MS.spell;
}

function CastOverlay({ ev }) {
  const isSecretReveal = ev.type === "secret";
  const isHero = ev.type === "hero_change";
  const hidden = ev.card && ev.card.hidden;
  const kind = isHero ? "hero" : ev.kind || "spell";
  const who = ev.mine ? "Juegas" : "Tu rival juega";
  return (
    <div className={"cast-overlay " + (ev.mine ? "mine" : "opp") + (isSecretReveal ? " secret-reveal" : "") + " k-" + kind}
      style={{ "--ov-ms": overlayMs(ev) + "ms" }}>
      {isSecretReveal && <div className="secret-flash" />}
      {isHero && <div className="hero-flash" />}
      <div className="cast-card">
        {!isSecretReveal && !isHero && !ev.secret && <div className="cast-who">{who}</div>}
        {isHero ? (
          <div className="hero-swap">
            {ev.old && <div className="hero-old"><Card card={ev.old} /></div>}
            <div className="hero-new"><Card card={ev.card} /></div>
          </div>
        ) : hidden ? (
          <div className="secret-back"><span>?</span></div>
        ) : (
          <Card card={ev.card} />
        )}
        {(isSecretReveal || ev.secret) && <div className="secret-banner">{isSecretReveal ? "¡Secreto!" : "Secreto"}</div>}
        {isHero && <div className="secret-banner hero-banner">{ev.mine ? "¡Tu nuevo héroe!" : "¡Nuevo héroe del rival!"}</div>}
      </div>
    </div>
  );
}

function Arrow({ from, to, className }) {
  if (!from || !to) return null;
  const midY = Math.min(from.y, to.y) - 60;
  return (
    <svg className={"arrow-layer " + (className || "")} width="100%" height="100%">
      <defs>
        <marker id={"ah-" + (className || "x")} markerWidth="5" markerHeight="5" refX="2.5" refY="2.5" orient="auto">
          <path d="M0,0 L5,2.5 L0,5 Z" className="arrow-head" />
        </marker>
      </defs>
      <path className="arrow-line" markerEnd={`url(#ah-${className || "x"})`}
        d={`M${from.x},${from.y} Q${(from.x + to.x) / 2},${midY} ${to.x},${to.y}`} />
    </svg>
  );
}

export function GameBoard({ gameId, onExit }) {
  const [view, setView] = useState(null);
  const [sel, setSel] = useState(null); // selección de objetivo: {kind, eid, targets, choose, position, from}
  const [chooseFor, setChooseFor] = useState(null);
  const [mull, setMull] = useState([]);
  const [error, setError] = useState(null);
  const [mouse, setMouse] = useState(null);
  const [drag, setDrag] = useState(null); // carta arrastrada desde la mano
  const [hover, setHover] = useState(null);
  const [attackAnim, setAttackAnim] = useState(null);
  const [effects, setEffects] = useState([]);
  const lastEffectSeq = useRef(null);
  // eventos: carta lanzada / secreto (de uno en uno), robos, muertes, invocaciones
  const lastEventSeq = useRef(null);
  const [overlay, setOverlay] = useState(null);
  const overlayQueue = useRef([]);
  const overlayBusy = useRef(false);
  const [flyers, setFlyers] = useState([]);
  const [marks, setMarks] = useState([]);
  const left = useCountdown(view);
  const esRef = useRef(null);
  const handRef = useRef(null);
  const fieldRef = useRef(null);
  const rectsRef = useRef({});
  const lastAttackSeq = useRef(null);
  const dragRef = useRef(null);

  // ------------------------------------------------------------- conexión en tiempo real
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
    const esc = (e) => e.key === "Escape" && (setSel(null), setChooseFor(null), setDrag(null), (dragRef.current = null));
    window.addEventListener("keydown", esc);
    return () => window.removeEventListener("keydown", esc);
  }, []);

  // muestra en grande las cartas lanzadas y los secretos, de una en una
  const pumpOverlay = () => {
    if (overlayBusy.current) return;
    const ev = overlayQueue.current.shift();
    if (!ev) return;
    overlayBusy.current = true;
    setOverlay(ev);
    const ms = overlayMs(ev);
    if (ev.type === "hero_change") {
      // el retrato del héroe brilla y se transforma cuando termina la presentación
      setTimeout(() => {
        const el = document.querySelector(`.board [data-eid="${ev.eid}"]`);
        if (el && el.animate) {
          el.animate(
            [{ transform: "scale(.6)", filter: "brightness(3) saturate(0)", boxShadow: "0 0 0 0 #f2c66b" },
              { transform: "scale(1.18)", filter: "brightness(1.6)", boxShadow: "0 0 50px 22px #f2c66b" },
              { transform: "scale(1)", filter: "none", boxShadow: "0 0 0 0 #f2c66b00" }],
            { duration: 1100, easing: "ease-out" },
          );
        }
      }, ms - 500);
    }
    setTimeout(() => {
      setOverlay(null);
      overlayBusy.current = false;
      setTimeout(pumpOverlay, 120);
    }, ms);
  };

  // ------------------------------------------------ animación de ataque (para los dos jugadores)
  useLayoutEffect(() => {
    if (!view) return;
    const la = view.last_attack;
    if (la && lastAttackSeq.current !== null && la.seq !== lastAttackSeq.current) {
      // usamos las posiciones de ANTES del ataque (el defensor puede haber muerto)
      const ra = rectsRef.current[la.attacker];
      const rd = rectsRef.current[la.defender];
      if (ra && rd) {
        const a = center(ra);
        const d = center(rd);
        setAttackAnim({ from: a, to: d, seq: la.seq });
        setTimeout(() => setAttackAnim((cur) => (cur && cur.seq === la.seq ? null : cur)), 900);
        const el = document.querySelector(`[data-eid="${la.attacker}"]`);
        if (el && el.animate) {
          const dx = (d.x - a.x) * 0.35;
          const dy = (d.y - a.y) * 0.35;
          el.animate(
            [{ transform: "translate(0,0)" }, { transform: `translate(${dx}px,${dy}px) scale(1.06)` }, { transform: "translate(0,0)" }],
            { duration: 480, easing: "ease-in-out" },
          );
        }
      }
    }
    if (la) lastAttackSeq.current = la.seq;
    else if (lastAttackSeq.current === null) lastAttackSeq.current = 0;

    // hechizos / poderes de héroe / gritos de batalla: proyectil hacia cada afectado
    const le = view.last_effect;
    if (le && lastEffectSeq.current !== null && le.seq !== lastEffectSeq.current) {
      const rectOf = (eid) => {
        const el = document.querySelector(`.board [data-eid="${eid}"]`);
        return (el && el.getBoundingClientRect()) || rectsRef.current[eid];
      };
      const rs = rectOf(le.source);
      if (rs) {
        const from = center(rs);
        const list = [];
        le.hits.forEach((h, i) => {
          const rt = h.died ? rectsRef.current[h.eid] || rectOf(h.eid) : rectOf(h.eid);
          if (!rt) return;
          list.push({ id: le.seq + "-" + i, from, to: center(rt), kind: h.kind, amount: h.amount, icon: le.icon, cls: le.class_key,
            delay: le.power ? 150 : 550 });
        });
        if (list.length) setEffects((cur) => [...cur, ...list]);
      }
    }
    if (le) lastEffectSeq.current = le.seq;
    else if (lastEffectSeq.current === null) lastEffectSeq.current = 0;

    // ---- eventos nuevos
    const evs = view.events || [];
    if (lastEventSeq.current === null) {
      lastEventSeq.current = view.event_seq || 0; // al entrar no repetimos lo ya ocurrido
    } else {
      const fresh = evs.filter((e) => e.seq > lastEventSeq.current);
      if (fresh.length) lastEventSeq.current = fresh[fresh.length - 1].seq;
      const rectOf = (sel) => {
        const el = document.querySelector(sel);
        return el && el.getBoundingClientRect();
      };
      const newFlyers = [];
      const newMarks = [];
      fresh.forEach((ev, idx) => {
        if ((ev.type === "cast" && ev.kind !== "hero") || ev.type === "secret" || ev.type === "hero_change") {
          // las cartas de héroe se muestran con su propia animación (hero_change)
          overlayQueue.current.push(ev);
        } else if (ev.type === "draw") {
          const deck = rectOf(`[data-deck="${ev.mine ? "me" : "opp"}"]`);
          [...(ev.eids || []), ...(ev.gained || [])].forEach((eid, j) => {
            const to = rectOf(`[data-hand-eid="${eid}"]`);
            const fromDeck = (ev.eids || []).includes(eid);
            if (!to) return;
            newFlyers.push({
              id: ev.seq + "-" + j, to: center(to), delay: j * 180,
              from: fromDeck && deck ? center(deck) : { x: window.innerWidth / 2, y: window.innerHeight / 2 },
              mine: ev.mine,
            });
          });
        } else if (ev.type === "death" || ev.type === "leave") {
          const r = rectsRef.current[ev.eid];
          if (r) newMarks.push({ id: "m" + ev.seq, kind: ev.type === "death" ? (ev.deathrattle ? "deathrattle" : "death") : "leave", rect: r, card: ev.card });
        } else if (ev.type === "summon") {
          const r = rectOf(`.board [data-eid="${ev.eid}"]`);
          if (r) newMarks.push({ id: "m" + ev.seq, kind: "summon", rect: r });
        } else if (ev.type === "hits") {
          const src = ev.source != null ? rectsRef.current[ev.source] : null;
          const list = [];
          ev.hits.forEach((h, i) => {
            const rt = (document.querySelector(`.board [data-eid="${h.eid}"]`) || {}).getBoundingClientRect?.() || rectsRef.current[h.eid];
            if (!rt) return;
            const to = center(rt);
            list.push({ id: "h" + ev.seq + "-" + i, from: src ? center(src) : to, to, kind: h.kind, noFly: !src,
              amount: h.amount, icon: null, cls: null, delay: 350 + idx * 60 });
          });
          if (list.length) setEffects((cur) => [...cur, ...list]);
        }
      });
      if (newFlyers.length) setFlyers((cur) => [...cur, ...newFlyers]);
      if (newMarks.length) {
        setMarks((cur) => [...cur, ...newMarks]);
        newMarks.forEach((m) => setTimeout(() => setMarks((cur) => cur.filter((x) => x.id !== m.id)), 1400));
      }
      pumpOverlay();
    }
    // guardamos dónde está cada entidad para la próxima animación
    const rects = {};
    document.querySelectorAll(".board [data-eid]").forEach((el) => {
      rects[el.getAttribute("data-eid")] = el.getBoundingClientRect();
    });
    rectsRef.current = rects;
  }, [view]);

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
  const dragTargets = drag && drag.arrow ? drag.card.targets || [] : [];
  const isDragTarget = (eid) => dragTargets.includes(eid);

  // hover: mostrar la carta en pequeño junto al ratón (no mientras arrastras)
  const hoverProps = (card) => ({
    onMouseEnter: (e) => !dragRef.current && setHover({ card, x: e.clientX, y: e.clientY }),
    onMouseMove: (e) => !dragRef.current && setHover({ card, x: e.clientX, y: e.clientY }),
    onMouseLeave: () => setHover(null),
  });

  const origin = (e) => {
    const r = e.currentTarget.getBoundingClientRect();
    setMouse({ x: e.clientX, y: e.clientY });
    return center(r);
  };

  const clickTarget = (eid) => {
    if (!sel || !isTarget(eid)) return false;
    if (sel.kind === "play") send({ type: "play", eid: sel.eid, target: eid, choose: sel.choose, position: sel.position ?? me.field.length });
    else if (sel.kind === "attack") send({ type: "attack", attacker: sel.eid, defender: eid });
    else if (sel.kind === "power") send({ type: "hero_power", target: eid, choose: sel.choose });
    return true;
  };

  // ------------------------------------------------------------ arrastrar cartas de la mano
  const fieldIndexAt = (x) => {
    const els = fieldRef.current ? [...fieldRef.current.querySelectorAll(":scope > .minion")] : [];
    let idx = 0;
    els.forEach((el) => {
      const r = el.getBoundingClientRect();
      if (x > r.left + r.width / 2) idx += 1;
    });
    return idx;
  };

  const outOfHand = (y) => {
    const r = handRef.current && handRef.current.getBoundingClientRect();
    return r ? y < r.top - 8 : true;
  };

  const overField = (x, y) => {
    const r = fieldRef.current && fieldRef.current.getBoundingClientRect();
    return r ? y > r.top - 90 && y < r.bottom + 40 : false;
  };

  const startDrag = (c, e) => {
    if (!myTurn || e.button !== 0) return;
    e.preventDefault();
    setHover(null);
    const r = e.currentTarget.getBoundingClientRect();
    const d = { card: c, startX: e.clientX, startY: e.clientY, x: e.clientX, y: e.clientY, moved: false, from: center(r) };
    dragRef.current = d;

    const move = (ev) => {
      const cur = dragRef.current;
      if (!cur) return;
      const moved = cur.moved || Math.hypot(ev.clientX - cur.startX, ev.clientY - cur.startY) > DRAG_THRESHOLD;
      const out = outOfHand(ev.clientY);
      const isMinion = cur.card.type === "Esbirro";
      const next = {
        ...cur, x: ev.clientX, y: ev.clientY, moved,
        out,
        // los hechizos con objetivo se convierten en flecha al salir de la mano
        arrow: out && !isMinion && !cur.card.choose && Array.isArray(cur.card.targets) && cur.card.targets.length > 0,
        slot: isMinion && out && overField(ev.clientX, ev.clientY) ? fieldIndexAt(ev.clientX) : null,
      };
      dragRef.current = next;
      setDrag(next);
    };

    const up = (ev) => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", up);
      const cur = dragRef.current;
      dragRef.current = null;
      setDrag(null);
      if (!cur || !cur.moved) {
        if (cur && !cur.card.playable) setError("No puedes jugar esa carta ahora");
        return;
      }
      // Al soltar, el navegador lanza también un "click" sobre lo que haya debajo. Ese click
      // cancelaba la flecha del Grito de batalla (o elegía objetivo sin querer): lo anulamos.
      const swallow = (ce) => { ce.stopPropagation(); ce.preventDefault(); };
      window.addEventListener("click", swallow, { capture: true, once: true });
      setTimeout(() => window.removeEventListener("click", swallow, { capture: true }), 250);
      if (!outOfHand(ev.clientY)) return; // la devolviste a la mano
      dropCard(cur, ev);
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);
  };

  const dropCard = (cur, ev) => {
    const c = cur.card;
    if (!c.playable) return setError(c.cost > me.mana ? "No tienes maná suficiente" : "No puedes jugar esa carta ahora");
    const isMinion = c.type === "Esbirro";
    const position = isMinion ? (cur.slot ?? me.field.length) : undefined;
    if (c.choose) return setChooseFor({ ...c, from: cur.from, position });
    if (Array.isArray(c.targets)) {
      if (isMinion) {
        // esbirro con Grito de batalla con objetivo: se coloca y luego eliges con flecha
        if (c.targets.length === 0) return send({ type: "play", eid: c.eid, position });
        setMouse({ x: ev.clientX, y: ev.clientY });
        return setSel({ kind: "play", eid: c.eid, targets: c.targets, position, from: { x: ev.clientX, y: ev.clientY } });
      }
      if (c.targets.length === 0) return setError("No hay objetivos válidos");
      const el = document.elementFromPoint(ev.clientX, ev.clientY);
      const tgt = el && el.closest("[data-eid]");
      const eid = tgt ? Number(tgt.getAttribute("data-eid")) : null;
      if (eid !== null && c.targets.includes(eid)) return send({ type: "play", eid: c.eid, target: eid });
      return; // soltaste la flecha fuera de un objetivo válido: se cancela
    }
    send({ type: "play", eid: c.eid, position });
  };

  const pickChoose = (o) => {
    const c = chooseFor;
    setChooseFor(null);
    if (!o.playable) return setError("Esa opción no se puede jugar ahora");
    if (o.targets) {
      if (o.targets.length === 0) return setError("No hay objetivos válidos");
      return setSel({ kind: "play", eid: c.eid, targets: o.targets, choose: o.eid, position: c.position, from: c.from });
    }
    send({ type: "play", eid: c.eid, choose: o.eid, position: c.position ?? me.field.length });
  };

  const clickMine = (ent, e) => {
    if (clickTarget(ent.eid)) return;
    if (!myTurn) return;
    if (sel && sel.eid === ent.eid) return setSel(null);
    if (ent.can_attack && ent.attack_targets && ent.attack_targets.length) {
      setHover(null);
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

  // campo propio con hueco donde caería el esbirro arrastrado
  const myField = [...me.field];
  const slot = drag && drag.slot !== null && drag.slot !== undefined ? drag.slot : null;

  return (
    <div className={"board" + (drag ? " dragging" : "")} onClick={(e) => {
      const c = e.target.classList;
      if (c.contains("board") || c.contains("side") || c.contains("field") || c.contains("hand") || c.contains("midline") || c.contains("hero-row")) setSel(null);
    }}>
      <div className="side opp">
        <div className="hand opp-hand">{opp.hand.map((c) => <div key={c.eid} data-hand-eid={c.eid}><CardBack /></div>)}</div>
        <Hero side={opp} hoverProps={hoverProps} targetable={isTarget(opp.hero.eid) || isDragTarget(opp.hero.eid)}
          onClick={sel ? () => clickTarget(opp.hero.eid) : undefined} />
        <div className="field">
          {opp.field.map((m) => (
            <Minion key={m.eid} m={m} hoverProps={hoverProps} targetable={isTarget(m.eid) || isDragTarget(m.eid)}
              onClick={sel ? () => clickTarget(m.eid) : undefined} />
          ))}
        </div>
      </div>

      <div className="midline">
        <div className="log">
          {view.log.slice(-5).map((entry, i) => (
            <div key={i} className="log-entry">
              {(Array.isArray(entry) ? entry : [{ t: String(entry) }]).map((seg, j) =>
                seg.card ? (
                  <span key={j} className="log-card" {...hoverProps(seg.card)}>{seg.card.name}</span>
                ) : (
                  <span key={j}>{seg.t}</span>
                ),
              )}
            </div>
          ))}
        </div>
        <div className="turn-info">
          {view.mulligan ? "Mulligan" : view.finished ? "Fin de la partida" : myTurn ? "Tu turno" : "Turno del rival"}
          {!view.finished && <span className={"timer" + (left <= 15 ? " low" : "")}>{left}s</span>}
        </div>
        <button className="primary end-turn" disabled={!myTurn} onClick={() => send({ type: "end_turn" })}>Terminar turno</button>
      </div>

      <div className="side mine">
        <div className={"field" + (slot !== null ? " drop-active" : "")} ref={fieldRef}>
          {myField.map((m, i) => [
            slot === i ? <div key={"slot" + i} className="drop-slot" /> : null,
            <Minion key={m.eid} m={m} hoverProps={hoverProps} canAct={myTurn && m.can_attack} active={sel && sel.eid === m.eid}
              targetable={isTarget(m.eid) || isDragTarget(m.eid)} onClick={(e) => clickMine(m, e)} />,
          ])}
          {slot === myField.length && <div className="drop-slot" />}
        </div>
        <Hero side={me} mine hoverProps={hoverProps} targetable={isTarget(me.hero.eid) || isDragTarget(me.hero.eid)}
          active={sel && sel.eid === me.hero.eid}
          canAct={myTurn && me.hero.can_attack} onClick={(e) => clickMine(me.hero, e)}
          onPower={clickPower} powerUsable={myTurn && me.power.usable} powerActive={sel && sel.kind === "power"} />
        <div className="hand" ref={handRef}>
          {me.hand.map((c) => (
            <div key={c.eid} data-hand-eid={c.eid} className={"hand-slot" + (drag && drag.card.eid === c.eid && drag.moved ? " lifted" : "")}
              onPointerDown={(e) => startDrag(c, e)} {...hoverProps(c)}>
              <Card card={c} small dim={myTurn && !c.playable} selected={sel && sel.eid === c.eid} />
            </div>
          ))}
        </div>
      </div>

      {/* carta que sigue al ratón mientras la arrastras */}
      {drag && drag.moved && !drag.arrow && (
        <div className="drag-ghost" style={{ left: drag.x + "px", top: drag.y + "px" }}>
          <Card card={drag.card} small />
        </div>
      )}
      {drag && drag.arrow && <Arrow from={drag.from} to={{ x: drag.x, y: drag.y }} className="aim" />}
      {sel && sel.from && mouse && <Arrow from={sel.from} to={mouse} className="aim" />}
      {attackAnim && <Arrow from={attackAnim.from} to={attackAnim.to} className="attack" />}
      {flyers.map((f) => <DrawFlyer key={f.id} f={f} onDone={() => setFlyers((cur) => cur.filter((x) => x.id !== f.id))} />)}
      {marks.map((m) => (
        <div key={m.id} className={"mark mark-" + m.kind}
          style={{ left: m.rect.left + "px", top: m.rect.top + "px", width: m.rect.width + "px", height: m.rect.height + "px" }}>
          {m.kind === "deathrattle" && <span className="mark-label">Último aliento</span>}
        </div>
      ))}
      {overlay && <CastOverlay ev={overlay} />}
      {effects.map((fx) => (
        <Projectile key={fx.id} fx={fx} onDone={() => setEffects((cur) => cur.filter((x) => x.id !== fx.id))} />
      ))}

      {sel && <div className="sel-hint">Elige un objetivo resaltado (Esc o clic fuera para cancelar)</div>}
      {error && <div className="toast error" onClick={() => setError(null)}>{error}</div>}
      {!drag && !sel && <HoverPreview hover={hover} />}

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
      <div className="board-credit">Arte © Blizzard Entertainment, vía HearthstoneJSON · Proyecto de fans sin ánimo de lucro</div>
      {!view.finished && (
        <button className="concede" onClick={() => window.confirm("¿Seguro que quieres rendirte?") && send({ type: "concede" })}>
          Rendirse
        </button>
      )}
    </div>
  );
}
