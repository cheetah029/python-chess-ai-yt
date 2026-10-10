"""Hand-stated rule boundaries for the validation games.

These are MY annotations of games small enough to be certain about, and
they exist to score rule identification before it is trusted on Royal
Chess. Two properties matter:

  - They are stated by HEAD PREDICATE, not by clause index, so they stay
    readable and survive edits to the game files.
  - They are stated ONLY for these tiny games. The designer's Royal Chess
    labels remain quarantined in lgref/reference/, which
    test_label_isolation keeps unreachable from identify/ and functions/.
    Nothing here concerns Royal Chess.

A rule groups clauses by the BEHAVIOUR they jointly implement. Where a
clause plausibly serves two rules, it is listed under both: membership is
soft, and forcing a single owner would make the reference partition
disagree with its own definition.
"""

# Tic-tac-toe. Four provisions, verifiable by reading the file:
#   marking      permission to mark a blank cell, and the board update
#                that follows (including cells left untouched)
#   alternation  control passing between the players
#   lines        the row/column/diagonal machinery that detects a win
#   ending       terminal and goal
TICTACTOE = {
    'marking': ['legal', 'cell'],
    'alternation': ['control'],
    'lines': ['row', 'column', 'diagonal', 'line'],
    'ending': ['terminal', 'goal', 'open'],
}

# Nim. Deliberately structured like tic-tac-toe at the rule level while
# sharing none of its vocabulary — no cells, no spatial structure.
#   taking       permission to take 1 or 2, and the resulting pile size
#   arithmetic   the successor relation the taking rule depends on
#   alternation  control passing between the players
#   ending       terminal and goal
NIM = {
    'taking': ['legal', 'pile'],
    'arithmetic': ['succ', 'positive', 'atleast2'],
    'alternation': ['control'],
    'ending': ['terminal', 'goal', 'empty_pile'],
}

# Corridor. Built for the Phase B properties the other two lack --
# shared statements they have, redundant and interacting rules they do
# not. Every property is VERIFIED by exhaustive enumeration in
# reference.py, not asserted here; three earlier versions of this game
# claimed properties it did not have.
#   movement     permission to step one or two, and the resulting square
#   boundary     the corridor limit -- REDUNDANT, since succ stops at 7
#                (succ/plus2 are SHARED with movement, listed under both)
#   blocking     may not land on the other token -- INTERACTS
#   tempo        no 2-step straight after a 2-step -- INTERACTS
#   alternation  control passing between the players
#   ending       terminal and goal
# SHARED MEMBERSHIP IS THE POINT, so `succ` and `plus2` are listed under
# BOTH the rules that need them. A first version gave arithmetic its own
# rule, which silos it -- and then no statement in ANY of the three games
# belonged to more than one rule, so "shared statements" was in the
# docstring and not in the data. Phase B asks for shared statements; this
# is what sharing looks like.
CORRIDOR = {
    'movement': ['legal', 'at', 'succ', 'plus2'],
    'boundary': ['inside', 'succ', 'plus2'],
    'blocking': ['clear'],
    'tempo': ['fresh', 'stale'],
    'alternation': ['control'],
    'ending': ['terminal', 'goal', 'home'],
}

#: Which rules are redundant or interacting, and what the exact reference
#: effect therefore IS. Recorded here because a benchmark's value is in
#: the answer being known in advance; computed and checked by
#: `reference.verify`, which the tests run.
#:
#: `boundary` must measure as EXACTLY ZERO on every observable -- states,
#: terminals and mean branching. A method that reports an effect for it is
#: reporting noise.
#:
#: `blocking` and `tempo` must measure as SUPER-ADDITIVE on mean
#: branching: +0.1232 and +0.1467 alone, +0.4149 together, so the joint
#: effect is 54% larger than the sum of the parts. A study that ablates
#: one rule at a time measures the two small numbers and misses the
#: interaction entirely -- which is the failure mode this game exists to
#: expose.
STRUCTURE = {
    'corridor': {
        'redundant': ('boundary',),
        'interacting': (('blocking', 'tempo'),),
        # The shared PREDICATES, not a rule name: `arithmetic` stopped
        # being a rule when it was folded into the two rules that use it.
        'shared': ('succ', 'plus2'),
    },
    # The two original benchmarks are clean partitions -- every rule
    # stands alone and no statement is shared. Recorded as empty rather
    # than left unstated, so "this game has no sharing" is a claim the
    # tests can check rather than an omission.
    'tictactoe': {'redundant': (), 'interacting': (), 'shared': ()},
    'nim': {'redundant': (), 'interacting': (), 'shared': ()},
}

#: Development, validation and held-out splits.
#:
#: RELATED VARIANTS STAY IN ONE SPLIT, as Phase B requires: a game and its
#: ablations share statements almost entirely, so putting a variant in
#: `test` while its baseline is in `dev` would leak nearly the whole
#: answer. The unit of splitting is the GAME, never the variant.
#:
#: `corridor` is the held-out game ON PURPOSE. It is the only one with
#: redundant and interacting rules, so holding it back means the method is
#: developed on separable rules and tested on inseparable ones -- which is
#: the harder direction and the honest one. Developing on it would make
#: the interaction a tuning target.
SPLITS = {
    'dev': ('tictactoe',),
    'validation': ('nim',),
    'test': ('corridor',),
}

GAMES = {
    'tictactoe': TICTACTOE,
    'nim': NIM,
    'corridor': CORRIDOR,
}


def expected_partition(game, nodes):
    """Map each clause node id to the set of rule names it belongs to.

    Clauses whose head predicate appears in no rule are returned under
    the empty set, so scoring can report coverage honestly rather than
    quietly dropping them.
    """
    spec = GAMES[game]
    by_predicate = {}
    for rule_name, predicates in spec.items():
        for predicate in predicates:
            by_predicate.setdefault(predicate, set()).add(rule_name)

    out = {}
    for node in nodes:
        out[node.node_id] = set(by_predicate.get(node.head_predicate, ()))
    return out
