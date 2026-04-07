"""
admin.py
--------
Administrator panel for the PathFinder system.

Opens as a separate Toplevel window that lets a privileged
user manage the road network without restarting the application:

    Tab 1 – View Roads     : scrollable table of all road/7 facts + conditions
    Tab 2 – Add Road       : form to assert a new road/7 fact
    Tab 3 – Update Status  : change a road's open/closed status
    Tab 4 – Conditions     : add or remove special_conditions/3 facts
"""

import tkinter as tk
from tkinter import ttk, messagebox

from utils import display_name, format_condition


# Colour palette  (matches the dark Waze-style theme in interface.py)
C = {
    "bg":       "#1a1f2e",   # window background
    "panel":    "#252d3d",   # card / tab surface
    "accent":   "#4a9eff",   # primary blue
    "success":  "#2ecc71",   # confirmation green
    "danger":   "#e74c3c",   # error red
    "text":     "#e8eaf0",   # primary text
    "sub":      "#8b9cb5",   # secondary / hint text
    "inp":      "#1e2636",   # text-entry background
    "border":   "#3a4a6a",   # subtle border
    "row_even": "#1e2636",
    "row_odd":  "#252d3d",
}

ROAD_TYPES = ["paved", "unpaved", "gravel"]
STATUSES   = ["open", "closed"]
WAYS_OPTS  = ["two_way", "one_way"]
CONDITIONS = ["deep_potholes", "broken_cisterns", "flooded", "landslide"]


