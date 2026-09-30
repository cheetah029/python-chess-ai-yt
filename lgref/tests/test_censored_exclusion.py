"""A capped game must not count as evidence about the outcome (#260).

`outcome_row` sets `white_win`, `black_win` and `decisive` to False for a
game stopped by the turn cap, and the analysis turned those into 0.0 and
averaged over every row -- so "we stopped watching" counted as evidence
that white did not win. `outcome_balance` and `decisive_rate` were biased
downward by the censored share, and `game_length` too, since a censored
length is a lower bound.

The cap cannot fix this. Over 400 uncapped random games every game
terminated, but the median was 312 and the maximum 1775, and each tenfold
increase in sample size has found a longer game: 1600 was "censor-free"
only against the 40 games of #204.
"""

from lgref.analysis.effects import CENSORED_UNOBSERVED, _observed, effect


def _row(seed, **over):
    row = {'seed': seed, 'variant': 'full', 'turn_cap_reached': False,
           'white_win': 1.0, 'black_win': 0.0, 'decisive': 1.0,
           'total_turns': 300.0, 'mean_branching': 60.0}
    row.update(over)
    return row


def test_outcome_metrics_drop_censored_rows():
    rows = [_row(0), _row(1, turn_cap_reached=True, white_win=0.0,
                          decisive=0.0, total_turns=3000.0)]
    for metric in ('white_win', 'decisive', 'total_turns'):
        assert len(_observed(metric, rows)) == 1, metric


def test_the_censoring_indicator_keeps_them():
    """Excluding censored rows from `turn_cap_reached` would zero it.

    It stands for `cycle_pressure`, so dropping the censored games would
    make the metric identically zero -- measuring nothing, and looking
    like a clean result.
    """
    rows = [_row(0), _row(1, turn_cap_reached=True)]
    assert len(_observed('turn_cap_reached', rows)) == 2
    assert 'turn_cap_reached' not in CENSORED_UNOBSERVED


def test_structural_metrics_keep_them():
    """A censored game's sampled positions are valid observations.

    Dropping them would throw away good data because the game happened
    to be long.
    """
    rows = [_row(0), _row(1, turn_cap_reached=True)]
    assert len(_observed('mean_branching', rows)) == 2


def test_censoring_no_longer_drags_a_win_rate_down():
    """The bias, shown as a number.

    Baseline: 4 games, all white wins. Variant: 4 games, all white wins,
    but two were censored. The true variant win rate over OBSERVED games
    is 1.0, identical to the baseline — there is no effect. Counting the
    censored games as non-wins invents one.
    """
    base = [_row(seed, white_win=1.0) for seed in range(4)]
    variant = [_row(seed, white_win=1.0) for seed in range(2)] + [
        _row(seed, turn_cap_reached=True, white_win=0.0, decisive=0.0)
        for seed in (2, 3)]

    got = effect('white_win', base, variant, 'v')
    # Every observed game in both arms is a white win, so the difference
    # is exactly zero and there is nothing to find.
    assert got is None or got.difference == 0.0, (
        'censored games are being counted as evidence that white lost: '
        'difference {}'.format(got and got.difference))


def test_a_variant_that_is_all_censored_yields_no_cell():
    """Not a zero. There is no observation to compare."""
    base = [_row(seed) for seed in range(4)]
    variant = [_row(seed, turn_cap_reached=True, white_win=0.0)
               for seed in range(4)]
    assert effect('white_win', base, variant, 'v') is None
