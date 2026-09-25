"""Phase 5: recommendations, with the argument that produced each one.

    python3 -m lgref.recommend.run --results results/lgref/phase4-sweep

Reads the same stored rows Phase 4 reads and recomputes nothing of its
own: the profile is the evidence, and this decides what to do about it
under each stated objective.

Two outputs, in this order, because the first is what the paper is for:

  EVIDENCE MATCHING   which strategic functions each ablation's measured
                      signature supports, and which it rules out. The
                      predictions were frozen before any game was played,
                      so they can be wrong here, and being able to be
                      wrong is the point.

  RECOMMENDATIONS     retain / revise / remove per objective, each with
                      the evidence it rests on, and a report of every
                      rule whose answer depends on which objective you
                      hold.
"""

import argparse
import collections
import os

from lgref.analysis import profile as profile_mod
from lgref.analysis.effects import effect
from lgref.analysis.run import BASELINE_VARIANT, load_rows
from lgref.recommend import intent as intent_mod
from lgref.recommend import policy
from lgref.recommend.verdicts import (CONFIRMED, CONTRADICTED, NOT_COMPARABLE,
                                      UNTESTED, match_all)


def analyse(rows, baseline=BASELINE_VARIANT):
    by_variant = collections.defaultdict(list)
    for row in rows:
        by_variant[row['variant']].append(row)
    if baseline not in by_variant:
        raise SystemExit('no baseline variant {!r}'.format(baseline))

    base_rows = by_variant[baseline]
    metrics = sorted(_ontology_metrics() |
                     set(profile_mod.DIMENSIONS.values()))
    effects_by_variant = collections.OrderedDict()
    for variant in sorted(by_variant):
        if variant == baseline:
            continue
        found = []
        for metric in metrics:
            got = effect(metric, base_rows, by_variant[variant], variant,
                         seed_key='seed_group')
            if got:
                found.append(got)
        effects_by_variant[variant] = found
    return effects_by_variant


def _ontology_metrics():
    from lgref.functions.strategic_ontology import ONTOLOGY
    return {metric for f in ONTOLOGY for metric in f.metrics}


def report(effects_by_variant):
    table = profile_mod.build(effects_by_variant)
    print('=' * 92)
    print('PHASE 5 — RECOMMENDATIONS')
    print('=' * 92)
    print()
    print('WHAT IS BEING RECOMMENDED ON. The behavioural sweep measures')
    print('designer-specified engine variants, not the clause clusters')
    print('Phase 1 discovers. Those are ablated in GDL and checked')
    print('structurally, because playing a GDL description through the')
    print('resolver costs over a minute per move. The two rule')
    print('vocabularies are NOT joined, and this reports on the one it')
    print('actually measured.')
    print()
    print('-' * 92)
    print('EVIDENCE MATCHING — which functions the measurements support')
    print()
    print('Predictions were frozen before any game was played. Several')
    print('functions predict the same movement, so a supported set is')
    print('what the evidence is CONSISTENT WITH, not what the rule does;')
    print('the ruled-out set is the stronger half of the report.')
    print()
    matched = collections.OrderedDict()
    for variant, effects in effects_by_variant.items():
        grouped = match_all(effects)
        matched[variant] = grouped
        print('  {}'.format(variant))
        for outcome, label in ((CONTRADICTED, 'ruled out'),
                               (CONFIRMED, 'supported')):
            names = [v.function for v in grouped[outcome]]
            print('      {:<12} {}'.format(
                label, ', '.join(names) if names else '(none)'))
        untested = len(grouped[UNTESTED]) + len(grouped[NOT_COMPARABLE])
        print('      {:<12} {} of 40 (no usable effect, or not a level)'
              .format('untested', untested))
        print()

    intents = intent_mod.load()
    print('-' * 92)
    print('WHAT EACH RULE IS FOR — the designer\'s annotation')
    print()
    print('Held out from identification and inference, read here so a')
    print('measurement can disagree with an intention. `revise` is a')
    print('claim that a rule failed at its OWN job, so without a stated')
    print('job there is nothing to fail at.')
    print()
    print('[framework] marks a mapping from the designer\'s PROSE onto')
    print('ontology names that this framework proposed and the designer')
    print('has not confirmed. A verdict resting on one rests on an')
    print('interpretation, and saying which is which is the difference')
    print('between held-out labels and labels this system wrote itself.')
    print()
    for variant in effects_by_variant:
        declared = intent_mod.declared(intents, variant)
        if declared is None:
            print('      {:<24} not declared — revision cannot be assessed'
                  .format(variant[:23]))
            continue
        mark = ('[framework] '
                if intent_mod.proposed_by_framework(intents, variant)
                else '[designer]  ')
        outcomes = {v.function: v.outcome
                    for group in matched[variant].values() for v in group}
        print('      {:<24} {}{}'.format(variant[:23], mark, ', '.join(
            '{} ({})'.format(f, outcomes.get(f, UNTESTED))
            for f in declared)))
    print()

    gaps = intent_mod.unmapped_phrases()
    if gaps:
        print('  WHAT THE ONTOLOGY HAS NO NAME FOR')
        print('  The designer said these and no function expresses them.')
        print('  A limitation of the vocabulary, not of the designer:')
        for rule, phrases in gaps.items():
            for phrase in phrases:
                print('      {:<24} "{}"'.format(rule[:23], phrase))
        print()

    print('-' * 92)
    print('RECOMMENDATIONS UNDER EACH STATED OBJECTIVE')
    print()
    all_recs = []
    for objective, weights in profile_mod.OBJECTIVES.items():
        print('  {}'.format(objective.upper()))
        for variant, row in table.items():
            value = profile_mod.index(row, weights)['index']
            rec = policy.recommend(
                variant, objective, weights, row, value,
                matched[variant][CONTRADICTED],
                intent_mod.declared(intents, variant))
            all_recs.append(rec)
            print('      {:<24} {:<22} {}'.format(
                variant[:23], rec.verdict, rec.reason))
        print()

    clashes = policy.disagreements(all_recs)
    print('-' * 92)
    if clashes:
        print('THE ANSWER DEPENDS ON THE OBJECTIVE — reported, not resolved')
        print()
        for variant, verdicts in clashes.items():
            print('  {:<24} {}'.format(variant[:23], ', '.join(
                '{}={}'.format(o, v) for o, v in verdicts.items())))
    else:
        print('No rule\'s recommendation changed with the objective. With')
        print('most cells unmeasurable that is a statement about the')
        print('evidence, not agreement between the objectives.')
    return all_recs


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results', required=True)
    parser.add_argument('--baseline', default=BASELINE_VARIANT)
    args = parser.parse_args(argv)
    if not os.path.isdir(args.results):
        raise SystemExit('no such results directory: {}'.format(args.results))
    rows = load_rows(args.results)
    if not rows:
        raise SystemExit('no rows under {}'.format(args.results))
    report(analyse(rows, args.baseline))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
