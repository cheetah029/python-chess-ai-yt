# LGREF identification versions: V0 (random) to now

Issue #409. One numbering for every build of LGREF's **rule
identification**, the step that groups a game's statements into
candidate rules and turns each group into an intervention. It works
like the player numbering in [`agent-versions.md`](agent-versions.md),
so tables, commit messages and the paper can say "V1" and mean one
thing.

**What counts as identification.** The code that decides which statements
go together, and how a group becomes an ablation:

- `lgref/identify/`: reading statements (`clauses.py`), the typed
  statement graph (`graph.py`), community detection, the overlap step and
  the ownership split (`cluster.py`), and the probe (`intervention.py`);
- `lgref/bench/methods.py`: the grouping methods behind one interface;
- `lgref/bench/interventions.py`: the intervention builder used by
  Paper A.

Scoring (`metrics.py`, `behaviour.py`, `ablation_metrics.py`), the
benchmark games and the reference variants are not identification, so a
change to them is not a new version.

## How the numbers are assigned

- A **major version** changes **what information decides which
  statements go together**. V0 uses none: statements are assigned to
  groups at random. V1 uses the static structure of the description: a
  typed, weighted statement graph and modularity community detection.
  Grouping by measured behaviour would be a new major version (see
  "Functional identification" below), and so would a new combination
  method such as the V2 proposal (`docs/paper-a/lgref-v2-proposal.md`,
  #411).
- A **minor version** (sub-version) is any commit that changes the
  groups or interventions produced while keeping the family's source of
  information: how statements are read, the graph's edges or weights,
  the resolution rule, the overlap step, the ownership split, an input
  dialect, a bug fix.
- A commit that touches identification code but **provably produces the
  same groups and interventions** is not a sub-version. It is listed
  under "Commits that did not change identification".
- The **representative** of a major version is its **latest
  sub-version**. It is the column the grouping-version tables use
  (`docs/paper-a/grouping-version-tables.md`, #410).
- Every SHA below was checked against `git log` on 2026-11-27 (the
  doc test re-checks it). Dates are commit dates.

## Baselines are not versions

The other grouping methods in `lgref/bench/methods.py` are **baseline
methods**. They are labelled columns in the tables, never versions,
because they are not builds of LGREF:

| baseline | what it is |
|---|---|
| `louvain_hard` | LGREF's graph and resolution with Louvain, no hold-out and no overlap step |
| `leiden` | Leiden in place of Louvain, everything else as LGREF |
| `leiden_hard` | Leiden with no overlap step |
| `link_communities` | Ahn, Bagrow and Lehmann (2010) on LGREF's weighted graph; overlap is native |
| `dependency_louvain` | Louvain at resolution 1.0 on the plain call graph |
| `components` | connected components of the typed graph |
| `name_tokens` | statements grouped when their head predicates share a name token |
| `singletons` | one group per statement |
| `one_group` | every statement in one group |

`docs/paper-a/methods.md` describes each one in full.

**Labelled variants are not versions either.** The post-freeze variant
`lgref_postfreeze_noterminal` (#394: V1.8 with the terminal edge off)
was run and reported beside the frozen result, but was not adopted. It
appears in tables only under its own label.
`lgref_plus_overlap` (#411: V1.8's groups plus at most one extra shared
membership per statement) was built only to be rated, to isolate
overlap from fragmentation, and is never a candidate for adoption.

## Summary: major versions only

| Version | Representative | How it groups statements | Run it today |
|---|---|---|---|
| **V0** | V0.0 (8d8a0ed) | at random, matched to V1's group sizes and overlap pattern | `lgref.bench.methods.METHODS['random_matched']`; `lgref identify --compare random` |
| **V1** | V1.8 (ab7b33b) | modularity community detection on the typed statement graph, with an overlap step and the ownership split | `lgref.bench.methods.METHODS['lgref']`; `lgref identify` |

---

## V0: matched random groupings

| | Date | SHA | What |
|---|---|---|---|
| **V0.0** | 2026-11-26 | 8d8a0ed | `random_matched` (379b67d, #350). V1's grouping at the same seed with the statements randomly permuted: the group count, the sizes and the overlap pattern are kept, and which statements go together is lost. **Representative.** |

V0 is the null: what V1's group shapes achieve with no information about
which statements belong together.

**How V0 is measured.** One draw is one random permutation. Since #396,
V0 is reported as the **mean over 30 draws** (`--draws 30`), never as
one draw, because one draw can land anywhere in V0's spread. That is a
measurement protocol, not a new build, so it has no new number.

## V1: the LGREF family (static statement graph)

| | Date | SHA | What changed in identification |
|---|---|---|---|
| **V1.0** | 2026-09-22 | 6d65258 | The pipeline (#187). Statements are normalised into typed nodes. The statement graph has typed, weighted edges: legality 3.0, shared_state 2.5, same_head 2.0, temporal 1.5, predicate 1.0, terminal 0.5, co_activation 0. Fluents read by at least 8% of statements give no shared_state edges, in games of 20 or more statements. Louvain runs at a fixed resolution of 1.0. Generic board updates are held out and reattached to every rule they serve, and a statement joins any community holding at least 25% of its edge weight. The ablation deletes a whole community. |
| **V1.1** | 2026-09-22 | 259a78d | Infix input (#190): a prefix `or` body becomes one statement per branch, so Royal Chess reads as 522 statements, not 488. Nodes and edges are inserted in sorted order, so the partition no longer depends on string hashing (18, 19 or 20 clusters over five `PYTHONHASHSEED` values before). |
| **V1.2** | 2026-09-22 | 30d1879 | The resolution is calibrated, not transferred (#189). It is chosen to hold the mean statements per rule at the validated value. Tic-tac-toe and Nim stay at 1.00; Royal Chess moves to 33.01. |
| **V1.3** | 2026-09-22 | ca4f5a0 | The coverage rule replaces V1.2's calibration (#202): the finest resolution whose coverage stays within 0.03 of the coarse-end reference. Nim's ARI rises from 0.734 to 0.838. Groups with no state dependence at any depth get the language verdict and are not ablated. |
| **V1.4** | 2026-10-29 | e483a1e | The statement reader reads GDL-III `knows` (444cf74, #280, landed with PR #270). Only GDL-III games can change: of the 25 fingerprinted games, only Cheryl's Birthday does. |
| **V1.5** | 2026-11-19 | d34aa7c | The ownership split (5661f8e, #313). A group's ablation deletes what it owns, relaxes the guards it defines, and keeps what other rules need. A group with nothing to remove or relax is `infrastructure`. On Royal Chess, 24 rule verdicts became 17. |
| **V1.6** | 2026-11-19 | 733eb9c | The action subject slot is discovered, not assumed to be argument 1, and clustering visits statements by position, not by id (3cdf53b, #314). A consistent renaming no longer changes the partition; before, it changed 32 of Royal Chess's rules. The groups change on 17 of the 25 fingerprinted games. |
| **V1.7** | 2026-11-19 | a951ac1 | Predicate aliases are detected by structure, not by name (924c1bb, #320). Under an opaque renaming, Royal Chess's five aliases are still found, so its rules no longer change. On readable names nothing changes: all 25 fingerprinted games are identical to V1.6. |
| **V1.8** | 2026-11-27 | ab7b33b | The Paper A freeze (#357; `paper-a/freeze.md`). It adds the bench intervention builder (d4ee216): the ownership split as before, plus whole-group deletion (`delete_group`) as a second reported procedure. The groups and the ownership split are identical to V1.7's on all 25 fingerprinted games. **Representative.** |

### Commits that did not change identification

These touch identification code, but leave every group and intervention
as it was. They are not sub-versions.

| Date | SHA | Why not |
|---|---|---|
| 2026-09-22 | 1d52ee3 | Relax and remove as ablation operations in `lgref/ablate/`. In `lgref/identify/` it changes only how networkx is imported. |
| 2026-09-23 | c4255f7 | A turn cap in the validation gate (`gate.py`), not in grouping. |
| 2026-11-18 | 7c5b67c | Fixes the `trace_only` validation baseline (05881c1); production LGREF and every other baseline are tested unchanged. |
| 2026-11-19 | 96e2dab | The validation protocol on eight labelled games (e857eac: `protocol.py`, new test games). Scoring only. |
| 2026-11-19 | 078d04e | Adds the `co_use` signal at weight 0, so it is never used (076c246, #321: neither play signal was adopted). |
| 2026-11-26 | 8d8a0ed | The methods interface (379b67d, #350). LGREF through it is tested equal to production clustering, so V1 is unchanged. (The same commit introduces V0.0.) |
| 2026-11-27 | b9646d4 | After the freeze (ca00aff, #363). `interventions.py` records which statements the ownership split protected; the interventions themselves are unchanged. |

Commits that only add test games under `lgref/identify/testgames/`
(238e243, ab792e8, f03c371, 16b9c90, 54a387d, 605ae6b) are data, not
identification.

### How "changed" and "identical" were checked

Each SHA above is the commit **on main** where the change landed: the
change's own commit for a squash merge, otherwise the merge commit (the
change's own commit is named beside it). Several changes were developed
in parallel: 3cdf53b, for example, does not contain 5661f8e, so only
their merge 733eb9c holds V1.6.

At each of those main-line commits, `tools/lgref_version_fingerprint.py`
was run in a clean `git clone --shared` copy, with `PYTHONHASHSEED=0`
and seed 0, on the **same 25 game files** (`lgref/identify/testgames/`
and `lgref/bench/games/` as of 501c5ae). It hashes two things per game:

- **groups**: the calibrated resolution, and each rule's statements and
  shared members;
- **ownership**: each rule's owned statements and relaxations (absent
  before V1.5).

The results are in `docs/lgref-version-fingerprints.json`.
Between consecutive commits, the number of games whose hash changed:

| from | to | games compared | groups changed | ownership changed |
|---|---|---|---|---|
| V1.0 (6d65258) | V1.1 (259a78d) | 22 | 22 | n/a |
| V1.1 | 1d52ee3 | 25 | 0 | n/a |
| 1d52ee3 | V1.2 (30d1879) | 25 | 23 | n/a |
| V1.2 | V1.3 (ca4f5a0) | 25 | 25 | n/a |
| V1.3 | c4255f7 | 25 | 0 | n/a |
| c4255f7 | V1.4 (e483a1e) | 25 | 1 | n/a |
| V1.4 | 7c5b67c | 25 | 0 | n/a |
| 7c5b67c | 96e2dab | 25 | 0 | n/a |
| 96e2dab | V1.5 (d34aa7c) | 25 | 0 | new |
| V1.5 | V1.6 (733eb9c) | 25 | 17 | 16 |
| V1.6 | V1.7 (a951ac1) | 25 | 0 | 0 |
| V1.7 | 078d04e | 25 | 0 | 0 |
| 078d04e | 8d8a0ed | 25 | 0 | 0 |
| 8d8a0ed | V1.8 (ab7b33b) | 25 | 0 | 0 |
| V1.8 | b9646d4 | 25 | 0 | 0 |

V1.0 reads prefix descriptions and fails on the three synthetic games,
so 22 games are compared there. Every "not a sub-version" commit
changes no hash. Two sub-versions change no hash on these files, and
each is a sub-version for a reason the files cannot show: V1.7 changes
the groups of a renamed description (the case it fixes), and V1.8 adds
an intervention procedure. The doc test checks this table against the
recorded fingerprints.

## Functional identification (later)

Reserved. Functional identification would group statements by what they
**do** in play, for example by the legal moves, endings and payoffs that
change together when a statement is removed, rather than by the shape of
the description. It uses a different source of information, so the
first build will be a **new major version**, with sub-versions numbered
as above. Nothing is built yet. Two play signals were tested as extra
graph edges inside V1 (`co_activation`, `co_use`, #321) and neither was
adopted; those were V1 experiments, not functional identification.
