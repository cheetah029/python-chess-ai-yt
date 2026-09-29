"""Invariants checked WHILE a long run is running, not only before it.

WHY THIS EXISTS. The pre-flight gate (`lgref.verify`) checks what would
invalidate a run before it starts. It cannot check what goes wrong at
game 80 of 132 -- and this project's defects have all been the silent
kind, producing plausible numbers rather than errors. A 40-hour run that
is discovered to be void at the end costs 40 hours; one that aborts at
game 3 costs twenty minutes.

THREE LAYERS, cheapest first.

1. EVERY ROW, as it arrives. A censored game, a missing column, an
   `agent` field holding an object instead of a name -- each is a defect
   this project has actually shipped, and each is visible in the row
   itself for free.

2. A CANARY, every `canary_every` games. A fixed-seed random game whose
   move sequence is checksummed at startup and re-checksummed later. It
   costs about a fifth of a second and it notices anything that changes
   what the engine does mid-run: a variant flag leaking between pool
   jobs, a mutated class attribute, an interpreter that stopped
   reproducing. `verify.checks` proves the engine is deterministic
   BEFORE the run; this proves it stayed that way DURING it.

3. RUNNING AGGREGATES. A column that is constant across the rows so far
   is either rare or broken, and the difference is worth knowing at game
   20 rather than at the end. Reported, not fatal -- rarity is real.

ABORTING IS THE POINT. `observe` returns violations and the runner
raises on them, because a run that continues after an invariant breaks
is producing rows nobody may use.
"""

import collections
import hashlib
import sys
import time

#: Columns whose absence or emptiness means the row is not a measurement.
#: Each is a defect this project has shipped: `agent` recorded a player
#: OBJECT where a name belonged (#230), and five outcome columns were a
#: constant zero across 1440 games because a hand-built record carried
#: four keys where nine were read (#221).
REQUIRED_COLUMNS = ('variant', 'seed', 'agent', 'total_turns',
                    'turn_cap_reached')

#: Columns that are legitimately all-zero in a short run. Measured rates
#: are in `docs/spec/measuring-rare-rules.md`; flagging them as broken
#: would train the reader to ignore this report.
RARE_COLUMNS = frozenset((
    'endgame_blocks', 'repetition_blocks', 'tiny_endgame_activated',
    'tiny_endgame_seen', 'repeated_state_frequency',
    'mean_protected_pieces', 'response_turns'))


class HealthViolation(RuntimeError):
    """An invariant broke mid-run. The rows after it are not usable."""


def canary_fingerprint(make_engine, seed=97, max_turns=200):
    """A checksum of one fixed-seed random game.

    RANDOM PLAY ON PURPOSE. This asks whether the ENGINE still does the
    same thing, not whether an agent is strong, so it wants the cheapest
    player that exercises the rules -- a fifth of a second against the
    hour a searched game costs.
    """
    import random

    from lgref.experiments.mcts import describe
    from lgref.experiments.random_play import build

    engine = make_engine('full', max_turns=max_turns)
    white = build('random', random.Random(seed * 2 + 1), 0)
    black = build('random', random.Random(seed * 2 + 2), 0)
    digest = hashlib.md5()
    while not engine.is_game_over():
        turns = engine.get_all_legal_turns()
        if not turns:
            break
        player = white if engine.current_player == 'white' else black
        chosen = player.choose_turn(turns, engine)
        digest.update(repr((len(turns), describe(chosen))).encode())
        engine.execute_turn(chosen)
    return digest.hexdigest()[:16]


def variant_flags(make_engine, names):
    """Each variant's ablation switches, to prove they do not leak.

    The pool REUSES its workers, so a job for `no_boulder` and a job for
    `full` run in the same interpreter. The switches are instance
    attributes with `True` defaults, which is what makes that safe --
    and this is what would notice if one ever became a class attribute
    that a previous job had set.
    """
    out = {}
    for name in names:
        board = make_engine(name, max_turns=50).board
        out[name] = (board.enable_knight_invulnerability,
                     board.enable_bishop_reactive,
                     board.enable_repetition,
                     board.boulder is not None)
    return out


