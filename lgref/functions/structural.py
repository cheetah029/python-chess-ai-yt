"""Structural inference: predict strategic functions from rule shape.

Channel 9.1 of the specification -- what the rules themselves suggest,
before the game is played. Modifying legal destinations suggests a
mobility function; reading history counters suggests a history function;
writing terminal conditions suggests a termination function; creating
temporary immunity suggests a survival function.

These are PREDICTIONS. The behavioural and causal channels confirm or
falsify them, and a prediction that cannot fail is not one, so a
function with no operational definition is predicted but flagged as
unfalsifiable rather than counted as a hit.
"""

import collections

from lgref.functions.strategic_ontology import BY_NAME, NOT_YET_OPERATIONAL

Prediction = collections.namedtuple(
    'Prediction', 'function confidence basis falsifiable')

MIN_CONFIDENCE = 0.15


def _ctx(nodes):
    counts = collections.Counter()
    control = collections.Counter()
    legal = [n for n in nodes if n.head_kind == 'legal']
    for node in nodes:
        counts.update(node.fluents_written)
        if node.head_kind == 'legal':
            control.update(node.fluents_read)
    terminal = set()
    for node in nodes:
        if node.head_kind in ('terminal', 'goal') or node.terminal_dependency:
            terminal |= set(node.fluents_read)
    guards = collections.Counter()
    for node in legal:
        guards.update(node.fluents_read)
        guards.update(node.body_predicates)
    # Fluents read NEGATIVELY as guards inside legal clauses: whatever
    # a description calls "you may not act while this holds".
    negated_guards = collections.Counter()
    for node in legal:
        negated_guards.update(node.negated_goals)

    # Predicates that gate legality and themselves depend on state --
    # blocking that is conditional on the position rather than fixed.
    stateful_guards = set()
    defined = collections.defaultdict(list)
    for node in nodes:
        if node.head_predicate:
            defined[node.head_predicate].append(node)
    for node in legal:
        for name in node.negated_goals:
            for clause in defined.get(name, ()):
                if clause.fluents_read:
                    stateful_guards.add(name)

    # Fluents written in response to an action and later consulted --
    # the shape of a rule that responds to what someone just did.
    action_written = set()
    for node in nodes:
        if node.head_kind == 'fluent_write' and node.actions_read:
            action_written |= set(node.fluents_written)

    # Counters: a fluent whose own transitions step between its values,
    # and which is compared against a constant somewhere. That is how a
    # description says "only so many times".
    counters = set()
    for node in nodes:
        if node.head_kind == 'fluent_write':
            written = node.head_predicate
            if written and written in node.fluents_read:
                counters.add(written)

    # Loss conditions that fire when a FILTERED legal set is empty.
    empties_into_loss = set()
    for node in nodes:
        if node.head_predicate in ('lost', 'terminal', 'goal'):
            empties_into_loss |= set(node.body_predicates)

    # Which loss-feeding predicates reach the board AT ANY DEPTH. The
    # first version tested a direct read and found none: `dead` and
    # `royal_queen_dead` consult the board through helpers, so a
    # one-step test saw nothing.
    reaches_board = set()
    frontier = list(empties_into_loss)
    seen_pred = set()
    while frontier:
        name = frontier.pop()
        if name in seen_pred:
            continue
        seen_pred.add(name)
        for clause in defined.get(name, ()):
            if counts and clause.fluents_read & {counts.most_common(1)[0][0]}:
                reaches_board.add(name)
            frontier += [b for b in clause.body_predicates
                         if b not in seen_pred]
    # Propagate back: a predicate whose helper reaches the board does too.
    for _ in range(4):
        for name in list(empties_into_loss):
            for clause in defined.get(name, ()):
                if set(clause.body_predicates) & reaches_board:
                    reaches_board.add(name)

    # Role constants, so "owned by a player" can be told from "owned by
    # nobody" without knowing what the players are called.
    roles = set()
    for node in nodes:
        if node.head_predicate == 'role' and isinstance(node.raw, tuple):
            roles |= {a for a in node.raw[1:] if isinstance(a, str)}

    return {
        'roles': roles,
        'negated_guards': negated_guards,
        'stateful_guards': stateful_guards,
        'action_written': action_written,
        'counters': counters,
        'empties_into_loss': empties_into_loss,
        'loss_reaches_board': reaches_board,
        'guard_norms': _guard_norms(nodes),
        'defined': defined,
        'dominant': counts.most_common(1)[0][0] if counts else None,
        'control': (control.most_common(1)[0][0]
                    if control and control.most_common(1)[0][1]
                    >= 0.8 * max(len(legal), 1) else None),
        'terminal': terminal,
        'guards': guards,
        'n_legal': len(legal),
    }


def _guard_norms(nodes, threshold=0.6):
    """Guards that MOST clauses of an action type carry.

    A clause lacking one its siblings share is permitting something
    they forbid. This finds the norm per action type so the exception
    can be spotted, without knowing what any guard means.
    """
    import collections as _c
    by_action = _c.defaultdict(list)
    for node in nodes:
        if node.head_kind == 'legal' and node.action_type:
            by_action[node.action_type].append(node)
    norms = {}
    for action, clauses in by_action.items():
        if len(clauses) < 3:
            continue
        counts = _c.Counter()
        for clause in clauses:
            counts.update(set(clause.negated_goals))
        norms[action] = {name for name, n in counts.items()
                         if n >= threshold * len(clauses)}
    return norms


