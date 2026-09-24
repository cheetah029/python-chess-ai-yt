"""Assign strategic functions to rules from structure alone.

Phase 2, and deliberately BEFORE any ablation runs. Every label here is
a prediction about what Phase 3 will measure, so it has to be made
without seeing those measurements.

Multi-label: a rule can do several jobs, and forcing one would
misrepresent rules that plainly do. Confidence reports how much of the
cluster matches a signature -- EVIDENCE STRENGTH, not a probability of
being right, which only the ablation can settle.

DETECTOR STRENGTH IS REPORTED, NOT HIDDEN. Three of these read directly
off GDL's own structure and are hard to get wrong; three infer from
weaker proxies and say so. A weak detector making a falsifiable
prediction is worth keeping -- it is exactly what pre-registration is
for -- but presenting it as firm would not be.
"""

import collections

from lgref.functions.ontology import BY_NAME
from lgref.identify.language import LANGUAGE, classify_all

#: How much of a cluster must match before a label is emitted at all.
MIN_CONFIDENCE = 0.15

STRONG, WEAK = 'strong', 'weak'

#: Which detectors rest on GDL's own reserved structure, and which on a
#: proxy that could misfire. Reported alongside every label.
DETECTOR_STRENGTH = {
    'termination_pressure': STRONG,   # `terminal` / `goal` are reserved
    'move_generation': STRONG,        # a `legal` head is unambiguous
    'turn_structure': STRONG,         # the control fluent is identifiable
    'move_restriction': WEAK,         # "guards a legal clause" over-collects
    'cross_turn_memory': WEAK,        # a written-and-read fluent may be within-turn
    'state_conversion': WEAK,         # "non-dominant fluent" is a proxy for identity change
    'capture_regime': WEAK,           # removal is encoded as ABSENT persistence
}

Label = collections.namedtuple('Label', 'function confidence strength basis')


def _dominant_fluent(nodes):
    """The fluent most clauses write -- a game's board, whatever it is.

    Derived rather than named: in Royal Chess it is `cell`, in nim it is
    `pile`. Used to tell an action that RELOCATES something from one
    that changes what it is.
    """
    counts = collections.Counter()
    for node in nodes:
        for fluent in node.fluents_written:
            counts[fluent] += 1
    return counts.most_common(1)[0][0] if counts else None


def _control_fluent(nodes):
    """The fluent that gates `legal` clauses almost universally.

    Whatever a description calls "whose turn it is", nearly every legal
    clause reads it. Found by that share rather than by its name.
    """
    legal = [n for n in nodes if n.head_kind == 'legal']
    if not legal:
        return None
    counts = collections.Counter()
    for node in legal:
        for fluent in node.fluents_read:
            counts[fluent] += 1
    best, n = counts.most_common(1)[0] if counts else (None, 0)
    return best if n >= 0.8 * len(legal) else None


def _has_exclusion(node):
    """Does this clause carry an exclusion guard?

    Removal is not written down in GDL. A piece is captured by its cell
    simply NOT being re-asserted, so the signature is a conditional
    persistence: re-assert the board unless the mover landed here.

    The guard is read off the RAW form because normalisation drops it --
    `distinct` is a GDL builtin, so it appears in neither
    `body_predicates` nor `negated_goals`, and the first version of this
    detector fired zero times on 36 clauses that matched every other
    criterion. `distinct` and `not` are reserved words, so reading for
    them stays game-agnostic.
    """
    def walk(term):
        if isinstance(term, tuple):
            if term and term[0] in ('distinct', 'not'):
                return True
            return any(walk(part) for part in term)
        return False

    return walk(node.raw)


class _Context(object):
    """Description-wide facts the detectors share."""

    def __init__(self, nodes):
        self.nodes = nodes
        self.dominant = _dominant_fluent(nodes)
        self.control = _control_fluent(nodes)
        self.terminal_fluents = set()
        for node in nodes:
            if node.head_kind in ('terminal', 'goal') or \
                    node.terminal_dependency:
                self.terminal_fluents |= set(node.fluents_read)
        self.legal_guards = collections.Counter()
        for node in nodes:
            if node.head_kind == 'legal':
                self.legal_guards.update(node.fluents_read)
                self.legal_guards.update(node.body_predicates)
        self.read_fluents = collections.Counter()
        for node in nodes:
            self.read_fluents.update(node.fluents_read)


def _labels_for(own, ctx):
    """Every function the cluster's own clauses give evidence for."""
    total = max(len(own), 1)
    out = []

    def add(name, hits, basis):
        if not hits:
            return
        out.append(Label(name, round(hits / total, 3),
                         DETECTOR_STRENGTH[name], basis))

    add('termination_pressure',
        sum(1 for n in own
            if n.head_kind in ('terminal', 'goal') or n.terminal_dependency
            or (n.fluents_written & ctx.terminal_fluents)),
        'feeds the ending condition')

    add('move_generation',
        sum(1 for n in own if n.head_kind == 'legal'),
        'defines legal clauses')

    if ctx.control:
        add('turn_structure',
            sum(1 for n in own if ctx.control in n.fluents_written),
            'writes the control fluent {}'.format(ctx.control))

    add('move_restriction',
        sum(1 for n in own
            if (n.fluents_written & set(ctx.legal_guards))
            or (n.head_predicate in ctx.legal_guards)),
        'its state or predicates guard legal clauses')

    add('cross_turn_memory',
        sum(1 for n in own
            if n.head_kind == 'fluent_write'
            and (n.fluents_written & set(ctx.read_fluents))
            and n.fluents_written != {ctx.dominant}),
        'writes state read on a later turn')

    if ctx.dominant:
        add('state_conversion',
            sum(1 for n in own
                if n.head_kind == 'fluent_write' and n.actions_read
                and ctx.dominant not in n.fluents_written),
            'an action whose effect is not on {}'.format(ctx.dominant))

        add('capture_regime',
            sum(1 for n in own
                if n.head_kind == 'fluent_write'
                and ctx.dominant in n.fluents_written
                and ctx.dominant in n.fluents_read
                and n.actions_read and _has_exclusion(n)),
            'conditional persistence of {} -- how removal is encoded'
            .format(ctx.dominant))

    return [l for l in out if l.confidence >= MIN_CONFIDENCE]


def infer(nodes, rules, skip_language=True):
    """{rule_id: [Label, ...]} for every rule worth labelling.

    Language clusters are skipped: coordinate arithmetic has no
    strategic function, and asking what job `file_delta_1` does is the
    error that held this phase up (#202).
    """
    kinds = classify_all(nodes, rules)
    ctx = _Context(nodes)
    out = collections.OrderedDict()
    for rule in rules:
        if skip_language and kinds[rule.rule_id] == LANGUAGE:
            continue
        own = [n for n in rule.nodes() if n.node_id in rule.clause_ids]
        out[rule.rule_id] = sorted(
            _labels_for(own, ctx), key=lambda l: -l.confidence)
    return out


def predictions(labels):
    """The falsifiable claims implied by a label set."""
    return [{'function': l.function,
             'predicted_effect': BY_NAME[l.function].prediction,
             'metric': BY_NAME[l.function].metric,
             'direction': BY_NAME[l.function].direction,
             'confidence': l.confidence,
             'detector_strength': l.strength}
            for l in labels]
