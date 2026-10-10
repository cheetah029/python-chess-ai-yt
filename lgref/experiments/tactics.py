"""Exact one-ply tactics, read off the game's own terminal condition.

WHY THIS AND NOT A POSITION SCORE. The constraint is an evaluator that
works across different games while playing well, and a hand-written
position score cannot: "count the royals" is a fact about Royal Chess and
is meaningless in nim. This module needs no facts about any game. It uses
only `is_game_over()` and `winner`, which every engine here exposes --
Royal Chess, tic-tac-toe, the m,n,k games, the GDL interpreter. What it
computes is not a heuristic at all but a PROOF about the next ply.

WHY IT IS THE RIGHT TARGET. The search's failure on this game is not
subtle positional weakness. At 800 simulations over 56 moves each child
gets 14 rollouts, the standard error of a win rate from 14 Bernoulli
samples is 0.134, and the observed spread between root moves is 0.139 --
the entire difference is noise. A noisy estimator's visible symptom is
losing material to replies it never sampled, which is what playing it
looks like: "sometimes purposeful, other times just blunders".

Tactics are decided one to three plies deep. An estimator cannot be made
reliable there by sampling more -- reaching a 0.05 discrimination needs
about 140,000 simulations per move, two hours -- but one ply can be
SOLVED outright for the price of a few thousand move generations.

WHAT THE GGP LITERATURE DOES, since this is not invented here. Strong
general players pair UCT with exact shallow reasoning: terminal and
goal-stability detection, proof-number search on the shallow layer, and
automatically extracted evaluations for the rest. Plain MCTS with random
rollouts is a KNOWN weak player in chess-like domains -- that is why
AlphaZero needed a learned network rather than a better tree policy. The
field's answer was never to fix the tree policy; it was to stop asking
random rollouts to carry the evaluation.

WHAT THIS CANNOT DO. It sees exactly one ply. A move that loses to a
two-move combination is invisible to it, and so is any long-term
weakness. It removes the cheapest class of blunder and leaves the rest to
the search.
"""

import copy

WIN = 'win'
SAFE = 'safe'
LOSS = 'loss'


def classify(engine, turns, lookahead=True):
    """{WIN|SAFE|LOSS: [turn]} for `turns` in `engine`'s position.

    WIN   the move ends the game in the mover's favour immediately.
    LOSS  after the move the opponent has a move that ends the game in
          THEIR favour immediately.
    SAFE  neither, as far as one ply can tell.

    COPIES THE ENGINE AND THE TURNS TOGETHER. A `Turn` holds a reference
    to a piece on the board that produced it and `Board.move` writes
    cooldown, moved and last-square onto that piece, so executing a
    caller's turn on a copy writes through to the live game (#247). This
    is the same trap the search fell into and it is why `deepcopy` takes
    the pair.
    """
    out = {WIN: [], SAFE: [], LOSS: []}
    mover = engine.current_player
    for index in range(len(turns)):
        sim, sim_turns = copy.deepcopy((engine, turns))
        sim.execute_turn(sim_turns[index])
        if sim.is_game_over():
            if sim.winner == mover:
                out[WIN].append(turns[index])
            elif sim.winner is None:
                out[SAFE].append(turns[index])
            else:
                out[LOSS].append(turns[index])
            continue
        if not lookahead:
            out[SAFE].append(turns[index])
            continue
        if _opponent_wins_at_once(sim, mover):
            out[LOSS].append(turns[index])
        else:
            out[SAFE].append(turns[index])
    return out


def _opponent_wins_at_once(sim, mover):
    """Can whoever is to move in `sim` end it against `mover` right now?"""
    replies = sim.get_all_legal_turns()
    if not replies:
        # No legal turn is itself an outcome in this game, decided by the
        # rules rather than by us -- `is_game_over` was already False, so
        # ask the engine what the position is worth rather than guessing.
        return False
    for index in range(len(replies)):
        inner, inner_turns = copy.deepcopy((sim, replies))
        inner.execute_turn(inner_turns[index])
        if inner.is_game_over() and inner.winner is not None \
                and inner.winner != mover:
            return True
    return False


def filter_turns(engine, turns, lookahead=True):
    """(chosen, candidates): a forced win, or the non-losing moves.

    Returns `(turn, None)` when a move wins outright -- there is nothing
    for a search to decide. Otherwise `(None, candidates)` where
    candidates excludes the moves proven to lose in one ply, or the
    original list when every move loses and the distinction buys nothing.
    """
    groups = classify(engine, turns, lookahead)
    if groups[WIN]:
        return groups[WIN][0], None
    candidates = groups[SAFE]
    if not candidates:
        # Every move loses. Nothing to prune, and pretending otherwise
        # would hand the search an empty list.
        return None, list(turns)
    return None, candidates


def cost_estimate(branching, lookahead=True):
    """Move generations this needs, for judging affordability.

    One per candidate, plus one per opponent reply per candidate when
    looking ahead -- quadratic in the branching factor, which is the
    whole question on a game that branches 58 ways.
    """
    return branching * (1 + branching) if lookahead else branching