def _acts_on_unowned(node, roles, dominant):
    """Does this legal clause read the board with a non-role owner?

    The owner slot holding a constant that is not a role is how a
    description says "this belongs to nobody". Found by comparing
    against the declared roles rather than by looking for a name.
    """
    def walk(term):
        if not isinstance(term, tuple):
            return False
        if term and term[0] == 'true' and len(term) > 1:
            inner = term[1]
            if isinstance(inner, tuple) and inner and inner[0] == dominant:
                constants = [a for a in inner[1:]
                             if isinstance(a, str) and not a.startswith('?')]
                if constants and not (set(constants) & roles):
                    return True
        return any(walk(part) for part in term)

    return walk(node.raw)


def predict(own, ctx):
    """Candidate strategic functions for one rule's own clauses."""
    total = max(len(own), 1)
    hits = collections.Counter()
    basis = {}

    def note(function, n, why):
        if n:
            hits[function] += n
            basis.setdefault(function, why)

    for node in own:
        kind = node.head_kind
        writes, reads = set(node.fluents_written), set(node.fluents_read)

        if kind in ('terminal', 'goal') or node.terminal_dependency:
            note('termination_guarantee', 1, 'feeds the ending condition')
            note('termination_acceleration', 1, 'feeds the ending condition')
        if writes & ctx['terminal']:
            note('delayed_victory', 1, 'writes state the ending reads')

        if kind == 'legal':
            note('mobility_expansion', 1, 'grants a legal action')
            if node.action_type and ctx['dominant'] and \
                    ctx['dominant'] not in writes:
                note('piece_transformation', 1,
                     'an action whose effect is not on the board fluent')
        if node.negated_goals:
            note('mobility_restriction', 1, 'guards a legal clause')
            note('forced_choice_creation', 1, 'removes otherwise legal moves')

        if writes & set(ctx['guards']):
            note('space_control', 1, 'its state gates where actions may go')

        if kind == 'fluent_write' and (writes & reads):
            note('state_persistence', 1, 'carries state across turns')
            note('historical_dependency', 1, 'legality depends on the past')
            note('cooldown_regulation', 1,
                 'state that must lapse before reuse')
        if kind == 'fluent_write' and node.actions_read:
            note('capture_enablement', 1, 'an effect conditioned on an action')
            note('retaliation', 1, 'responds to the opponent\'s action')

        if ctx['control'] and ctx['control'] in writes:
            note('outcome_balancing', 1, 'governs turn order')

        # PROTECTION: a fluent written from an action and read NEGATED
        # as a guard in legal clauses forbids acting on whatever it
        # marks -- that is protection, and because it is set per action
        # rather than held indefinitely, temporary protection.
        protective = writes & set(ctx['negated_guards'])
        if protective and node.actions_read:
            note('temporary_protection', 1,
                 'sets state that blocks actions against what it marks')
            note('survivability', 1,
                 'sets state that blocks actions against what it marks')

        # RESPONSE: a fluent written from someone's action and consulted
        # as a precondition for acting is how a description encodes
        # "you may do this BECAUSE they just did that".
        if node.head_kind == 'fluent_write' and node.actions_read and \
                (writes & set(ctx['guards'])):
            note('retaliation', 1, 'armed by an action, then permits one')
            note('pinning_immobilization', 1,
                 'the opponent acting is what enables the response')

        # OBSTRUCTION: a predicate that gates movement AND depends on
        # the position -- blocking that moves with the game rather than
        # fixed geometry.
        if node.head_predicate in ctx['stateful_guards']:
            note('path_obstruction', 1,
                 'position-dependent blocking of movement')
            note('area_denial', 1,
                 'position-dependent blocking of movement')
            note('space_control', 1,
                 'position-dependent blocking of movement')

        # COUNTER-GATED LEGALITY: a rule that removes options based on
        # how many times something has already happened. Both readings
        # are emitted -- repetition of a STATE, or lack of progress --
        # because structure alone cannot separate them and the ablation
        # can.
        consulted_counters = (reads | set(node.body_predicates)) & \
            ctx['counters']
        if consulted_counters and (node.negated_goals or
                                   node.head_kind == 'legal'):
            note('cycle_prevention', 1,
                 'legality gated on a count of prior occurrences')
            note('anti_drift_control', 1,
                 'legality gated on a count of prior occurrences')
            note('historical_dependency', 1,
                 'legality gated on a count of prior occurrences')

        # RUNNING OUT AS A LOSS: a loss condition that fires when the
        # filtered legal set is empty converts a would-be stalemate into
        # a decided result.
        if node.head_predicate in ctx['empties_into_loss'] and \
                node.negated_goals:
            note('draw_suppression', 1,
                 'having no filtered legal move is a LOSS, not a draw')
            note('termination_acceleration', 1,
                 'having no filtered legal move is a LOSS, not a draw')
            note('termination_guarantee', 1,
                 'having no filtered legal move is a LOSS, not a draw')

        # UNCONSTRAINED DESTINATION: a movement rule whose body relates
        # the origin to the destination through no step or path
        # predicate reaches anywhere at all.
        if kind == 'legal' and node.action_type:
            geometric = [b for b in node.body_predicates
                         if b in ctx['defined']
                         and not ctx['defined'][b][0].fluents_read]
            if not geometric:
                note('repositioning', 1,
                     'a move with no geometric path constraint')
                note('escape_facilitation', 1,
                     'a move with no geometric path constraint')
                note('penetration', 1,
                     'a move with no geometric path constraint')

        # NEUTRAL SUBJECT: a legal action on an entity whose owner slot
        # holds a constant that is not a role -- something belonging to
        # nobody that either player may act on.
        if kind == 'legal' and ctx['roles'] and ctx['dominant']:
            if _acts_on_unowned(node, ctx['roles'], ctx['dominant']):
                note('shared_object_influence', 1,
                     'acts on an entity owned by no role')
                note('space_control', 1,
                     'acts on an entity owned by no role')

        # ATTACK vs SACRIFICE: a legal action requiring an OPPOSING
        # occupant at the target projects threat; one requiring a
        # FRIENDLY occupant removes one's own material on purpose.
        if kind == 'legal':
            body = set(node.body_predicates)
            if any('enemy' in b or 'opponent' in b for b in body):
                note('threat_projection', 1,
                     'requires an opposing occupant at the target')
                note('capture_enablement', 1,
                     'requires an opposing occupant at the target')
            if any('friend' in b for b in body) and not node.negated_goals \
                    & {b for b in body if 'friend' in b}:
                note('sacrificial_clearance', 1,
                     'may act on one\'s own occupant')

        # ROYAL PRESERVATION: a predicate feeding the ending that names
        # a specific occupant type rather than the board at large.
        if node.head_predicate in ctx['loss_reaches_board']:
            note('royal_preservation', 1,
                 'the ending depends on specific occupants surviving')
            note('objective_salience', 1,
                 'the ending depends on specific occupants surviving')

        # PERMISSION BY OMISSION. Every use of the self-exclusion guard
        # in this description is negated, so no clause REQUIRES a
        # friendly target -- the rule that lets a piece take its own is
        # written as the ABSENCE of the guard its siblings carry. A
        # detector matching on what a clause contains cannot see that.
        if kind == 'legal' and node.action_type:
            missing = ctx['guard_norms'].get(node.action_type, set()) - \
                set(node.negated_goals)
            if missing:
                note('sacrificial_clearance', 1,
                     'omits a guard its sibling actions carry: {}'.format(
                         ', '.join(sorted(missing))))

    out = []
    for function, n in hits.items():
        confidence = round(n / total, 3)
        if confidence < MIN_CONFIDENCE:
            continue
        out.append(Prediction(
            function, confidence, basis[function],
            function not in NOT_YET_OPERATIONAL))
    return sorted(out, key=lambda p: -p.confidence)


