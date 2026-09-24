"""The Rule Contribution Profile, and summaries of it under objectives.

Phase 4's primary result is the PROFILE: the full vector of standardised
effects per rule, with intervals. It answers "in which dimensions is
this rule influential", and it stays the headline.

The Rule Contribution Index is a SUMMARY of that profile under a stated
design objective, not a discovered constant. There is deliberately no
universal RCI: different objectives weight different dimensions and
produce different rankings. Reporting one number as though it were the
rule's worth would hide exactly the judgement the framework is supposed
to expose.

If a rule's rank flips under a reasonable reweighting, that is a finding
to report, not to smooth over.
"""

import collections

#: Design objectives, each weighting the dimensions it cares about.
#: Weights are a statement of what is being optimised for, not an
#: empirical quantity, and are named so a reader can disagree with them.
OBJECTIVES = collections.OrderedDict((
    ('competitive_balance', {
        'outcome_balance': 1.0, 'decisive_rate': 0.6,
        'choice_diversity': 0.4}),
    ('anti_stagnation', {
        'game_length': -1.0, 'cycle_pressure': 1.0, 'decisive_rate': 0.8}),
    ('tactical_richness', {
        'choice_diversity': 1.0, 'threat_reach': 0.8, 'game_length': 0.2}),
    ('accessibility', {
        'choice_diversity': -0.6, 'game_length': -0.8,
        'decisive_rate': 0.4}),
))

#: Which measured metric stands for each profile dimension.
DIMENSIONS = collections.OrderedDict((
    ('game_length', 'total_turns'),
    ('choice_diversity', 'mean_branching'),
    ('threat_reach', 'mean_attack_coverage'),
    ('space_reach', 'mean_reachable_mover'),
    ('outcome_balance', 'white_win'),
    ('decisive_rate', 'decisive'),
    ('cycle_pressure', 'turn_cap_reached'),
))


def build(effects_by_variant):
    """{variant: {dimension: Effect}} -> the profile table."""
    profile = collections.OrderedDict()
    for variant, effects in effects_by_variant.items():
        by_metric = {e.metric: e for e in effects}
        row = collections.OrderedDict()
        for dimension, metric in DIMENSIONS.items():
            row[dimension] = by_metric.get(metric)
        profile[variant] = row
    return profile


def index(profile_row, weights):
    """Weighted sum of standardised effects, skipping what is not real.

    An effect the variance decomposition marked seed-dominated, or whose
    interval spans zero, contributes NOTHING rather than its point
    estimate. Summing unreliable estimates is how a confident total gets
    built out of noise.
    """
    total, used, skipped = 0.0, [], []
    for dimension, weight in weights.items():
        entry = profile_row.get(dimension)
        if entry is None:
            skipped.append((dimension, 'not measured'))
            continue
        if entry.verdict != 'effect':
            skipped.append((dimension, entry.verdict))
            continue
        d = entry.cohens_d
        if d != d or abs(d) == float('inf'):
            skipped.append((dimension, 'undefined effect size'))
            continue
        total += weight * d
        used.append(dimension)
    return {'index': round(total, 3), 'dimensions_used': used,
            'dimensions_skipped': skipped}


def rank_sensitivity(profile):
    """How each rule ranks under every objective, and whether it moves.

    A rank that flips under a reasonable reweighting is reported. The
    framework's job is to make the dependence on the objective visible,
    not to pick one and present its answer as the answer.
    """
    rankings = collections.OrderedDict()
    for name, weights in OBJECTIVES.items():
        scored = [(variant, index(row, weights)['index'])
                  for variant, row in profile.items()]
        scored.sort(key=lambda pair: -pair[1])
        rankings[name] = [variant for variant, _ in scored]

    positions = collections.defaultdict(dict)
    for objective, order in rankings.items():
        for place, variant in enumerate(order, start=1):
            positions[variant][objective] = place

    unstable = {variant: places for variant, places in positions.items()
                if max(places.values()) - min(places.values()) >= 2}
    return rankings, dict(positions), unstable


def format_profile(profile):
    dims = list(DIMENSIONS)
    lines = ['{:<24}'.format('variant') +
             ''.join('{:>18}'.format(d[:17]) for d in dims)]
    lines.append('-' * (24 + 18 * len(dims)))
    for variant, row in profile.items():
        cells = []
        for dimension in dims:
            entry = row.get(dimension)
            if entry is None:
                cells.append('{:>18}'.format('-'))
            elif entry.verdict != 'effect':
                cells.append('{:>18}'.format(entry.verdict[:10]))
            else:
                # d and the interval are on DIFFERENT scales -- d is
                # standardised, the interval is on the raw difference --
                # so they are not printed side by side as though one
                # bracketed the other.
                cells.append('{:>18}'.format(
                    'd={:+.2f}'.format(entry.cohens_d)))
        lines.append('{:<24}'.format(variant[:23]) + ''.join(cells))
    return '\n'.join(lines)
