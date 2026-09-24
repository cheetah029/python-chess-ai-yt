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
    return {
        'dominant': counts.most_common(1)[0][0] if counts else None,
        'control': (control.most_common(1)[0][0]
                    if control and control.most_common(1)[0][1]
                    >= 0.8 * max(len(legal), 1) else None),
        'terminal': terminal,
        'guards': guards,
        'n_legal': len(legal),
    }


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
    """Which ontology functions were predicted at all, and which never.

    A function nothing ever predicts is a claim about the DESCRIPTION or
    a gap in the detectors, and either way it should be visible rather
    than absent from the table.
    """
    seen = {p.function for ps in predictions.values() for p in ps}
    return seen, sorted(set(BY_NAME) - seen)
