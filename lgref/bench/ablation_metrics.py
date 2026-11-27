"""Ablation-based grouping metrics (Paper A, #363: the user's list).

Over the fixed state set S, a description's BEHAVIOUR is its set of
atoms:

    ('legal', s, role, move)     move is legal for role in state s
    ('terminal', s)              s ends the game
    ('goal', s, role, value)     role's payoff in s (terminal s only)
    ('next', s, joint, s2)       the joint move leads from s to s2

The user's definition lists the first three. The fourth is added, and
reported as its own kind, because without it a rule that only changes
what a move DOES is invisible: Othello's `no_flip` edits only `next`
statements, so over legal/terminal/goal atoms at the fixed states of S
its reference ablation changes nothing, and every inert intervention
scored as functionally exact (found by the validation pass, #363).

For a rule r, with `base` the unmodified game, A a method's ablation of
r and R the reference ablation of r, and

    changed(X) = atoms(X) symmetric-difference atoms(base)

the metrics are (numbered as in the user's list):

  1 exactness   |atoms(A) sym-diff atoms(R)|; 0 = functionally exact
  2 collateral  |changed(A) - changed(R)|: behaviour A changed that R
                leaves alone. Broken down by OWNER: an atom is owned by
                every rule whose reference ablation changes it, so a
                collateral atom owned by rule r' is damage to r'. Atoms
                no reference ablation touches are 'unowned'.
  3 shortfall   |changed(R) - changed(A)|: what A failed to remove
  9 kinds       every count is also split by atom kind, so a change to
                when the game ends or who wins is never hidden inside a
                legal-move count

1 = 2 + 3, always, since atoms(A) sym-diff atoms(R) is exactly
changed(A) sym-diff changed(R); the tests check it.

  7 scatter     for one ablation: how many action types and reference
                rules its changes touch, the largest share in one action
                type (intervention.py's concentration), and the entropy
                of the change over action types, normalised to [0, 1].

Breakage rate (4), fragility (5), rejections (6) and repair (8) are
aggregates over these, built in `lgref.bench.report`.
"""

import math


def atoms(beh):
    """The behaviour of a description as a frozenset of atoms."""
    if beh is None or not beh.loads:
        return None
    out = set()
    for (index, role), moves in beh.legal.items():
        for move in moves:
            out.add(('legal', index, role, move))
    for index, terminal in beh.terminal.items():
        if terminal:
            out.add(('terminal', index))
    for (index, role), values in beh.goal.items():
        for value in values:
            out.add(('goal', index, role, value))
    for (index, joint), successor in beh.next.items():
        out.add(('next', index, joint, successor))
    return frozenset(out)


def changed(x, base):
    return x ^ base


def kind_counts(atom_set):
    out = {'legal': 0, 'terminal': 0, 'goal': 0, 'next': 0}
    for atom in atom_set:
        out[atom[0]] += 1
    return out


def compare(a, r, base, owners=None, rule=None):
    """Metrics 1-3 (and 9) for ablation atoms `a` against reference
    atoms `r`. `owners` maps a rule id to changed(R) of that rule's
    reference ablation, for the owner breakdown of collateral; `rule` is
    the rule being ablated, never counted as its own victim."""
    ca, cr = changed(a, base), changed(r, base)
    collateral = ca - cr
    shortfall = cr - ca
    out = {'exactness': len(a ^ r),
           'collateral': len(collateral),
           'shortfall': len(shortfall),
           'exactness_by_kind': kind_counts(a ^ r),
           'collateral_by_kind': kind_counts(collateral),
           'shortfall_by_kind': kind_counts(shortfall)}
    if owners is not None:
        damaged = {}
        unowned = 0
        for atom in collateral:
            hit = [o for o, atoms_o in owners.items()
                   if o != rule and atom in atoms_o]
            if not hit:
                unowned += 1
            for o in hit:
                damaged[o] = damaged.get(o, 0) + 1
        out['rules_broken'] = sorted(damaged)
        out['damage_by_rule'] = damaged
        out['collateral_unowned'] = unowned
    return out


def _move_name(move):
    return move[0] if isinstance(move, tuple) and move else str(move)


def action_type(atom):
    """The action an atom is about: the move's name for a legal atom,
    the name of the joint move's one non-noop move for a successor atom,
    'terminal' or 'goal' otherwise."""
    if atom[0] == 'legal':
        return _move_name(atom[3])
    if atom[0] == 'next':
        names = sorted({_move_name(m) for m in atom[2]} - {'noop'})
        return names[0] if len(names) == 1 else 'joint:' + '+'.join(names)
    return atom[0]


def scatter(change_set, owners=None):
    """Metric 7 for one ablation's changed atoms."""
    if not change_set:
        return {'n_action_types': 0, 'n_rules': 0, 'concentration': None,
                'entropy': None}
    by_type = {}
    for atom in change_set:
        t = action_type(atom)
        by_type[t] = by_type.get(t, 0) + 1
    total = float(len(change_set))
    shares = [n / total for n in by_type.values()]
    if len(shares) > 1:
        entropy = -sum(p * math.log(p) for p in shares) / math.log(
            len(shares))
    else:
        entropy = 0.0
    rules = set()
    if owners:
        for atom in change_set:
            rules |= {o for o, atoms_o in owners.items() if atom in atoms_o}
    return {'n_action_types': len(by_type), 'n_rules': len(rules),
            'concentration': max(shares), 'entropy': entropy}
