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

SELECTORS (#315). A head predicate alone cannot separate two rules that
grant different actions through the same `legal` head and update the
same board fluent -- breakthrough's advancing and capturing. So an entry
may narrow a head predicate by the ACTION the statement grants or reads:

    'cell'              every statement whose head is `cell`
    'cell/advance'      ... that grants or reads the action `advance`
    'cell/'             ... that mentions no action at all
    'legal/move.guard'  ... whose action `move` carries the constant
                        `guard` (an action's subject)

Matched against the statement as WRITTEN (its raw form), never against
anything LGREF derives, so the reference cannot inherit the method's
mistakes -- the subject slot in particular (#314).

THE LABELS FOR THE GAMES ADDED BY #315 WERE WRITTEN BEFORE LGREF WAS RUN
ON THOSE GAMES, and committed separately from any score, so the commit
history shows the order.
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

# Drop-three (#315). Tic-tac-toe with gravity.
#   dropping     permission to drop into a column, and the board update
#   gravity      where a dropped counter lands
#   lines        the line machinery that detects a win
#   alternation  control passing between the players
#   ending       terminal and goal
DROPTHREE = {
    'dropping': ['legal/drop', 'cell'],
    'gravity': ['landing', 'below'],
    'lines': ['hline', 'vline', 'dline', 'line', 'right'],
    'alternation': ['control', 'legal/noop'],
    'ending': ['terminal', 'goal', 'open'],
}

# Breakthrough-mini (#315). Two movement rules distinguished only by the
# action they grant. `forward` and `opponent` are SHARED: both movement
# rules and the ending's mobility test need them. The frame statement
# and the initial cells (`cell/`) are board machinery both moves rely on.
BREAKTHROUGH = {
    'advancing': ['legal/advance', 'cell/advance', 'changed/advance',
                  'cell/', 'forward'],
    'capturing': ['legal/capture', 'cell/capture', 'changed/capture',
                  'cell/', 'forward', 'beside', 'opponent'],
    'alternation': ['control', 'legal/noop'],
    'ending': ['terminal', 'goal', 'arrived', 'goalrow', 'blocked',
               'mobile', 'forward', 'opponent'],
}

# Skirmish (#315). Subject-specific movement, the structure Royal Chess
# has: `move(guard, ...)` and `move(lancer, ...)`. Coordinates and the
# board update (`at`, `vacated`) are SHARED by both movement rules;
# blocking and capture are each consulted by both.
SKIRMISH = {
    'guard_movement': ['legal/move.guard', 'kingstep', 'close',
                       'coord', 'succ', 'at', 'vacated'],
    'lancer_movement': ['legal/move.lancer', 'slide', 'north', 'south',
                        'east', 'west', 'coord', 'succ', 'at',
                        'vacated'],
    'blocking': ['empty', 'occupied'],
    'capture': ['enemy_at', 'struck'],
    'alternation': ['control', 'legal/noop'],
    'ending': ['terminal', 'goal', 'guardless', 'hasguard', 'opponent',
               'tick', 'tsucc'],
}

# Monty Hall (#315; GDL-II, a random player and private sight). Labelled
# by the steps a reader of the rules would name. `door` is SHARED by
# hiding and choosing. The persistence of a choice reads `switch`, so it
# is part of switching.
MONTYHALL = {
    'hiding': ['legal/hide_car', 'car', 'door'],
    'choosing': ['legal/choose', 'chosen/choose', 'door'],
    'opening': ['legal/open_door', 'closed', 'sees'],
    'switching': ['legal/switch', 'chosen/switch'],
    'sequence': ['step', 'legal/noop', 'terminal'],
    'payoff': ['goal'],
}

# Muddy children (#315; GDL-III, knowledge as a game condition). `child`
# and `yesno` are vocabulary several rules read and are listed under each.
# `someMuddy` is defined and never used, so it is left unlabelled -- the
# coverage figure reports it rather than a label inventing a role for it.
MUDDYCHILDREN = {
    'dealing': ['legal/muddy', 'oneMuddy', 'yesno', 'has'],
    'observing': ['sees', 'child'],
    'knowledge': ['isMuddy', 'isClean', 'knowsOwn'],
    'announcing': ['legal/say', 'child'],
    'rounds': ['round', 'legal/noop', 'terminal', 'child'],
    'payoff': ['goal', 'knowsOwn', 'child'],
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
    # The #315 games. Their SHARED predicates are the ones their labels
    # list under more than one rule. No redundant or interacting rule was
    # designed into them, and none is claimed: only corridor's are
    # verified by exhaustive enumeration (`reference.verify`).
    'dropthree': {'redundant': (), 'interacting': (), 'shared': ()},
    'breakthrough': {'redundant': (), 'interacting': (),
                     'shared': ('forward', 'opponent')},
    'skirmish': {'redundant': (), 'interacting': (),
                 'shared': ('coord', 'succ', 'at', 'vacated')},
    'montyhall': {'redundant': (), 'interacting': (), 'shared': ('door',)},
    'muddychildren': {'redundant': (), 'interacting': (),
                      'shared': ('child', 'knowsOwn')},
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
#: THE #315 SPLITS, fixed before any of the new games was scored:
#:
#: - `dev` is the only split a hyperparameter may be TUNED on: two
#:   perfect-information board games with one action type each.
#: - `validation` decides whether a tuned value replaces the default --
#:   once, by the rule in `lgref.identify.protocol` -- and is never tuned
#:   on: a counting game, and a game with a random player and private
#:   sight.
#: - `test` is reported and never used for any choice: the games whose
#:   structure is hardest -- shared, redundant and interacting rules
#:   (corridor), two movement rules told apart only by their action
#:   (breakthrough), subject-specific movement (skirmish), and knowledge
#:   as a game condition (muddy children).
SPLITS = {
    'dev': ('tictactoe', 'dropthree'),
    'validation': ('nim', 'montyhall'),
    'test': ('corridor', 'breakthrough', 'skirmish', 'muddychildren'),
}

GAMES = {
    'tictactoe': TICTACTOE,
    'nim': NIM,
    'corridor': CORRIDOR,
    'dropthree': DROPTHREE,
    'breakthrough': BREAKTHROUGH,
    'skirmish': SKIRMISH,
    'montyhall': MONTYHALL,
    'muddychildren': MUDDYCHILDREN,
}


def _actions_mentioned(form):
    """(action name, constant arguments) of every action the statement
    grants (a `legal` head) or reads (a `does` goal), as written."""
    found = []

    def action(term):
        if isinstance(term, tuple) and term:
            found.append((term[0], {a for a in term[1:]
                                    if isinstance(a, str)
                                    and not a.startswith('?')}))
        elif isinstance(term, str):
            found.append((term, set()))

    def walk(term):
        if not isinstance(term, tuple) or not term:
            return
        if term[0] in ('legal', 'does') and len(term) == 3:
            action(term[2])
        for child in term:
            walk(child)

    walk(form)
    return found


def matches(entry, node):
    """Does the label entry select this statement? See SELECTORS."""
    head, _, narrowing = entry.partition('/')
    if node.head_predicate != head:
        return False
    if '/' not in entry:
        return True
    mentioned = _actions_mentioned(node.raw)
    if not narrowing:
        return not mentioned
    name, _, constant = narrowing.partition('.')
    return any(found == name and (not constant or constant in args)
               for found, args in mentioned)


def expected_partition(game, nodes):
    """Map each clause node id to the set of rule names it belongs to.

    Clauses whose head predicate appears in no rule are returned under
    the empty set, so scoring can report coverage honestly rather than
    quietly dropping them.
    """
    spec = GAMES[game]
    out = {}
    for node in nodes:
        out[node.node_id] = {rule_name
                             for rule_name, entries in spec.items()
                             if any(matches(e, node) for e in entries)}
    return out
