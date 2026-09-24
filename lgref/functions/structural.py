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
import itertools

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

    dominant = counts.most_common(1)[0][0] if counts else None
    return {
        'roles': roles,
        'config': _configuration(nodes, dominant, roles, counters),
        'negated_guards': negated_guards,
        'stateful_guards': stateful_guards,
        'action_written': action_written,
        'counters': counters,
        'empties_into_loss': empties_into_loss,
        'loss_reaches_board': reaches_board,
        'guard_norms': _guard_norms(nodes),
        'defined': defined,
        'dominant': dominant,
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

        # ---- CONFIGURATION STRUCTURE ---------------------------
        # Everything below reads argument positions rather than
        # predicate names, so none of it knows what a queen is.
        cfg = ctx['config']
        action = _action_of(node)
        acting = action[0] if action else None
        written = _written_fluent(node)
        head = _head_body(node)[0]
        atoms = _body_atoms(node)

        if acting in cfg['reconfiguring']:
            note('tactical_reconfiguration', 1,
                 'sets a mode and never writes the board: the piece '
                 'stays where it is and its repertoire changes')
            if acting in cfg['reversible']:
                note('power_preservation', 1,
                     'the mode can be set back to its initial value, so '
                     'changing form spends nothing')

        touches_mode = False
        for fluent, spec in cfg['modes'].items():
            if not spec['persistent'] or len(spec['values']) < 3:
                continue
            if written is not None and written[0] == fluent:
                touches_mode = True
            for atom, args, _neg in atoms:
                if atom == fluent and any(_is_constant(a) for a in args):
                    touches_mode = True
        if touches_mode or acting in cfg['reconfiguring'] or \
                node.head_predicate in cfg['mode_menus']:
            note('strategic_diversity', 1,
                 'one of several modes that persist across turns, each '
                 'with its own repertoire')

        if acting in cfg['converting']:
            note('resource_conversion', 1,
                 'the subject is read as one type and written as another')

        if acting in cfg['redistributing']:
            note('threat_redistribution', 1,
                 'moves an entity whose owner it read from the board and '
                 'is not the actor: the position moves, the capacity does '
                 'not')

        # A MENU parameter: the action carries a slot filled from a list
        # of forms rather than from the board, so one move has several
        # different results and the player picks among them.
        if kind == 'legal' and action is not None:
            chosen = set()
            for atom, args, negated in atoms:
                if atom in cfg['mode_menus'] and not negated:
                    chosen |= {a for a in args if _is_variable(a)}
            if chosen & {a for a in action[1:] if _is_variable(a)}:
                note('tactical_flexibility', 1,
                     'the action carries a parameter chosen from a menu '
                     'of forms: one move, several different results')

        # AVAILABILITY GATED ON LOSS: a clause offering a particular
        # value only when the game's memory records that same value
        # having gone. What can be had is tied to what has been spent.
        head_constants = ({a for a in head[1:] if _is_constant(a)}
                          if isinstance(head, tuple) else set())
        if head_constants:
            for atom, args, negated in atoms:
                if atom != 'true' or negated or not args or \
                        not isinstance(args[0], tuple):
                    continue
                fluent = args[0]
                if fluent[0] in cfg['historical'] and head_constants & \
                        {a for a in fluent[1:] if _is_constant(a)}:
                    note('piece_type_balancing', 1,
                         'offers a type only while the record says that '
                         'same type has been lost')

        # THE REVERSAL BAN and the memory that serves it.
        if kind == 'legal' and action is not None:
            for atom, args, negated in atoms:
                if atom != 'true' or not negated or not args or \
                        not isinstance(args[0], tuple):
                    continue
                if (acting, args[0][0]) in cfg['reversal_guards']:
                    note('decision_compression', 1,
                         'refuses exactly the undoing of the last such '
                         'action, which is a move that changes nothing')
        if written is not None and \
                (acting, written[0]) in cfg['reversal_guards']:
            note('decision_compression', 1,
                 'records what the reversal guard later refuses')

        # DIRECTIONAL REACH: a clause calling a self-recursive relation
        # reaches along a line for as far as nothing interrupts it, so
        # what it threatens is concentrated in that direction.
        if set(node.body_predicates) & cfg['recursive']:
            note('threat_concentration', 1,
                 'reaches along a direction until something interrupts '
                 'it, concentrating what it covers on lines')

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

    Two reasons, and only one of them is an excuse the framework is
    entitled to:

      measured_null   the function is the null result of another one --
                      the same structure with the opposite measured
                      outcome. Structure cannot propose it, because
                      proposing it means proposing that a structural
                      prediction will fail.
      detector_gap    structurally findable and not yet found.

    THE TWO REASONS THIS USED TO GIVE ARE GONE (#215). It claimed that a
    function with no operational definition could not be found by any
    channel, and that a function whose evidence is a measured quantity
    was never structure's to find. Both are false. Every function's
    CONFIRMATION is measured; that has no bearing on whether its shape
    is visible in the rules. And ten unfalsifiable functions were being
    predicted while the report was explaining seven others away on the
    grounds of being unfalsifiable. Nine of the ten then turned out to
    be present in Royal Chess, seven of them in the queen's rules.
    """
    from lgref.functions.strategic_ontology import MEASURED_NULLS
    _, never = coverage(predictions)
    out = collections.OrderedDict((('measured_null', []),
                                   ('detector_gap', [])))
    for name in never:
        if name in MEASURED_NULLS:
            out['measured_null'].append(name)
        else:
            out['detector_gap'].append(name)
    return out


# ---------------------------------------------------------------------
# CONFIGURATION STRUCTURE (#215)
#
# The detectors above read a clause's surface: which fluents it touches,
# whether a guard is negated, what kind of head it has. That is enough
# for mobility, threat and termination, and it is not enough for the
# whole of categories E and H, which are about a game carrying a SECOND
# kind of state -- a mode a piece is in, a record of what has been
# spent, a parameter chosen at the moment of acting.
#
# Those need the clause's argument structure, not just its predicate
# names: WHICH slot holds a constant, whether two clauses agree on it,
# whether an effect writes back a value it read. Everything below works
# on argument positions and variable identity, so none of it knows what
# a queen is. A game whose units switch stances, a card game where a
# card changes suit, and a queen that becomes a rook are one shape.
# ---------------------------------------------------------------------


def _is_variable(term):
    return isinstance(term, str) and term.startswith('?')


def _is_constant(term):
    return isinstance(term, str) and not term.startswith('?')


def _head_body(node):
    """The clause's head term and its list of body goals."""
    if node.kind == 'rule' and isinstance(node.raw, tuple) and \
            len(node.raw) > 1:
        return node.raw[1], list(node.raw[2:])
    return node.raw, []


def _atoms(term, negated=False, out=None):
    """Every atom in a goal, with its arguments and negation.

    Descends into arguments as well as conjuncts, so `true(cell(...))`
    yields both the wrapper and the fluent itself -- the fluent's own
    argument list is what the detectors below need.
    """
    out = [] if out is None else out
    if not isinstance(term, tuple) or not term:
        return out
    name = term[0]
    if name == 'not':
        for sub in term[1:]:
            _atoms(sub, True, out)
        return out
    if name in ('and', 'or'):
        for sub in term[1:]:
            _atoms(sub, negated, out)
        return out
    if isinstance(name, str):
        out.append((name, tuple(term[1:]), negated))
    for sub in term[1:]:
        _atoms(sub, negated, out)
    return out


def _body_atoms(node):
    _head, body = _head_body(node)
    out = []
    for goal in body:
        _atoms(goal, False, out)
    return out


def _action_of(node):
    """The action this clause makes legal, or that it reacts to.

    A legal clause names it in the head; an effect clause names it in a
    `does` goal. Both are the same object here -- the thing whose
    argument slots other clauses refer to.
    """
    head, _ = _head_body(node)
    if node.head_kind == 'legal' and isinstance(head, tuple) and \
            len(head) > 2 and isinstance(head[2], tuple):
        return head[2]
    for name, args, _neg in _body_atoms(node):
        if name == 'does' and len(args) > 1 and isinstance(args[1], tuple):
            return args[1]
    return None


def _written_fluent(node):
    """The fluent term a `next` or `init` clause writes."""
    head, _ = _head_body(node)
    if node.head_kind in ('fluent_write', 'fluent_init') and \
            isinstance(head, tuple) and len(head) > 1 and \
            isinstance(head[1], tuple):
        return head[1]
    return None


def _slots(args, action):
    """Positions in the action's arguments that these arguments occupy.

    None unless every argument is a variable carried from the action,
    which is what separates "stores where the move came from" from
    "stores something else entirely".

    ALL positions per argument, not the first. A pawn capturing straight
    ahead is `move(pawn,FF,FR,FF,TR)` -- one variable in both the origin
    file and the destination file -- and taking the first occurrence
    read a destination guard as though it named the origin. That is
    exactly the shape `_reversal_guards` looks for, so it reported the
    invulnerability guard as a ban on going back.
    """
    if action is None:
        return None
    carrier = list(action[1:])
    out = []
    for arg in args:
        if not _is_variable(arg) or arg not in carrier:
            return None
        out.append(frozenset(i for i, c in enumerate(carrier) if c == arg))
    return tuple(out)


def _compatible(one, other):
    """Could these two slot readings name the same arguments?"""
    return len(one) == len(other) and \
        all(a & b for a, b in zip(one, other))


def _scales(nodes):
    """Constants a game relates to one another: a scale, not a menu.

    A successor fact, an adjacency fact, anything whose head puts two
    constants in different slots says those values have a position
    relative to each other. Cooldowns and counters are built from such
    values; forms are not, and that is the difference between a rule
    that counts down and a rule that offers a choice. Without this the
    frame clause every persistent fluent carries -- `next(F(X)) :-
    true(F(X))` -- makes a mode look like a counter.
    """
    pairs = set()
    for node in nodes:
        head, _ = _head_body(node)
        if node.head_kind not in ('derived', 'fact') or \
                not isinstance(head, tuple):
            continue
        constants = [a for a in head[1:] if _is_constant(a)]
        for i, one in enumerate(constants):
            for other in constants[i + 1:]:
                pairs.add(frozenset((one, other)))
    return pairs


def _modes(nodes, dominant, roles, scales):
    """Fluents that hold a MODE: which of several forms an entity is in.

    A mode is a fluent that (1) is not the board itself, (2) an action
    writes, (3) legal clauses consult positively, and (4) carries two or
    more unrelated constants in one argument slot -- the forms.

    The exclusions keep it from matching everything. The board fluent
    carries piece names in a slot and would qualify, so it is excluded
    by identity: a mode is a SECOND state a game keeps beside its
    positions. Turn order carries role names and is excluded by those
    being roles. A cooldown carries numbers the game relates to each
    other through a successor fact, and is excluded by that -- counting
    down is a different function with a different ablation.
    """
    # Constants seen in a slot ANYWHERE, and constants seen in a slot
    # that a LEGAL clause tests. Only the second identifies the mode: a
    # form is a value the rules branch on, and the difference matters
    # because an init clause fixes a starting square as well as a
    # starting form. Reading every slot equally made the queen's file
    # letters -- b and g, the two squares the royal queens start on --
    # look like the set of forms a queen can take.
    values = collections.defaultdict(lambda: collections.defaultdict(set))
    gate_values = collections.defaultdict(lambda: collections.defaultdict(set))
    action_written, gated = collections.defaultdict(set), set()
    persistent = set()
    initial = collections.defaultdict(lambda: collections.defaultdict(set))

    for node in nodes:
        for name, args, negated in _body_atoms(node):
            if name != 'true' or not args or not isinstance(args[0], tuple):
                continue
            fluent = args[0]
            for index, arg in enumerate(fluent[1:]):
                if _is_constant(arg):
                    values[fluent[0]][index].add(arg)
            if node.head_kind == 'legal' and not negated:
                gated.add(fluent[0])
                for index, arg in enumerate(fluent[1:]):
                    if _is_constant(arg):
                        gate_values[fluent[0]][index].add(arg)
            if node.head_kind == 'fluent_write' and \
                    node.head_predicate == fluent[0]:
                persistent.add(fluent[0])
        written = _written_fluent(node)
        if written is None:
            continue
        for index, arg in enumerate(written[1:]):
            if _is_constant(arg):
                values[written[0]][index].add(arg)
                if node.head_kind == 'fluent_init':
                    initial[written[0]][index].add(arg)
        action = _action_of(node)
        if node.head_kind == 'fluent_write' and action is not None:
            action_written[written[0]].add(action[0])

    modes = {}
    for fluent, slots in values.items():
        if fluent == dominant:
            continue
        if fluent not in gated or fluent not in action_written:
            continue
        for slot, constants in sorted(gate_values[fluent].items()):
            if len(constants) < 2 or constants <= roles:
                continue
            if any(frozenset(pair) in scales
                   for pair in itertools.combinations(sorted(constants), 2)):
                continue
            modes[fluent] = {
                'slot': slot,
                # Every value the slot ever holds, not only the ones a
                # legal clause tests: a form nothing branches on is
                # still a form the piece can be in.
                'values': constants | slots.get(slot, set()),
                'actions': action_written[fluent],
                'persistent': fluent in persistent,
                # Only the VALUE slot's starting constant. An init
                # clause also fixes where the piece stands, and those
                # coordinates are not forms to return to.
                'initial': initial[fluent].get(slot, set()),
            }
            break
    return modes


def _mode_menus(nodes, modes, mode_actions):
    """Predicates saying which modes are currently available.

    Found by asking which helpers the legal clause of a mode-setting
    action consults that carry that mode's own values in their heads.
    That is the rule governing what a piece may become, wherever a game
    puts it. Reaching it through the action rather than through the
    values alone is what stops a capture table -- which also carries
    piece names in a slot -- being read as a menu of forms.
    """
    wanted = set()
    for spec in modes.values():
        wanted |= spec['values']
    consulted = set()
    for node in nodes:
        if node.head_kind != 'legal':
            continue
        action = _action_of(node)
        if action is not None and action[0] in mode_actions:
            consulted |= set(node.body_predicates)
    menus = set()
    for node in nodes:
        head, _ = _head_body(node)
        if node.head_predicate not in consulted or not isinstance(head, tuple):
            continue
        if {a for a in head[1:] if _is_constant(a)} & wanted:
            menus.add(node.head_predicate)
    return menus


def _reversal_guards(nodes):
    """Guards forbidding exactly the undoing of the last action.

    The shape: an effect stores some of an action's arguments, and a
    later legal clause of THE SAME action refuses to proceed when a
    DIFFERENT set of its arguments matches what was stored. Storing
    where a move came from and refusing to go back there is that shape;
    storing where it went and refusing to land there again is not, and
    the slot comparison is what tells them apart.
    """
    stored = collections.defaultdict(set)
    for node in nodes:
        written, action = _written_fluent(node), _action_of(node)
        if written is None or action is None or \
                node.head_kind != 'fluent_write':
            continue
        slots = _slots(written[1:], action)
        if slots:
            stored[(action[0], written[0])].add(slots)

    guards = set()
    for node in nodes:
        if node.head_kind != 'legal':
            continue
        action = _action_of(node)
        if action is None:
            continue
        for name, args, negated in _body_atoms(node):
            if name != 'true' or not negated or not args or \
                    not isinstance(args[0], tuple):
                continue
            fluent = args[0]
            slots = _slots(fluent[1:], action)
            key = (action[0], fluent[0])
            if slots and stored.get(key) and \
                    not any(_compatible(slots, seen) for seen in stored[key]):
                guards.add(key)
    return guards


def _configuration(nodes, dominant, roles, counters):
    """Everything the configuration detectors need, computed once."""
    modes = _modes(nodes, dominant, roles, _scales(nodes))
    board_writing = set()
    for node in nodes:
        action = _action_of(node)
        if action is not None and node.head_kind == 'fluent_write' and \
                node.head_predicate == dominant:
            board_writing.add(action[0])

    # An action that sets a mode and never touches the board changes
    # what a piece IS without changing where anything stands.
    reconfiguring = set()
    for spec in modes.values():
        reconfiguring |= {a for a in spec['actions'] if a not in board_writing}

    # An action that can restore a mode's INITIAL value can be undone,
    # so nothing is permanently spent to use it.
    reversible = set()
    for node in nodes:
        if node.head_kind != 'legal':
            continue
        action = _action_of(node)
        if action is None or action[0] not in reconfiguring:
            continue
        for spec in modes.values():
            if spec['initial'] & {a for a in action[1:] if _is_constant(a)}:
                reversible.add(action[0])

    # CONVERSION: the subject is read as one type and written as
    # another. Judged ONE CLAUSE AT A TIME. Pooling an action's read
    # and written types across its clauses made a reactive capture look
    # like a conversion -- one clause moves a bishop, another moves a
    # queen, and the pooled sets then differ although neither clause
    # changes anything's type. Where an effect clause reads no type at
    # all, because a promotion writes its result without consulting
    # what it replaces, the subject comes from the action's own legal
    # clauses instead.
    subject_types = collections.defaultdict(set)
    named_in_actions = set()
    for node in nodes:
        action = _action_of(node)
        if action is None or node.head_kind != 'legal':
            continue
        named_in_actions |= {a for a in action[1:] if _is_constant(a)}
        for name, args, negated in _body_atoms(node):
            if name == dominant and not negated:
                subject_types[action[0]] |= {
                    a for a in args if _is_constant(a)}

    converting = set()
    for node in nodes:
        written, action = _written_fluent(node), _action_of(node)
        if written is None or action is None or written[0] != dominant:
            continue
        produced = {a for a in written[1:] if _is_constant(a)}
        if not produced:
            continue
        consumed = set()
        for name, args, negated in _body_atoms(node):
            if name == dominant and not negated:
                consumed |= {a for a in args if _is_constant(a)}
        if not consumed:
            consumed = subject_types.get(action[0], set())
        # What is consumed has to be something the game treats as a
        # player in its own right -- a value that appears in an action
        # term somewhere, so it has a repertoire of its own. Without
        # this, filling an empty square reads as a conversion, since
        # writing `x` where `b` was has the same shape as writing a
        # queen where a pawn was. Every placement game would then
        # convert resources, which would leave the function meaning
        # nothing.
        if consumed & named_in_actions and produced - consumed:
            converting.add(action[0])

    # REDISTRIBUTION: moving someone else's piece. Three things at
    # once, because any two of them also describe an ordinary move or a
    # frame clause -- the destination comes from the ACTION, the
    # identity comes from the PRE-STATE, and the performer does not
    # appear in what is written. An ordinary move writes the mover's
    # own name into the owner slot; a frame clause writes back what it
    # read and takes nothing from the action.
    redistributing = set()
    for node in nodes:
        written = _written_fluent(node)
        action = _action_of(node)
        if written is None or action is None or written[0] != dominant:
            continue
        performer = None
        for name, args, _neg in _body_atoms(node):
            if name == 'does' and args:
                performer = args[0]
        carried = set()
        for name, args, negated in _body_atoms(node):
            if name == dominant and not negated:
                carried |= {a for a in args if _is_variable(a)}
        from_action = {a for a in action[1:] if _is_variable(a)}
        args = [a for a in written[1:] if _is_variable(a)]
        if performer in args:
            continue
        if any(a in from_action for a in args) and \
                any(a in carried and a not in from_action for a in args):
            redistributing.add(action[0])

    # RAYS: a relation that recurses on itself AND refuses to continue
    # through something. The negated goal in the recursive clause is
    # what makes it a line of sight rather than a symmetric fact --
    # `adjacent(X,Y) :- adjacent(Y,X)` recurses too, and threatens
    # nothing along a direction.
    recursive = set()
    for node in nodes:
        if node.head_predicate and \
                node.head_predicate in node.body_predicates and \
                node.negated_goals:
            recursive.add(node.head_predicate)

    # Fluents an action writes are the game's memory of what happened;
    # one nothing writes from an action is a standing fact.
    historical = set()
    for node in nodes:
        written = _written_fluent(node)
        if written is not None and node.head_kind == 'fluent_write' and \
                _action_of(node) is not None:
            historical.add(written[0])

    mode_actions = set()
    for spec in modes.values():
        mode_actions |= spec['actions']

    return {
        'modes': modes,
        'reconfiguring': reconfiguring,
        'reversible': reversible,
        'converting': converting,
        'redistributing': redistributing,
        'recursive': recursive,
        'historical': historical,
        'mode_menus': _mode_menus(nodes, modes, mode_actions),
        'reversal_guards': _reversal_guards(nodes),
    }
