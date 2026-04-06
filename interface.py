"""
interface.py
------------
Main Waze-inspired GUI for the PathFinder Rural Roads Network system.

Design goals (mirroring the Waze screenshots provided):
  ┌────────────────────────────────────────────────────────────┐
  │  HEADER  –  title + "Road Network Active" badge + Admin    │
  ├────────────────────────────────────────────────────────────┤
  │                                                            │
  │   MAP CANVAS                                               │
  │     • Dark background with subtle grid (Waze tile style)   │
  │     • Paved roads  = blue lines                            │
  │     • Unpaved roads = orange-brown lines                   │
  │     • Closed roads  = red lines                            │
  │     • Highlighted route = bright cyan with dashed centre   │
  │     • Node circles (white) with name labels                │
  │     • ▲ yellow triangle icons for deep_potholes            │
  │     • ● blue circle icons for broken_cisterns              │
  │     • Tooltip popup on icon hover (Waze hazard pop-up)     │
  │     • 🏁 destination flag on found route                   │
  │                                                            │
  ├────────────────────────────────────────────────────────────┤
  │  LEGEND  –  road type / condition colour key               │
  ├────────────────────────────────────────────────────────────┤
  │  SEARCH PANEL                                              │
  │    [From ▼]  [To ▼]  [Criteria ▼]  [🔍 Find Route] [✕]    │
  ├────────────────────────────────────────────────────────────┤
  │  ROUTE CARDS  (Waze-style multiple route options)          │
  │    Card 1: primary algorithm result (highlighted on map)   │
  │    Card 2: Dijkstra distance alternative (if different)    │
  │    Card 3: Dijkstra time alternative   (if different)      │
  └────────────────────────────────────────────────────────────┘

Author: Group  |  UTech Jamaica – AI / Expert Systems  |  2026
"""

import tkinter as tk
from tkinter import ttk, messagebox
from collections import defaultdict
import math
import os
from io import BytesIO

# ── Optional packages for Google Maps tile background ─────────────────────────
# Install with:  pip install requests Pillow python-dotenv
try:
    from urllib.request import urlopen
    import importlib

    Image = importlib.import_module("PIL.Image")
    ImageTk = importlib.import_module("PIL.ImageTk")
    _MAP_LIBS = True
except ImportError:
    Image = None
    ImageTk = None
    _MAP_LIBS = False

try:
    __import__("dotenv").load_dotenv()   # reads .env file from the project directory
except Exception:
    pass                                 # python-dotenv not installed → skip silently

# Read the API key from the environment (set in .env or system env vars)
GOOGLE_MAPS_API_KEY: str = os.getenv("GOOGLE_MAPS_API_KEY", "")

from utils import (
    display_name, prolog_name,
    format_path, format_distance, format_time,
    format_condition, compute_path_totals,
    validate_node, validate_nodes_different,
    ALGORITHM_MAP, ALGORITHM_LABELS,
)
from admin import AdminPanel


# =============================================================================
# Colour palette  (Waze dark-mode inspired)
# =============================================================================
C = {
    "bg":         "#1a1f2e",   # window / panel background
    "map_bg":     "#16213e",   # canvas background (darker navy)
    "header":     "#12192a",   # header bar
    "panel":      "#1e2636",   # search / result panel
    "border":     "#2a3a54",
    "paved":      "#4a9eff",   # blue road line
    "unpaved":    "#c4944a",   # orange-brown road line
    "closed":     "#ff4444",   # red for closed roads
    "route":      "#00d4ff",   # bright cyan for the active route highlight
    "route_alt":  "#888888",   # grey for alternative routes
    "node_fill":  "#ffffff",
    "node_sel":   "#4a9eff",   # selected-source node fill (Waze blue dot)
    "node_out":   "#4a9eff",
    "node_text":  "#1a1f2e",
    "pot_icon":   "#f0c040",   # yellow warning triangle
    "cis_icon":   "#5eb8ff",   # blue circle
    "text":       "#e8eaf0",
    "sub":        "#8b9cb5",
    "accent":     "#4a9eff",
    "success":    "#2ecc71",
    "danger":     "#e74c3c",
    "card_sel":   "#1d3a5a",   # selected route card background
    "card_bg":    "#1e2636",   # unselected card background
    "card_border":"#00d4ff",   # selected card left border
    "inp":        "#252d3d",
    "btn_go":     "#00bcd4",
    "btn_clr":    "#546e7a",
}

# =============================================================================
# Node positions on the 840 × 520 canvas
# (Approximates the rural Saint Catherine road geography)
# =============================================================================
NODE_POSITIONS = {
    "old_harbour":      ( 90, 285),
    "gutters":          (245, 205),
    "calbeck_junction": (245, 375),
    "bushy_park":       (195,  95),
    "spring_villiage":  (410, 145),   # Note: typo preserved from aiproject.pl
    "dover":            (535, 225),
    "content":          (620, 335),
    "bamboo":           (700, 430),
    "byles":            (770, 515),
}

NODE_R    = 14    # node circle radius (px)
ROAD_W    = 4     # default road line width
ROUTE_W   = 10    # route highlight width
ADMIN_PWD = "admin123"   # Demo password – replace with proper auth in production

