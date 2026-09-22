"""Intervention coherence: does a candidate cluster behave like a rule?

The final Phase 1 filter (issue #187). Clustering proposes groups of
clauses; this decides which of them are RULES. A group whose removal
breaks the game, or whose removal changes nothing, or whose removal
scatters damage across unrelated behaviour, is not a gameplay provision
however tightly its clauses are connected in the graph.

THE TEST

For each candidate, build an ablated description with its clauses
removed and ask three questions:

  compiles   does the result still parse and load?
  playable   does the mover still have legal moves at the start?
  changes    did anything observably change — either the legal moves
             available, or WHEN THE GAME ENDS?

A rule that governs termination removes no legal moves at all: deleting
tic-tac-toe's line detection leaves every mark available and simply stops
the game ever being won. Judging only on legal moves would reject such a
rule as inert, so termination is probed separately by playing the same
seeded move sequence through both descriptions and comparing whether, and
when, they end.

A cluster that fails any of these is not a rule. Reporting that is the
point: the brief calls a failing cluster "not a mechanic", and a
framework that proposed rules without being able to reject any would be
proposing nothing.

WHY "INTERFACE-PRESERVING" MATTERS

Ablating a rule must leave a playable game, or the comparison in Phase 3
is between a game and a non-game. A cluster whose removal makes the
mover immobile has not isolated a rule; it has removed the game's
ability to function, and its measured "contribution" would be an
artefact of that.

This is also why `playable` is checked at the START state specifically:
it is the one position every variant shares, so a difference there is
attributable to the ablation rather than to divergent play.

NOTHING HERE IS GAME-SPECIFIC. Action types are whatever the description
declares; coherence is measured over those, not over any fixed list.
"""

import collections
import os
import tempfile
import time


class CoherenceReport(object):
    """Verdict on one candidate cluster."""

    __slots__ = ('rule_id', 'compiles', 'playable', 'focused', 'n_clauses',
                 'actions_before', 'actions_after', 'actions_lost',
                 'moves_before', 'moves_after', 'error', 'concentration',
                 'terminal_before', 'terminal_after', 'changes_termination')

    def __init__(self, rule_id, n_clauses):
        self.rule_id = rule_id
        self.n_clauses = n_clauses
        self.compiles = False
        self.playable = False
        self.focused = False
        self.actions_before = {}
        self.actions_after = {}
        self.actions_lost = {}
        self.moves_before = 0
        self.moves_after = 0
        self.concentration = 0.0
        self.terminal_before = None
        self.terminal_after = None
        self.changes_termination = False
        self.error = None

    @property
    def changes_behaviour(self):
        """Did ablation change anything observable?

        Either legal moves disappeared in a focused way, or the game's
        ending changed. A rule must do one or the other; a cluster that
        does neither is inert and is not a provision.
        """
        return bool(self.focused or self.changes_termination)

    @property
    def verdict(self):
        """One of: 'rule', 'load_bearing', 'inert', 'broken'.

        The distinction between 'rule' and 'load_bearing' matters and
        should not be collapsed into pass/fail.

        A LOAD-BEARING cluster is very likely a genuine rule — turn
        alternation certainly is — but removing it leaves no playable
        game, so its contribution CANNOT BE MEASURED BY ABLATION. There
        is nothing to compare against. Calling it "not a rule" would be
        wrong; calling it a measurable rule would be worse, because
        Phase 3 would then compare a game with a non-game and report the
        difference as a contribution.

        An INERT cluster changes nothing observable when removed. Either
        it is not a provision, or its effect lies outside what this probe
        reaches (a rule that only acts in positions a short random
        playout never visits). Reported as inert rather than rejected,
        so the distinction stays visible.
        """
        if not self.compiles:
            return 'broken'
        if not self.playable:
            return 'load_bearing'
        if not self.changes_behaviour:
            return 'inert'
        return 'rule'

    @property
    def is_rule(self):
        """True only for clusters whose contribution ablation can
        actually measure."""
        return self.verdict == 'rule'

    def describe(self):
        return {
            'rule_id': self.rule_id,
            'n_clauses': self.n_clauses,
            'compiles': self.compiles,
            'playable': self.playable,
            'focused': self.focused,
            'changes_termination': self.changes_termination,
            'verdict': self.verdict,
            'is_rule': self.is_rule,
            'moves_before': self.moves_before,
            'moves_after': self.moves_after,
            'actions_lost': self.actions_lost,
            'concentration': round(self.concentration, 3),
            'error': self.error,
        }


def ablate_forms(nodes, clause_ids):
    """The description with `clause_ids` removed, as raw GDL forms."""
    drop = set(clause_ids)
    return [n.raw for n in nodes if n.node_id not in drop]


