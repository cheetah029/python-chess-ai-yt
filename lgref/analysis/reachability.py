"""Rules that almost never fire, and how to measure them anyway.

THE PROBLEM, STATED GENERALLY. Some rules govern situations that
imperfect play does not reach. Royal Chess has two: the tiny-endgame
rule needs a pawnless, balanced, few-piece position, and the repetition
rule needs a player to want to stall. Both need near-optimal play from
both sides ON TOP OF a niche position. Ablating such a rule measures
nothing, and the measurement is not wrong -- it is correct and empty.

This is not a quirk of one game. Any rule set has rules that fire only
in late, rare or adversarially-produced states, and a framework that
measures rules by playing games will under-measure exactly those.

THE DECOMPOSITION. A rule's contribution splits in two, and conflating
them is what makes the empty result look like a null result:

    contribution  =  P(the rule's condition arises)  x  effect given it does

The first factor is a property of the rule and the population of play.
The second is a property of the rule alone. Measured separately they are
both meaningful; multiplied without being named, a dormant rule and a
harmless rule are indistinguishable.

A RULE THAT NEVER FIRES IS A FINDING, not a failed measurement. "You
wrote a rule that competent play never reaches" is among the most
actionable things a designer can be told, and the framework should say
it in those words rather than reporting a contribution of zero.

HOW TO MEASURE THE SECOND FACTOR WITHOUT LEAVING THE GAME. Construct
the states and you risk measuring positions that cannot legally occur;
a contribution computed over impossible positions is worse than no
contribution. So REACH them instead, by legal play under a bias chosen
to shorten the path to the rule's condition -- capture-biased play
reaches pawnless endgames quickly -- and record the bias, because the
conditional effect is conditional on how the states were reached.

Every position stays legal by construction, and the weighting stays
explicit: the conditional effect is reported WITH its activation rate
under neutral play, never folded into a single number.

WHAT MAKES THIS GAME-AGNOSTIC. The activation condition does not have
to be supplied by a designer. The framework already parses the rules
into clauses, so a rule's own clause body IS its activation condition:
whatever must hold for the rule to have any effect. `tiny_endgame_active`
and a repetition count of two are not Royal Chess facts hand-entered
here -- they are the guards the rule's own clauses carry. Any GDL game
gets the same treatment from the same parse.
"""

import collections
import math

#: Which recorded column says the ablated rule's condition arose. Named
#: per variant because the column is the rule's own activation marker;
#: `identify/` can derive these from clause guards, which is the
#: game-agnostic route and is not wired yet (#237).
ACTIVATION = {
    'no_tiny_endgame': 'tiny_endgame_activated',
    'no_repetition_rule': 'repetition_blocks',
    'no_knight_invulnerability': 'protection_active_turns',
    'no_bishop_reactive': 'mean_armed_responses',
}

#: Events needed before an effect on the conditional quantity is worth
#: estimating. Thirty is a convention, stated so it can be argued with.
TARGET_EVENTS = 30

Reach = collections.namedtuple(
    'Reach', 'variant column games activated rate bound needed verdict')

MEASURABLE = 'measurable'
UNDERPOWERED = 'underpowered'
DORMANT = 'never activated'


def upper_bound_zero(games, confidence=0.95):
    """If it never happened in n games, how often can it happen at most?

    The rule-of-three bound: observing zero events in n trials puts the
    rate below about 3/n at 95% confidence. Reporting this instead of
    "rate = 0" is the difference between "this cannot happen" and "we
    did not see it happen", and the first claim is not one the data
    supports.
    """
    if not games:
        return 1.0
    return round(-math.log(1 - confidence) / games, 6)


def games_needed(rate, target=TARGET_EVENTS):
    """How many games to expect `target` activations at this rate."""
    if rate <= 0:
        return None
    return int(math.ceil(target / rate))


def assess(rows, activation=None):
    """Per variant: did the ablated rule's condition ever arise?"""
    activation = ACTIVATION if activation is None else activation
    by_variant = collections.defaultdict(list)
    for row in rows:
        by_variant[row.get('variant')].append(row)

    out = []
    for variant, column in sorted(activation.items()):
        games = by_variant.get(variant) or []
        if not games:
            continue
        hits = sum(1 for r in games if r.get(column))
        rate = hits / len(games)
        if not hits:
            bound = upper_bound_zero(len(games))
            out.append(Reach(variant, column, len(games), 0, 0.0, bound,
                             games_needed(bound), DORMANT))
            continue
        verdict = MEASURABLE if hits >= TARGET_EVENTS else UNDERPOWERED
        out.append(Reach(variant, column, len(games), hits, round(rate, 4),
                         None, games_needed(rate), verdict))
    return out


def report(assessments):
    lines = ['RULE REACHABILITY — what the games never reached',
             '',
             'A rule whose condition does not arise cannot be measured by',
             'playing, and that is a finding about the RULE rather than a',
             'failed measurement. Contribution splits in two:',
             '',
             '    contribution = P(condition arises) x effect given it does',
             '',
             'and a dormant rule and a harmless rule are only',
             'distinguishable when the two are reported apart.',
             '']
    for item in assessments:
        if item.verdict == DORMANT:
            lines.append(
                '  {:<28} NEVER in {} games. Rate is not zero, it is '
                'below {:.4f}'.format(item.variant[:27], item.games,
                                      item.bound))
            lines.append(
                '  {:<28} at 95% confidence; {} games would be needed to '
                'expect {}.'.format('', item.needed, TARGET_EVENTS))
        else:
            lines.append(
                '  {:<28} {} of {} games ({:.1%}) — {}, {} games for {} '
                'events'.format(item.variant[:27], item.activated,
                                item.games, item.rate, item.verdict,
                                item.needed, TARGET_EVENTS))
    return '\n'.join(lines)
