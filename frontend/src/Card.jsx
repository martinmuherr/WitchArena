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
      <div className={"cost" + (costChanged ? " changed" : "")}>{card.cost}</div>
      <div className="card-name">{card.name}</div>
      <Art icon={card.icon} cls={card.class_key} />
      <div className="card-type">
        {card.type}{card.races && card.races.length ? " · " + card.races.map(raceEs).join(", ") : ""}
      </div>
      <div className="card-text"><RichText text={card.text} /></div>
      <div className="card-foot">
        <span className="card-meta">{card.class}{card.set ? " · " + card.set : ""}</span>
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