def _write_gdl(forms):
    """Serialise forms back to GDL text in a temporary file.

    Written in infix HRF, the project's official dialect (issue #190),
    so that an ablated description can be read by a human and re-fed to
    the framework in the same notation as the original.
    """
    from ggp.infix import forms_to_infix_lines

    handle = tempfile.NamedTemporaryFile('w', suffix='.gdl', delete=False)
    try:
        for line in forms_to_infix_lines(forms):
            handle.write(line + '\n')
    finally:
        handle.close()
    return handle.name


def _action_histogram(moves):
    """How many legal moves of each action type, by the description's own
    action names — never a fixed list."""
    counts = collections.Counter()
    for move in moves:
        if isinstance(move, tuple) and move:
            counts[move[0]] += 1
        else:
            counts[str(move)] += 1
    return dict(counts)


def _legal_at_start(path):
    """Legal moves for each role in the initial state."""
    from ggp.game import GGPGame
    game = GGPGame.from_file(path)
    out = {}
    for role in game.roles:
        out[role] = list(game.legal_moves(role))
    return out


def _termination_differs(before, after, min_relative_shift=0.10):
    """Did ablation change how games END, across the seeded probes?

    Two signals, because either alone gets it wrong:

    WHETHER games end. If the ablated version stops terminating at all,
    that is decisive.

    HOW LONG they take, compared as MEANS. Exact ply tuples cannot be
    used: once an ablation changes the legal-move set the seeded
    sequences diverge immediately, so individual plies differ for
    trivial reasons and nearly every cluster would look
    termination-changing. But the ply is often the whole signal —
    removing tic-tac-toe's line detection leaves every game terminating,
    just always after the full nine marks (mean 9.0) instead of ending
    early on a line (mean 7.8). Comparing only the boolean misses that
    entirely.

    The threshold is RELATIVE to the baseline's own game length, because
    an absolute one does not travel between games: a one-ply shift is
    decisive in nine-ply tic-tac-toe and invisible in a 300-ply chess
    variant. A shift of 10% of mean game length is the smallest worth
    calling a change.

    This replaced an absolute 1.0-ply threshold that was measurably too
    brittle: with five probe seeds the line-detection rule shifted mean
    length 8.2 -> 9.0, just under the cut, and read as inert; with ten
    seeds the same rule shifted 7.8 -> 9.0 and passed. A criterion whose
    answer depends on the sample size is not a criterion.
    """
    reached_before = sum(1 for t, _ in before if t)
    reached_after = sum(1 for t, _ in after if t)
    if reached_before != reached_after:
        return True
    if not before or not after:
        return False
    mean_before = sum(p for _, p in before) / len(before)
    mean_after = sum(p for _, p in after) / len(after)
    if mean_before <= 0:
        return mean_after > 0
    return (abs(mean_before - mean_after) / mean_before) >= min_relative_shift


def _one_probe(path, max_plies, seed):
    import random
    from ggp.game import GGPGame
    rng = random.Random(seed)
    game = GGPGame.from_file(path)
    for ply in range(max_plies):
        if game.is_terminal():
            return True, ply
        moves = {}
        for role in game.roles:
            legal = game.legal_moves(role)
            if not legal:
                return False, ply
            moves[role] = rng.choice(sorted(legal, key=repr))
        game.step(moves)
    return game.is_terminal(), max_plies


def _termination_probe(path, max_plies=20, seeds=tuple(range(10))):
    """Play several seeded random sequences and report how each ended.

    Returns a tuple of (terminal_reached, plies) per seed. The SAME seeds
    are used for both descriptions, so a difference is attributable to
    the ablation rather than to divergent play — as far as the move sets
    allow, which is why the result is reported rather than asserted.

    SEVERAL seeds, not one, because a single playout easily misses a
    rule's effect. Deleting tic-tac-toe's line detection leaves a game
    that still ends after nine marks — the board fills — so one seeded
    probe showed no difference at all and the rule read as inert. Other
    seeds end early on a line and do differ.
    """
    return tuple(_one_probe(path, max_plies, seed) for seed in seeds)


