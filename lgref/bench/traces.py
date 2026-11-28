"""Legal-move agreement along played-out traces (#402): logic-based and
representation-invariant.

The atom metrics compare two descriptions at the FIXED states of S. That
misses what an ablation does to where the game goes next, and the
successor atoms that would catch it compare STATES -- sets of fluents --
which depend on how a description encodes its state: an ablation that
deletes an unused turn counter changes every successor state without
changing the game. So the dynamics are measured by playing out instead.

Both descriptions start from their own initial state. At each step:

  - every role's legal moves are compared: moves in one and not the
    other are counted (LEGAL-MOVE DIFFERENCES, the primary count);
  - whether each says the state is terminal is compared, and, at a
    state both call terminal, each role's payoff;
  - a joint move legal in BOTH is chosen by a seeded generator and
    played in both.

A trace stops when both are terminal, when they disagree on
termination, when no common joint move exists, or after `max_plies`.
States are never compared, so how either description represents its
state cannot matter; only MOVES are compared, and a move is a term in
the game's action vocabulary, which every intervention and reference
variant of one game shares. (Comparing descriptions with DIFFERENT
action vocabularies needs a move mapping, which `move_map` supplies,
as the scramble rewrite requires.)
"""

import random

from lgref.bench import wellformed


def _legal(game, roles):
    return {r: frozenset(game.legal_moves(r)) for r in roles}


def play_out(text_a, text_b, games=20, max_plies=60, seed=0,
             move_map=None, role_map=None):
    """Counts over `games` seeded traces of A against B.

    `move_map` / `role_map` translate B's moves and roles into A's
    vocabulary (identity when None). Returns a dict:

      legal_differences   moves legal in one description and not the
                          other, summed over every step of every trace
      terminal_differences  steps where exactly one says terminal
      goal_differences    terminal steps where some role's payoff differs
      diverged            traces that stopped because no joint move was
                          legal in both
      steps               steps compared
    """
    move_map = move_map or (lambda m: m)
    role_map = role_map or (lambda r: r)
    a = wellformed.open_game(text_a)
    b = wellformed.open_game(text_b)
    roles = list(a.roles)
    b_role = {r: next(x for x in b.roles if role_map(x) == r)
              for r in roles}
    out = {'legal_differences': 0, 'terminal_differences': 0,
           'goal_differences': 0, 'diverged': 0, 'steps': 0,
           'traces': games}
    start_a, start_b = frozenset(a.state), frozenset(b.state)
    for index in range(games):
        rng = random.Random(seed * 100003 + index)  # nosec B311: play
        wellformed.at(a, start_a)
        wellformed.at(b, start_b)
        for _ply in range(max_plies):
            out['steps'] += 1
            term_a, term_b = a.is_terminal(), b.is_terminal()
            if term_a != term_b:
                out['terminal_differences'] += 1
                break
            if term_a:
                for r in roles:
                    if wellformed.goal_values(a, r) != \
                            wellformed.goal_values(b, b_role[r]):
                        out['goal_differences'] += 1
                        break
                break
            legal_a = _legal(a, roles)
            legal_b = {r: frozenset(move_map(m)
                                    for m in b.legal_moves(b_role[r]))
                       for r in roles}
            for r in roles:
                out['legal_differences'] += len(legal_a[r] ^ legal_b[r])
            common = [sorted(legal_a[r] & legal_b[r], key=repr)
                      for r in roles]
            if any(not c for c in common):
                out['diverged'] += 1
                break
            joint = [rng.choice(c) for c in common]
            # B plays the move it writes for the move A plays.
            in_b = {}
            for r, m in zip(roles, joint):
                in_b[b_role[r]] = next(m_b for m_b in b.legal_moves(
                    b_role[r]) if move_map(m_b) == m)
            a.step(dict(zip(roles, joint)))
            b.step(in_b)
    return out


def exact(result):
    """True when the traces show no difference of any kind."""
    return not (result['legal_differences']
                or result['terminal_differences']
                or result['goal_differences'])
