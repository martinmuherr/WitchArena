import { createRoot } from "react-dom/client";
import { useEffect, useState, useCallback } from "react";
import { api, setCsrf, setRoom } from "./api.js";
import { Card, CardArt, RichText } from "./Card.jsx";
import { GameBoard, HoverPreview } from "./Game.jsx";
import "./styles.css";

function Auth({ onLogin }) {
  const [mode, setMode] = useState("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const r = await api.post(mode === "login" ? "/api/login" : "/api/register", { username, password });
      setCsrf(r.csrf);
      onLogin(r.username);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="auth">
      <h1 className="logo">WitchArena</h1>
      <p className="tagline">El Arena de Hearthstone de 2017-2018: Kóbolds y Catacumbas o El Bosque Embrujado, tal y como eran al salir.</p>
      <form className="panel" onSubmit={submit}>
        <div className="tabs">
          <button type="button" className={mode === "login" ? "on" : ""} onClick={() => setMode("login")}>Entrar</button>
          <button type="button" className={mode === "register" ? "on" : ""} onClick={() => setMode("register")}>Crear cuenta</button>
        </div>
        <label>Usuario
          <input value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" maxLength={20} required />
        </label>
        <label>Contraseña
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)}
            autoComplete={mode === "login" ? "current-password" : "new-password"} minLength={mode === "register" ? 8 : 1} required />
        </label>
        {mode === "register" && <p className="hint">3-20 caracteres (letras, números o _). Contraseña de 8 caracteres o más.</p>}
        {error && <p className="error">{error}</p>}
        <button className="primary" disabled={busy}>{mode === "login" ? "Entrar" : "Crear cuenta"}</button>
      </form>
      <Disclaimer />
    </div>
  );
}

function Disclaimer() {
  return (
    <p className="disclaimer">
      Proyecto de fans sin ánimo de lucro. Hearthstone, sus cartas y su arte son propiedad de Blizzard Entertainment;
      este sitio no está afiliado ni respaldado por Blizzard. Iconos de{" "}
      <a href="https://game-icons.net" target="_blank" rel="noopener noreferrer">game-icons.net</a>{" "}
      (Lorc, Delapouite y otros autores), licencia{" "}
      <a href="https://creativecommons.org/licenses/by/3.0/" target="_blank" rel="noopener noreferrer">CC BY 3.0</a>.{" "}
      <a href="https://github.com/martinmuherr/WitchArena" target="_blank" rel="noopener noreferrer">Código fuente (AGPL-3.0)</a>.
      <br />
      Arte de las cartas © Blizzard Entertainment, Inc., obtenido de{" "}
      <a href="https://hearthstonejson.com/docs/images.html" target="_blank" rel="noopener noreferrer">HearthstoneJSON</a> (HearthSim).
    </p>
  );
}

function ManaCurve({ deck }) {
  const counts = Array(8).fill(0);
  deck.forEach((c) => (counts[Math.min(c.cost, 7)] += 1));
  const max = Math.max(1, ...counts);
  return (
    <div className="curve">
      {counts.map((n, i) => (
        <div key={i} className="curve-col">
          <div className="curve-bar" style={{ height: (n / max) * 60 + "px" }} />
          <span>{i === 7 ? "7+" : i}</span>
        </div>
      ))}
    </div>
  );
}

function DeckList({ deck }) {
  const [hover, setHover] = useState(null);
  const grouped = {};
  deck.forEach((c) => {
    grouped[c.id] = grouped[c.id] || { card: c, n: 0 };
    grouped[c.id].n += 1;
  });
  const rows = Object.values(grouped).sort((a, b) => a.card.cost - b.card.cost || a.card.name.localeCompare(b.card.name));
  return (
    <div className="decklist">
      <h3>Tu mazo ({deck.length}/30)</h3>
      <ManaCurve deck={deck} />
      <ul>
        {rows.map(({ card, n }) => (
          <li key={card.id}
            onMouseEnter={(e) => setHover({ card, x: e.clientX, y: e.clientY })}
            onMouseMove={(e) => setHover({ card, x: e.clientX, y: e.clientY })}
            onMouseLeave={() => setHover(null)}>
            <span className="dl-cost">{card.cost}</span>
            <span className="dl-name">{card.name}</span>
            {n > 1 && <span className="dl-n">×{n}</span>}
          </li>
        ))}
      </ul>
      <HoverPreview hover={hover} />
    </div>
  );
}

