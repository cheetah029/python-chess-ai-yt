"""Observe which clauses fire together in real games.

Phase 1's dynamic signal (issue #187). Static structure cannot tell a
helper GENUINELY shared between two rules from one that merely could be:
both look the same in a dependency graph. Only watching games can
separate them.

WHAT "FIRES" MEANS

A clause fires in a state when its body is satisfiable there — the
conditions it states are met, so it contributes to what the game allows
or does next. This is checked by querying the body as a conjunction
against the live state, which needs no instrumentation of the resolver
and stays correct if the resolver changes.

A fact (a clause with no body) is trivially satisfiable in every state
and is therefore excluded. Counting it would link every clause to every
other through the constants they share, which is the same hub failure
that ubiquitous fluents caused in the static graph.

WHY CO-ACTIVATION IS WEIGHTED BELOW LEGALITY

Firing together is evidence, not proof: two clauses can fire in the same
position by coincidence of the board rather than by belonging to one
rule. The weight in cluster.DEFAULT_WEIGHTS reflects that — it is
observed rather than assumed, but noisy.

COST

One body query per clause per sampled state. Cheap on small games;
measured before use on anything larger, because the resolver is the slow
part of this project and an unbounded sweep here would be a poor trade
for a signal that is already weighted below the static ones.
"""

import random


def _rule_bodies(nodes):
    """(node_id, body goals) for clauses that have a body.

    Facts are skipped: satisfiable everywhere, so they carry no
    information about which clauses belong together.
    """
    out = []
    for node in nodes:
        raw = node.raw
        if not (isinstance(raw, tuple) and raw and raw[0] == '<='):
            continue
        body = list(raw[2:])
        if not body:
            continue
        out.append((node.node_id, body))
    return out


def active_clauses(resolver, bodies, limit_per_clause=1):
    """Node ids whose body is satisfiable in the resolver's current state.

    `limit_per_clause` stops at the first solution: whether a clause
    fires is a yes/no question, and enumerating every binding would cost
    far more for no extra signal.
    """
    fired = set()
    for node_id, body in bodies:
        try:
            found = 0
            for _ in resolver._query_conjunction(body, {}, 0, set()):
                found += 1
                if found >= limit_per_clause:
                    break
            if found:
                fired.add(node_id)
        except Exception:
            # A clause the resolver cannot evaluate (unsupported
            # construct, recursion cut) is treated as not firing rather
            # than aborting the trace. Silence here is safe: a missing
            # co-activation edge weakens a signal, it does not invent one.
            continue
    return fired


def collect_traces(gdl_path, nodes, n_games=3, max_plies=12, seed=0,
                   record_every=1):
    """Play random games and record which clauses fire at each state.

    Returns a list of sets of node ids — one per recorded state — ready
    for `ClauseGraph.add_co_activation`.

    Uses the GDL interpreter rather than a native engine so the tracer
    works for ANY game, which is the point: identification must not
    depend on a hand-written engine existing for the game under study.
    """
    from ggp.game import GGPGame

    bodies = _rule_bodies(nodes)
    rng = random.Random(seed)
    traces = []

    for game_index in range(n_games):
        game = GGPGame.from_file(gdl_path)
        for ply in range(max_plies):
            if game.is_terminal():
                break
            if ply % record_every == 0:
                traces.append(active_clauses(game._resolver_for_state(), bodies)
                              if hasattr(game, '_resolver_for_state')
                              else active_clauses(_resolver(game), bodies))
            moves = {}
            for role in game.roles:
                legal = game.legal_moves(role)
                if not legal:
                    moves = None
                    break
                moves[role] = rng.choice(legal)
            if moves is None:
                break
            game.step(moves)
    return traces


def _resolver(game):
    """A resolver bound to the game's current state."""
    from ggp.resolver import Resolver
    return Resolver(game._state_kb())