# =============================================================================
# Real GPS coordinates for each road node (Saint Catherine, Jamaica)
# Used to project nodes onto the Google Maps Static tile.
# If no API key is present the app falls back to self._node_positions above.
# =============================================================================
NODE_LATLNG = {
    "old_harbour":       (17.9463, -77.1117),
    "gutters":           (17.9812, -77.0623),
    "calbeck_junction":  (17.9313, -77.0823),
    "bushy_park":        (18.0312, -77.0889),
    "spring_villiage":   (18.0756, -76.9821),   # typo preserved from aiproject.pl
    "dover":             (18.0834, -76.9212),
    "content":           (18.0623, -76.8956),
    "bamboo":            (17.9978, -76.8678),
    "byles":             (17.9534, -76.8434),
}

# Google Maps Static API settings
MAP_ZOOM   = 11        # zoom level (10–12 works well for this area)
MAP_W      = 880       # tile width  – must match canvas width
MAP_H      = 520       # tile height – must match canvas height
MAP_TYPE   = "roadmap" # "roadmap" | "satellite" | "hybrid" | "terrain"

# Dark-mode style string passed to the Static Maps API so the tile matches the
# navy/dark UI palette instead of the default white Google Maps look.
_MAP_DARK_STYLE = (
    "&style=feature:all|element:geometry|color:0x16213e"
    "&style=feature:road|element:geometry.fill|color:0x1e3a6e"
    "&style=feature:road|element:geometry.stroke|color:0x0a1628"
    "&style=feature:road.arterial|element:geometry|color:0x253d6e"
    "&style=feature:water|element:geometry|color:0x0a1628"
    "&style=feature:landscape|element:geometry|color:0x12192a"
    "&style=feature:poi|element:geometry|color:0x1a2a40"
    "&style=feature:administrative|element:labels.text.fill|color:0x8b9cb5"
    "&style=feature:road|element:labels.text.fill|color:0x4a9eff"
    "&style=feature:all|element:labels.text.stroke|color:0x0a1020"
)


# =============================================================================
# Mercator projection helpers
# =============================================================================

def _world_px(lat: float, lng: float, zoom: int):
    """
    Convert a (lat, lng) pair to world-pixel coordinates at a given zoom.
    This is the standard Web Mercator used by Google Maps tiles.
    The world is 256 * 2^zoom pixels wide at any zoom level.
    """
    scale = 256 * (2 ** zoom)
    x = (lng + 180.0) / 360.0 * scale
    sin_lat = math.sin(math.radians(lat))
    # Clamp to avoid log(0) at the poles
    sin_lat = max(-0.9999, min(0.9999, sin_lat))
    y = (0.5 - math.log((1 + sin_lat) / (1 - sin_lat)) / (4 * math.pi)) * scale
    return x, y


