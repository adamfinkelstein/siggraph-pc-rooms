# Assign SIGGRAPH PC Rooms
### Adam Finkelstein (Sep-Oct 2022)

This program optimizes room assignment for parallel sessions in the SIGGRAPH PC
meeting.

The program reads a set of anonymized papers with anonymized reviewers from a
CSV file. In typical cases, each paper has two reviewers. It ignores papers that
have no reviewers, and also papers that have been marked as "withdrawn". Papers
with only one reviewer are marked as "singletons" and set aside.

The program tries to partition the reviewers into two rooms of approximately
equal size, while trying also to keep both reviewers of each paper in the same
room. 

This is posed as a graph optimization problem. The reviewers are nodes, and the
papers are edges between nodes. If there are more than one paper shared by a
pair of reviewers, this simply increases the edge weight (1 per paper). The
objective is to partition the graph into two subgraphs, with a minimal cut
between them. 

The graph partition is performed using the 
[Kernighan-Lin](https://en.wikipedia.org/wiki/Kernighan%E2%80%93Lin_algorithm)
(KL) bisection algorithm, which divides the nodes (reviewers) into two roughly
equal size while heuristically attempting to minimize the overall cost of the
"cut" -- papers that cannot be in either room because they link reviewers in
separate rooms.

In general, it is difficult or impossible to find a small cut in a dense graph
such as the one typical of a SIGGRAPH PC. Early experiments suggest that a
minimal cut contains a large fraction (perhaps a quarter) of the papers (edges)
in the pool. Therefore, this program performs the cut twice, so as to cover
almost all papers, as follows. 

First, we divide the reviewers (and papers) into two rooms A and B using KL.
Some papers remain in Cut C -- papers that are not assignable to A or B. In a
second round, we construct a sub-graph using only papers (edges) in Cut C,
together with the reviewers (nodes) linked by those edges. The sub-graph is now
partioned using KL into two new rooms X and Y, with (possibly) a few remaining
cut edges Z. 

In our experiments, typical graphs, when partitioned twice by this procedure,
leave very few remaining cut edges in Z (roughly 1% of the original edges). Thus
there are diminishing returns to further cuts, and two rounds should be
sufficient for a typical meeting.

There is an added benefit to the two rounds of cuts: some papers can appear in
either of two rooms, for example A or X. These degrees of freedom allow us to
further balance the distribution of papers in the rooms in a way that is not
available in a single round. With a single round, the reviewers(nodes) emerge
close to balanced by the KL algorithm, in rooms A and B. However, the number of
papers in A and B are generally not balanced. On the other hand, with two rounds
(rooms A and B in round 1, and X and Y in round 2) some papers can appear in
either one of two rooms (A or X, A or Y, B or X, B or Y).

Thus we balance the rooms as follows. In the first round, every reviewer is in
either Room A or Room B, and every paper is in Room A, Room B, or Cut C. Some
reviewers do not participate in the second round. Therefore, after the second
round, we randomly assign reviewers who did not participate in the second round
to Room X or Y such that the room populations remain roughly balanced. Next we
categorize every paper (not just papers in Cut C) as being in Room X, Room Y, or
Cut Z. Together with the results of the first round, every paper is in one of
nine categories, numbered and named as follows:

| #   | Name | Meaning
| --- | ---  | ---
| 0 | AX | in A or X
| 1 | BX | in B or X
| 2 | AY | in A or Y
| 3 | BY | in B or Y
| 4 | CX | in X
| 5 | CY | in Y
| 6 | AZ | in A
| 7 | BZ | in B
| 8 | CZ | no room possible

For example:

* Category 0 (AX) are papers that could be in either Room A or Room X.
* Category 1 (BX) are papers that could be in either Room B or Room X.
* Category 4 (CX) means a paper can only be in Room X (because it was in Cut C,
meaning neither Room A nor Room B).
* Category 8 (CZ) includes the small fraction (~1%) of papers that cannot appear
in any room (and must be handled specially).

Categories 0-3 provide degrees of freedom that allow us to balance rooms A, B, X
and Y. First we determine how many papers **must** appear in these four rooms
from Categories 4-7. Next we put a cap on the papers from Categories 0-3 that
can appear in each room, by subtracting from the overall average. For example: 

```
Room Ave Capacity: R = CEIL( SUM(COUNT in Categories 0-7) / 4 )
Room A remaining capacity: Ra =  R - COUNT(Category 6)
```

We solve this constrained search problem using a modern SAT solver. Each paper
in Categories 0-3 can appear in one of two rooms, so we assign a boolean
variable to each such paper indicating which room it belongs in. For example, if
a paper is in Category 0, its variable indicates whether it belongs in Room A
(FALSE) or Room X (TRUE).

Next, the constraint for Room A described above, along with the other three
equivalent constraints (for Rooms B, X and Y) appear as natural cardinality
constraints for the SAT solver. These are the only four constraints, and
typically there are many SAT variables, so this problem is relatively
under-constrained and the solver can easily find a solution. A solution however
is not guaranteed, so we consider many rounds as part of a larger optimization.

The program executes multiple iterations of the steps outlined above, seeking
successful solutions to the SAT problem and also minimizing the number of papers
in the second cut:

REPEAT MANY TIMES:

* Use KL to partition graph nodes into Rooms A and B, with Cut edges C.
* Make subgraph including edges C and nodes adjacent to those edges.
* Use KL to partition subgraph into Rooms X and Y with Cut edges Z.
* Randomly assign remaining nodes (graph - subgraph) to Rooms X or Y.
* Assign all papers (edges) outside Cut Z to rooms X and Y.
* Solve SAT problem to assign each paper in AX,AY,BX,BY to A,B,X, or Y.
* Keep solution if SAT solved and this is minimal size Cut Z so far.

After this optimization papers marked as "singletons" above are assigned
randomly to one of the rooms where they can be.

It outputs the assignments of papers and people to rooms, in two CSV files.

To setup this program:

```
python3 -m venv myvenv
source myvenv/bin/activate
pip install networkx
pip install python-sat
```

Then to run this program:
```
python assign-pc-rooms.py filename.csv
```

It writes out files `paper-rooms.csv` and `people-rooms.csv`.