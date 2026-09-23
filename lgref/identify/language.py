"""Tell the language a game is written in from the rules written in it.

Issue #202. Several candidate rules were the coordinate arithmetic that
rules are EXPRESSED in rather than gameplay provisions -- `file_delta_1`,
`between_rank`, `rank_delta_2`. The intervention probe cannot separate
them, because removing the language a rule is written in removes moves
exactly as removing the rule would: delete `knight_step` and knights
stop moving, and the probe sees a focused, playable, behaviour-changing
ablation either way.

THE CRITERION

    A cluster is LANGUAGE if no clause in it depends, at any depth, on
    game state -- any fluent or any action.

Coordinate arithmetic depends on nothing: `file_delta_1(a,b)` is true of
the board's names whatever is standing on it. A provision is about the
game, so something in it reads or writes state.

WHY THIS WORKS WHERE THE CLAUSE-LEVEL TEST DID NOT

Applied to single clauses, "touches no fluent" captured 275 of 488 and
swept in genuine rule content. Two changes fix it:

  CLUSTER LEVEL. A static helper serving one rule is clustered WITH that
  rule by predicate edges, so it inherits the rule's state dependence.
  Only self-contained arithmetic comes out static.

  TRANSITIVE. `empty` reads no fluent itself -- it depends on `occupied`,
  which reads `cell`. Testing direct reads left it static.

It also needs the calibrated resolution (#189): at the transferred
resolution clusters were large and mixed, so nearly every one touched
state and nothing separated.

WHAT IT DOES NOT DO

A small game-specific constant table -- Royal Chess's `boulder_first_dest`
naming the four squares the boulder may open to -- reads as language,
because it IS a geometric table. What makes it rule content is the clause
that consults it under a state condition, and that clause is correctly
marked stateful. Ablating the consuming cluster is the right experiment;
ablating the table is not. Measured precision on Royal Chess is 0.81.
"""

import collections

#: A cluster reached a predicate the description never defines, so
#: whether it depends on state cannot be decided from the text. Royal
#: Chess has four such predicates -- the unfinished tiny-endgame
#: arithmetic and `next_state_hash` -- and a cluster resting on one is
#: incomplete rather than static.
UNDETERMINED = 'undetermined'
LANGUAGE = 'language'
RULE = 'rule_content'


def state_dependent_predicates(nodes):
    """Predicates that depend on game state, at any depth.

    Seeded with the clauses that read or write a fluent or inspect an
    action, then closed over the call graph to a fixpoint.
    """
    defines = collections.defaultdict(list)
    for node in nodes:
        if node.head_predicate:
            defines[node.head_predicate].append(node)

    stateful = {node.head_predicate for node in nodes
                if node.head_predicate
                and (node.fluents_read or node.fluents_written
                     or node.actions_read)}

    changed = True
    while changed:
        changed = False
        for predicate, clauses in defines.items():
            if predicate in stateful:
                continue
            if any(called in stateful
                   for clause in clauses
                   for called in clause.body_predicates):
                stateful.add(predicate)
                changed = True
    return stateful


def undefined_predicates(nodes):
    """Consulted but never defined -- see UNDETERMINED."""
    defined, consulted = set(), set()
    for node in nodes:
        if node.head_predicate:
            defined.add(node.head_predicate)
        consulted |= set(node.body_predicates)
    return consulted - defined


def classify(rule, stateful, undefined):
    """LANGUAGE, RULE or UNDETERMINED for one candidate cluster.

    Only the cluster's OWN clauses are consulted. Shared members serve
    several rules by definition, so letting a borrowed helper decide
    would make the verdict depend on which rule happened to borrow it.
    """
    own = [n for n in rule.nodes() if n.node_id in rule.clause_ids]
    for node in own:
        if node.fluents_read or node.fluents_written or node.actions_read:
            return RULE
        if node.head_predicate in stateful:
            return RULE
        # The head check is sufficient: `state_dependent_predicates`
        # has already closed over the call graph, so a clause whose
        # body reaches state has a head in `stateful` too. Testing the
        # body again was dead code -- mutating it away changed no test,
        # which is how it was found.
    for node in own:
        if any(called in undefined for called in node.body_predicates):
            return UNDETERMINED
    return LANGUAGE


def classify_all(nodes, rules):
    """{rule_id: verdict} for every candidate."""
    stateful = state_dependent_predicates(nodes)
    undefined = undefined_predicates(nodes)
    return {rule.rule_id: classify(rule, stateful, undefined)
            for rule in rules}
