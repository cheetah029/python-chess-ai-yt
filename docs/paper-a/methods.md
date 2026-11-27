# Paper A: the grouping methods compared

Built for issue #350 (stage 2). The code is `lgref/bench/methods.py`.
Every method takes a description's statements and returns groups of
statements, which may overlap. Scoring and intervention building see
only those groups, so every method is scored and intervened on in the
same way. The protocol is `docs/paper-a/protocol.md`.

| method | what it is | overlap | seeded |
|---|---|---|---|
| `lgref` | production LGREF. Louvain on the typed, weighted statement graph at the coverage-calibrated resolution. Generic board updates are held out, then reattached to every rule they serve, and the overlap step runs (a statement joins any community that holds ≥ 25% of its edge weight) | post-processing | yes |
| `louvain_hard` | the same graph and resolution, with no hold-out, no reattachment and no overlap step | none | yes |
| `leiden` | Leiden (igraph 0.11.8) in place of Louvain. Everything else is the same: graph, modularity objective, resolution, hold-out and overlap step | post-processing | yes |
| `leiden_hard` | Leiden with no overlap, as `louvain_hard` | none | yes |
| `link_communities` | Ahn, Bagrow & Lehmann (2010) on the same weighted graph. Edges are clustered by weighted Tanimoto similarity, with single linkage, cut at maximum partition density. A statement is in the community of each of its edges | native | no |
| `dependency_louvain` | basic dependency clustering: Louvain at resolution 1.0 on the plain call graph (predicate edges only, unit weight) | none | yes |
| `components` | connected components of the typed graph: what GGP factoring finds on a single game | none | no |
| `name_tokens` | statements grouped when their head predicates share a name token (the #315 baseline) | through tokens | no |
| `singletons` | one group per statement | none | no |
| `one_group` | every statement in one group | none | no |
| `random_matched` | LGREF's grouping at the same seed, with the statements randomly permuted. The group count, the sizes and the overlap pattern are kept. Which statements go together is lost | as LGREF | yes |

How each method is checked to do what its name says
(`lgref/tests/test_paper_a_methods.py`):

- **`lgref` matches production.** Through the pluggable pipeline it equals
  production `lgref.identify.cluster.cluster` exactly, on all five dev
  games. The overlap step fires on every one of them. Disabling it makes
  all five equality tests fail, so the test does reach the overlap
  machinery.
- **Leiden** splits two cliques joined by one edge into the two cliques.
  It runs on its own seeded generator and leaves the global random state
  untouched.
- **Link communities** gives Ahn et al.'s answer on two triangles that
  share a node: two communities, the shared node in both, partition
  density 1. On a 5-clique it gives one community, and on a path it
  keeps every edge apart.
- **`random_matched`** keeps LGREF's group sizes and membership counts,
  and nothing else.
- **Coverage and determinism.** Every method covers every statement and
  repeats itself. It also gives the same groups in two processes with
  different `PYTHONHASHSEED`, which catches set-ordering bugs that
  repeating inside one interpreter cannot.

## The groups each method proposes on the dev games

Seed 0. Each cell is groups / statements in two or more groups /
statements in no group. These are counts, not scores. Scores against
the reference sheets are stage 4's.

| method | tictactoe | nim | corridor | breakthrough5 | othello4 |
|---|---|---|---|---|---|
| lgref | 6 / 6 / 0 | 8 / 11 / 0 | 10 / 8 / 0 | 8 / 6 / 0 | 8 / 13 / 0 |
| louvain_hard | 5 / 0 / 13 | 8 / 0 / 0 | 10 / 0 / 0 | 8 / 0 / 1 | 8 / 0 / 0 |
| leiden | 6 / 6 / 0 | 8 / 11 / 0 | 9 / 6 / 0 | 8 / 6 / 0 | 8 / 13 / 0 |
| leiden_hard | 5 / 0 / 13 | 8 / 0 / 0 | 9 / 0 / 2 | 8 / 0 / 1 | 8 / 0 / 0 |
| link_communities | 11 / 12 / 0 | 6 / 6 / 0 | 20 / 29 / 0 | 19 / 16 / 0 | 27 / 58 / 0 |
| dependency_louvain | 4 / 0 / 22 | 3 / 0 / 8 | 3 / 0 / 19 | 5 / 0 / 28 | 4 / 0 / 10 |
| components | 4 / 0 / 0 | 3 / 0 / 0 | 4 / 0 / 0 | 3 / 0 / 0 | 2 / 0 / 0 |
| name_tokens | 11 / 0 / 0 | 10 / 1 / 0 | 12 / 0 / 6 | 20 / 0 / 0 | 26 / 0 / 0 |
| singletons | 35 / 0 / 0 | 22 / 0 / 0 | 44 / 0 / 0 | 75 / 0 / 0 | 75 / 0 / 0 |
| one_group | 1 / 0 / 0 | 1 / 0 / 0 | 1 / 0 / 0 | 1 / 0 / 0 | 1 / 0 / 0 |
| random_matched | 6 / 6 / 0 | 8 / 11 / 0 | 10 / 8 / 0 | 8 / 6 / 0 | 8 / 13 / 0 |

Two observations:

- **`components` finds two to four groups on every game**, as the
  research notes predicted for GGP-style factoring of a single game.
- **The hard variants leave statements unclustered.** On tic-tac-toe, 13
  statements end up in no group. With the generic board update left in
  the partition, the board statements group differently and some fall
  out as singletons. That is a cost of switching overlap off, not a
  defect.

## The dependency

Leiden comes from `igraph==0.11.8`, with its one dependency
`texttable==1.7.3`. Both are pinned in `requirements.txt` and installed
in the project `.venv` from PyPI. Nothing outside `lgref/bench/` imports
igraph.