def check_cluster(nodes, rule, baseline=None, baseline_path=None,
                  baseline_termination=None, min_concentration=0.6,
                  probe_plies=20, probe_seeds=tuple(range(10))):
    """Run the three coherence checks on one candidate cluster.

    `min_concentration` is the share of lost legal moves that must fall
    in a single action type for the loss to count as focused. A rule
    removes a describable behaviour; a bad cluster removes pieces of
    several unrelated ones.
    """
    report = CoherenceReport(rule.rule_id, len(rule.clause_ids))
    own_baseline_path = None

    # Only the cluster's OWN clauses are removed. Shared helpers serve
    # other rules too, so removing them would ablate those rules as well
    # and the result would not isolate anything.
    forms = ablate_forms(nodes, rule.clause_ids)
    path = _write_gdl(forms)
    try:
        try:
            after = _legal_at_start(path)
            report.compiles = True
        except Exception as exc:
            report.error = '{}: {}'.format(type(exc).__name__, exc)
            return report

        # Build the baseline here when the caller did not supply one.
        # Both the legal-move baseline AND its termination probe are
        # needed: without the probe, changes_termination can never be
        # true and every termination-governing rule reads as inert.
        own_baseline_path = None
        if baseline is None or baseline_path is None:
            own_baseline_path = _write_gdl([n.raw for n in nodes])
            if baseline is None:
                baseline = _legal_at_start(own_baseline_path)
            if baseline_path is None:
                baseline_path = own_baseline_path

        movers_before = sum(len(v) for v in baseline.values())
        movers_after = sum(len(v) for v in after.values())
        report.moves_before = movers_before
        report.moves_after = movers_after
        report.playable = movers_after > 0

        before_hist = _action_histogram(
            [m for v in baseline.values() for m in v])
        after_hist = _action_histogram(
            [m for v in after.values() for m in v])
        report.actions_before = before_hist
        report.actions_after = after_hist

        lost = {}
        for action, count in before_hist.items():
            delta = count - after_hist.get(action, 0)
            if delta > 0:
                lost[action] = delta
        report.actions_lost = lost

        # Termination probe: a rule may change WHEN the game ends rather
        # than what is legal. Run only when the ablated game is playable,
        # since probing an immobile game says nothing.
        if report.playable:
            try:
                report.terminal_after = _termination_probe(
                    path, max_plies=probe_plies, seeds=probe_seeds)
                # The baseline probe is IDENTICAL for every cluster, so
                # it is computed once by check_all and passed in.
                # Recomputing it here ran the most expensive operation
                # in this module once per cluster: measured, that turned
                # a ~4 minute sweep into one still unfinished at 25.
                if baseline_termination is not None:
                    report.terminal_before = baseline_termination
                elif baseline_path:
                    report.terminal_before = _termination_probe(
                        baseline_path, max_plies=probe_plies,
                        seeds=probe_seeds)
                else:
                    report.terminal_before = None
                if report.terminal_before is not None:
                    report.changes_termination = _termination_differs(
                        report.terminal_before, report.terminal_after)
            except Exception:
                # A probe failure must not mask the legal-move findings.
                report.terminal_after = None

        total_lost = sum(lost.values())
        if total_lost:
            report.concentration = max(lost.values()) / total_lost
            report.focused = report.concentration >= min_concentration
        else:
            # No legal move disappeared. Not a failure by itself — a rule
            # may govern termination instead, which the probe above
            # checks — so `focused` records only that the legal-move
            # evidence was absent.
            report.concentration = 0.0
            report.focused = False
        return report
    finally:
        os.unlink(path)
        if own_baseline_path:
            os.unlink(own_baseline_path)


def check_all(nodes, rules, probe_plies=20, probe_seeds=tuple(range(10)),
              progress=None, **kw):
    """Check every candidate, computing the baseline exactly once.

    Both baselines — legal moves and the termination probe — are
    identical for every cluster, and the termination probe is by far the
    most expensive thing here.

    `progress`, if given, is called with (stage, index, total, seconds)
    after the baseline and after each cluster. A sweep over a real
    description takes minutes, and a run with no output is a run that
    cannot be distinguished from a hung one — which has cost this
    project time before. The callback makes the rate observable from the
    first cluster instead of only at the end.
    """
    base_path = _write_gdl([n.raw for n in nodes])
    try:
        started = time.time()
        baseline = _legal_at_start(base_path)
        baseline_termination = _termination_probe(
            base_path, max_plies=probe_plies, seeds=probe_seeds)
        if progress:
            progress('baseline', 0, len(rules), time.time() - started)

        reports = []
        for index, rule in enumerate(rules, start=1):
            mark = time.time()
            reports.append(check_cluster(
                nodes, rule, baseline=baseline, baseline_path=base_path,
                baseline_termination=baseline_termination,
                probe_plies=probe_plies, probe_seeds=probe_seeds, **kw))
            if progress:
                progress(reports[-1].verdict, index, len(rules),
                         time.time() - mark)
        return reports
    finally:
        os.unlink(base_path)


def format_table(reports):
    header = ('{:<7} {:>8} {:>6} {:>6} {:>9} {:>13} {:>9}  {}'
              .format('rule', 'clauses', 'plays', 'focus', 'ends-diff',
                      'verdict', 'moves', 'actions lost'))
    lines = [header, '-' * (len(header) + 6)]
    for r in reports:
        lines.append('{:<7} {:>8} {:>6} {:>6} {:>9} {:>13} {:>9}  {}'
                     .format(r.rule_id, r.n_clauses,
                             'yes' if r.playable else 'NO',
                             'yes' if r.focused else '-',
                             'yes' if r.changes_termination else '-',
                             r.verdict,
                             '{}->{}'.format(r.moves_before, r.moves_after),
                             r.actions_lost or ('ERROR: ' + (r.error or '')[:32]
                                                if r.error else '(none)')))
    return '\n'.join(lines)
