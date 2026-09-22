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

GAMES = {
    'tictactoe': TICTACTOE,
    'nim': NIM,
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
