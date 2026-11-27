"""Behaviour of a description over a fixed state set, and agreement of a
candidate intervention with a reference variant.

THE STATE SET S (docs/paper-a/protocol.md, fixed before any candidate is
scored): the probe states; every reachable state where that is under
`EXHAUSTIVE_LIMIT`; otherwise the states of `BASE_GAMES` seeded random
games of the unmodified game plus `VARIANT_GAMES` of each reference
variant, so states only a variant reaches are in S too.

BEHAVIOUR is a set of ATOMS evaluated at every state of S:

  legal(s, role, move)   is `move` legal for `role` in s
  next(s, joint)         the successor of a joint move (for joint moves
                         legal in every description compared)
  terminal(s)            does s end the game
  goal(s, role)          the goal values (at states terminal in every
                         description compared)

AGREEMENT. An atom is CHANGED by a description if its value differs
from the unmodified game's. A candidate's change is CORRECT if its value
equals the reference variant's. precision = correct / changed by the
candidate, recall = correct / changed by the reference. A `None` is "not
measurable" (nothing changed on that side), never a zero.

VALIDITY. A description is a valid game on S when it loads, every role
has a legal move in the initial state, and no state of S or of
`VALIDITY_GAMES` seeded random games of the description itself is
non-terminal with a role that has no legal move, or terminal with two
goal values for one role -- where the unmodified game is not already
ill-formed in the same way at that state (see `validity`).
"""

import itertools

from lgref.bench import probes as _probes
from lgref.bench import wellformed

EXHAUSTIVE_LIMIT = 10000
BASE_GAMES = 200
VARIANT_GAMES = 50
VALIDITY_GAMES = 40


def state_set(game, base_text=None):
    """(sorted list of states, description of how S was built)."""
    from lgref.bench.catalog import game_path

    if base_text is None:
        with open(game_path(game)) as handle:
            base_text = handle.read()
    states = set()
    _meta, changes = _probes.load_variants(game)
    for change in changes:
        for probe in change.probes:
            states.add(frozenset(_probes._state(probe['state'])))
    found, mode = wellformed.walk(base_text, exhaustive=True,
                                  limit=EXHAUSTIVE_LIMIT)
    if mode == 'exhaustive':
        states.update(found)
        how = 'probes + all {} reachable states'.format(len(found))
    else:
        found, _m = wellformed.walk(base_text, games=BASE_GAMES, seed=0)
        states.update(found)
        n_base = len(found)
        n_variant = 0
        for change in changes:
            text = _probes.variant_text(base_text, change)
            more, _m = wellformed.walk(text, games=VARIANT_GAMES, seed=1)
            n_variant += len(more)
            states.update(more)
        how = ('probes + {} base random games ({} states) + {} per variant '
               '({} states)'.format(BASE_GAMES, n_base, VARIANT_GAMES,
                                    n_variant))
    ordered = sorted(states, key=lambda s: sorted(map(repr, s)))
    return ordered, how


class Behaviour(object):
    """Atoms of one description over S. `loads` False means none."""

    __slots__ = ('loads', 'error', 'legal', 'terminal', 'goal', 'next',
                 'roles')

    def __init__(self):
        self.loads = False
        self.error = None
        self.legal = {}      # (s, role) -> frozenset of moves
        self.terminal = {}   # s -> bool
        self.goal = {}       # (s, role) -> frozenset of values
        self.next = {}       # (s, joint) -> frozenset state
        self.roles = ()


def behaviour(text, states):
    """The atoms of `text` at each state of `states` (by index)."""
    out = Behaviour()
    try:
        game = wellformed.open_game(text)
    except Exception as exc:                       # noqa: BLE001
        out.error = '{}: {}'.format(type(exc).__name__, exc)
        return out
    out.loads = True
    out.roles = tuple(game.roles)
    for index, state in enumerate(states):
        try:
            wellformed.at(game, state)
            terminal = game.is_terminal()
            out.terminal[index] = terminal
            legal = {}
            for role in game.roles:
                legal[role] = frozenset(game.legal_moves(role))
                out.legal[(index, role)] = legal[role]
            if terminal:
                for role in game.roles:
                    out.goal[(index, role)] = frozenset(
                        wellformed.goal_values(wellformed.at(game, state),
                                               role))
                continue
            for joint in itertools.product(
                    *[sorted(legal[r], key=repr) for r in game.roles]):
                moves = dict(zip(game.roles, joint))
                out.next[(index, joint)] = wellformed.successor(
                    game, state, moves)
        except Exception as exc:                   # noqa: BLE001
            out.error = 'state {}: {}: {}'.format(index, type(exc).__name__,
                                                  exc)
    return out


def _atoms(base, ref, cand):
    """Every atom compared, with its value in each description."""
    rows = []
    for key in sorted(set(base.terminal) & set(ref.terminal)
                      & set(cand.terminal)):
        rows.append((('terminal', key), base.terminal[key],
                     ref.terminal[key], cand.terminal[key]))
    for key in sorted(set(base.legal) | set(ref.legal) | set(cand.legal),
                      key=repr):
        moves = (base.legal.get(key, frozenset())
                 | ref.legal.get(key, frozenset())
                 | cand.legal.get(key, frozenset()))
        for move in sorted(moves, key=repr):
            rows.append((('legal', key, move),
                         move in base.legal.get(key, ()),
                         move in ref.legal.get(key, ()),
                         move in cand.legal.get(key, ())))
    for key in sorted(set(base.next) & set(ref.next) & set(cand.next),
                      key=repr):
        rows.append((('next', key), base.next[key], ref.next[key],
                     cand.next[key]))
    for key in sorted(set(base.goal) & set(ref.goal) & set(cand.goal),
                      key=repr):
        rows.append((('goal', key), base.goal[key], ref.goal[key],
                     cand.goal[key]))
    return rows


