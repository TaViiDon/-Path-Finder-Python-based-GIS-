# PathFinder — Jamaica Rural Roads Network

A hybrid Python + SWI-Prolog pathfinding application for Jamaican rural roads.
Built for the UTech Jamaica AI / Expert Systems course (2026).

---

## What You Need to Download and Install

### 1. SWI-Prolog (Required)

SWI-Prolog is the logic engine that powers all pathfinding and road knowledge in this project.

- Go to: https://www.swi-prolog.org/download/stable
- Download the **Windows 64-bit installer** (`.exe` file)
- Run the installer and use all default settings
- **Important:** Make sure "Add SWI-Prolog to PATH" is checked during installation
- After installing, restart your terminal or VS Code

Verify it installed correctly:
```bash
swipl --version
```

### 2. Python 3.10 or newer (Required)

- Go to: https://www.python.org/downloads/
- Download and install Python 3.10+
- During install, check **"Add Python to PATH"**

Verify:
```bash
python --version
```

PySwip is the bridge that lets Python talk to SWI-Prolog.

Install all Python dependencies at once:
```bash
pip install -r requirements.txt
```

Or individually:
```bash
pip install pyswip requests Pillow python-dotenv
```

---

### 4. Google Maps API Key (Optional but Recommended)

Without a key the app still works — it uses a dark grid background.
With a key it shows a real Google Maps tile of the Saint Catherine road area.

**How to set it up:**

1. Go to [https://console.cloud.google.com/](https://console.cloud.google.com/)
2. Create or select a project
3. Enable the **Maps Static API**
4. Go to **Credentials → Create Credentials → API Key**
5. Copy the file `.env.example` to `.env`:
   ```bash
   copy .env.example .env
   ```
6. Open `.env` and replace `your_google_maps_api_key_here` with your real key:
   ```
   GOOGLE_MAPS_API_KEY=AIzaSy...your_key_here
   ```
7. Run the app — the canvas will show a real dark-mode map tile

> The `.env` file is gitignored and stays on your machine only.

---

## How to Run the Application

1. Make sure SWI-Prolog is installed and on your PATH (see above)
2. Install dependencies: `pip install -r requirements.txt`
3. (Optional) Add your Google Maps API key to a `.env` file (see above)
4. Open a terminal in the project folder
4. Run:

```bash
python main.py
```

The application window will open showing the Jamaica road network map.

---

## How to Use the App

### Finding a Route
1. Select a **From** location in the top-left dropdown
2. Select a **To** location in the second dropdown
3. Choose a **Criteria** (algorithm):
   - **Shortest Distance (Dijkstra)** — fewest kilometres
   - **Fastest Route (Dijkstra)** — least travel time, avoids bad roads
   - **Any Route (BFS)** — first path found
   - **Paved Roads Only (BFS)** — avoids unpaved roads
   - **Open Roads Only (BFS)** — avoids closed roads
   - **Depth-First Search (DFS)** — explores deep paths first
   - **Avoid Broken Cisterns (DFS)** — skips roads with broken cisterns
   - **Avoid Deep Potholes (DFS)** — skips roads with deep potholes
4. Click **Find Route**
5. Route options appear as cards on the right — click a card to switch between routes

### Map Icons
Hover over any icon on the map to see what it means:
- Yellow triangle with `!` — Deep Potholes
- Blue oval with `~` — Broken Cistern
- Orange oval with `!` — Other road condition

### Admin Panel
1. Click the **Admin** button (top right)
2. Enter the password: `admin123`
3. From the admin panel you can:
   - View all roads and conditions
   - Add a new road
   - Update a road's status (open/closed/under repair)
   - Add or remove road conditions
   - Save changes back to the knowledge base file

---

## Project Files

| File | Purpose |
|---|---|
| `main.py` | Entry point — run this to start the app |
| `aiproject.pl` | SWI-Prolog knowledge base (roads, rules, algorithms) |
| `bridge.py` | Python ↔ Prolog connector (PrologBridge class) |
| `interface.py` | Main GUI — Waze-style map and route cards |
| `admin.py` | Admin panel for editing roads and conditions |
| `utils.py` | Formatting helpers and algorithm name map |
| `requirements.txt` | Python dependencies (`pyswip`) |

---

## Troubleshooting

**`SwiPrologNotFoundError`**
SWI-Prolog is not installed or not on the PATH. Install it from the link above and restart your terminal.

**`ModuleNotFoundError: No module named 'pyswip'`**
Run `pip install pyswip` in your terminal.

**App opens but routes return nothing**
Make sure `aiproject.pl` is in the same folder as `main.py`. The knowledge base file must be present for queries to work.

**Still getting SWI-Prolog not found after installing**
Try setting the path manually before running:
```bash
set SWI_HOME_DIR=C:\Program Files\swipl
python main.py
```