function Draft({ run, onUpdate }) {
  const d = run.draft;
  const [error, setError] = useState(null);
  const pick = async (path, index) => {
    setError(null);
    try {
      onUpdate((await api.post(path, { index })).run);
    } catch (e) {
      setError(e.message);
    }
  };
  if (d.phase === "hero") {
    return (
      <div className="draft">
        <h2>Elige tu clase</h2>
        <div className="heroes">
          {d.hero_options.map((h, i) => (
            <button key={h.key} className={"hero-pick portrait c-" + h.key.toLowerCase()} onClick={() => pick("/api/run/hero", i)}>
              <div className="hp-art">
                <CardArt id={h.hero} big cls={h.key.toLowerCase()} className="hp-img" />
              </div>
              <span className="hp-name">{h.name}</span>
              {h.hero_name && <span className="hp-hero">{h.hero_name}</span>}
              {h.power && (
                <div className="hp-tip">
                  <div className="hp-power-art">
                    <CardArt id={h.power.id} icon={h.power.icon} cls={h.power.class_key} className="hp-pimg" />
                  </div>
                  <div>
                    <span className="hp-pname">{h.power.name}</span>
                    <span className="hp-cost">Poder de héroe · {h.power.cost} de maná</span>
                    <p><RichText text={(h.power.text || "").replace(/^<b>Poder de héroe<\/b>\s*/i, "")} /></p>
                  </div>
                </div>
              )}
            </button>
          ))}
        </div>
        {error && <p className="error">{error}</p>}
      </div>
    );
  }
  return (
    <div className="draft draft-cards">
      <div>
        <h2>{d.card_class_name} · elección {d.pick_number} de 30</h2>
        <div className="offer">
          {d.offer.map((c, i) => (
            <Card key={i + c.id} card={c} onClick={() => pick("/api/run/pick", i)} />
          ))}
        </div>
        {error && <p className="error">{error}</p>}
      </div>
      <DeckList deck={d.deck} />
    </div>
  );
}