def predict_all(nodes, rules, skip=None):
    """Predictions per rule, with language clusters skipped by default.

    Skipping is the DEFAULT rather than the caller's responsibility.
    Asking what strategic job `file_delta_1` performs is the error this
    phase was held up over, and a safe behaviour that depends on every
    caller remembering an argument is not safe.
    """
    if skip is None:
        from lgref.identify.language import LANGUAGE, classify_all
        kinds = classify_all(nodes, rules)
        skip = {r.rule_id for r in rules if kinds[r.rule_id] == LANGUAGE}
    ctx = _ctx(nodes)
    out = collections.OrderedDict()
    for rule in rules:
        if rule.rule_id in skip:
            continue
        own = [n for n in rule.nodes() if n.node_id in rule.clause_ids]
        out[rule.rule_id] = predict(own, ctx)
    return out


def coverage(predictions):
    """Which ontology functions were predicted at all, and which never."""
    seen = {p.function for ps in predictions.values() for p in ps}
    return seen, sorted(set(BY_NAME) - seen)


def explain_gaps(predictions):
    """WHY each unpredicted function is unpredicted.

    An undifferentiated "never predicted" list reads as the detectors
    being poor, which for some of these is right and for others is a
    category error. Three reasons, and they call for different things:

      behavioural   the function's own evidence is a MEASURED quantity,
                    so structure was never the channel that could find
                    it. Phase 3 supplies it.
      undefined     no operational definition yet, so it cannot be
                    confirmed or falsified by any channel.
      detector_gap  structurally findable and not yet found. This is
                    the only group that is a shortcoming here.
    """
    _, never = coverage(predictions)
    out = collections.OrderedDict(
        (('behavioural', []), ('undefined', []), ('detector_gap', [])))
    for name in never:
        spec = BY_NAME[name]
        if name in NOT_YET_OPERATIONAL:
            out['undefined'].append(name)
        elif spec.metrics:
            out['behavioural'].append(name)
        else:
            out['detector_gap'].append(name)
    return out
