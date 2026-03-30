%knowledge database

%dynamic updates
:- dynamic road/7.
:- dynamic special_conditions/3.

%road(source, destination, distance, time, type, status, ways)
road(old_harbour,gutters, 5, 9, paved, open, two_way).
road(gutters,spring_villiage, 10, 15, paved, open, two_way).
road(gutters,bushy_park, 5, 5, unpaved, open, two_way).
road(spring_villiage,dover, 12, 15,unpaved, open, two_way).
road(dover,content, 7, 9,unpaved, open, two_way).
road(content,bamboo, 5, 6, paved, open, two_way).
road(bamboo,byles, 10,15 , paved, open, two_way).
road(old_harbour,calbeck_junction, 7, 10, paved, open, two_way).

%special conditions
%special_conditions(source, destination, condition).
special_conditions(old_harbour, gutters, deep_potholes).
special_conditions(old_harbour, gutters, broken_cisterns).

%bidirectionl and oneway roads
%if roads are label one way
connected(Source, Des, Dis, Time, Type, Status, ways) :- road(Source, Des, Dis, Time, Type, Status, one_way).

%if roads are labeled as two ways they are bidirectional
connected(Source, Des, Dis, Time, Type, Status, ways) :- road(Source, Des, Dis, Time, Type, Status, two_way).
connected(Source, Des, Dis, Time, Type, Status, ways) :- road(Des, Source, Dis, Time, Type, Status, two_way).

%search functionality

% Get all neighbors of a node
neighbors(Node, Neighbors) :-
    findall(N, road(Node, N,_,_,_,_,_), Neighbors).

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
    road(Current, Next,_,_,_,_,_),
    \+ member(Next, Visited),
    dfs_helper(Next, Goal, [Next|Visited], Path).