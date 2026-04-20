# interface.py — PathFinder GUI: interactive map, search panel, route cards, admin access.

import tkinter as tk
from tkinter import ttk, messagebox
import os

# cspell:ignore tkintermapview
try:
    import tkintermapview  # type: ignore[import-untyped]
    _MAP_LIVE = True
except ImportError:
    tkintermapview = None
    _MAP_LIVE = False

try:
    __import__("dotenv").load_dotenv()   # reads .env if present
except Exception:
    pass

GOOGLE_MAPS_API_KEY: str = os.getenv("GOOGLE_MAPS_API_KEY", "")

from utils import (
    display_name, prolog_name,
    format_path, format_distance, format_time,
    format_condition, compute_path_totals,
    validate_node, validate_nodes_different,
    ALGORITHM_MAP, ALGORITHM_LABELS,
)
from admin import AdminPanel


# ── Colour palette (Waze dark-mode inspired) ──────────────────────────────────
C = {
    "bg":          "#1a1f2e",
    "map_bg":      "#16213e",
    "header":      "#12192a",
    "panel":       "#1e2636",
    "border":      "#2a3a54",
    "paved":       "#4a9eff",
    "unpaved":     "#c4944a",
    "closed":      "#ff4444",
    "route":       "#00d4ff",
    "route_alt":   "#888888",
    "node_fill":   "#ffffff",
    "node_sel":    "#4a9eff",
    "node_out":    "#4a9eff",
    "node_text":   "#1a1f2e",
    "pot_icon":    "#f0c040",
    "cis_icon":    "#5eb8ff",
    "land_icon":   "#c97c30",
    "flood_icon":  "#1a9eba",
    "text":        "#e8eaf0",
    "sub":         "#8b9cb5",
    "accent":      "#4a9eff",
    "success":     "#2ecc71",
    "danger":      "#e74c3c",
    "card_sel":    "#1d3a5a",
    "card_bg":     "#1e2636",
    "card_border": "#00d4ff",
    "inp":         "#252d3d",
    "btn_go":      "#00bcd4",
    "btn_clr":     "#546e7a",
}

# Tooltip / marker details for each road condition
CONDITION_TIPS = {
    "deep_potholes":   ("Deep Potholes",
                        "Road surface severely damaged. +5 min delay.",
                        C["pot_icon"]),
    "broken_cisterns": ("Broken Cisterns",
                        "Water infrastructure hazard on this segment.",
                        C["cis_icon"]),
    "landslide":       ("Landslide",
                        "Road partially blocked by debris. Use caution.",
                        C["land_icon"]),
    "flooded":         ("Flooded Road",
                        "Water on road surface. May be impassable.",
                        C["flood_icon"]),
}

CONDITION_SYMBOLS = {
    "deep_potholes":   "⚠",
    "broken_cisterns": "◆",
    "landslide":       "▼",
    "flooded":         "〰",
}

# Real GPS coordinates for each road node (Saint Catherine, Jamaica)
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

ADMIN_PWD    = "admin123"   # Demo password – replace with proper auth in production
DEFAULT_ZOOM = 11

# CartoDB Dark Matter tile server – dark navy aesthetic, no API key required.
# Matches the app's colour palette out of the box.
TILE_SERVER = "https://a.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png"

# Road line widths (pixels) for the live map paths
_ROAD_WIDTH_NORMAL = 4
_ROAD_WIDTH_ROUTE  = 7


