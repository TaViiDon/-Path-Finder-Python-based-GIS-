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
connected(Source, Des, Dis, Time, Type, Status, Ways) :- road(Source, Des, Dis, Time, Type, Status, one_way).

%if roads are labeled as two ways they are bidirectional
connected(Source, Des, Dis, Time, Type, Status, Ways) :- road(Source, Des, Dis, Time, Type, Status, two_way).
connected(Source, Des, Dis, Time, Type, Status, Ways) :- road(Des, Source, Dis, Time, Type, Status, two_way).

