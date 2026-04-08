"""
utils.py
--------
Utility / helper functions shared across the application.

Covers:
  - Node name formatting (Prolog atom ↔ human-readable display string)
  - Input validation
  - Path, distance, and time formatting for display
  - Python-side travel-time calculation (mirrors the Prolog dijkstra_time logic)
  - Algorithm label → bridge method mapping used by the UI

"""

# NODE NAME FORMATTING
def display_name(node_id: str) -> str:
    """
    Convert a Prolog atom node name to a human-readable display string.

    Examples:
        'old_harbour'       →  'Old Harbour'
        'spring_villiage'   →  'Spring Villiage'   (preserves original spelling)
        'calbeck_junction'  →  'Calbeck Junction'
    """
    return node_id.replace("_", " ").title()


def prolog_name(display: str) -> str:
    """
    Convert a display name back to the Prolog atom format used in queries.

    Examples:
        'Old Harbour'  →  'old_harbour'
        'Byles'        →  'byles'
    """
    return display.strip().lower().replace(" ", "_")


# =============================================================================
# INPUT VALIDATION
# =============================================================================

def validate_node(node_id: str, valid_nodes: list) -> bool:
    """
    Check that a node atom exists in the road network.

    This prevents Prolog from running a search with an unknown node, which
    would silently return no solutions and confuse the user.
    """
    return node_id in valid_nodes


def validate_nodes_different(src: str, dst: str) -> bool:
    """
    Ensure source and destination are not the same node.
    A path from A to A is trivially empty and not useful.
    """
    return src != dst


def validate_positive_int(value: str) -> bool:
    """Return True if value is a string representation of a positive integer."""
    try:
        return int(value) > 0
    except (ValueError, TypeError):
        return False



# DISPLAY FORMATTING
def format_path(path: list) -> str:
    """
    Join a list of node atom strings into a human-readable route string.

    Example:
        ['old_harbour', 'gutters', 'byles']  →  'Old Harbour → Gutters → Byles'
    """
    if not path:
        return "No path"
    return " → ".join(display_name(n) for n in path)


def format_distance(km) -> str:
    """Format a distance value as a display string with unit."""
    return f"{km} km"


def format_time(minutes) -> str:
    """
    Format a travel time in minutes.
    Shows hours + minutes when ≥ 60 mins (matches real navigation apps).

    Examples:
        25  →  '25 mins'
        90  →  '1 hr 30 mins'
        60  →  '1 hr'
    """
    minutes = int(minutes)
    if minutes < 60:
        return f"{minutes} mins"
    hours = minutes // 60
    mins  = minutes % 60
    if mins == 0:
        return f"{hours} hr"
    return f"{hours} hr {mins} mins"


def format_condition(condition_id: str) -> str:
    """
    Convert a Prolog condition atom to a readable label.

    Examples:
        'deep_potholes'    →  'Deep Potholes'
        'broken_cisterns'  →  'Broken Cisterns'
    """
    return condition_id.replace("_", " ").title()


# TRAVEL TIME CALCULATION  (Python-side mirror of Prolog dijkstra_time logic)

# Extra minutes added for each affected segment — mirrors the Prolog rule:
#   (has_condition(deep_potholes) ; has_condition(broken_cisterns)) → +5
CONDITION_TIME_PENALTY = 5


def adjusted_segment_time(base_time: int, conditions: list) -> int:
    """
    Calculate the travel time for one road segment after applying any
    condition penalties.

    Mirrors the logic inside dijkstra_time/4 in aiproject.pl:
    +5 minutes when the segment has deep_potholes OR broken_cisterns.

    This Python version is used to compute totals for display; Prolog
    handles the actual search cost internally.
    """
    if "deep_potholes" in conditions or "broken_cisterns" in conditions:
        return base_time + CONDITION_TIME_PENALTY
    return base_time


def compute_path_totals(path: list, roads: list, conditions: list):
    """
    Walk a found path and sum up total distance and adjusted travel time.

    Parameters
    ----------
    path       : list of node atom strings  e.g. ['old_harbour', 'gutters', ...]
    roads      : list of road dicts from bridge.get_all_roads()
    conditions : list of condition dicts from bridge.get_all_conditions()

    Returns
    -------
    (total_dist_km, total_adjusted_time_mins)
    Both are 0 for a single-node or empty path.
    """
    if not path or len(path) < 2:
        return 0, 0

    total_dist = 0
    total_time = 0

    for i in range(len(path) - 1):
        src = path[i]
        dst = path[i + 1]

        seg = _find_road_segment(src, dst, roads)
        if seg is None:
            continue

        total_dist += seg["dist"]

        # Collect every condition on this segment (check both directions
        # because special_conditions may be stored in either direction)
        seg_conds = [
            c["condition"] for c in conditions
            if (c["src"] == src and c["dst"] == dst)
            or (c["src"] == dst and c["dst"] == src)
        ]
        total_time += adjusted_segment_time(seg["time"], seg_conds)

    return total_dist, total_time


def _find_road_segment(src: str, dst: str, roads: list):
    """
    Internal helper: find the road dict for the segment src→dst.
    Checks both directions for two-way roads.
    """
    for r in roads:
        if r["src"] == src and r["dst"] == dst:
            return r
        if r["ways"] == "two_way" and r["src"] == dst and r["dst"] == src:
            return r
    return None


# ALGORITHM LABEL → BRIDGE METHOD MAPPING

# Maps the UI dropdown label to:
#   (bridge method suffix,  True if query also returns a cost value)
#
# The bridge method is called as:   bridge.query_<suffix>(src, dst)
# Cost queries return (path, cost); path-only queries return path.

ALGORITHM_MAP = {
    "Shortest Distance  (Dijkstra)":  ("dijkstra_distance", True),
    "Fastest Route      (Dijkstra)":  ("dijkstra_time",     True),
    "Any Route          (BFS)":       ("bfs",               False),
    "Paved Roads Only   (BFS)":       ("bfs_paved",         False),
    "Open Roads Only    (BFS)":       ("bfs_open",          False),
    "Depth-First Search (DFS)":       ("dfs",               False),
    "Avoid Broken Cisterns (DFS)":    ("dfs_no_cisterns",   False),
    "Avoid Deep Potholes   (DFS)":    ("dfs_no_potholes",   False),
    "Avoid Landslides      (DFS)":    ("dfs_no_landslides", False),
    "Avoid Floods          (DFS)":    ("dfs_no_floods",     False),
}

ALGORITHM_LABELS = list(ALGORITHM_MAP.keys())
