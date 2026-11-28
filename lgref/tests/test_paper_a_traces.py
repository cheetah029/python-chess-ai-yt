"""#402: legal-move agreement along played-out traces.

The logic-based, representation-invariant counterpart of the atom
metrics: two descriptions written differently but logically identical
must give 0 differences, an ablation that only drops an unused state
fluent must give 0 (successor atoms would call it different), and a
real rule change must show up.
"""

import lgref  # noqa: F401
from lgref.bench import probes, rewrites, traces
from lgref.bench.catalog import game_path


def _text(game):
    with open(game_path(game)) as handle:
        return handle.read()


def test_a_description_agrees_with_itself():
    text = _text('breakthrough5')
    got = traces.play_out(text, text, games=5)
    assert traces.exact(got) and got['steps'] > 5


def test_logically_identical_descriptions_written_differently():
    """Arguments permuted, statements reordered, helpers extracted,
    inlined and duplicated, and every name renamed: 0 differences."""
    from ggp.infix import parse_infix
    from lgref.bench.experiments import _symbol_inverse, _unmap
    for game in ('checkers_4x4', 'othello4', 'kalah_mini'):
        text = _text(game)
        forms = parse_infix(text)
        for name in ('permute', 'reorder', 'extract', 'inline',
                     'duplicate'):
            new, _ = rewrites.rewrite(name, forms)
            got = traces.play_out(text, rewrites.to_text(new), games=4)
            assert traces.exact(got), (game, name, got)
        new, _ = rewrites.rewrite('scramble', forms)
        inverse = _symbol_inverse(forms, [])
        got = traces.play_out(text, rewrites.to_text(new), games=4,
                              move_map=lambda m: _unmap(m, inverse),
                              role_map=lambda r: _unmap(r, inverse))
        assert traces.exact(got), (game, 'scramble', got)


def test_dropping_an_unused_fluent_changes_nothing_logically():
    """Checkers' `tick` counter is written but never read by a rule.
    Deleting it changes every successor STATE (a representation
    difference) and no legal move, ending or payoff."""
    text = _text('checkers_4x4')
    stripped = '\n'.join(
        line for line in text.splitlines()
        if not line.startswith('next(tick(')
        and not line.startswith('init(tick('))
    assert stripped != text
    got = traces.play_out(text, stripped, games=5)
    assert traces.exact(got), got


def test_a_real_rule_change_shows_up():
    text = _text('breakthrough5')
    change = {c.id: c for c in probes.load_variants('breakthrough5')[1]}[
        'no_capture']
    got = traces.play_out(text, probes.variant_text(text, change),
                          games=10)
    assert got['legal_differences'] > 0 and not traces.exact(got)


def test_trace_rows_rebuild_the_scored_ablation():
    """The singleton deleting `legal(P,take(2))` is nim take_one_only's
    exact ablation: its play-out against the reference shows nothing."""
    from lgref.bench import experiments as X
    rows, setup = X.intervention_rows(['nim'], ['singletons'])
    record = {'rows': rows, 'setup': setup, 'games': ['nim'], 'seed': 0}
    got = X.trace_rows(record, games=5, procedures=('delete_group',))
    row = next(r for r in got if r['change'] == 'take_one_only')
    assert row['exact'] and row['steps'] > 0
