"""
bridge.py
---------
Manages the connection between Python and the SWI-Prolog engine via PySwip.

All Prolog queries are funnelled through this single class so the rest of the
application stays completely free of Prolog syntax.  

"""

import importlib
import os


class PrologBridge:
    """
    Wrapper around the PySwip Prolog engine.

    Typical usage::

        bridge = PrologBridge()
        bridge.load("aiproject.pl")
        path, km = bridge.query_dijkstra_distance("old_harbour", "byles")
    """

    def __init__(self):
        # A single shared SWI-Prolog engine for the whole application session
        self.prolog  = self._create_prolog_engine()
        self.kb_path = None   # Stored so save_kb() knows where to write

    def _create_prolog_engine(self):
        """
        Dynamically import PySwip to avoid static import-resolution issues in
        editors when the dependency is not installed in the active environment.
        """
        try:
            pyswip_module = importlib.import_module("pyswip")
            return pyswip_module.Prolog()
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "Missing dependency 'pyswip'.  Install with:  pip install pyswip"
            ) from exc

    # LOADING THE KNOWLEDGE BASE
    def load(self, kb_path: str) -> bool:
        """
        Consult (load + compile) a Prolog .pl file into the engine.

        The path is converted to an absolute forward-slash path because
        SWI-Prolog on Windows can be fussy about backslashes inside consult/1.

        Returns True on success, False if an exception is raised.
        """
        try:
            abs_path = os.path.abspath(kb_path).replace("\\", "/")
            self.prolog.consult(abs_path)
            self.kb_path = kb_path
            return True
        except Exception as exc:
            print(f"[Bridge] Failed to load KB '{kb_path}': {exc}")
            return False

    # DATA ACCESS  –  Reading facts from Prolog
    def get_all_roads(self) -> list:
        """
        Query every road/7 fact from the knowledge base.

        The predicate signature in aiproject.pl is:
            road(Source, Destination, Distance_km, Time_mins, Type, Status, Ways)

        Returns a list of plain Python dicts so callers never touch PySwip types.
        """
        roads = []
        try:
            query = "road(Src, Dst, Dist, Time, Type, Status, Ways)"
            for sol in self.prolog.query(query):
                roads.append({
                    "src":    str(sol["Src"]),
                    "dst":    str(sol["Dst"]),
                    "dist":   int(sol["Dist"]),
                    "time":   int(sol["Time"]),
                    "type":   str(sol["Type"]),
                    "status": str(sol["Status"]),
                    "ways":   str(sol["Ways"]),
                })
        except Exception as exc:
            print(f"[Bridge] get_all_roads error: {exc}")
        return roads

    def get_all_conditions(self) -> list:
        """
        Query every special_conditions/3 fact.

        Signature:  special_conditions(Source, Destination, Condition)

        Returns a list of dicts: {src, dst, condition}
        """
        conds = []
        try:
            for sol in self.prolog.query("special_conditions(Src, Dst, Cond)"):
                conds.append({
                    "src":       str(sol["Src"]),
                    "dst":       str(sol["Dst"]),
                    "condition": str(sol["Cond"]),
                })
        except Exception as exc:
            print(f"[Bridge] get_all_conditions error: {exc}")
        return conds

    def get_all_nodes(self) -> list:
        """
        Derive every unique node name by scanning road/7 facts for both
        source and destination atoms.

        Returns a sorted list of plain strings (Prolog atom names).
        """
        nodes = set()
        for r in self.get_all_roads():
            nodes.add(r["src"])
            nodes.add(r["dst"])
        return sorted(nodes)

    # PATH QUERIES  –  Calling the search algorithms
    # Each public method maps to one Prolog predicate defined in aiproject.pl.
    # Path-only queries return a list[str] or None.
    # Cost queries return (list[str], int) or (None, None).

    def query_bfs(self, start: str, goal: str):
        """BFS – finds any reachable path (no road-type or condition filter)."""
        return self._path_query("bfs", start, goal)

    def query_bfs_paved(self, start: str, goal: str):
        """BFS – only traverses paved road segments."""
        return self._path_query("paved_roads_bfs", start, goal)

    def query_bfs_open(self, start: str, goal: str):
        """BFS – skips roads whose status is 'closed'."""
        return self._path_query("open_roads_bfs", start, goal)

    def query_dfs(self, start: str, goal: str):
        """DFS – depth-first search with no extra filters."""
        return self._path_query("dfs", start, goal)

    def query_dfs_no_cisterns(self, start: str, goal: str):
        """
        DFS – avoids road segments that have a broken_cisterns condition.
        Calls the corrected predicate dfs_no_cisterns/3 added to aiproject.pl.
        """
        return self._path_query("dfs_no_cisterns", start, goal)

    def query_dfs_no_potholes(self, start: str, goal: str):
        """
        DFS – avoids road segments that have a deep_potholes condition.
        Calls the corrected predicate dfs_no_potholes/3 added to aiproject.pl.
        """
        return self._path_query("dfs_no_potholes", start, goal)

    def query_dfs_no_landslides(self, start: str, goal: str):
        """
        DFS – avoids road segments that have a landslide condition.
        Calls the predicate dfs_no_landslides/3 from aiproject.pl.
        """
        return self._path_query("dfs_no_landslides", start, goal)

    def query_dfs_no_floods(self, start: str, goal: str):
        """
        DFS – avoids road segments that have a flooded condition.
        Calls the predicate dfs_no_floods/3 from aiproject.pl.
        """
        return self._path_query("dfs_no_floods", start, goal)

    def query_dijkstra_distance(self, start: str, goal: str):
        """
        Dijkstra – minimises total distance (km).
        Uses dijkstra_dis/4 in aiproject.pl.
        Returns (path, distance_km) or (None, None).
        """
        return self._cost_query("dijkstra_dis", start, goal)

    def query_dijkstra_time(self, start: str, goal: str):
        """
        Dijkstra – minimises total travel time (minutes).
        Uses dijkstra_time/4 which adds +5 min penalty for deep_potholes
        or broken_cisterns on each affected segment.
        Returns (path, time_mins) or (None, None).
        """
        return self._cost_query("dijkstra_time", start, goal)

    # =========================================================================
    # ADMIN  –  Modifying the knowledge base at runtime
    # =========================================================================

    def add_road(self, src, dst, dist, time_val, road_type, status, ways) -> bool:
        """
        Assert a new road/7 fact into the live Prolog engine using assertz/1.
        assertz adds the fact at the END of the clause list — the conventional
        position for dynamically added facts.

        Changes are in-memory only until save_kb() is called.
        """
        fact = (
            f"road({src}, {dst}, {dist}, {time_val}, "
            f"{road_type}, {status}, {ways})"
        )
        try:
            # Consuming the generator is required to actually execute the query
            list(self.prolog.query(f"assertz({fact})"))
            return True
        except Exception as exc:
            print(f"[Bridge] add_road error: {exc}")
            return False

    def update_road_status(self, src, dst, new_status) -> bool:
        """
        Change the open/closed status of a road segment.

        Strategy:
          1. Read the current road fact to capture its exact field values.
          2. Retract the old fact (exact match is required by retract/1).
          3. Assert the new fact with the updated status field.
        """
        try:
            # 1. Fetch current values
            results = list(self.prolog.query(
                f"road({src}, {dst}, Dist, Time, Type, OldStatus, Ways)"
            ))
            if not results:
                print(f"[Bridge] Road {src}->{dst} not found for status update.")
                return False

            r        = results[0]
            dist     = int(r["Dist"])
            time_val = int(r["Time"])
            rtype    = str(r["Type"])
            old_stat = str(r["OldStatus"])
            ways     = str(r["Ways"])

            # 2. Retract the existing fact (fields must match exactly)
            retract_q = (
                f"retract(road({src}, {dst}, {dist}, {time_val}, "
                f"{rtype}, {old_stat}, {ways}))"
            )
            list(self.prolog.query(retract_q))

            # 3. Assert the updated fact
            new_fact = (
                f"road({src}, {dst}, {dist}, {time_val}, "
                f"{rtype}, {new_status}, {ways})"
            )
            list(self.prolog.query(f"assertz({new_fact})"))
            return True

        except Exception as exc:
            print(f"[Bridge] update_road_status error: {exc}")
            return False

    def add_condition(self, src, dst, condition) -> bool:
        """Assert a new special_conditions/3 fact into the engine."""
        fact = f"special_conditions({src}, {dst}, {condition})"
        try:
            list(self.prolog.query(f"assertz({fact})"))
            return True
        except Exception as exc:
            print(f"[Bridge] add_condition error: {exc}")
            return False

    def remove_condition(self, src, dst, condition) -> bool:
        """Retract a special_conditions/3 fact from the engine."""
        try:
            list(self.prolog.query(
                f"retract(special_conditions({src}, {dst}, {condition}))"
            ))
            return True
        except Exception as exc:
            print(f"[Bridge] remove_condition error: {exc}")
            return False

    def save_kb(self, filepath: str) -> bool:
        """
        Persist the current in-memory state back to the .pl file on disk.

        Algorithm:
          1. Read the original file line by line.
          2. Drop lines that are road/7 or special_conditions/3 FACTS
             (we'll regenerate them from the live Prolog engine).
          3. Insert fresh fact lines right after the ':- dynamic' declarations.
          4. Write the reconstructed content back to disk.

        This approach preserves all rule and algorithm predicates unchanged.
        """
        try:
            with open(filepath, "r") as f:
                original_lines = f.readlines()

            # Keep every line that is NOT a data fact line
            kept = []
            for line in original_lines:
                stripped = line.strip()
                is_fact = (
                    stripped.startswith("road(") or
                    stripped.startswith("special_conditions(")
                )
                if not is_fact:
                    kept.append(line)

            # Build fresh fact lines from live Prolog state
            new_facts = ["\n%road(source, destination, distance, time, type, status, ways)\n"]
            for r in self.get_all_roads():
                new_facts.append(
                    f"road({r['src']},{r['dst']}, {r['dist']}, {r['time']}, "
                    f"{r['type']}, {r['status']}, {r['ways']}).\n"
                )
            new_facts.append("\n%special conditions\n")
            new_facts.append("%special_conditions(source, destination, condition).\n")
            for c in self.get_all_conditions():
                new_facts.append(
                    f"special_conditions({c['src']}, {c['dst']}, {c['condition']}).\n"
                )
            new_facts.append("\n")

            # Find insertion point: just after the last ':- dynamic' line
            insert_at = 0
            for i, line in enumerate(kept):
                if line.strip().startswith(":- dynamic"):
                    insert_at = i + 1

            final = kept[:insert_at] + new_facts + kept[insert_at:]

            with open(filepath, "w") as f:
                f.writelines(final)

            print(f"[Bridge] KB saved -> {filepath}")
            return True

        except Exception as exc:
            print(f"[Bridge] save_kb error: {exc}")
            return False

    # INTERNAL HELPERS

    def _path_query(self, predicate: str, start: str, goal: str):
        """
        Generic path-only query (no cost variable).

        PySwip returns each solution as a dict; 'Path' maps to a PySwip list
        of Atom objects.  We str() each element to get plain Python strings.
        Returns the first solution's path, or None if no solution exists.
        """
        try:
            solutions = list(self.prolog.query(f"{predicate}({start}, {goal}, Path)"))
            if solutions:
                return [str(n) for n in solutions[0]["Path"]]
        except Exception as exc:
            print(f"[Bridge] _path_query '{predicate}' error: {exc}")
        return None

    def _cost_query(self, predicate: str, start: str, goal: str):
        """
        Generic path + cost query (Dijkstra-style).

        The Prolog predicate binds both Path and Cost.
        Returns (path_list, cost_int) or (None, None) on failure.
        """
        try:
            solutions = list(
                self.prolog.query(f"{predicate}({start}, {goal}, Path, Cost)")
            )
            if solutions:
                path = [str(n) for n in solutions[0]["Path"]]
                cost = int(solutions[0]["Cost"])
                return path, cost
        except Exception as exc:
            print(f"[Bridge] _cost_query '{predicate}' error: {exc}")
        return None, None
