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
    # `effective_choice` leads here and raw `choice_diversity` is
    # demoted from 1.0 to 0.3 ON PURPOSE. Counting legal actions is the
    # very thing `complexity_without_depth` warns about: a rule can
    # lengthen the legal list without adding anything worth choosing,
    # and until the near-optimal count was measured this objective had
    # no way to tell that from real richness. Raw count keeps a small
    # weight because having options at all is not nothing.
    ('tactical_richness', {
        'effective_choice': 1.0, 'threat_reach': 0.8,
        'force_concentration': 0.4, 'choice_diversity': 0.3,
        'game_length': 0.2}),
    ('accessibility', {
        'choice_diversity': -0.6, 'effective_choice': -0.3,
        'game_length': -0.8, 'decisive_rate': 0.4}),
))

#: Which measured metric stands for each profile dimension.
DIMENSIONS = collections.OrderedDict((
    ('game_length', 'total_turns'),
    ('choice_diversity', 'mean_branching'),
    ('effective_choice', 'mean_policy_branching'),
    ('threat_reach', 'mean_attack_coverage'),
    ('force_concentration', 'mean_attack_overlap'),
    ('space_reach', 'mean_reachable_mover'),
    ('spatial_denial', 'mean_denied_squares'),
    ('material_variety', 'mean_distinct_types'),
    ('outcome_balance', 'white_win'),
    ('decisive_rate', 'decisive'),
    ('cycle_pressure', 'turn_cap_reached'),
))

#: Metrics the sweep records that are deliberately NOT profile
#: dimensions, and why. Without this the list of recorded columns and
#: the list of consulted ones drift apart silently, which is how five
#: columns came to be a constant zero for 1440 games without anyone
#: noticing they were never read.
#:
#: The distinction that matters is TAUTOLOGY. Removing a rule drives
#: the count of turns that use it to exactly zero; reporting that as a
#: contribution reports that the ablation worked. Those counters are
#: still worth recording -- Phase 5 uses them to check that a rule's
#: own activity actually stopped -- but as a profile axis they would
#: manufacture a large effect for every removal and none for any
#: relaxation.
NOT_A_DIMENSION = collections.OrderedDict((
    ('foreign_turns', 'usage counter: a removal zeroes it by definition'),
    ('shared_entity_turns',
     'usage counter: a removal zeroes it by definition'),
    ('mode_change_turns', 'usage counter: a removal zeroes it by definition'),
    ('mode_reentry_turns', 'usage counter: a removal zeroes it by definition'),
    ('conversion_turns', 'usage counter: a removal zeroes it by definition'),
    ('response_turns', 'usage counter: a removal zeroes it by definition'),
    ('self_removal_turns',
     'usage counter: a removal zeroes it by definition'),
    ('turns_move', 'per-rule usage frequency, reported separately'),
    ('turns_boulder', 'per-rule usage frequency, reported separately'),
    ('turns_manipulation', 'per-rule usage frequency, reported separately'),
    ('turns_transformation', 'per-rule usage frequency, reported separately'),
    ('repetition_blocks', 'usage counter for one rule, not a shared axis'),
    ('endgame_blocks', 'usage counter for one rule, not a shared axis'),
    ('mean_protected_pieces',
     'a condition only one rule creates: evidence for that function, '
     'not an axis every rule can be placed on'),
    ('mean_restrained_pieces',
     'a condition only some rules create: evidence, not an axis'),
    ('mean_armed_responses',
     'a condition only some rules create: evidence, not an axis'),
    ('mean_move_entropy',
     'a second reading of the same policy as effective_choice'),
    ('mean_action_types',
     'closely tracks the usage counters it is derived from'),
    ('mean_max_same_type',
     'the other half of material_variety; one axis is enough'),
    ('mean_objective_distance',
     'evidence for objective_salience; not comparable across games '
     'with different objectives'),
    ('total_captures', 'evidence for several functions; material '
     'exchange is not itself a design dimension'),
    ('repeated_state_frequency',
     'evidence for cycle_prevention; cycle_pressure is the axis'),
    ('tiny_endgame_activated', 'activation of one rule, not an axis'),
    ('tiny_endgame_seen', 'activation of one rule, not an axis'),
    ('black_win', 'the mirror of outcome_balance'),
    ('draw_or_censored', 'the mirror of decisive_rate'),
    ('loss_reason', 'categorical; used by name in function evidence'),
    ('winner', 'categorical; the dimensions derive from it'),
    ('variant', 'identifier'), ('seed', 'identifier'),
    ('seed_group', 'identifier'), ('wall_clock_s', 'cost, not an effect'),
    ('sampled_positions', 'provenance'),
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


#: The profile printed in blocks, because eleven dimensions on one row
#: is 222 characters and wraps into nonsense. The grouping is not
#: cosmetic: each block answers a different question about a rule, and
#: reading a rule across one block is the comparison worth making.
#: Every dimension appears in exactly one block, which a test enforces
#: so a new dimension cannot be added and silently never printed.
DIMENSION_GROUPS = collections.OrderedDict((
    ('outcome and duration',
     ('game_length', 'decisive_rate', 'outcome_balance', 'cycle_pressure')),
    ('choice', ('choice_diversity', 'effective_choice')),
    ('space and force',
     ('threat_reach', 'force_concentration', 'space_reach',
      'spatial_denial', 'material_variety')),
))


#: Wide enough for the longest dimension name and the longest verdict,
#: because a truncated `force_concentrati` and a truncated
#: `seed-domin` both make the reader guess.
CELL = 21


def _cell(entry, width=CELL):
    if entry is None:
        return '{:>{}}'.format('-', width)
    if entry.verdict != 'effect':
        return '{:>{}}'.format(entry.verdict, width)
    # d and the interval are on DIFFERENT scales -- d is standardised,
    # the interval is on the raw difference -- so they are not printed
    # side by side as though one bracketed the other.
    return '{:>{}}'.format('d={:+.2f}'.format(entry.cohens_d), width)


def format_profile(profile):
    lines = []
    for title, dims in DIMENSION_GROUPS.items():
        header = '{:<24}'.format('variant') + ''.join(
            '{:>{}}'.format(d, CELL) for d in dims)
        lines.append('')
        lines.append(title.upper())
        lines.append(header)
        lines.append('-' * len(header))
        for variant, row in profile.items():
            lines.append('{:<24}'.format(variant[:23]) + ''.join(
                _cell(row.get(d)) for d in dims))
    return '\n'.join(lines[1:])
