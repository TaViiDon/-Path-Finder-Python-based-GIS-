%knowledge database

%dynamic updates
:- dynamic road/7.
:- dynamic special_conditions/3.

%road(source, destination, distance, time, type, status, ways)
road(old_harbour,gutters, 5, 9, paved, open, two_way).
road(gutters,spring_villiage, 10, 15, paved, open, two_way).
road(gutters,bushy_park, 5, 5, unpaved, open, two_way).
road(spring_villiage,dover, 12, 15, unpaved, open, two_way).
road(dover,content, 7, 9, unpaved, open, two_way).
road(content,bamboo, 5, 6, paved, open, two_way).
road(bamboo,byles, 10, 15, paved, open, two_way).
road(old_harbour,calbeck_junction, 7, 10, paved, open, two_way).
road(calbeck_junction,bushy_park, 8, 12, unpaved, open, two_way).
road(montego_bay,falmouth, 32, 45, paved, open, two_way).

%special conditions
%special_conditions(source, destination, condition).
special_conditions(old_harbour, gutters, deep_potholes).
special_conditions(old_harbour, gutters, broken_cisterns).


%road(source, destination, distance, time, type, status, ways)

%special conditions
%special_conditions(source, destination, condition).


%road(source, destination, distance, time, type, status, ways)

%special conditions
%special_conditions(source, destination, condition).

%bidirectionl and oneway roads
%if roads are label one way
connected(Source, Des, Dis, Time, Type, Status, ways) :- road(Source, Des, Dis, Time, Type, Status, one_way).

%if roads are labeled as two ways they are bidirectional
connected(Source, Des, Dis, Time, Type, Status, ways) :- road(Source, Des, Dis, Time, Type, Status, two_way).
connected(Source, Des, Dis, Time, Type, Status, ways) :- road(Des, Source, Dis, Time, Type, Status, two_way).

% Check if condition exists in either direction
has_condition(A, B, Condition) :- special_conditions(A, B, Condition).
has_condition(A, B, Condition) :- special_conditions(B, A, Condition).

%search functionality

% Get all neighbors of a node
neighbors(Node, Neighbors) :-
    findall(N, connected(Node, N,_,_,_,_,_), Neighbors).

% ============================================================
%  BFS - Breadth-First Search
%  bfs(+Start, +Goal, -Path)
% ============================================================

bfs(Start, Goal, Path) :-
    bfs_queue([[Start]], Goal, RevPath),
    reverse(RevPath, Path).

% bfs_queue(+Queue, +Goal, -Path)
bfs_queue([[Goal|Rest]|_], Goal, [Goal|Rest]).
bfs_queue([[Current|Visited]|RestQueue], Goal, Path) :-
    neighbors(Current, Neighbors),
    exclude(member_check(Visited), Neighbors, Unvisited),
    maplist(prepend(Current, Visited), Unvisited, NewPaths),
    append(RestQueue, NewPaths, UpdatedQueue),
    bfs_queue(UpdatedQueue, Goal, Path).

member_check(List, Elem) :- member(Elem, List).

prepend(Current, Visited, Neighbor, [Neighbor, Current|Visited]).

%avoid unpaved roads
% Get all neighbors of a node
paved_neighbors(Node, Paved_Neighbors) :-
    findall(N, connected(Node, N,_,_,paved,_,_), Paved_Neighbors).

paved_roads_bfs(Start, Goal, Path) :-
    bfs_queue_paved([[Start]], Goal, RevPath),
    reverse(RevPath, Path).

bfs_queue_paved([[Goal|Rest]|_], Goal, [Goal|Rest]).
bfs_queue_paved([[Current|Visited]|RestQueue], Goal, Path) :-
    paved_neighbors(Current, Paved_Neighbors),
    exclude(member_check(Visited), Paved_Neighbors, Unvisited),
    maplist(prepend(Current, Visited), Unvisited, NewPaths),
    append(RestQueue, NewPaths, UpdatedQueue),
    bfs_queue_paved(UpdatedQueue, Goal, Path).


%avoid closed roads
% Get all neighbors of a node
open_neighbors(Node, Open_Neighbors) :-
    findall(N, connected(Node, N,_,_,_,open,_), Open_Neighbors).

open_roads_bfs(Start, Goal, Path) :-
    bfs_queue_open([[Start]], Goal, RevPath),
    reverse(RevPath, Path).

bfs_queue_open([[Goal|Rest]|_], Goal, [Goal|Rest]).
bfs_queue_open([[Current|Visited]|RestQueue], Goal, Path) :-
    open_neighbors(Current, Open_Neighbors),
    exclude(member_check(Visited), Open_Neighbors, Unvisited),
    maplist(prepend(Current, Visited), Unvisited, NewPaths),
    append(RestQueue, NewPaths, UpdatedQueue),
    bfs_queue_open(UpdatedQueue, Goal, Path).


% ============================================================
%  DFS - Depth-First Search
%  dfs(+Start, +Goal, -Path)
% ============================================================

dfs(Start, Goal, Path) :-
    dfs_helper(Start, Goal, [Start], RevPath),
    reverse(RevPath, Path).

% dfs_helper(+Current, +Goal, +Visited, -Path)
dfs_helper(Goal, Goal, Visited, Visited).
dfs_helper(Current, Goal, Visited, Path) :-
    connected(Current, Next,_,_,_,open,_),
    \+ member(Next, Visited),
    dfs_helper(Next, Goal, [Next|Visited], Path).