class RunHealth:
    """Watches a run as its rows arrive, and refuses to let it continue.

    `observe(row)` returns a list of violation strings -- empty when the
    row is sound. The caller raises; this class does not, so a caller
    that wants to collect rather than abort can.
    """

    def __init__(self, make_engine, expected_agent=None,
                 expected_variants=(), expected_simulations=None,
                 canary_every=10, report_every=10, stream=None):
        self.make_engine = make_engine
        self.expected_agent = expected_agent
        self.expected_variants = frozenset(expected_variants)
        self.expected_simulations = expected_simulations
        self.canary_every = canary_every
        self.report_every = report_every
        self.stream = stream if stream is not None else sys.stderr

        self.seen = 0
        self.censored = 0
        self.by_variant = collections.Counter()
        self.decisive_by_variant = collections.Counter()
        self.values = collections.defaultdict(set)
        self.started = time.time()

        # The reference the canary compares against. Taken BEFORE any
        # measurement, so it describes the engine the run was started
        # with.
        self.reference = canary_fingerprint(make_engine)
        self.reference_flags = variant_flags(
            make_engine, sorted(self.expected_variants) or ('full',))
        self.canary_checks = 0

    # ---- per row ---------------------------------------------------------

    def observe(self, row):
        """Violations in this row, plus any the periodic checks found."""
        self.seen += 1
        problems = []
        if not isinstance(row, dict):
            return ['row {} is {!r}, not a record'.format(
                self.seen, type(row))]

        for column in REQUIRED_COLUMNS:
            if column not in row:
                problems.append('row {} has no {!r} column'.format(
                    self.seen, column))

        variant = row.get('variant')
        self.by_variant[variant] += 1
        if self.expected_variants and variant not in self.expected_variants:
            problems.append('row {} has variant {!r}, which the config does '
                            'not list'.format(self.seen, variant))

        # A CENSORED GAME IS NOT A DRAW. There is no draw condition, so a
        # game stopped by the cap contributes no outcome at all; it is
        # the failure `CENSOR_FREE_TURN_CAP` exists to prevent, and if it
        # starts happening mid-run the cap is wrong for this agent.
        if row.get('turn_cap_reached'):
            self.censored += 1
            problems.append(
                'row {} ({}, seed {}) hit the turn cap at {} turns: no draw '
                'condition exists, so this game contributes no outcome'
                .format(self.seen, variant, row.get('seed'),
                        row.get('total_turns')))
        elif row.get('winner'):
            self.decisive_by_variant[variant] += 1

        # `agent` MUST BE A NAME. It once held the player object, because
        # a loop variable shadowed the parameter, and the provenance
        # field of every row in a 1440-game sweep recorded a repr (#230).
        agent = row.get('agent')
        if agent is not None and not isinstance(agent, str):
            problems.append('row {} records agent as {!r}, not a name'.format(
                self.seen, type(agent).__name__))
        elif self.expected_agent and agent != self.expected_agent:
            problems.append('row {} was played by {!r}, the config says {!r}'
                            .format(self.seen, agent, self.expected_agent))

        simulations = row.get('agent_simulations')
        if (self.expected_simulations is not None and simulations is not None
                and simulations != self.expected_simulations):
            problems.append('row {} used {} simulations, the config says {}'
                            .format(self.seen, simulations,
                                    self.expected_simulations))

        if not row.get('total_turns'):
            problems.append('row {} played {!r} turns'.format(
                self.seen, row.get('total_turns')))

        for key, value in row.items():
            if isinstance(value, (str, int, float, bool)) or value is None:
                self.values[key].add(value)

        if self.canary_every and self.seen % self.canary_every == 0:
            problems.extend(self.check_canary())
        if self.report_every and self.seen % self.report_every == 0:
            self.report()
        return problems

    # ---- periodic --------------------------------------------------------

    def check_canary(self):
        """Has the engine changed since the run started?"""
        self.canary_checks += 1
        problems = []
        now = canary_fingerprint(self.make_engine)
        if now != self.reference:
            problems.append(
                'THE ENGINE CHANGED MID-RUN: the canary game checksummed {} '
                'at startup and {} after {} games. Every row from here is '
                'suspect, and the earlier ones may be too'.format(
                    self.reference, now, self.seen))
        flags = variant_flags(self.make_engine,
                              sorted(self.reference_flags))
        for name, current in sorted(flags.items()):
            if current != self.reference_flags[name]:
                problems.append(
                    'VARIANT {} CHANGED MID-RUN: switches were {} at startup '
                    'and are {} now -- an ablation is leaking between jobs'
                    .format(name, self.reference_flags[name], current))
        return problems

    def constant_columns(self):
        """Columns with one value so far, minus the ones that should be.

        SUCCESS IS NOT A DEFECT, and this check reported it as one until
        it was measured: when NO game is censored, `turn_cap_reached`
        and `draw_or_censored` are uniformly False precisely because
        nothing was cut off, and `decisive` uniformly True because every
        game reached a result. Naming those teaches the reader to skim
        this report, which is the one thing it cannot afford. The gate's
        `check_no_constant_columns` had the same bug (#253).
        """
        exempt = set(RARE_COLUMNS) | {'agent', 'agent_simulations'}
        if not self.censored:
            exempt |= {'turn_cap_reached', 'draw_or_censored', 'decisive'}
        return sorted(column for column, values in self.values.items()
                      if len(values) == 1 and column not in exempt)

    def report(self):
        elapsed = (time.time() - self.started) / 60.0
        constant = self.constant_columns()
        print('[health] {} games, {} censored, {} canary checks, {:.0f} min; '
              '{}'.format(self.seen, self.censored, self.canary_checks,
                          elapsed,
                          'constant so far: ' + ', '.join(constant)
                          if constant else 'no unexpected constants'),
              file=self.stream, flush=True)

    def summary(self):
        lines = ['{} games, {} censored'.format(self.seen, self.censored)]
        for variant in sorted(self.by_variant):
            played = self.by_variant[variant]
            decisive = self.decisive_by_variant[variant]
            lines.append('  {:<26} {:>3} games, {:>3} decisive'.format(
                variant, played, decisive))
        constant = self.constant_columns()
        if constant:
            lines.append('  constant columns: ' + ', '.join(constant))
        return '\n'.join(lines)
