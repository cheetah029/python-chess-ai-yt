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


# ---- proof co-use (#321) ----------------------------------------------------
#
# WHY A SECOND SIGNAL. "Satisfiable in the same state" cannot see the
# failure the validation protocol found: statements two rules share are
# almost never kept in both (0 of 21 on breakthrough). A board helper is
# satisfiable nearly everywhere, so it associates with everything or
# nothing. What separates a helper SHARED by two rules from one that
# merely could be is whether it is USED: whether it appears in the
# derivation of moves granted by both. So this signal records, for every
# outcome actually derived in play -- each legal move, each successor
# fact, the ending and the payoff -- the statements its proof used.

_USED = '__lgref_used__'
_PROOF = '__lgref_proof__'


def _traced(resolver):
    """`resolver`, made to record which statements each proof uses.

    Every statement's body gains a final marker goal; solving the marker
    pushes the statement's index onto a chain carried IN the
    substitution, so the record follows backtracking exactly -- a
    statement tried and abandoned leaves no mark. Proofs under negation
    are discarded with the negation, as they should be: a statement that
    failed was consulted, not used. The class is extended per instance
    so a GDL-III resolver keeps answering `knows`.
    """
    base = type(resolver)

    def _query(self, goal, subst=None, depth=0, in_progress=None):
        if isinstance(goal, tuple) and goal and goal[0] == _USED:
            out = dict(subst or {})
            out[_PROOF] = (goal[1], out.get(_PROOF))
            yield out
            return
        yield from base._query(self, goal, subst, depth, in_progress)

    resolver.__class__ = type('Traced' + base.__name__, (base,),
                              {'_query': _query})
    return resolver


def _proof_ids(subst):
    out, link = set(), subst.get(_PROOF)
    while link is not None:
        out.add(link[0])
        link = link[1]
    return out


def _traced_kb(game, forms, extra_facts=()):
    """The game's current-state KB, every statement marked with its
    index. Facts become rules with only the marker, so a fact used in a
    proof is recorded like any other statement; `init` facts are left
    out, as the game leaves them out."""
    from ggp.kb import KnowledgeBase, canonical

    kb = KnowledgeBase()
    for index, form in enumerate(forms):
        if isinstance(form, tuple) and form and form[0] == '<=':
            head = canonical(form[1])
            body = [canonical(g) for g in form[2:]]
        else:
            head, body = canonical(form), []
            if isinstance(head, tuple) and head and head[0] == 'init':
                continue
        kb._add_rule(head, body + [(_USED, index)])
    for fact in game.state:
        kb._add_fact(('true', fact))
    for fact in extra_facts:
        kb._add_fact(fact)
    return kb


def _proofs(resolver, goal, cap):
    """Distinct statement sets used by the proofs of `goal`, at most
    `cap` proofs read (a recursive helper can have very many)."""
    seen = set()
    for n, subst in enumerate(resolver._query(goal, {}, 0, set())):
        if n >= cap:
            break
        ids = frozenset(_proof_ids(subst))
        if ids:
            seen.add(ids)
    return seen


def collect_proof_traces(gdl_path, nodes, n_games=20, max_plies=40,
                         seed=0, proofs_per_goal=200):
    """Play random games; for every outcome derived, record the
    statements its proof used.

    Returns a list of sets of node ids, one per distinct proof, ready for
    `ClauseGraph.add_co_use`. Uses the GDL interpreter, not a native
    engine, so it works for any game.
    """
    from ggp.game import GGPGame

    with open(gdl_path) as handle:
        forms = list(GGPGame._parse_any_dialect(handle.read()))
    if len(forms) != len(nodes):
        raise ValueError('statements and parsed forms do not line up')
    ids = [n.node_id for n in nodes]
    rng = random.Random(seed)
    proofs = []

    def record(game, goal, extra=()):
        resolver = _traced(game._resolver(_traced_kb(game, forms, extra)))
        for used in _proofs(resolver, goal, proofs_per_goal):
            proofs.append({ids[i] for i in used})

    for _ in range(n_games):
        game = GGPGame.from_file(gdl_path)
        for _ply in range(max_plies):
            if game.is_terminal():
                record(game, ('terminal',))
                for role in game.roles:
                    record(game, ('goal', role, '?value'))
                break
            moves = {}
            for role in game.roles:
                record(game, ('legal', role, '?move'))
                legal = game.legal_moves(role)
                if not legal:
                    moves = None
                    break
                moves[role] = rng.choice(legal)
            if moves is None:
                break
            record(game, ('next', '?fact'),
                   [('does', role, move) for role, move in moves.items()])
            game.step(moves)
    return proofs
