<div align="center">

# 🕯️ WitchArena

### El Arena de Hearthstone tal y como era en 2017-2018

*Vuelve a jugar el Arena de Kóbolds y Catacumbas o el del Año del Cuervo, recién estrenado El Bosque Embrujado, contra otras personas y online.*

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)
![Starlette](https://img.shields.io/badge/Starlette-ASGI-2a9d8f)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-o_SQLite-4169E1?logo=postgresql&logoColor=white)
![Parche](https://img.shields.io/badge/Parches-10.0_y_11.0-d9a441)
![Licencia](https://img.shields.io/badge/Licencia-AGPL--3.0-blue)

<img src="docs/img/partida.png" alt="Partida en WitchArena" width="820">

</div>

---

## ✨ Qué es

WitchArena es una web hecha por fans para jugar el **modo Arena de Hearthstone en PvP**, con las
**reglas, cartas y balance exactos** de dos momentos del juego. Al entrar eliges sala, y ves cuánta gente hay conectada en cada una:

| Sala | Parche | Colección del draft |
|---|---|---|
| 🌲 **El Bosque Embrujado** | 11.0 (10 de abril de 2018, build 23966) | Básico, Clásico, Un'Goro, Trono Helado, Kóbolds y Bosque Embrujado (869 cartas) |
| 🕯️ **Kóbolds y Catacumbas** | 10.0 (7 de diciembre de 2017, build 22611) | Año del Mamut: Básico, Clásico, Viejos Dioses, Karazhan, Gadgetzan, Un'Goro, Trono Helado y Kóbolds (1050 cartas) |

Cada sala tiene sus propias runs, su cola de emparejamiento y sus valores de cartas (en Kóbolds, por ejemplo,
el Reptador del pasillo es 5/5, Parches tiene Carga y el poder de Raza el Encadenado cuesta 0).

- 🧙 **Draft completo**: eliges entre 3 clases (con el retrato del héroe y su poder de héroe al pasar el ratón) y haces 30 elecciones de 1 entre 3 cartas.
- ⚔️ **Partidas contra otras personas** en tiempo real, con mulligan, Descubrir, Elige una opción, secretos y armas.
- 🏆 **Runs de Arena reales**: hasta **12 victorias o 3 derrotas**, con historial.
- 📜 **Cartas en español** con sus textos de 2018 y su arte, que el navegador carga desde HearthstoneJSON (con iconos libres de respaldo).
- 🍺 **Mesa de taberna** de diseño propio.
- 🖐️ **Cartas que se arrastran**: coloca cada esbirro en el hueco que quieras de tu fila; los hechizos con objetivo se convierten en una flecha al salir de la mano.
- 🎯 **Flechas de ataque** que siguen al ratón y animación de ataque visible para los dos jugadores.
- 🔍 **Vista previa al pasar el ratón** (en la mesa y en el registro): la carta original con sus valores base y las mejoras que tiene encima, y de dónde vienen.
- 🛡️ **Provocar** se ve como un escudo detrás del esbirro; **Escudo divino**, como un halo dorado.
- ✨ **Efectos visuales** para hechizos, poderes de héroe y Gritos de batalla: un proyectil vuela hasta cada objetivo y muestra el daño o la curación.
- 🃏 **Cada carta jugada se ve en grande** unos instantes (hechizos, esbirros y armas); los secretos que saltan se anuncian con un destello morado.
- 👑 **Cartas de héroe** (Hagatha, caballeros de la muerte, Lord Jaraxxus…) con su propia animación: el héroe antiguo se aparta y aparece el nuevo.
- ❄️ **Congelado** se ve como rombos de hielo alrededor del marco del esbirro o del héroe.
- 📚 **Mazo visible** junto a cada héroe y animación de cada robo; animaciones al morir (con aviso de Último aliento) y al aparecer esbirros.

| Draft | Atacando |
|:---:|:---:|
| <img src="docs/img/draft.png" width="400"> | <img src="docs/img/ataque.png" width="400"> |

---

## 🚀 Ponerlo en marcha (Windows)

> Necesitas **Python 3.10+**. Node.js solo hace falta si quieres recompilar la web (ya viene compilada en `frontend/dist`).

1. Descarga o clona el repositorio.
2. Doble clic en **`instalar.bat`**. Crea el entorno de Python, instala dependencias, prepara la base de
   datos y crea usuarios de prueba (contraseñas en `backend/test_users.txt`, que nunca se sube a git).
3. Doble clic en **`iniciar.bat`**. Arranca el servidor y abre **http://127.0.0.1:8000**.

Para probar una partida solo, abre una ventana normal y otra de incógnito y entra con dos usuarios distintos.

### 🌍 Publicarlo en internet desde tu PC (Cloudflare Tunnel)

Sin abrir puertos del router ni exponer tu IP:

1. **`descargar_cloudflared.bat`**: baja `cloudflared.exe` (versión portable oficial) a la carpeta `tunel/`.
2. **`publicar.bat`**: arranca el servidor en **modo público** y abre un túnel. Al terminar te muestra la dirección
   `https://….trycloudflare.com` (también queda guardada en `tunel/url.txt`).
3. **`reiniciar_servidor.bat`**: tras una actualización, reinicia solo el servidor; el túnel y su dirección se mantienen.

En modo público (`PUBLIC_MODE=1`) las cookies solo viajan por HTTPS, el límite de intentos usa la IP real del
visitante (`CF-Connecting-IP`) y las cuentas de prueba no pueden entrar. El Quick Tunnel es gratuito y no necesita
cuenta, pero **la dirección cambia cada vez que se reinicia** y Cloudflare lo considera solo para pruebas. Como no deja
pasar los eventos en tiempo real (SSE), la web pasa sola a preguntar el estado cada segundo.

<details>
<summary><b>Linux / macOS</b></summary>

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python tools/create_test_users.py
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```
</details>

<details>
<summary><b>Recompilar el frontend</b></summary>

```bash
cd frontend
npm install
npm run build      # o: npm run watch
```
</details>

---

## 🏗️ Arquitectura

```mermaid
flowchart LR
    A[Navegador<br/>React] -- "HTTP / JSON<br/>(acciones)" --> B[Servidor Python<br/>Starlette + uvicorn]
    B -- "Server-Sent Events<br/>(estado de la partida)" --> A
    B --> C[Motor de juego<br/>Fireplace]
    B --> D[(SQLite en local<br/>PostgreSQL en servidor)]
    C --> E[Datos de cartas<br/>build 23966]
```

- **El servidor es la única autoridad.** El cliente solo envía intenciones ("juega esta carta sobre ese objetivo")
  y el motor las valida. Cada jugador recibe solo lo que vería en el juego real: la mano y los secretos del rival van ocultos.
- Las partidas y la cola viven en memoria, así que hay que arrancar **un solo proceso** de uvicorn.

<details>
<summary><b>Estructura del proyecto</b></summary>

```
backend/
├── app/
│   ├── main.py            API, emparejamiento, partidas y SSE
│   ├── auth.py            contraseñas (scrypt), sesiones, CSRF y límite de intentos
│   ├── db.py              SQLite / PostgreSQL, siempre con consultas parametrizadas
│   ├── rooms.py           salas (Kóbolds 10.0 y Bosque Embrujado 11.0) y cambio de colección del motor
│   ├── arena_rules.py     sets, cartas prohibidas y rarezas de 2017-2018
│   ├── draft.py           elección de héroe y de cartas
│   ├── game_session.py    partida PvP, vista por jugador y temporizadores
│   └── cards.py           textos en español, iconos y pool de Arena
├── data/                  datos de cartas 10.0 y 11.0, alias de IDs e iconos
├── vendor/                Fireplace (motor) y python-hearthstone
├── tests/                 tests de las cartas de los parches 10.0 y 11.0 y de las salas
└── tools/                 comparación de builds, iconos, simulaciones, usuarios de prueba
frontend/
├── src/                   React: login, salas, lobby, draft y tablero
├── public/icons/          iconos SVG de game-icons.net
└── dist/                  web compilada (lista para servir)
```
</details>

---

## 🕰️ Fidelidad a los parches 10.0 y 11.0

Los datos de las cartas son los **oficiales de las builds 22611 (10.0) y 23966 (11.0)**, extraídos por
[HearthSim/hsdata](https://github.com/HearthSim/hsdata). El motor, Fireplace, estaba programado para el
parche 17.6, así que `tools/diff_builds.py` compara ambas versiones carta a carta y los efectos que cambiaron
se han devuelto a su versión de 2018:

| Carta | En WitchArena (11.0) | Cambio posterior |
|---|---|---|
| Pacto oscuro | Restaura **8** de salud | 4 |
| Preparación | Siguiente hechizo cuesta **3** menos | 2 |
| Núcleo de cristal | Esbirros **5/5** | 4/4 |
| Abre el portal | **6** hechizos | 8 |
| Castigo sagrado | **2** de daño a cualquier objetivo | 3 solo a esbirros |
| Palabra de poder: escudo | +2 de salud **y roba una carta** | sin robo |
| Poderes de héroe básicos | IDs de 2018 (`CS2_083b`…) enlazados al motor | renombrados a `HERO_0Xbp` |
| Coleccionista de bibelots, Archimago Arugal, Maestro de muñecas Dorian | reaccionan al robar | fallo del motor corregido |
| Hidra de cueva | daña a los esbirros adyacentes al objetivo | fallo del motor corregido |
| Glinda Piel de Cuervo | los esbirros de la mano tienen Eco | fallo del motor corregido |
| Nova sagrada | 2 de daño a **todos los enemigos** (también al héroe) | solo a esbirros |
| Pacto sacrificial | destruye **cualquier** Demonio | solo aliados |
| Raza el Encadenado | poder a **0** en Kóbolds y a **1** en El Bosque Embrujado (nerf de la 10.2) | — |

**Pool de Arena:** los sets Standard de cada momento (ver tabla de salas). Excluye el Salón de la Fama y aplica la
lista de cartas prohibidas de 2018 (misiones, caballeros de la muerte y cartas débiles). En El Bosque Embrujado se
suman Humongous Razorleaf y Ancient Watcher, que la 11.0 sacó del draft.

> ⚠️ **Aproximaciones:** Blizzard nunca publicó las probabilidades exactas del draft. Las probabilidades de cada
> rareza y el peso extra de las cartas de clase y de la expansión nueva son estimaciones, y están en
> [`arena_rules.py`](backend/app/arena_rules.py) para poder ajustarlas.

---

## 🧪 Pruebas

```bash
cd backend
python -m pytest -q tests                  # cartas de los parches 10.0 y 11.0, salas y armas
python tools/sim_pvp.py 300 1 both         # 300 rondas: una partida en cada sala a la vez
python tools/e2e_api.py http://127.0.0.1:8000 usuario1 clave1 usuario2 clave2
```

## 🔒 Seguridad

- Contraseñas con **scrypt** y sal por usuario; sesiones en cookie `HttpOnly` + `SameSite=Strict` (en la base solo se guarda su hash).
- Token **CSRF** en todas las peticiones que cambian algo y **límite de intentos** de login y registro.
- Consultas SQL siempre parametrizadas; cabeceras **CSP**, `X-Frame-Options` y `nosniff`.
- El servidor valida cada jugada y nunca envía información oculta al rival.

## 🗺️ Próximos pasos

- [ ] Publicarlo en un dominio propio (Nginx + HTTPS + PostgreSQL)
- [ ] Revisar a mano los iconos genéricos de algunas cartas
- [ ] Reconexión a mitad de partida tras reiniciar el servidor

---

## 📄 Créditos y licencias

- **Motor:** [Fireplace](https://github.com/jleclanche/fireplace) de Jerome Leclanche y colaboradores (AGPL-3.0), con cambios marcados como `HS_WitchArena`.
- **Datos de cartas:** [python-hearthstone](https://github.com/HearthSim/python-hearthstone) y [hsdata](https://github.com/HearthSim/hsdata) de HearthSim.
- **Arte de las cartas:** © Blizzard Entertainment, Inc. No está incluido en este repositorio: el navegador de cada jugador lo descarga de la [API de imágenes de HearthstoneJSON](https://hearthstonejson.com/docs/images.html) (HearthSim). Para desactivarlo basta con poner `CARD_ART = false` en [`frontend/src/config.js`](frontend/src/config.js) y recompilar.
- **Iconos de respaldo:** [game-icons.net](https://game-icons.net) (Lorc, Delapouite y otros autores), licencia [CC BY 3.0](https://creativecommons.org/licenses/by/3.0/).
- Este proyecto se distribuye bajo **AGPL-3.0** (ver [`LICENSE`](LICENSE)), igual que Fireplace.

> **Aviso:** WitchArena es un proyecto de fans **sin ánimo de lucro**. Hearthstone, sus cartas, nombres, textos y
> arte son propiedad de **Blizzard Entertainment**. Este sitio no está afiliado ni respaldado por Blizzard.