class PathFinderApp:
    """
    Main application window.

    Manages the map canvas, search controls, route display, admin access,
    and all canvas drawing logic.
    """

    def __init__(self, root: tk.Tk, bridge):
        self.root   = root
        self.bridge = bridge

        # Live data – refreshed from Prolog whenever the map redraws
        self.all_nodes      = []
        self.all_roads      = []
        self.all_conditions = []

        # Route state
        self.active_path    = []    # node atoms of the highlighted route
        self.route_edges    = set() # (src, dst) pairs in the active route
        self.route_options  = []    # list of (path, label, time, dist) for the cards

        # Canvas item tracking
        self._icon_items  = {}       # (src,dst,cond) → canvas id
        self._tooltip     = None     # active tooltip Toplevel
        self._map_photo   = None     # holds reference to PhotoImage so GC won't collect it
        self._map_img_raw = None     # raw PIL Image kept for rescaling on window resize
        self._map_zoom    = MAP_ZOOM # current zoom level (changed by +/- buttons)
        self._centre_lat  = None     # map centre – set when tile loads
        self._centre_lng  = None
        self._resize_job  = None     # pending after() id for debounced resize redraw

        # Node positions on the canvas – computed from GPS coords if Google Maps
        # API key is available, otherwise fall back to the hardcoded pixel positions.
        self._node_positions = dict(NODE_POSITIONS)   # start with fallback values

        self._build_window()
        self._load_map_tile()   # fetches the satellite/roadmap tile (needs API key)
        self._refresh_data()
        self._draw_map()

    # =========================================================================
    # WINDOW LAYOUT
    # =========================================================================

    def _build_window(self):
        self.root.title("PathFinder – Jamaica Rural Roads")
        self.root.configure(bg=C["bg"])
        self.root.geometry("880x820")
        self.root.resizable(True, True)
        self.root.minsize(720, 680)

        self._build_header()
        self._build_canvas()
        self._build_legend()
        self._build_search_panel()
        self._build_route_panel()

    # ── Header ────────────────────────────────────────────────────────────────

    def _build_header(self):
        hdr = tk.Frame(self.root, bg=C["header"], height=52)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        # App title (left)
        tk.Label(
            hdr, text="  🗺  PathFinder  |  Jamaica Rural Roads",
            bg=C["header"], fg=C["text"],
            font=("Helvetica", 14, "bold"),
        ).pack(side="left", padx=12, pady=10)

        # Status badge (centre-ish)
        tk.Label(
            hdr, text="🔶  Road Network Active",
            bg=C["header"], fg=C["sub"],
            font=("Helvetica", 9),
        ).pack(side="left", padx=14)

        # Admin button (top-right – like Waze's hamburger menu)
        tk.Button(
            hdr, text="⚙  Admin",
            bg="#2a3a54", fg=C["accent"],
            font=("Helvetica", 10, "bold"),
            relief="flat", cursor="hand2",
            padx=10, pady=4,
            command=self._open_admin,
        ).pack(side="right", padx=16, pady=10)

        # Zoom controls (right of header, left of Admin)
        tk.Button(
            hdr, text=" + ",
            bg="#2a3a54", fg=C["success"],
            font=("Helvetica", 12, "bold"),
            relief="flat", cursor="hand2",
            padx=6, pady=2,
            command=self._zoom_in,
        ).pack(side="right", padx=(0, 2), pady=10)

        tk.Label(
            hdr, text="Zoom",
            bg=C["header"], fg=C["sub"],
            font=("Helvetica", 8),
        ).pack(side="right", padx=(8, 2))

        tk.Button(
            hdr, text=" − ",
            bg="#2a3a54", fg=C["danger"],
            font=("Helvetica", 12, "bold"),
            relief="flat", cursor="hand2",
            padx=6, pady=2,
            command=self._zoom_out,
        ).pack(side="right", padx=(2, 0), pady=10)

    # ── Map Canvas ────────────────────────────────────────────────────────────

    def _build_canvas(self):
        """
        The map canvas is the visual centrepiece.
        We draw all roads, nodes, and condition icons on it using
        Tkinter Canvas primitives (create_line, create_oval, create_polygon).

        If a Google Maps API key is present the canvas background will be a
        real satellite/roadmap tile of the Saint Catherine area fetched via
        the Maps Static API.  Without a key the classic dark navy grid is used.
        """
        frame = tk.Frame(self.root, bg=C["map_bg"])
        frame.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(
            frame,
            bg=C["map_bg"],
            highlightthickness=0,
            width=MAP_W, height=MAP_H,
        )
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", self._on_canvas_resize)

        # Fallback: subtle grid lines – mimic Waze's dark map tile seams.
        # These are drawn first and will be hidden behind the map tile if one loads.
        for x in range(0, MAP_W + 40, 55):
            self.canvas.create_line(x, 0, x, MAP_H + 80, fill="#1c2640",
                                    width=1, tags=("grid",))
        for y in range(0, MAP_H + 80, 55):
            self.canvas.create_line(0, y, MAP_W + 40, y, fill="#1c2640",
                                    width=1, tags=("grid",))

    # ── Legend ────────────────────────────────────────────────────────────────

    def _build_legend(self):
        """Colour-coded legend strip below the map (Waze info bar style)."""
        leg = tk.Frame(self.root, bg=C["header"], height=26)
        leg.pack(fill="x")
        leg.pack_propagate(False)

        items = [
            ("━━", C["paved"],    "Paved"),
            ("━━", C["unpaved"],  "Unpaved"),
            ("━━", C["closed"],   "Closed"),
            ("━━", C["route"],    "Active Route"),
            ("▲",  C["pot_icon"], "Deep Potholes"),
            ("●",  C["cis_icon"], "Broken Cisterns"),
        ]
        for sym, col, label in items:
            tk.Label(leg, text=sym, bg=C["header"], fg=col,
                     font=("Helvetica", 10, "bold")).pack(side="left", padx=(10, 1))
            tk.Label(leg, text=label, bg=C["header"], fg=C["sub"],
                     font=("Helvetica", 8)).pack(side="left", padx=(0, 8))

    # ── Google Maps tile ──────────────────────────────────────────────────────

    def _load_map_tile(self):
        """
        Fetch a Google Maps Static API tile centred on the Saint Catherine
        road network and draw it as the canvas background.

        Requirements:
          - GOOGLE_MAPS_API_KEY set in a .env file (or as a system env var)
          - pip install Pillow python-dotenv

        If the key is missing or the request fails the canvas keeps its dark
        grid fallback – no crash, just a log message.

        How the Static Maps URL works:
          center  = lat,lng of the map centre
          zoom    = how far in (11 covers roughly the whole road network)
          size    = WIDTHxHEIGHT pixels (matches canvas)
          maptype = roadmap / satellite / hybrid / terrain
          style   = custom dark-mode colours to match the app palette
          key     = your API key
        """
        if not GOOGLE_MAPS_API_KEY or not _MAP_LIBS:
            if not GOOGLE_MAPS_API_KEY:
                print("[map]  No GOOGLE_MAPS_API_KEY found in .env - using grid fallback.")
            else:
                print("[map]  Pillow not installed - using grid fallback.")
            return

        # Compute centre of the road network from the GPS coords (once)
        if self._centre_lat is None:
            lats = [ll[0] for ll in NODE_LATLNG.values()]
            lngs = [ll[1] for ll in NODE_LATLNG.values()]
            self._centre_lat = (min(lats) + max(lats)) / 2
            self._centre_lng = (min(lngs) + max(lngs)) / 2

        # Google's free Static Maps API caps tiles at 640x640.
        # We fetch at max free-tier size and scale to the actual canvas later.
        FETCH_W, FETCH_H = 640, 640
        url = (
            f"https://maps.googleapis.com/maps/api/staticmap"
            f"?center={self._centre_lat},{self._centre_lng}"
            f"&zoom={self._map_zoom}"
            f"&size={FETCH_W}x{FETCH_H}"
            f"&maptype={MAP_TYPE}"
            f"{_MAP_DARK_STYLE}"
            f"&key={GOOGLE_MAPS_API_KEY}"
        )

        try:
            with urlopen(url, timeout=10) as resp:
                data = resp.read()
            self._map_img_raw = Image.open(BytesIO(data))
            self._map_img_raw.load()   # force decode before BytesIO closes

            self._apply_tile_to_canvas()
            print(f"[map]  Google Maps tile loaded (zoom={self._map_zoom}).")

        except Exception as exc:
            print(f"[map]  Could not load Google Maps tile: {exc}")
            print("[map]  Falling back to grid background.")

    def _apply_tile_to_canvas(self):
        """
        Scale the stored raw tile to the current canvas size and draw it as the
        background.  Called after initial fetch and after every canvas resize.
        """
        if self._map_img_raw is None:
            return

        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        if w < 10 or h < 10:          # canvas not yet realised
            w, h = MAP_W, MAP_H

        img = self._map_img_raw.resize((w, h), Image.LANCZOS)
        self._map_photo = ImageTk.PhotoImage(img)

        self.canvas.delete("maptile")
        self.canvas.create_image(0, 0, anchor="nw",
                                 image=self._map_photo, tags=("maptile",))
        self.canvas.tag_lower("maptile")
        self.canvas.delete("grid")

        self._compute_node_positions(w, h)

    def _on_canvas_resize(self, event):
        """Debounced resize handler – redraws tile 200 ms after last resize event."""
        if self._map_img_raw is None:
            return
        if self._resize_job:
            self.root.after_cancel(self._resize_job)
        self._resize_job = self.root.after(200, self._on_resize_done)

    def _on_resize_done(self):
        self._resize_job = None
        self._apply_tile_to_canvas()
        self._draw_map()

    def _zoom_in(self):
        if self._map_zoom < 16:
            self._map_zoom += 1
            self._load_map_tile()
            self._draw_map()

    def _zoom_out(self):
        if self._map_zoom > 8:
            self._map_zoom -= 1
            self._load_map_tile()
            self._draw_map()

    def _compute_node_positions(self, canvas_w: int, canvas_h: int):
        """
        Project each node's GPS coordinate onto the canvas using Web Mercator.
        Uses self._map_zoom and self._centre_lat/_centre_lng set at load time.
        """
        if self._centre_lat is None:
            return

        cx_world, cy_world = _world_px(self._centre_lat, self._centre_lng,
                                        self._map_zoom)

        for node, (lat, lng) in NODE_LATLNG.items():
            nx, ny = _world_px(lat, lng, self._map_zoom)
            canvas_x = int(canvas_w / 2 + (nx - cx_world))
            canvas_y = int(canvas_h / 2 + (ny - cy_world))
            self._node_positions[node] = (canvas_x, canvas_y)

    # ── Search Panel ──────────────────────────────────────────────────────────

    def _build_search_panel(self):
        """
        Bottom search drawer – mirrors Waze's 'Where to?' bar.
        Two rows: (From / To dropdowns) and (Algorithm / Buttons).
        """
        panel = tk.Frame(self.root, bg=C["panel"])
        panel.pack(fill="x", side="bottom")

        # ── Row 1: From / To ─────────────────────────────────────────────────
        r1 = tk.Frame(panel, bg=C["panel"])
        r1.pack(fill="x", padx=14, pady=(10, 4))

        tk.Label(r1, text="From:", bg=C["panel"], fg=C["sub"],
                 font=("Helvetica", 9)).pack(side="left", padx=(0, 4))

        self.src_var = tk.StringVar()
        self.src_cb  = ttk.Combobox(r1, textvariable=self.src_var,
                                    width=19, state="readonly",
                                    font=("Helvetica", 10))
        self.src_cb.pack(side="left", padx=(0, 14))
        self.src_cb.bind("<<ComboboxSelected>>", self._on_src_changed)

        tk.Label(r1, text="To:", bg=C["panel"], fg=C["sub"],
                 font=("Helvetica", 9)).pack(side="left", padx=(0, 4))

        self.dst_var = tk.StringVar()
        self.dst_cb  = ttk.Combobox(r1, textvariable=self.dst_var,
                                    width=19, state="readonly",
                                    font=("Helvetica", 10))
        self.dst_cb.pack(side="left")

        # ── Row 2: Algorithm + Buttons ────────────────────────────────────────
        r2 = tk.Frame(panel, bg=C["panel"])
        r2.pack(fill="x", padx=14, pady=(0, 10))

        tk.Label(r2, text="Criteria:", bg=C["panel"], fg=C["sub"],
                 font=("Helvetica", 9)).pack(side="left", padx=(0, 4))

        self.algo_var = tk.StringVar(value=ALGORITHM_LABELS[0])
        self.algo_cb  = ttk.Combobox(r2, textvariable=self.algo_var,
                                     values=ALGORITHM_LABELS, width=32,
                                     state="readonly", font=("Helvetica", 10))
        self.algo_cb.pack(side="left", padx=(0, 14))

        # "Go Now" equivalent
        tk.Button(
            r2, text="  🔍  Find Route  ",
            bg=C["btn_go"], fg="white",
            font=("Helvetica", 11, "bold"),
            relief="flat", cursor="hand2",
            padx=10, pady=5,
            command=self._find_route,
        ).pack(side="left", padx=(0, 8))

        # Clear / reset
        tk.Button(
            r2, text="✕  Clear",
            bg=C["btn_clr"], fg=C["text"],
            font=("Helvetica", 10),
            relief="flat", cursor="hand2",
            padx=8, pady=5,
            command=self._clear_route,
        ).pack(side="left")

    # ── Route Result Panel ────────────────────────────────────────────────────

    def _build_route_panel(self):
        """
        Scrollable area that shows Waze-style route option cards.
        Each card displays: time, distance, via description, and can be clicked
        to switch the highlighted route on the map.
        """
        outer = tk.Frame(self.root, bg=C["bg"])
        outer.pack(fill="x", side="bottom")

        # Scrollable canvas for route cards (Waze bottom sheet)
        self._card_canvas = tk.Canvas(
            outer, bg=C["bg"], height=0,
            highlightthickness=0,
        )
        self._card_canvas.pack(fill="x")

        self._card_frame = tk.Frame(self._card_canvas, bg=C["bg"])
        self._card_canvas.create_window((0, 0), window=self._card_frame, anchor="nw")

        # No-path label (hidden until needed)
        self._no_path_label = tk.Label(
            outer, text="", bg=C["bg"], fg=C["danger"],
            font=("Helvetica", 10, "bold"),
        )
        self._no_path_label.pack(anchor="w", padx=16)

    # =========================================================================
    # DATA MANAGEMENT
    # =========================================================================

    def _refresh_data(self):
        """Fetch the latest facts from Prolog and update the search dropdowns."""
        self.all_nodes      = self.bridge.get_all_nodes()
        self.all_roads      = self.bridge.get_all_roads()
        self.all_conditions = self.bridge.get_all_conditions()

        # Give any brand-new nodes a canvas position so they render immediately
        self._assign_missing_node_positions()

        names = [display_name(n) for n in self.all_nodes]
        self.src_cb["values"] = names
        self.dst_cb["values"] = names

    def _assign_missing_node_positions(self):
        """
        Auto-place any node that has no canvas position yet.
        Called after every data refresh so admin-added nodes appear immediately.

        New nodes are arranged in a horizontal row across the top of the canvas,
        clearly separated from the existing network so they are easy to spot.
        """
        missing = [n for n in self.all_nodes if n not in self._node_positions]
        if not missing:
            return

        cw = self.canvas.winfo_width() or MAP_W
        # Row just below the top edge; spread nodes evenly across the width
        margin  = 70
        step    = max(90, (cw - 2 * margin) // max(1, len(missing)))
        row_y   = 36

        for i, node in enumerate(missing):
            x = margin + i * step
            self._node_positions[node] = (x, row_y)
            print(f"[map]  New node '{node}' auto-placed at ({x}, {row_y}) "
                  f"- add GPS coords to NODE_LATLNG for accurate positioning.")

    # =========================================================================
    # MAP DRAWING
    # =========================================================================

    def _draw_map(self):
        """
        Full map redraw sequence:
          1. Roads (coloured by type and status, highlighted if on active route)
          2. Condition icons at road midpoints
          3. Node circles and labels
        """
        self.canvas.delete("road", "node", "lbl", "icon")
        self._icon_items.clear()

        self._draw_roads()
        self._draw_condition_icons()
        self._draw_nodes()

    # ── Roads ─────────────────────────────────────────────────────────────────

    def _draw_roads(self):
        """
        Draw each road/7 fact as a thick coloured line on the canvas.

        Colour priority:
          closed road   →  red
          on active route →  bright cyan glow (Waze blue route style)
          paved         →  blue
          unpaved       →  orange-brown

        Distance labels are printed near each road midpoint.
        """
        for road in self.all_roads:
            src    = road["src"]
            dst    = road["dst"]
            rtype  = road["type"]
            status = road["status"]

            # Skip roads whose nodes have no canvas position yet
            # (can happen if admin adds a road with a brand-new node)
            if src not in self._node_positions or dst not in self._node_positions:
                continue

            x1, y1 = self._node_positions[src]
            x2, y2 = self._node_positions[dst]

            on_route = ((src, dst) in self.route_edges or
                        (dst, src) in self.route_edges)

            if on_route:
                # Outer glow layer (thick cyan)
                self.canvas.create_line(
                    x1, y1, x2, y2,
                    fill=C["route"], width=ROUTE_W + 4,
                    capstyle="round", tags=("road",),
                )
                # Dashed white centreline  (Waze's dashed active-route style)
                self.canvas.create_line(
                    x1, y1, x2, y2,
                    fill="white", width=2,
                    capstyle="round", dash=(10, 6),
                    tags=("road",),
                )
            else:
                # Determine colour
                if status == "closed":
                    colour = C["closed"]
                elif rtype == "paved":
                    colour = C["paved"]
                else:
                    colour = C["unpaved"]

                self.canvas.create_line(
                    x1, y1, x2, y2,
                    fill=colour, width=ROAD_W,
                    capstyle="round", tags=("road",),
                )

            # Distance label at midpoint (small, subtle – like Waze distance numbers)
            mx, my = (x1 + x2) // 2, (y1 + y2) // 2
            self.canvas.create_text(
                mx, my - 11,
                text=f"{road['dist']}km",
                fill=C["sub"], font=("Helvetica", 7),
                tags=("lbl",),
            )

    # ── Condition icons ────────────────────────────────────────────────────────

    def _draw_condition_icons(self):
        """
        Draw Waze-style hazard icons at the midpoint of each road segment
        that has a special_conditions/3 entry.

        Icons:
          deep_potholes   →  yellow warning triangle  ▲  with '!'
          broken_cisterns →  blue circle              ●  with '~'
          other           →  orange circle            ●  with '!'

        Hovering triggers a tooltip popup (Waze road report bubble style).
        """
        # Group conditions by segment so we can offset multiple icons
        seg_conds = defaultdict(list)
        for cond in self.all_conditions:
            seg_conds[(cond["src"], cond["dst"])].append(cond["condition"])

        for (src, dst), conds in seg_conds.items():
            if src not in self._node_positions or dst not in self._node_positions:
                continue

            x1, y1 = self._node_positions[src]
            x2, y2 = self._node_positions[dst]
            mx, my = (x1 + x2) // 2, (y1 + y2) // 2

            # Space icons horizontally when there are multiple on one segment
            n       = len(conds)
            start_x = mx - (n - 1) * 20 // 2

            for i, condition in enumerate(conds):
                cx = start_x + i * 20
                cy = my + 8

                if condition == "deep_potholes":
                    iid = self._icon_pothole(cx, cy)
                elif condition == "broken_cisterns":
                    iid = self._icon_cistern(cx, cy)
                else:
                    iid = self._icon_generic(cx, cy)

                tip_text = f"⚠  {format_condition(condition)}"
                self._bind_tip(iid, tip_text)
                self._icon_items[(src, dst, condition)] = iid

    def _icon_pothole(self, cx, cy):
        """
        Draw a yellow warning triangle for deep_potholes.
        Matches the Waze hazard triangle icon.
        """
        s   = 9   # half-size of triangle
        pts = [cx, cy - s, cx - s, cy + s, cx + s, cy + s]
        # Dark shadow for depth
        self.canvas.create_polygon(
            [cx, cy - s - 1, cx - s - 1, cy + s + 1, cx + s + 1, cy + s + 1],
            fill="#0a1020", outline="", tags=("icon",),
        )
        iid = self.canvas.create_polygon(
            pts, fill=C["pot_icon"], outline="#b09010", width=1,
            tags=("icon",),
        )
        self.canvas.create_text(
            cx, cy + 2, text="!", fill="#1a1f2e",
            font=("Helvetica", 7, "bold"), tags=("icon",),
        )
        return iid

    def _icon_cistern(self, cx, cy):
        """
        Draw a blue circle for broken_cisterns (water hazard).
        Matches the Waze water/hazard bubble icon.
        """
        r = 8
        self.canvas.create_oval(
            cx - r - 1, cy - r - 1, cx + r + 1, cy + r + 1,
            fill="#0a1020", outline="", tags=("icon",),
        )
        iid = self.canvas.create_oval(
            cx - r, cy - r, cx + r, cy + r,
            fill=C["cis_icon"], outline="#2070bb", width=1,
            tags=("icon",),
        )
        self.canvas.create_text(
            cx, cy, text="~", fill="white",
            font=("Helvetica", 9, "bold"), tags=("icon",),
        )
        return iid

    def _icon_generic(self, cx, cy):
        """Draw a generic orange circle icon for other conditions."""
        r = 8
        iid = self.canvas.create_oval(
            cx - r, cy - r, cx + r, cy + r,
            fill="#ff8800", outline="#cc5500", width=1, tags=("icon",),
        )
        self.canvas.create_text(
            cx, cy, text="!", fill="white",
            font=("Helvetica", 8, "bold"), tags=("icon",),
        )
        return iid

    # ── Nodes ─────────────────────────────────────────────────────────────────

    def _draw_nodes(self):
        """
        Draw a circle + label for each node.

        The currently selected source node gets a blue glowing ring
        (Waze's 'you are here' blue pulsing dot).
        The destination of the active route gets a 🏁 flag above it.
        """
        selected_src = prolog_name(self.src_var.get()) if self.src_var.get() else None

        for node, (x, y) in self._node_positions.items():
            r = NODE_R

            if node == selected_src:
                # Outer glow ring
                self.canvas.create_oval(
                    x - r - 5, y - r - 5, x + r + 5, y + r + 5,
                    fill=C["node_sel"], outline="", tags=("node",),
                )
                fill = C["node_sel"]
                txt  = "white"
            else:
                fill = C["node_fill"]
                txt  = C["node_text"]

            self.canvas.create_oval(
                x - r, y - r, x + r, y + r,
                fill=fill, outline=C["node_out"], width=2,
                tags=("node",),
            )

            # Abbreviated label below the circle
            label = display_name(node)
            if len(label) > 13:
                label = label[:11] + "…"
            self.canvas.create_text(
                x, y + r + 10,
                text=label, fill=C["text"],
                font=("Helvetica", 8, "bold"),
                tags=("lbl",),
            )

        # Destination flag on active route
        if self.active_path:
            dst_node = self.active_path[-1]
            if dst_node in self._node_positions:
                dx, dy = self._node_positions[dst_node]
                self.canvas.create_text(
                    dx, dy - NODE_R - 12,
                    text="🏁", font=("Helvetica", 16),
                    tags=("node",),
                )

    # =========================================================================
    # TOOLTIPS  (Waze hazard report popup behaviour)
    # =========================================================================

    def _bind_tip(self, item_id, text: str):
        """Bind hover enter/leave events to a canvas item for tooltip display."""
        self.canvas.tag_bind(item_id, "<Enter>",
                             lambda e, t=text: self._show_tip(e, t))
        self.canvas.tag_bind(item_id, "<Leave>",
                             lambda e: self._hide_tip())

    def _show_tip(self, event, text: str):
        """
        Display a small dark tooltip window near the mouse cursor.
        Styled like Waze's yellow road-report popups.
        """
        self._hide_tip()

        rx = self.canvas.winfo_rootx() + event.x + 16
        ry = self.canvas.winfo_rooty() + event.y - 30

        self._tooltip = tw = tk.Toplevel(self.root)
        tw.wm_overrideredirect(True)   # No title bar or border
        tw.wm_geometry(f"+{rx}+{ry}")
        tw.configure(bg=C["pot_icon"])

        tk.Label(
            tw, text=f"  {text}  ",
            bg=C["pot_icon"], fg="#1a1f2e",
            font=("Helvetica", 9, "bold"),
            relief="flat", bd=2,
        ).pack()

    def _hide_tip(self):
        """Destroy the active tooltip window if it exists."""
        if self._tooltip:
            self._tooltip.destroy()
            self._tooltip = None

    # =========================================================================
    # EVENT HANDLERS
    # =========================================================================

    def _on_src_changed(self, _event=None):
        """
        Called when the user picks a source node.
        Refreshes node drawing so the selected source gets the blue glow.
        """
        self.canvas.delete("node", "lbl")
        self._draw_nodes()

    def _find_route(self):
        """
        Primary search action – the 'Go Now' button equivalent.

        Steps:
          1. Validate source, destination, and selection.
          2. Run the user-selected algorithm via the bridge.
          3. Run Dijkstra distance + Dijkstra time as automatic alternatives.
          4. Build route cards and highlight the primary route on the map.
        """
        src_d = self.src_var.get()
        dst_d = self.dst_var.get()
        algo  = self.algo_var.get()

        # ── Basic validation ──────────────────────────────────────────────────
        if not src_d or not dst_d:
            messagebox.showwarning("Missing Input",
                                   "Please select both a source and a destination.")
            return

        src = prolog_name(src_d)
        dst = prolog_name(dst_d)

        if not validate_nodes_different(src, dst):
            messagebox.showwarning("Invalid Input",
                                   "Source and destination must be different locations.")
            return

        if not validate_node(src, self.all_nodes) or \
           not validate_node(dst, self.all_nodes):
            messagebox.showerror("Unknown Node",
                                 "Selected node is not in the road network.")
            return

        # ── Run primary algorithm ─────────────────────────────────────────────
        method, has_cost = ALGORITHM_MAP[algo]
        bridge_fn        = getattr(self.bridge, f"query_{method}")

        if has_cost:
            primary_path, primary_cost = bridge_fn(src, dst)
        else:
            primary_path = bridge_fn(src, dst)
            primary_cost = None

        if not primary_path:
            self._show_no_path(src_d, dst_d, algo)
            return

        # ── Auto-compute alternatives (like Waze's route list) ────────────────
        alt_dis_path, alt_dis_cost = self.bridge.query_dijkstra_distance(src, dst)
        alt_tim_path, alt_tim_cost = self.bridge.query_dijkstra_time(src, dst)

        # Compute Python-side totals for display
        def totals(path, cost_override, is_time=False):
            d, t = compute_path_totals(path, self.all_roads, self.all_conditions)
            if cost_override is not None:
                if is_time:
                    t = cost_override
                else:
                    d = cost_override
            return d, t

        pri_dist, pri_time   = totals(primary_path, primary_cost,
                                      is_time=("time" in method))
        dis_dist, dis_time   = totals(alt_dis_path, alt_dis_cost,
                                      is_time=False) if alt_dis_path else (0, 0)
        tim_dist, tim_time   = totals(alt_tim_path, alt_tim_cost,
                                      is_time=True)  if alt_tim_path else (0, 0)

        # Build the ordered options list – primary first, no duplicates
        seen = []
        options = []

        def _add(path, label, dist, time_val):
            if path and path not in seen:
                seen.append(path)
                options.append((path, label, dist, time_val))

        _add(primary_path, algo, pri_dist, pri_time)
        _add(alt_dis_path, "Shortest Distance  (Dijkstra)", dis_dist, dis_time)
        _add(alt_tim_path, "Fastest Route      (Dijkstra)", tim_dist, tim_time)

        self.route_options = options

        # ── Activate the primary route on the map ─────────────────────────────
        self._activate_route(primary_path)
        self._render_route_cards(options, selected_idx=0)

    def _activate_route(self, path: list):
        """
        Highlight a given path on the map canvas and store it as the active route.
        """
        self.active_path = path
        self.route_edges = set()
        for i in range(len(path) - 1):
            self.route_edges.add((path[i], path[i + 1]))
        self._draw_map()

    # ── Route cards (Waze's route options list) ────────────────────────────────

    def _render_route_cards(self, options: list, selected_idx: int = 0):
        """
        Render one card per route option below the search panel.
        Each card shows: time, distance, route description, 'Best' badge.
        Clicking a card highlights that route on the map – Waze UX pattern.
        """
        # Clear existing cards
        for widget in self._card_frame.winfo_children():
            widget.destroy()
        self._no_path_label.configure(text="")

        if not options:
            return

        # Resize the card canvas to fit content
        card_h = 60
        self._card_canvas.configure(height=min(len(options) * card_h + 10,
                                               card_h * 3 + 10))

        for idx, (path, label, dist, time_val) in enumerate(options):
            is_sel = (idx == selected_idx)

            # Card frame
            card = tk.Frame(
                self._card_frame,
                bg=C["card_sel"] if is_sel else C["card_bg"],
                cursor="hand2",
            )
            card.pack(fill="x", padx=8, pady=(4 if idx == 0 else 2, 0))

            # Left accent bar (Waze's blue selected-route highlight)
            bar_col = C["card_border"] if is_sel else C["border"]
            tk.Frame(card, bg=bar_col, width=4).pack(side="left", fill="y")

            # Time (big, like Waze)
            time_str = format_time(time_val)
            tk.Label(
                card, text=time_str,
                bg=card["bg"], fg=C["route"] if is_sel else C["text"],
                font=("Helvetica", 14, "bold"),
                width=10, anchor="w",
            ).pack(side="left", padx=(10, 0), pady=8)

            # "Best" badge on the primary route
            if idx == 0:
                tk.Label(
                    card, text=" Best ",
                    bg=C["route"], fg="#1a1f2e",
                    font=("Helvetica", 8, "bold"),
                ).pack(side="left", padx=4)

            # Distance + via label
            info_frame = tk.Frame(card, bg=card["bg"])
            info_frame.pack(side="left", padx=8, fill="x", expand=True)

            tk.Label(
                info_frame,
                text=f"{format_distance(dist)}  ·  Via {format_path(path[1:-1] if len(path) > 2 else path[1:])}",
                bg=card["bg"], fg=C["sub"],
                font=("Helvetica", 9),
                anchor="w",
            ).pack(anchor="w")

            tk.Label(
                info_frame,
                text=label.strip(),
                bg=card["bg"], fg=C["sub"],
                font=("Helvetica", 8),
                anchor="w",
            ).pack(anchor="w")

            # Bind click to switch route
            _path = path
            _idx  = idx
            for widget in [card] + list(card.winfo_children()):
                widget.bind(
                    "<Button-1>",
                    lambda e, p=_path, i=_idx: self._on_card_click(p, i),
                )

    def _on_card_click(self, path: list, idx: int):
        """
        User clicked a route card → highlight that route on the map
        and re-render cards with the new selection.
        """
        self._activate_route(path)
        self._render_route_cards(self.route_options, selected_idx=idx)

    def _show_no_path(self, src: str, dst: str, algo: str):
        """Show a Waze-style 'no route available' notification."""
        self._clear_route()
        self._no_path_label.configure(
            text=f"No path available from {src} to {dst} using '{algo.strip()}'."
        )
        self._card_canvas.configure(height=0)
        messagebox.showinfo(
            "No Route Found",
            f"No valid path from {src} to {dst}\n"
            f"using criteria: {algo.strip()}\n\n"
            "Try a different algorithm or check road statuses.",
        )

    def _clear_route(self):
        """Reset all route state and redraw the map in its neutral state."""
        self.active_path   = []
        self.route_edges   = set()
        self.route_options = []

        for widget in self._card_frame.winfo_children():
            widget.destroy()
        self._card_canvas.configure(height=0)
        self._no_path_label.configure(text="")
        self._draw_map()

    # =========================================================================
    # ADMIN PANEL
    # =========================================================================

    def _open_admin(self):
        """
        Show a password prompt then open the AdminPanel Toplevel.
        Simple gate – replace with proper auth for production use.
        """
        pw_win = tk.Toplevel(self.root)
        pw_win.title("Admin Login")
        pw_win.geometry("330x170")
        pw_win.configure(bg=C["bg"])
        pw_win.resizable(False, False)
        pw_win.grab_set()    # Modal – blocks main window interaction

        tk.Label(
            pw_win, text="Enter Admin Password",
            bg=C["bg"], fg=C["text"],
            font=("Helvetica", 12, "bold"),
        ).pack(pady=(18, 6))

        pw_var = tk.StringVar()
        pw_ent = tk.Entry(
            pw_win, textvariable=pw_var,
            show="●", width=24,
            bg=C["inp"], fg=C["text"],
            insertbackground=C["text"],
            font=("Helvetica", 11), relief="flat",
        )
        pw_ent.pack(pady=6)
        pw_ent.focus()

        err_lbl = tk.Label(pw_win, text="", bg=C["bg"], fg=C["danger"])
        err_lbl.pack()

        def _check():
            if pw_var.get() == ADMIN_PWD:
                pw_win.destroy()
                AdminPanel(
                    self.root, self.bridge,
                    kb_path="aiproject.pl",
                    on_close=self._on_admin_closed,
                )
            else:
                err_lbl.configure(text="Incorrect password. Try again.")

        pw_ent.bind("<Return>", lambda _e: _check())
        tk.Button(
            pw_win, text="Login",
            bg=C["accent"], fg="white",
            font=("Helvetica", 10, "bold"),
            relief="flat", cursor="hand2",
            padx=14, pady=4,
            command=_check,
        ).pack(pady=8)

    def _on_admin_closed(self):
        """
        Called by AdminPanel whenever data changes or the window is closed.
        Refreshes Prolog data and redraws the map so edits appear immediately.
        """
        self._refresh_data()
        self._draw_map()
