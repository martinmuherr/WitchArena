// Carta sin arte: coste, nombre, tipo, texto y estadísticas.
// El texto viene del servidor ya limpio y solo puede contener <b> e <i>;
// aun así lo convertimos a nodos de React en vez de usar innerHTML.

export function RichText({ text }) {
  if (!text) return null;
  const parts = [];
  const re = /<(\/?)(b|i)>/g;
  let last = 0;
  let bold = false;
  let ital = false;
  let m;
  let k = 0;
  const push = (s) => {
    if (!s) return;
    let node = s;
    if (ital) node = <i key={"i" + k}>{node}</i>;
    if (bold) node = <b key={"b" + k}>{node}</b>;
    parts.push(<span key={k++}>{node}</span>);
  };
  while ((m = re.exec(text))) {
    push(text.slice(last, m.index));
    const on = m[1] !== "/";
    if (m[2] === "b") bold = on;
    else ital = on;
    last = re.lastIndex;
  }
  push(text.slice(last));
  return <>{parts}</>;
}

const RARITY_CLASS = {
  "Común": "r-common", "Básica": "r-free", "Rara": "r-rare", "Épica": "r-epic", "Legendaria": "r-legendary",
};

import { useState } from "react";
import { ART_BASE, CARD_ART } from "./config.js";

// Arte de la carta (HearthstoneJSON). Si falla o está desactivado, usamos el icono.
export function CardArt({ id, icon, cls, className, big }) {
  const [failed, setFailed] = useState(false);
  if (!CARD_ART || !id || failed) return <Art icon={icon} cls={cls} className={(className || "art") + " art-fallback"} />;
  const base = big ? ART_BASE.replace("/256x/", "/512x/") : ART_BASE;
  return (
    <div className={(className || "art") + " art-img"}>
      <img src={base + id + ".jpg"} alt="" loading="lazy" draggable="false"
        referrerPolicy="no-referrer" onError={() => setFailed(true)} />
    </div>
  );
}

// Icono de game-icons.net (CC BY 3.0) teñido con el color de la clase mediante una máscara CSS.
export function Art({ icon, cls, className }) {
  if (!icon) return null;
  const url = `url(/assets/icons/${icon}.svg)`;
  return <div className={(className || "art") + " c-" + (cls || "neutral")} style={{ maskImage: url, WebkitMaskImage: url }} />;
}

export function Card({ card, onClick, selected, highlight, dim, small, base }) {
  const cls = [
    "card", small ? "card-small" : "", RARITY_CLASS[card.rarity] || "",
    selected ? "selected" : "", highlight ? "highlight" : "", dim ? "dim" : "",
    onClick ? "clickable" : "", card.playable ? "playable" : "",
  ].join(" ");
  const isMinion = card.type === "Esbirro";
  const isWeapon = card.type === "Arma";
  const costChanged = base && base.cost !== undefined && base.cost !== card.cost;
  return (
    <div className={cls} onClick={onClick}>
      {/* el arte ocupa toda la carta; encima van el nombre y un recuadro translúcido con el texto */}
      <div className="card-bg">
        <CardArt id={card.id} icon={card.icon} cls={card.class_key} big={!small} />
      </div>
      <div className={"cost" + (costChanged ? " changed" : "")}>{card.cost}</div>
      <div className="card-name">{card.name}</div>
      <div className="card-box">
        <div className="card-type">
          {card.type}{card.races && card.races.length ? " · " + card.races.map(raceEs).join(", ") : ""}
        </div>
        {card.text && <div className="card-text"><RichText text={card.text} /></div>}
        <div className="card-foot">
          <span className="card-meta">{card.class}{card.set ? " · " + card.set : ""}</span>
        </div>
      </div>
      {isMinion && (
        <>
          <div className="stat atk">{card.atk}</div>
          <div className={"stat hp" + (card.damage ? " hurt" : "")}>{card.health}</div>
        </>
      )}
      {isWeapon && (
        <>
          <div className="stat atk">{card.atk}</div>
          <div className="stat dur">{card.durability}</div>
        </>
      )}
    </div>
  );
}

export function CardBack() {
  return <div className="card-back" />;
}

const RACES = {
  BEAST: "Bestia", DEMON: "Demonio", DRAGON: "Dragón", ELEMENTAL: "Elemental", MECHANICAL: "Robot",
  MURLOC: "Múrloc", PIRATE: "Pirata", TOTEM: "Tótem", ALL: "Todos",
};
export function raceEs(r) {
  return RACES[r] || r;
}