KINDS = ('legal', 'terminal', 'goal', 'next')


def agreement(base, ref, cand):
    """Precision, recall and F1 of the candidate's behavioural change
    against the reference variant's, over the atoms of S -- and two
    COUNTS beside them (#358, the user's correctness instruction):

      differ      atoms where the candidate and the reference variant
                  disagree, in either direction, by kind. 0 in every
                  kind means the candidate is FUNCTIONALLY EXACT on S
                  (assuming the reference is right); F1 says how close
                  a candidate that is not exact comes.
      collateral  atoms the candidate changes that the reference leaves
                  as they were: damage to behaviour belonging to other
                  rules, by kind.

    `next` atoms exist only for joint moves legal in all three
    descriptions and `goal` atoms only at states terminal in all three,
    so a disagreement there is already counted under `legal` or
    `terminal`; the totals add all four kinds anyway, and the kinds are
    reported apart.
    """
    if not cand.loads:
        changed_ref = sum(1 for _a, b, r, _c in _atoms(base, ref, ref)
                          if r != b)
        return {'precision': None,
                'recall': 0.0 if changed_ref else None, 'f1': None,
                'changed_ref': changed_ref, 'changed_cand': None,
                'correct': 0, 'unintended': None, 'missed': changed_ref,
                'differ': None, 'differ_total': None, 'collateral': None,
                'collateral_total': None, 'exact': False}
    changed_ref = changed_cand = correct = unintended = 0
    differ = dict.fromkeys(KINDS, 0)
    collateral = dict.fromkeys(KINDS, 0)
    for atom, b, r, c in _atoms(base, ref, cand):
        kind = atom[0]
        if c != r:
            differ[kind] += 1
        if c != b and r == b:
            collateral[kind] += 1
        if r != b:
            changed_ref += 1
        if c != b:
            changed_cand += 1
            if c == r:
                correct += 1
            else:
                unintended += 1
    precision = correct / float(changed_cand) if changed_cand else None
    recall = correct / float(changed_ref) if changed_ref else None
    if precision is None or recall is None:
        f1 = None
    elif precision + recall:
        f1 = 2 * precision * recall / (precision + recall)
    else:
        f1 = 0.0
    return {'precision': precision, 'recall': recall, 'f1': f1,
            'changed_ref': changed_ref, 'changed_cand': changed_cand,
            'correct': correct, 'unintended': unintended,
            'missed': changed_ref - correct,
            'differ': differ, 'differ_total': sum(differ.values()),
            'collateral': collateral,
            'collateral_total': sum(collateral.values()),
            'exact': not sum(differ.values())}


def changes_anything(base, cand):
    """Does the candidate differ from the unmodified game anywhere on S?"""
    if not cand.loads:
        return True
    return any(b != c for _a, b, _r, c in _atoms(base, base, cand))


def _defects(beh):
    """{(state index, kind, role)} where a description is ill-formed."""
    out = set()
    for (index, role), moves in beh.legal.items():
        if not moves and not beh.terminal[index]:
            out.add((index, 'no legal move', role))
    for (index, role), values in beh.goal.items():
        if len(values) > 1:
            out.add((index, 'two goal values', role))
    return out


def validity(text, states, cand=None, base=None):
    """(valid, reason). `cand` reuses an already computed Behaviour.

    S holds probe states that the unmodified game never reaches, and the
    unmodified game can be ill-formed there (a far-row pawn with its own
    side to move, say). A defect the candidate shares with `base` at the
    same state is inherited, not caused, so only defects `base` does not
    have count against the candidate.
    """
    cand = cand or behaviour(text, states)
    if not cand.loads:
        return False, 'does not load: ' + (cand.error or '')
    if cand.error:
        return False, cand.error
    game = wellformed.open_game(text)
    if base is not None and tuple(game.roles) != tuple(base.roles):
        return False, 'roles changed: {} -> {}'.format(
            list(base.roles), list(game.roles))
    if not game.roles:
        return False, 'no roles'
    for role in game.roles:
        if not game.legal_moves(role):
            return False, 'no legal move for {} at the start'.format(role)
    inherited = _defects(base) if base is not None else set()
    caused = sorted(_defects(cand) - inherited, key=repr)
    if caused:
        index, kind, role = caused[0]
        return False, 'state {}: {} has {}'.format(
            index, role, 'no legal move' if kind == 'no legal move'
            else 'two goal values')
    try:
        own, _mode = wellformed.walk(text, games=VALIDITY_GAMES, seed=7)
        problems = wellformed.check(text, own)
    except Exception as exc:                       # noqa: BLE001
        return False, 'own play fails: {}: {}'.format(
            type(exc).__name__, exc)
    if problems:
        return False, 'own play: ' + problems[0]
    return True, 'ok'