class PathFinderApp:
    """Main application window — map, search, route cards, admin."""

    def __init__(self, root: tk.Tk, bridge):
        self.root   = root
        self.bridge = bridge

        # Live data – refreshed from Prolog whenever the map redraws
        self.all_nodes      = []
        self.all_roads      = []
        self.all_conditions = []

        # Route state
        self.active_path   = []    # node atoms of the highlighted route
        self.route_edges   = set() # (src, dst) pairs in the active route
        self.route_options = []    # list of (path, label, time, dist) for the cards

        # tkintermapview overlay objects (kept so we can delete/redraw them)
        self._road_paths        = []   # set_path() return values
        self._node_markers      = []   # set_marker() for network nodes
        self._condition_markers = []   # set_marker() for hazard icons

        # Map state
        self._map_zoom       = DEFAULT_ZOOM
        self._network_center = None    # (lat, lng) mean of all node coords

        # Condition info display (StringVar wired to legend strip)
        self._cond_info_var  = None
        self._cond_clear_job = None    # pending after() job to clear info text

        self._build_window()
        self._refresh_data()
        self._draw_map()

    # ── WINDOW LAYOUT ─────────────────────────────────────────────────────────

    def _build_window(self):
        self.root.title("PathFinder – Jamaica Rural Roads")
        self.root.configure(bg=C["bg"])
        self.root.geometry("920x860")
        self.root.resizable(True, True)
        self.root.minsize(720, 680)

        self._build_header()
        self._build_map()
        self._build_legend()
        self._build_search_panel()
        self._build_route_panel()

    # ── Header ────────────────────────────────────────────────────────────────

    def _build_header(self):
        hdr = tk.Frame(self.root, bg=C["header"], height=52)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        tk.Label(
            hdr, text="  🗺  PathFinder  |  Jamaica Rural Roads",
            bg=C["header"], fg=C["text"],
            font=("Helvetica", 14, "bold"),
        ).pack(side="left", padx=12, pady=10)

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

        # Zoom controls
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

    # ── Live Map ──────────────────────────────────────────────────────────────

    def _build_map(self):
        """Create the live map widget. Shows an install hint if tkintermapview is missing."""
        frame = tk.Frame(self.root, bg=C["map_bg"])
        frame.pack(fill="both", expand=True)

        if not _MAP_LIVE:
            tk.Label(
                frame,
                text=(
                    "Live map requires tkintermapview.\n"
                    "Run:  pip install tkintermapview\n"
                    "Then restart the application."
                ),
                bg=C["map_bg"], fg=C["danger"],
                font=("Helvetica", 12),
                justify="center",
            ).pack(expand=True)
            self.map_widget = None
            return

        self.map_widget = tkintermapview.TkinterMapView(
            frame,
            corner_radius=0,
        )
        self.map_widget.pack(fill="both", expand=True)

        # Dark tile server – visually consistent with the navy UI theme
        self.map_widget.set_tile_server(TILE_SERVER, max_zoom=19)

        # Compute and store the geographic centre of the road network
        all_lats = [ll[0] for ll in NODE_LATLNG.values()]
        all_lngs = [ll[1] for ll in NODE_LATLNG.values()]
        self._network_center = (
            (min(all_lats) + max(all_lats)) / 2,
            (min(all_lngs) + max(all_lngs)) / 2,
        )

        self.map_widget.set_position(*self._network_center)
        self.map_widget.set_zoom(self._map_zoom)

    # ── Legend ────────────────────────────────────────────────────────────────

    def _build_legend(self):
        """Colour-coded legend strip; right side shows hazard detail on marker click."""
        leg = tk.Frame(self.root, bg=C["header"], height=26)
        leg.pack(fill="x")
        leg.pack_propagate(False)

        items = [
            ("━━", C["paved"],      "Paved"),
            ("━━", C["unpaved"],    "Unpaved"),
            ("━━", C["closed"],     "Closed"),
            ("━━", C["route"],      "Active Route"),
            ("▲",  C["pot_icon"],   "Deep Potholes"),
            ("●",  C["cis_icon"],   "Broken Cisterns"),
            ("▼",  C["land_icon"],  "Landslide"),
            ("≈",  C["flood_icon"], "Flooded"),
        ]
        for sym, col, label in items:
            tk.Label(
                leg, text=sym, bg=C["header"], fg=col,
                font=("Helvetica", 10, "bold"),
            ).pack(side="left", padx=(10, 1))
            tk.Label(
                leg, text=label, bg=C["header"], fg=C["sub"],
                font=("Helvetica", 8),
            ).pack(side="left", padx=(0, 8))

        # Right-aligned condition info label (updated on marker click)
        self._cond_info_var = tk.StringVar(value="")
        tk.Label(
            leg,
            textvariable=self._cond_info_var,
            bg=C["header"], fg=C["text"],
            font=("Helvetica", 8, "italic"),
        ).pack(side="right", padx=12)

    # ── Search Panel ──────────────────────────────────────────────────────────

    def _build_search_panel(self):
        """From / To dropdowns, criteria selector, Find Route and Clear buttons."""
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

        tk.Button(
            r2, text="  🔍  Find Route  ",
            bg=C["btn_go"], fg="white",
            font=("Helvetica", 11, "bold"),
            relief="flat", cursor="hand2",
            padx=10, pady=5,
            command=self._find_route,
        ).pack(side="left", padx=(0, 8))

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
        """Scrollable container for route result cards shown after a search."""
        outer = tk.Frame(self.root, bg=C["bg"])
        outer.pack(fill="x", side="bottom")

        self._card_canvas = tk.Canvas(
            outer, bg=C["bg"], height=0,
            highlightthickness=0,
        )
        self._card_canvas.pack(fill="x")

        self._card_frame = tk.Frame(self._card_canvas, bg=C["bg"])
        self._card_canvas.create_window((0, 0), window=self._card_frame, anchor="nw")

        self._no_path_label = tk.Label(
            outer, text="", bg=C["bg"], fg=C["danger"],
            font=("Helvetica", 10, "bold"),
        )
        self._no_path_label.pack(anchor="w", padx=16)

    # ── DATA MANAGEMENT ───────────────────────────────────────────────────────

    def _refresh_data(self):
        """Fetch the latest facts from Prolog and update the search dropdowns."""
        self.all_nodes      = self.bridge.get_all_nodes()
        self.all_roads      = self.bridge.get_all_roads()
        self.all_conditions = self.bridge.get_all_conditions()

        names = [display_name(n) for n in self.all_nodes]
        self.src_cb["values"] = names
        self.dst_cb["values"] = names

    # ── MAP OVERLAY DRAWING ───────────────────────────────────────────────────

    def _clear_map_overlays(self):
        """Delete every path and marker this app has placed on the map."""
        for obj in self._road_paths + self._node_markers + self._condition_markers:
            try:
                obj.delete()
            except Exception:
                pass
        self._road_paths.clear()
        self._node_markers.clear()
        self._condition_markers.clear()

    def _clear_node_markers_only(self):
        """Delete only node markers – used for cheap source-highlight refresh."""
        for m in self._node_markers:
            try:
                m.delete()
            except Exception:
                pass
        self._node_markers.clear()

    def _draw_map(self):
        """Redraw all map overlays: roads, hazard markers, node pins."""
        if self.map_widget is None:
            return
        self._clear_map_overlays()
        self._draw_roads()
        self._draw_condition_icons()
        self._draw_nodes()

    # ── Roads ─────────────────────────────────────────────────────────────────

    def _draw_roads(self):
        """Draw each road segment coloured by status/type; cyan + thick on the active route."""
        for road in self.all_roads:
            src    = road["src"]
            dst    = road["dst"]
            rtype  = road["type"]
            status = road["status"]

            if src not in NODE_LATLNG or dst not in NODE_LATLNG:
                continue

            pos1 = NODE_LATLNG[src]
            pos2 = NODE_LATLNG[dst]

            on_route = (src, dst) in self.route_edges or \
                       (dst, src) in self.route_edges

            if on_route:
                color = C["route"]
                width = _ROAD_WIDTH_ROUTE
            elif status == "closed":
                color = C["closed"]
                width = _ROAD_WIDTH_NORMAL
            elif rtype == "paved":
                color = C["paved"]
                width = _ROAD_WIDTH_NORMAL
            else:
                color = C["unpaved"]
                width = _ROAD_WIDTH_NORMAL

            path = self.map_widget.set_path([pos1, pos2], color=color, width=width)
            self._road_paths.append(path)

    # ── Condition Hazard Markers ───────────────────────────────────────────────

    def _draw_condition_icons(self):
        """Place a hazard pin at the midpoint of each segment that has a special condition."""
        for cond in self.all_conditions:
            src       = cond["src"]
            dst       = cond["dst"]
            condition = cond["condition"]

            if src not in NODE_LATLNG or dst not in NODE_LATLNG:
                continue

            lat1, lng1 = NODE_LATLNG[src]
            lat2, lng2 = NODE_LATLNG[dst]
            mid_lat    = (lat1 + lat2) / 2
            mid_lng    = (lng1 + lng2) / 2

            tip_info = CONDITION_TIPS.get(condition)
            if tip_info:
                title, detail, color = tip_info
            else:
                title  = format_condition(condition)
                detail = ""
                color  = "#ff8800"

            sym = CONDITION_SYMBOLS.get(condition, "!")

            # Darken the outer ring for a two-tone pin look
            outer = {
                C["pot_icon"]:  "#7a6010",
                C["cis_icon"]:  "#1a4a7a",
                C["land_icon"]: "#6a3a10",
                C["flood_icon"]:"#0a5a6a",
            }.get(color, "#333333")

            marker = self.map_widget.set_marker(
                mid_lat, mid_lng,
                text=sym,
                marker_color_circle=color,
                marker_color_outside=outer,
                text_color="#ffffff",
                command=lambda *_a, t=title, d=detail, c=color:
                    self._show_condition_info(t, d, c),
            )
            self._condition_markers.append(marker)

    # ── Node Markers ──────────────────────────────────────────────────────────

    def _draw_nodes(self):
        """Pin every network node; cyan ▶ = source, green ★ = dest, ● = on route."""
        selected_src = prolog_name(self.src_var.get()) if self.src_var.get() else None
        dst_node     = self.active_path[-1] if self.active_path else None
        route_set    = set(self.active_path)

        for node, (lat, lng) in NODE_LATLNG.items():
            label = display_name(node)
            if len(label) > 13:
                label = label[:11] + "…"

            if node == selected_src:
                circle_color  = "#00d4ff"
                outside_color = "#004f66"
                text_color    = "#ffffff"
                label         = "▶ " + label
            elif node == dst_node:
                circle_color  = "#2ecc71"
                outside_color = "#145a32"
                text_color    = "#ffffff"
                label         = "★ " + label
            elif node in route_set:
                circle_color  = "#00b4d8"
                outside_color = "#003d52"
                text_color    = "#e0f7ff"
                label         = "● " + label
            else:
                circle_color  = "#4a9eff"
                outside_color = "#1a2a4a"
                text_color    = "#b8d0ff"

            marker = self.map_widget.set_marker(
                lat, lng,
                text=label,
                marker_color_circle=circle_color,
                marker_color_outside=outside_color,
                text_color=text_color,
            )
            self._node_markers.append(marker)

    # ── Condition Info Display ────────────────────────────────────────────────

    def _show_condition_info(self, title: str, detail: str, color: str):
        """
        Update the legend strip with the clicked hazard's details.
        Auto-clears after 5 seconds.
        """
        if self._cond_info_var is None:
            return

        # Cancel any pending clear job
        if self._cond_clear_job is not None:
            self.root.after_cancel(self._cond_clear_job)

        self._cond_info_var.set(f"  ⚠  {title}  –  {detail}")
        self._cond_clear_job = self.root.after(
            5000, lambda: self._cond_info_var.set("")
        )

    # ── ZOOM ──────────────────────────────────────────────────────────────────

    def _zoom_in(self):
        if self.map_widget and self._map_zoom < 18:
            self._map_zoom += 1
            self.map_widget.set_zoom(self._map_zoom)

    def _zoom_out(self):
        if self.map_widget and self._map_zoom > 8:
            self._map_zoom -= 1
            self.map_widget.set_zoom(self._map_zoom)

    # ── EVENT HANDLERS ────────────────────────────────────────────────────────

    def _on_src_changed(self, _event=None):
        """Refresh node pins only so the selected source gets its cyan glow instantly."""
        if self.map_widget is None:
            return
        self._clear_node_markers_only()
        self._draw_nodes()

    def _find_route(self):
        """Validate input, run the chosen algorithm, generate alternative routes, update the map."""
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

        def totals(path, cost_override, is_time=False):
            d, t = compute_path_totals(path, self.all_roads, self.all_conditions)
            if cost_override is not None:
                if is_time:
                    t = cost_override
                else:
                    d = cost_override
            return d, t

        pri_dist, pri_time = totals(primary_path, primary_cost,
                                    is_time=("time" in method))
        dis_dist, dis_time = totals(alt_dis_path, alt_dis_cost,
                                    is_time=False) if alt_dis_path else (0, 0)
        tim_dist, tim_time = totals(alt_tim_path, alt_tim_cost,
                                    is_time=True)  if alt_tim_path else (0, 0)

        # Build the ordered options list – primary first, no duplicates
        seen    = []
        options = []

        def _add(path, label, dist, time_val):
            if path and path not in seen:
                seen.append(path)
                options.append((path, label, dist, time_val))

        _add(primary_path, algo,                              pri_dist, pri_time)
        _add(alt_dis_path, "Shortest Distance  (Dijkstra)",  dis_dist, dis_time)
        _add(alt_tim_path, "Fastest Route      (Dijkstra)",  tim_dist, tim_time)

        self.route_options = options

        # ── Activate the primary route on the map ─────────────────────────────
        self._activate_route(primary_path)
        self._render_route_cards(options, selected_idx=0)

    def _activate_route(self, path: list):
        """Store the active route edges, redraw the map, and trigger cascade zoom."""
        self.active_path = path
        self.route_edges = set()
        for i in range(len(path) - 1):
            self.route_edges.add((path[i], path[i + 1]))

        self._draw_map()
        self._animate_to_route(path)

    # ── Cascade Zoom Animation ────────────────────────────────────────────────

    def _animate_to_route(self, path_nodes: list):
        """
        Cascade zoom: step 1 pulls back to network overview, step 2 fits the
        route bounding box with dynamic padding (25 % of span, min 0.015°),
        step 3 re-centres on the route midpoint for a crisp finish.
        """
        if self.map_widget is None or self._network_center is None:
            return

        coords = [NODE_LATLNG[n] for n in path_nodes if n in NODE_LATLNG]
        if len(coords) < 2:
            return

        lats = [c[0] for c in coords]
        lngs = [c[1] for c in coords]

        lat_span = max(lats) - min(lats)
        lng_span = max(lngs) - min(lngs)

        # Dynamic padding: 25 % of span so every node stays visible
        pad_lat = max(lat_span * 0.28, 0.015)
        pad_lng = max(lng_span * 0.28, 0.015)

        nw_corner = (max(lats) + pad_lat, min(lngs) - pad_lng)
        se_corner  = (min(lats) - pad_lat, max(lngs) + pad_lng)

        # Route centre for the tightening step
        route_center = (
            (max(lats) + min(lats)) / 2,
            (max(lngs) + min(lngs)) / 2,
        )

        # Step 1: pull back so the user sees context
        self.map_widget.set_position(*self._network_center)
        self.map_widget.set_zoom(10)

        # Step 2: fit bounding box around the route
        self.root.after(
            700,
            lambda: self.map_widget.fit_bounding_box(nw_corner, se_corner),
        )

        # Step 3: nudge the camera to the exact route centre for a crisp finish
        self.root.after(
            1400,
            lambda: self.map_widget.set_position(*route_center),
        )

    # ── Route Cards (Waze's route options list) ───────────────────────────────

    def _render_route_cards(self, options: list, selected_idx: int = 0):
        """Render one clickable card per route option; selected card has cyan accent bar."""
        for widget in self._card_frame.winfo_children():
            widget.destroy()
        self._no_path_label.configure(text="")

        if not options:
            return

        card_h = 60
        self._card_canvas.configure(
            height=min(len(options) * card_h + 10, card_h * 3 + 10)
        )

        for idx, (path, label, dist, time_val) in enumerate(options):
            is_sel = (idx == selected_idx)

            card = tk.Frame(
                self._card_frame,
                bg=C["card_sel"] if is_sel else C["card_bg"],
                cursor="hand2",
            )
            card.pack(fill="x", padx=8, pady=(4 if idx == 0 else 2, 0))

            # Left accent bar (Waze's blue selected-route highlight)
            tk.Frame(
                card,
                bg=C["card_border"] if is_sel else C["border"],
                width=4,
            ).pack(side="left", fill="y")

            # Time (large, like Waze)
            tk.Label(
                card,
                text=format_time(time_val),
                bg=card["bg"],
                fg=C["route"] if is_sel else C["text"],
                font=("Helvetica", 14, "bold"),
                width=10, anchor="w",
            ).pack(side="left", padx=(10, 0), pady=8)

            # 'Best' badge on the primary route
            if idx == 0:
                tk.Label(
                    card, text=" Best ",
                    bg=C["route"], fg="#1a1f2e",
                    font=("Helvetica", 8, "bold"),
                ).pack(side="left", padx=4)

            # Distance + via label
            info_frame = tk.Frame(card, bg=card["bg"])
            info_frame.pack(side="left", padx=8, fill="x", expand=True)

            via_nodes = path[1:-1] if len(path) > 2 else path[1:]
            tk.Label(
                info_frame,
                text=f"{format_distance(dist)}  ·  Via {format_path(via_nodes)}",
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

            # Bind click to switch highlighted route
            _path = path
            _idx  = idx
            for w in [card] + list(card.winfo_children()):
                w.bind("<Button-1>",
                       lambda e, p=_path, i=_idx: self._on_card_click(p, i))

    def _on_card_click(self, path: list, idx: int):
        """User clicked a route card → highlight that route and re-render cards."""
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
        """Reset route state, form fields, result cards, map overlays, and camera."""
        self.active_path   = []
        self.route_edges   = set()
        self.route_options = []

        # Reset search form fields
        self.src_var.set("")
        self.dst_var.set("")
        self.algo_var.set(ALGORITHM_LABELS[0])

        # Clear result cards and status label
        for widget in self._card_frame.winfo_children():
            widget.destroy()
        self._card_canvas.configure(height=0)
        self._no_path_label.configure(text="")

        self._draw_map()

        # Return camera to full-network overview
        if self.map_widget and self._network_center:
            self.map_widget.set_position(*self._network_center)
            self.map_widget.set_zoom(DEFAULT_ZOOM)

    # ── ADMIN PANEL ───────────────────────────────────────────────────────────

    def _open_admin(self):
        """Modal password prompt; opens AdminPanel on correct entry."""
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
        """Refresh Prolog data and redraw the map after admin changes."""
        self._refresh_data()
        self._draw_map()