class AdminPanel:
    """
    Administrator management window (Tkinter Toplevel).

    Parameters
    ----------
    parent   : tk.Tk root window
    bridge   : active PrologBridge instance
    kb_path  : path to aiproject.pl (for save_kb)
    on_close : optional callable fired whenever data changes or window closes
    """

    def __init__(self, parent: tk.Tk, bridge, kb_path: str, on_close=None):
        self.bridge   = bridge
        self.kb_path  = kb_path
        self.on_close = on_close    # Callback → refreshes the main map

        # Top-level window
        self.win = tk.Toplevel(parent)
        self.win.title("PathFinder – Administrator Panel")
        self.win.geometry("880x640")
        self.win.configure(bg=C["bg"])
        self.win.resizable(True, True)
        self.win.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build_ui()
        self._refresh_view()   # Populate the View Roads tab immediately

    # UI CONSTRUCTION
    def _build_ui(self):
        """Assemble header + tabbed notebook."""

        # ── Header bar ───────────────────────────────────────────────────────
        hdr = tk.Frame(self.win, bg=C["accent"], height=52)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        tk.Label(
            hdr, text="Administrator Panel",
            bg=C["accent"], fg="white",
            font=("Helvetica", 14, "bold"), anchor="w",
        ).pack(side="left", padx=16, pady=10)

        # Save to File button in the header (like a toolbar action)
        tk.Button(
            hdr, text="Save to File",
            bg="#1a6bc4", fg="white",
            font=("Helvetica", 10, "bold"),
            relief="flat", cursor="hand2",
            padx=12, pady=4,
            command=self._save_kb,
        ).pack(side="right", padx=16, pady=10)

        # ── Notebook (tabbed interface) ───────────────────────────────────────
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("A.TNotebook",
                        background=C["bg"], borderwidth=0)
        style.configure("A.TNotebook.Tab",
                        background=C["panel"], foreground=C["sub"],
                        padding=[14, 6], font=("Helvetica", 10))
        style.map("A.TNotebook.Tab",
                  background=[("selected", C["accent"])],
                  foreground=[("selected", "white")])

        self.nb = ttk.Notebook(self.win, style="A.TNotebook")
        self.nb.pack(fill="both", expand=True, padx=10, pady=10)

        self._build_tab_view()
        self._build_tab_add()
        self._build_tab_status()
        self._build_tab_conditions()

    # Tab 1 – View all roads
    def _build_tab_view(self):
        f = tk.Frame(self.nb, bg=C["bg"])
        self.nb.add(f, text="  View Roads  ")

        # Treeview style
        s = ttk.Style()
        s.configure("Roads.Treeview",
                    background=C["row_even"], foreground=C["text"],
                    fieldbackground=C["row_even"], rowheight=26,
                    font=("Helvetica", 10))
        s.configure("Roads.Treeview.Heading",
                    background=C["panel"], foreground=C["accent"],
                    font=("Helvetica", 10, "bold"))
        s.map("Roads.Treeview",
              background=[("selected", C["accent"])])

        cols = ("From", "To", "Dist", "Time", "Type", "Status", "Direction")
        tf = tk.Frame(f, bg=C["bg"])
        tf.pack(fill="both", expand=True, padx=10, pady=(10, 4))

        sy = tk.Scrollbar(tf, orient="vertical")
        sx = tk.Scrollbar(tf, orient="horizontal")

        self.roads_tree = ttk.Treeview(
            tf, columns=cols, show="headings",
            yscrollcommand=sy.set, xscrollcommand=sx.set,
            style="Roads.Treeview",
        )
        sy.config(command=self.roads_tree.yview)
        sx.config(command=self.roads_tree.xview)

        col_widths = [130, 130, 75, 75, 85, 75, 90]
        for col, w in zip(cols, col_widths):
            self.roads_tree.heading(col, text=col)
            self.roads_tree.column(col, width=w, anchor="center")

        sy.pack(side="right", fill="y")
        sx.pack(side="bottom", fill="x")
        self.roads_tree.pack(fill="both", expand=True)

        # ── Conditions sub-section ────────────────────────────────────────────
        tk.Label(f, text="Special Conditions:",
                 bg=C["bg"], fg=C["accent"],
                 font=("Helvetica", 11, "bold")).pack(anchor="w", padx=12, pady=(8, 2))

        self.cond_text = tk.Text(
            f, height=5,
            bg=C["inp"], fg=C["text"],
            font=("Courier", 10), relief="flat",
            state="disabled",
        )
        self.cond_text.pack(fill="x", padx=10, pady=(0, 6))

        tk.Button(
            f, text="Refresh",
            bg=C["accent"], fg="white",
            font=("Helvetica", 10, "bold"),
            relief="flat", cursor="hand2",
            padx=12, pady=4,
            command=self._refresh_view,
        ).pack(pady=(0, 8))

    # Tab 2 – Add a new road
    def _build_tab_add(self):
        f = tk.Frame(self.nb, bg=C["bg"])
        self.nb.add(f, text="  Add Road  ")

        tk.Label(f, text="Add a New Road Segment",
                 bg=C["bg"], fg=C["accent"],
                 font=("Helvetica", 13, "bold")).pack(pady=(18, 12))

        form = tk.Frame(f, bg=C["bg"])
        form.pack(padx=40)

        # Field definitions: (label text, var key, widget type, options list)
        self._add_vars = {}
        fields = [
            ("Source Node:",        "src",    "entry", None),
            ("Destination Node:",   "dst",    "entry", None),
            ("Distance (km):",      "dist",   "entry", None),
            ("Time (mins):",        "time",   "entry", None),
            ("Road Type:",          "rtype",  "combo", ROAD_TYPES),
            ("Status:",             "status", "combo", STATUSES),
            ("Direction:",          "ways",   "combo", WAYS_OPTS),
        ]

        for row, (lbl, key, wtype, opts) in enumerate(fields):
            tk.Label(form, text=lbl,
                     bg=C["bg"], fg=C["text"],
                     font=("Helvetica", 10), width=20, anchor="e"
                     ).grid(row=row, column=0, padx=(0, 10), pady=7, sticky="e")

            var = tk.StringVar(value=(opts[0] if opts else ""))
            self._add_vars[key] = var

            if wtype == "entry":
                tk.Entry(form, textvariable=var, width=26,
                         bg=C["inp"], fg=C["text"],
                         insertbackground=C["text"],
                         relief="flat", font=("Helvetica", 10),
                         ).grid(row=row, column=1, pady=7, sticky="w")
            else:
                ttk.Combobox(form, textvariable=var, values=opts,
                             width=23, state="readonly",
                             font=("Helvetica", 10),
                             ).grid(row=row, column=1, pady=7, sticky="w")

        tk.Button(
            f, text="Add Road",
            bg=C["success"], fg="white",
            font=("Helvetica", 11, "bold"),
            relief="flat", cursor="hand2",
            padx=20, pady=6,
            command=self._do_add_road,
        ).pack(pady=16)

        self._add_msg = tk.Label(f, text="", bg=C["bg"], font=("Helvetica", 10))
        self._add_msg.pack()

    # Tab 3 – Update road status (open / closed)
    def _build_tab_status(self):
        f = tk.Frame(self.nb, bg=C["bg"])
        self.nb.add(f, text="  Update Status  ")

        tk.Label(f, text="Update Road Open / Closed Status",
                 bg=C["bg"], fg=C["accent"],
                 font=("Helvetica", 13, "bold")).pack(pady=(18, 20))

        form = tk.Frame(f, bg=C["bg"])
        form.pack(padx=40)

        self._upd_vars = {}
        fields = [
            ("Source Node:",      "src",    "entry", None),
            ("Destination Node:", "dst",    "entry", None),
            ("New Status:",       "status", "combo", STATUSES),
        ]

        for row, (lbl, key, wtype, opts) in enumerate(fields):
            tk.Label(form, text=lbl,
                     bg=C["bg"], fg=C["text"],
                     font=("Helvetica", 10), width=20, anchor="e",
                     ).grid(row=row, column=0, padx=(0, 10), pady=8, sticky="e")

            var = tk.StringVar(value=(opts[0] if opts else ""))
            self._upd_vars[key] = var

            if wtype == "entry":
                tk.Entry(form, textvariable=var, width=26,
                         bg=C["inp"], fg=C["text"],
                         insertbackground=C["text"],
                         relief="flat", font=("Helvetica", 10),
                         ).grid(row=row, column=1, pady=8, sticky="w")
            else:
                ttk.Combobox(form, textvariable=var, values=opts,
                             width=23, state="readonly",
                             ).grid(row=row, column=1, pady=8, sticky="w")

        tk.Button(
            f, text="Update Status",
            bg=C["accent"], fg="white",
            font=("Helvetica", 11, "bold"),
            relief="flat", cursor="hand2",
            padx=20, pady=6,
            command=self._do_update_status,
        ).pack(pady=20)

        self._upd_msg = tk.Label(f, text="", bg=C["bg"], font=("Helvetica", 10))
        self._upd_msg.pack()

    # Tab 4 – Manage special conditions
    def _build_tab_conditions(self):
        f = tk.Frame(self.nb, bg=C["bg"])
        self.nb.add(f, text="  Conditions  ")

        tk.Label(f, text="Add / Remove Road Conditions",
                 bg=C["bg"], fg=C["accent"],
                 font=("Helvetica", 13, "bold")).pack(pady=(18, 12))

        form = tk.Frame(f, bg=C["bg"])
        form.pack(padx=40)

        self._cond_vars = {}
        fields = [
            ("Source Node:",      "src",       "entry", None),
            ("Destination Node:", "dst",       "entry", None),
            ("Condition:",        "condition", "combo", CONDITIONS),
        ]

        for row, (lbl, key, wtype, opts) in enumerate(fields):
            tk.Label(form, text=lbl,
                     bg=C["bg"], fg=C["text"],
                     font=("Helvetica", 10), width=20, anchor="e",
                     ).grid(row=row, column=0, padx=(0, 10), pady=8, sticky="e")

            var = tk.StringVar(value=(opts[0] if opts else ""))
            self._cond_vars[key] = var

            if wtype == "entry":
                tk.Entry(form, textvariable=var, width=26,
                         bg=C["inp"], fg=C["text"],
                         insertbackground=C["text"],
                         relief="flat", font=("Helvetica", 10),
                         ).grid(row=row, column=1, pady=8, sticky="w")
            else:
                ttk.Combobox(form, textvariable=var, values=opts,
                             width=23, state="readonly",
                             ).grid(row=row, column=1, pady=8, sticky="w")

        btn_row = tk.Frame(f, bg=C["bg"])
        btn_row.pack(pady=16)

        tk.Button(
            btn_row, text="Add Condition",
            bg=C["success"], fg="white",
            font=("Helvetica", 10, "bold"),
            relief="flat", cursor="hand2",
            padx=14, pady=5,
            command=self._do_add_condition,
        ).pack(side="left", padx=8)

        tk.Button(
            btn_row, text="Remove Condition",
            bg=C["danger"], fg="white",
            font=("Helvetica", 10, "bold"),
            relief="flat", cursor="hand2",
            padx=14, pady=5,
            command=self._do_remove_condition,
        ).pack(side="left", padx=8)

        self._cond_msg = tk.Label(f, text="", bg=C["bg"], font=("Helvetica", 10))
        self._cond_msg.pack()

    # DATA REFRESH  –  populates Tab 1 with live Prolog data
    def _refresh_view(self):
        """Reload all roads and conditions from the Prolog engine."""

        # Clear the treeview
        for item in self.roads_tree.get_children():
            self.roads_tree.delete(item)

        # Repopulate roads table
        for i, r in enumerate(self.bridge.get_all_roads()):
            tag = "even" if i % 2 == 0 else "odd"
            self.roads_tree.insert(
                "", "end",
                values=(
                    display_name(r["src"]),
                    display_name(r["dst"]),
                    f"{r['dist']} km",
                    f"{r['time']} min",
                    r["type"].capitalize(),
                    r["status"].upper(),
                    r["ways"],
                ),
                tags=(tag,),
            )

        self.roads_tree.tag_configure("even", background=C["row_even"])
        self.roads_tree.tag_configure("odd",  background=C["row_odd"])

        # Repopulate conditions text area
        conds = self.bridge.get_all_conditions()
        self.cond_text.configure(state="normal")
        self.cond_text.delete("1.0", "end")
        if conds:
            for c in conds:
                self.cond_text.insert(
                    "end",
                    f"  {display_name(c['src'])}  ↔  {display_name(c['dst'])}"
                    f"    →    {format_condition(c['condition'])}\n",
                )
        else:
            self.cond_text.insert("end", "  No special conditions recorded.\n")
        self.cond_text.configure(state="disabled")

    # ACTIONS –  called by the buttons in Tabs 2-4 to modify the Prolog KB

    def _do_add_road(self):
        """Validate the Add Road form and assert the new fact into Prolog."""
        v   = self._add_vars
        src = v["src"].get().strip().lower().replace(" ", "_")
        dst = v["dst"].get().strip().lower().replace(" ", "_")

        if not src or not dst:
            self._msg(self._add_msg, "⚠  Source and destination cannot be empty.", "danger")
            return
        if src == dst:
            self._msg(self._add_msg, "⚠  Source and destination must differ.", "danger")
            return

        try:
            dist     = int(v["dist"].get())
            time_val = int(v["time"].get())
        except ValueError:
            self._msg(self._add_msg, "⚠  Distance and Time must be whole numbers.", "danger")
            return

        if dist <= 0 or time_val <= 0:
            self._msg(self._add_msg, "⚠  Distance and Time must be positive.", "danger")
            return

        rtype  = v["rtype"].get()
        status = v["status"].get()
        ways   = v["ways"].get()

        if self.bridge.add_road(src, dst, dist, time_val, rtype, status, ways):
            self._msg(
                self._add_msg,
                f"✔  Road '{display_name(src)} → {display_name(dst)}' added.", "success",
            )
            self._refresh_view()
            self._notify_map()
        else:
            self._msg(self._add_msg, "✘  Failed to add road. Check console.", "danger")

    def _do_update_status(self):
        """Validate the Update Status form and retract/reassert the road fact."""
        src    = self._upd_vars["src"].get().strip().lower().replace(" ", "_")
        dst    = self._upd_vars["dst"].get().strip().lower().replace(" ", "_")
        status = self._upd_vars["status"].get()

        if not src or not dst:
            self._msg(self._upd_msg, "⚠  Fill in source and destination.", "danger")
            return

        if self.bridge.update_road_status(src, dst, status):
            self._msg(
                self._upd_msg,
                f"✔  {display_name(src)} → {display_name(dst)} set to {status.upper()}.",
                "success",
            )
            self._refresh_view()
            self._notify_map()
        else:
            self._msg(self._upd_msg, "✘  Road not found or update failed.", "danger")

    def _do_add_condition(self):
        """Assert a new special_conditions/3 fact."""
        src       = self._cond_vars["src"].get().strip().lower().replace(" ", "_")
        dst       = self._cond_vars["dst"].get().strip().lower().replace(" ", "_")
        condition = self._cond_vars["condition"].get()

        if not src or not dst or not condition:
            self._msg(self._cond_msg, "⚠  Fill all fields.", "danger")
            return

        if self.bridge.add_condition(src, dst, condition):
            self._msg(
                self._cond_msg,
                f"✔  '{format_condition(condition)}' added to "
                f"{display_name(src)} ↔ {display_name(dst)}.",
                "success",
            )
            self._refresh_view()
            self._notify_map()
        else:
            self._msg(self._cond_msg, "✘  Failed to add condition.", "danger")

    def _do_remove_condition(self):
        """Retract a special_conditions/3 fact."""
        src       = self._cond_vars["src"].get().strip().lower().replace(" ", "_")
        dst       = self._cond_vars["dst"].get().strip().lower().replace(" ", "_")
        condition = self._cond_vars["condition"].get()

        if not src or not dst:
            self._msg(self._cond_msg, "⚠  Fill source and destination.", "danger")
            return

        if self.bridge.remove_condition(src, dst, condition):
            self._msg(self._cond_msg, "✔  Condition removed.", "success")
            self._refresh_view()
            self._notify_map()
        else:
            self._msg(self._cond_msg, "✘  Condition not found or already removed.", "danger")

    def _save_kb(self):
        """Persist the current Prolog engine state to aiproject.pl on disk."""
        if not self.kb_path:
            messagebox.showerror("Error", "No knowledge base file path configured.")
            return
        if self.bridge.save_kb(self.kb_path):
            messagebox.showinfo("Saved", f"Knowledge base saved to:\n{self.kb_path}")
        else:
            messagebox.showerror("Error", "Save failed – check the console for details.")

    # HELPERS
    def _msg(self, label: tk.Label, text: str, kind: str):
        """Update a status label with colour-coded feedback text."""
        label.configure(text=text, fg=C[kind])

    def _notify_map(self):
        """Fire the on_close callback so the main map redraws after changes."""
        if self.on_close:
            self.on_close()

    def _on_close(self):
        """Called when the admin window X button is pressed."""
        self._notify_map()
        self.win.destroy()