function RoomSelect({ user, onPick, onLogout }) {
  const [rooms, setRooms] = useState(null);
  const [error, setError] = useState(null);
  useEffect(() => {
    let alive = true;
    const load = () => api.get("/api/rooms").then((r) => alive && setRooms(r.rooms)).catch((e) => alive && setError(e.message));
    load();
    const t = setInterval(load, 5000); // conectados en cada sala, casi en directo
    return () => { alive = false; clearInterval(t); };
  }, []);
  return (
    <div className="lobby">
      <header className="topbar">
        <span className="logo small">WitchArena</span>
        <span className="who">{user}</span>
        <button onClick={onLogout}>Salir</button>
      </header>
      <div className="rooms-screen">
        <h2>Elige sala</h2>
        <p className="hint">Cada sala tiene su propia colección de cartas, sus propias runs de Arena y su propia cola.</p>
        {error && <p className="error">{error}</p>}
        {!rooms ? <div className="loading">Cargando salas…</div> : (
          <div className="rooms">
            {rooms.map((r) => (
              <button key={r.key} className="room-card" onClick={() => onPick(r)}>
                <div className="rc-art"><CardArt id={r.art} big className="rc-img" /></div>
                <span className="rc-online">{r.online} {r.online === 1 ? "conectado" : "conectados"}</span>
                <div className="rc-body">
                  <h3>{r.name}</h3>
                  <div className="rc-sub">{r.subtitle}</div>
                  <p className="rc-desc">{r.description}</p>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
      <Disclaimer />
    </div>
  );
}

function Lobby({ user, room, onLogout, onChangeRoom }) {
  const [run, setRun] = useState(undefined);
  const [queue, setQueue] = useState({ status: "idle" });
  const [gameId, setGameId] = useState(null);
  const [history, setHistory] = useState([]);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    const r = await api.get("/api/run");
    setRun(r.run);
    const q = await api.get("/api/queue/status");
    setQueue(q);
    if (q.status === "in_game") setGameId(q.game_id);
    setHistory((await api.get("/api/history")).runs);
  }, []);

  useEffect(() => {
    load().catch((e) => setError(e.message));
  }, [load]);

  // latido: así la sala cuenta que estás conectado aunque no hagas nada
  useEffect(() => {
    const t = setInterval(() => api.get("/api/rooms").catch(() => {}), 25000);
    return () => clearInterval(t);
  }, []);

  // Mientras estás en la cola, preguntamos cada 2 s si ya hay rival
  useEffect(() => {
    if (queue.status !== "queued") return;
    const t = setInterval(async () => {
      try {
        const q = await api.get("/api/queue/status");
        setQueue(q);
        if (q.status === "in_game") setGameId(q.game_id);
      } catch (e) {
        setError(e.message);
      }
    }, 2000);
    return () => clearInterval(t);
  }, [queue.status]);

  const act = async (fn) => {
    setError(null);
    try {
      await fn();
    } catch (e) {
      setError(e.message);
    }
  };

  if (gameId) {
    return <GameBoard gameId={gameId} onExit={() => { setGameId(null); setQueue({ status: "idle" }); load(); }} />;
  }
  if (run === undefined) return <div className="loading">Cargando…</div>;

  return (
    <div className="lobby">
      <header className="topbar">
        <span className="logo small">WitchArena</span>
        <span className="room-tag">{room.name}</span>
        <span className="who">{user}</span>
        <button onClick={() => act(async () => {
          if (queue.status === "queued") await api.post("/api/queue/leave");
          onChangeRoom();
        })}>Cambiar de sala</button>
        <button onClick={onLogout}>Salir</button>
      </header>
      {error && <p className="error">{error}</p>}
      {!run && (
        <div className="panel center">
          <h2>Arena</h2>
          <p>Elige clase, haz un draft de 30 cartas y juega contra otras personas hasta 12 victorias o 3 derrotas.</p>
          <button className="primary" onClick={() => act(async () => setRun((await api.post("/api/run/new")).run))}>
            Empezar un Arena
          </button>
        </div>
      )}
      {run && run.status === "drafting" && <Draft run={run} onUpdate={setRun} />}
      {run && run.status === "playing" && (
        <div className="draft-cards">
          <div className="panel center">
            <h2>{run.draft.card_class_name}</h2>
            <div className="record">
              <span className="wins">{run.wins} victorias</span>
              <span className="losses">{run.losses} / {run.max_losses} derrotas</span>
            </div>
            {queue.status === "queued" ? (
              <>
                <p className="searching">Buscando rival… ({queue.players_in_queue} en cola)</p>
                <button onClick={() => act(async () => setQueue(await api.post("/api/queue/leave")))}>Cancelar</button>
              </>
            ) : (
              <button className="primary" onClick={() => act(async () => {
                const q = await api.post("/api/queue/join");
                setQueue(q);
                if (q.status === "in_game") setGameId(q.game_id);
              })}>Buscar partida</button>
            )}
            <button className="link" onClick={() => act(async () => {
              if (window.confirm("¿Retirarte de este Arena? Perderás la run.")) {
                await api.post("/api/run/retire");
                await load();
              }
            })}>Retirarse</button>
          </div>
          <DeckList deck={run.draft.deck} />
        </div>
      )}
      {history.length > 0 && (
        <div className="panel history">
          <h3>Tus últimos Arenas</h3>
          <ul>
            {history.map((h) => (
              <li key={h.id}><b>{h.class}</b> · {h.wins}-{h.losses}{h.status === "retired" ? " (retirado)" : ""}
                <span className="hint"> · {h.room_name}</span></li>
            ))}
          </ul>
        </div>
      )}
      <Disclaimer />
    </div>
  );
}

function App() {
  const [user, setUser] = useState(undefined);
  const [room, setRoomState] = useState(null);
  const chooseRoom = (r) => {
    setRoom(r ? r.key : null);
    setRoomState(r);
  };
  const enter = async () => {
    const r = await api.get("/api/me");
    if (r.csrf) setCsrf(r.csrf);
    setUser(r.user ? r.user.username : null);
    // si tienes una partida en marcha, vuelves directamente a su sala
    if (r.game_room) {
      const list = (await api.get("/api/rooms")).rooms;
      chooseRoom(list.find((x) => x.key === r.game_room) || null);
    }
  };
  useEffect(() => {
    enter().catch(() => setUser(null));
  }, []);
  const logout = async () => { await api.post("/api/logout"); setCsrf(null); chooseRoom(null); setUser(null); };
  if (user === undefined) return <div className="loading">Cargando…</div>;
  if (!user) return <Auth onLogin={() => enter().catch(() => setUser(null))} />;
  if (!room) return <RoomSelect user={user} onPick={chooseRoom} onLogout={logout} />;
  return <Lobby key={room.key} user={user} room={room} onLogout={logout} onChangeRoom={() => chooseRoom(null)} />;
}

createRoot(document.getElementById("root")).render(<App />);