%avoid roads with broken cisterns
dfs_noBrokencisterns(Start, Goal, Path) :-
    dfs_helper(Start, Goal, [Start], RevPath),
    reverse(RevPath, Path).

dfs_nocis(Goal, Goal, Visited, Visited).
dfs_nocis(Current, Goal, Visited, Path) :-
    connected(Current, Next, _, _, _, open, _),
    \+ has_condition(Current, Next, broken_cisterns),  % skip edges WITH broken_cisterns
    \+ member(Next, Visited),
    dfs_nocis(Next, Goal, [Next|Visited], Path).

%avoid roads with broken cisterns
dfs_nopotholes(Start, Goal, Path) :-
    dfs_helper(Start, Goal, [Start], RevPath),
    reverse(RevPath, Path).

dfs_pot(Goal, Goal, Visited, Visited).
dfs_pot(Current, Goal, Visited, Path) :-
    connected(Current, Next, _, _, _, open, _),
    \+ has_condition(Current, Next, deep_potholes),  % skip edges WITH broken_cisterns
    \+ member(Next, Visited),
    dfs_pot(Next, Goal, [Next|Visited], Path).


% ============================================================
%  Bug-fixed DFS entry points
%  (The originals dfs_noBrokencisterns / dfs_nopotholes both
%   called dfs_helper which has NO filtering. These corrected
%   versions call the proper filtered inner predicates.)
% ============================================================

% Avoid roads flagged with broken_cisterns
dfs_no_cisterns(Start, Goal, Path) :-
    dfs_nocis(Start, Goal, [Start], RevPath),
    reverse(RevPath, Path).

% Avoid roads flagged with deep_potholes
dfs_no_potholes(Start, Goal, Path) :-
    dfs_pot(Start, Goal, [Start], RevPath),
    reverse(RevPath, Path).

% ============================================================
%  Dijkstra's Shortest Path Algorithm 
% ============================================================

%  dijkstra(+Start, +Goal, -Path, -TotalCost)
% ============================================================
%finding the path with the shortest distance
dijkstra_dis(Start, Goal, Path, Cost) :-
    % Priority queue entry: pq(Cost, CurrentNode, PathSoFar)
    dijkstra_loop([pq(0, Start, [Start])], Goal, [], RevPath, Cost),
    reverse(RevPath, Path).

%finding path with shortest time
dijkstra_time(Start, Goal, Path, Cost) :-
    % Priority queue entry: pq(Cost, CurrentNode, PathSoFar)
    dijkstra_loop2([pq(0, Start, [Start])], Goal, [], RevPath, Cost),
    reverse(RevPath, Path).


% ============================================================
%  CORE LOOP
%  dijkstra_loop(+PriorityQueue, +Goal, +Visited, -Path, -Cost)
% ============================================================

% Base case: reached the goal node
dijkstra_loop([pq(Cost, Goal, Path)|_], Goal, _, Path, Cost) :- !.

% Recursive case: expand the lowest-cost node
dijkstra_loop([pq(Cost, Node, Path)|RestQueue], Goal, Visited, FinalPath, FinalCost) :-
    ( member(Node, Visited)
    ->  % Node already settled — skip it
        dijkstra_loop(RestQueue, Goal, Visited, FinalPath, FinalCost)
    ;
        % Mark node as settled
        NewVisited = [Node|Visited],
        % Find all unvisited neighbors and compute tentative costs
        findall(
            pq(NewCost, Neighbor, [Neighbor|Path]),
            (
                connected(Node, Neighbor, Weight,_,_,open,_),
                \+ member(Neighbor, NewVisited),
                NewCost is Cost + Weight
            ),
            NewEntries
        ),
        % Merge new entries into priority queue and re-sort
        append(RestQueue, NewEntries, MergedQueue),
        sort(MergedQueue, SortedQueue),          % sort by pq/3 first arg (cost)
        dijkstra_loop(SortedQueue, Goal, NewVisited, FinalPath, FinalCost)
    ).

dijkstra_loop2([pq(Cost, Goal, Path)|_], Goal, _, Path, Cost) :- !.

dijkstra_loop2([pq(Cost, Node, Path)|RestQueue], Goal, Visited, FinalPath, FinalCost) :-
    ( member(Node, Visited)
    ->  % Node already settled — skip it
        dijkstra_loop2(RestQueue, Goal, Visited, FinalPath, FinalCost)
    ;
        % Mark node as settled
        NewVisited = [Node|Visited],
        % Find all unvisited neighbors and compute tentative costs
        findall(
    pq(NewCost, Neighbor, [Neighbor|Path]),
    (
        connected(Node, Neighbor, _, Weight, _, open, _),
        \+ member(Neighbor, Path),
        (
            (has_condition(Node, Neighbor, deep_potholes) ;
             has_condition(Node, Neighbor, broken_cisterns))
        ->
            NewCost is Cost + Weight + 5
        ;
            NewCost is Cost + Weight %if the roads have broken cisterns or deep potholes the time to traverse increases by 5
        )
    ),
    NewEntries
),
        % Merge new entries into priority queue and re-sort
        append(RestQueue, NewEntries, MergedQueue),
        sort(MergedQueue, SortedQueue),          % sort by pq/3 first arg (cost)
        dijkstra_loop2(SortedQueue, Goal, NewVisited, FinalPath, FinalCost)
    ).










 
