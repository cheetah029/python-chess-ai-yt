"""Replication gating: which learned weights are findings.

The failure this guards against is on the record. Two trainings
differing only in seed put `King` at +0.281 against `RoyalQueen` +0.236,
then at +0.100 against +0.160 -- the ordering reversed -- and the first
run had already been reported as a per-piece valuation.
"""

from lgref.experiments.replicate import (effective, gate, report,
                                         summarise)


def test_a_sign_flip_is_never_replicated():
    """The case that actually happened. Whatever the mean, a feature
    that changes direction between runs has no direction to report."""
    runs = [{'King': 0.281, 'RoyalQueen': 0.236},
            {'King': 0.100, 'RoyalQueen': 0.160}]
    kept, dropped = gate(runs)
    # Both agree in sign here, so the ORDERING is what failed, not the
    # sign -- which is why sign agreement alone is not enough.
    flipper = [{'X': +0.5}, {'X': -0.4}, {'X': +0.6}]
    kept2, dropped2 = gate(flipper)
    assert 'X' in dropped2 and 'X' not in kept2
    assert set(kept) | set(dropped) == {'King', 'RoyalQueen'}


def test_agreement_without_separation_is_not_enough():
    """A feature can agree on sign across every run and still be
    indistinguishable from zero."""
    runs = [{'tiny': 0.001}, {'tiny': 0.400}, {'tiny': 0.002}]
    rows = {r.feature: r for r in summarise(runs)}
    assert rows['tiny'].sign_agreement == 1.0
    assert rows['tiny'].t < 2.0
    assert not rows['tiny'].replicated


def test_a_stable_feature_survives():
    runs = [{'Rook': 0.552}, {'Rook': 0.538}, {'Rook': 0.561}]
    kept, dropped = gate(runs)
    assert 'Rook' in kept
    assert abs(kept['Rook'] - 0.550) < 0.01
    assert not dropped


def test_absence_counts_as_zero_not_as_missing():
    """The extractors omit a feature where it is zero, so averaging only
    over the runs that produced it averages over exactly the runs where
    it was large -- a biased subsample, which is the same mistake that
    had to be fixed for the threat features and the m,n,k line counts.
    """
    runs = [{'sparse': 0.9}, {}, {}]
    rows = {r.feature: r for r in summarise(runs)}
    assert rows['sparse'].runs == 3
    assert abs(rows['sparse'].mean - 0.3) < 1e-9
    assert not rows['sparse'].replicated, (
        'present in one run of three must not read as a finding')


def test_a_single_run_can_never_replicate():
    """One sample has no spread, so it cannot support a claim. This is
    the discipline the king/queen report violated."""
    rows = summarise([{'anything': 5.0}])
    assert rows[0].runs == 1
    assert not rows[0].replicated


def test_the_report_shows_what_failed_as_well_as_what_passed():
    """A reader who sees only the survivors cannot tell whether two of
    three replicated or two of forty."""
    runs = [{'a': 0.5, 'b': 0.01}, {'a': 0.52, 'b': -0.4}]
    text = report(runs)
    assert 'UNMEASURED' in text
    assert 'b' in text
    assert 'of 2 features replicated' in text


def test_effective_units_are_used_for_comparison():
    """Raw weights are in normalised units, so two runs' raw vectors are
    on two different scalings and must not be averaged directly."""
    payload = {'weights': {'f': 2.0}, 'scales': {'f': 4.0}}
    assert effective(payload) == {'f': 0.5}
    # A stored `effective` block wins, since that is what the run itself
    # reported.
    assert effective({'effective': {'f': 9.0}}) == {'f': 9.0}


def test_a_zero_scale_does_not_divide_by_zero():
    payload = {'weights': {'f': 2.0}, 'scales': {'f': 0.0}}
    assert effective(payload) == {'f': 2.0}


def test_nothing_here_knows_a_game():
    import ast
    import inspect

    import lgref.experiments.replicate as module

    tree = ast.parse(inspect.getsource(module))
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef)):
            text = ast.get_docstring(node, clean=False)
            if text is not None:
                docstrings.add(text)
    live = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Str) and node.s not in docstrings:
            live.add(node.s)
        elif isinstance(node, ast.Attribute):
            live.add(node.attr)
        elif isinstance(node, ast.Name):
            live.add(node.id)
    short = ' '.join(x for x in live if len(x) < 40)
    for banned in ('Rook', 'Bishop', 'Knight', 'Pawn', 'royal', 'Line:'):
        assert banned not in short, banned
