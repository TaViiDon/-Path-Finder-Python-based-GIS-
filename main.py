"""
main.py
-------
Application entry point for the PathFinder Rural Roads Network system.

Responsibilities:
  1. Check that PySwip is installed (gives a clear install command if not).
  2. Initialise the PrologBridge and load aiproject.pl into the SWI-Prolog engine.
  3. Create the Tkinter root window and launch PathFinderApp.

Run from the project directory:
    python main.py

Requirements (install once):
    pip install pyswip
    SWI-Prolog >= 8.x  →  https://www.swi-prolog.org/Download.html

Author: Group  |  UTech Jamaica – AI / Expert Systems  |  2026
"""

import sys
import os
import importlib.util
import tkinter as tk
from tkinter import messagebox


# =============================================================================
# Dependency check
# =============================================================================

def _check_deps() -> bool:
    """
    Verify that PySwip is installed.
    PySwip also requires SWI-Prolog to be installed and its DLL on the PATH;
    if SWI-Prolog is missing, PySwip will raise an error when Prolog() is
    first constructed (caught below in main()).
    """
    if importlib.util.find_spec("pyswip") is not None:
        return True

    print(
        "\n[PathFinder]  Missing dependency: pyswip\n"
        "  Install with:  pip install pyswip\n"
        "  Also install SWI-Prolog 8.x from: https://www.swi-prolog.org\n"
    )
    return False


# =============================================================================
# Knowledge base path
# =============================================================================

# Resolve path relative to this file so the app works regardless of cwd
KB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "aiproject.pl")


# =============================================================================
# Entry point
# =============================================================================

def main():
    print("=" * 58)
    print("  PathFinder  –  Jamaica Rural Roads Network")
    print("  UTech Jamaica  |  AI / Expert Systems  |  2026")
    print("=" * 58)

    # 1. Dependency check – fail fast with a helpful message
    if not _check_deps():
        sys.exit(1)

    # Import after the dependency check so we get the clear error above
    # if pyswip is missing (rather than a cryptic ImportError traceback).
    from bridge import PrologBridge
    from interface import PathFinderApp

    # 2. Initialise the Prolog engine and load the knowledge base
    print(f"\n[main]  Loading knowledge base: {KB_FILE}")
    bridge = PrologBridge()

    if not bridge.load(KB_FILE):
        # Show a GUI error dialog so users without a terminal still see feedback
        _root = tk.Tk()
        _root.withdraw()
        messagebox.showerror(
            "Knowledge Base Error",
            f"Failed to load Prolog knowledge base:\n{KB_FILE}\n\n"
            "• Ensure SWI-Prolog 8.x is installed.\n"
            "• Ensure aiproject.pl is in the same folder as main.py.\n"
            "• Check the terminal for details.",
        )
        sys.exit(1)

    print("[main]  Knowledge base loaded successfully.")
    print("[main]  Launching GUI …\n")

    # 3. Create root window and start the GUI
    root = tk.Tk()

    # Allow transparency on Windows
    try:
        root.wm_attributes("-alpha", 1.0)
    except Exception:
        pass

    _app = PathFinderApp(root, bridge)   # holds all UI state for the session
    root.protocol("WM_DELETE_WINDOW", root.destroy)

    # Bring window to the foreground so it isn't hidden behind VSCode / other apps
    root.lift()
    root.attributes("-topmost", True)
    root.after(200, lambda: root.attributes("-topmost", False))  # stop forcing on top after 0.2 s

    root.mainloop()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[main]  Interrupted – exiting.")
        sys.exit(0)
