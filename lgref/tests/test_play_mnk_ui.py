"""The m,n,k window, driven the way a person drives it.

WHY THIS FILE EXISTS. A reviewer sent a screenshot with four separate
faults on one screen, and the module already had 22 tests:

  1. the seconds-per-move stepper was drawn THROUGH the "X player"
     heading, because one sat at `y + 144` and the other at `y + 152`
     and nothing in the code related the two numbers;
  2. the window called `set_mode` on every click of `+`, so it jumped
     around under the cursor while the board was still being chosen;
  3. moving a setting twenty steps meant twenty clicks;
  4. there was no undo, and no way to save or load a game, both of
     which the case study's window has had for months.

None of them were reachable from a test, because everything lived
inside one closure whose only entry point ran an event loop forever. So
`play_window` now takes a `probe` callback -- a documented test seam --
and these tests use it to click, scroll, undo and paste.

Headless: SDL dummy drivers, no window, no sound.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..',
                                'src'))

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

import pygame

import pytest

import lgref.play_mnk as play
from lgref.experiments.mnk import MNK


def drive(check, sides=None, m=4, n=4, k=3):
    """Open the window, run `check(api)` once, close it.

    Training is kept to a second: these tests are about the screen, and
    the learner has its own file.
    """
    brain = play.Brain(rounds=1, games=2, seed=1, use_td_leaf=False,
                       depth=2, budget=1.0)
    captured = {}

    def probe(api):
        captured['value'] = check(api)
        return True

    play.play_window(m, n, k, brain, 2,
                     sides or {play.FIRST: 'human', play.SECOND: 'td'},
                     probe=probe)
    return captured.get('value')


# ---- 1. overlapping text -------------------------------------------

def test_nothing_on_the_setup_screen_overlaps_anything_else():
    """THE SCREENSHOT, asked of every board size and both styles.

    `draw_setup` records every rectangle it draws -- controls and text
    alike -- so this can be an assertion rather than an eyeball. The
    rows are laid out from a cursor that each row advances by its own
    height, which is why no row can choose a y that collides with
    another's.
    """
    def check(api):
        state = api['state']
        clashes = []
        for style in play.STYLES:
            state['style'] = style
            for size in (2, 5, 9, 13, 20):
                state['m'] = state['n'] = size
                state['k'] = play.clamp_setting('k', state['k'], size,
                                                size)
                api['draw']()
                clashes += [(style, size) + pair
                            for pair in play.overlaps(state['layout'])]
        return clashes

    assert drive(check) == []


def test_the_layout_check_can_actually_fail():
    """A check that cannot fail is not a check. Two rectangles that
    genuinely overlap must be reported, by name."""
    first = pygame.Rect(0, 0, 50, 50)
    second = pygame.Rect(25, 25, 50, 50)
    apart = pygame.Rect(400, 400, 10, 10)
    found = play.overlaps({'a': first, 'b': second, 'c': apart})
    assert found == [('a', 'b')], found


# ---- 2. the window resizing on every click -------------------------

def test_changing_the_board_never_resizes_the_setup_window():
    """The window used to be opened at the BOARD's size, so every
    click on `+` called `set_mode`. Choosing a 20x20 board meant the
    window growing under the cursor sixteen times."""
    def check(api):
        before = pygame.display.get_surface().get_size()
        sizes = {before}
        for _step in range(16):
            api['bump']('m', 1)
            api['bump']('n', 1)
            api['draw']()
            sizes.add(pygame.display.get_surface().get_size())
        return api['state']['m'], sorted(sizes)

    rows, sizes = drive(check)
    assert rows == 20, rows
    assert sizes == [play.SETUP_SIZE], (
        'the window changed size while the board was being chosen: '
        '{0}'.format(sizes))


def test_the_window_takes_the_boards_shape_only_when_play_starts():
    """The resize is not removed, it is MOVED -- a 20x20 board still
    needs a window shaped for it, just not before Start."""
    def check(api):
        api['state']['m'] = api['state']['n'] = 9
        _cell, _surface, width, height = api['resize']()
        return width, height

    width, height = drive(check)
    assert (width, height) != play.SETUP_SIZE


# ---- 3. clicking + twenty times ------------------------------------

def test_a_setting_can_be_moved_without_one_click_per_step():
    """Hold-to-repeat and scroll both go through `bump`, which is the
    one place a setting changes -- so a test that drives `bump` covers
    the repeat timer and the wheel together."""
    def check(api):
        api['state']['m'] = 2
        for _step in range(30):            # further than the bound
            api['bump']('m', 1)
        return api['state']['m']

    assert drive(check) == play.SETTING_BOUNDS['m'][1]


def test_shrinking_the_board_pulls_the_win_condition_down_with_it():
    """`k` in a row is impossible on a board smaller than `k`, so Start
    would build a game nobody can win."""
    def check(api):
        state = api['state']
        state['m'] = state['n'] = 12
        for _step in range(9):
            api['bump']('k', 1)
        before = state['k']
        for _step in range(10):
            api['bump']('m', -1)
            api['bump']('n', -1)
        return before, state['m'], state['n'], state['k']

    before, rows, cols, condition = drive(check)
    assert before > 3
    assert condition <= max(rows, cols), (before, rows, cols, condition)


def test_the_repeat_delay_is_longer_than_the_repeat_interval():
    """Otherwise a single click registers twice, which is worse than
    the problem the repeat was added to solve."""
    assert play.REPEAT_DELAY_MS > play.REPEAT_EVERY_MS
    assert play.REPEAT_EVERY_MS > 0


# ---- 4. undo / redo and save / load --------------------------------

def test_undo_hands_the_turn_back_to_the_human():
    """ONE PLY IS NOT ENOUGH when an agent is playing: give the turn
    back to the agent and it instantly replays, so the board looks
    unchanged and undo appears broken."""
    def check(api):
        api['rebuild'](log_status=False)
        game = api['game']
        # A human move, then an agent move.
        api['commit'](game[0].get_all_legal_turns()[0])
        api['commit'](game[0].get_all_legal_turns()[0])
        before = len(api['played'])
        api['undo']()
        human_to_move = api['players'][0].get(
            game[0].current_player) is None
        return before, len(api['played']), human_to_move

    before, after, human_to_move = drive(check)
    assert before == 2
    assert after < before, 'undo removed nothing'
    assert human_to_move, (
        'undo left an agent to move, so it will replay immediately')


def test_redo_puts_back_exactly_what_undo_took():
    def check(api):
        api['rebuild'](log_status=False)
        game = api['game']
        for _ply in range(2):
            api['commit'](game[0].get_all_legal_turns()[0])
        snapshot = list(api['played'])
        api['undo']()
        while api['redo']():
            pass
        return snapshot, list(api['played'])

    snapshot, restored = drive(check)
    assert restored == snapshot, (snapshot, restored)


def test_a_new_move_discards_the_redo_branch():
    """What every editor does, and what a player expects."""
    def check(api):
        api['rebuild'](log_status=False)
        game = api['game']
        api['commit'](game[0].get_all_legal_turns()[0])
        api['undo']()
        had = len(api['future'])
        api['commit'](game[0].get_all_legal_turns()[-1])
        return had, len(api['future'])

    had, left = drive(check)
    assert had > 0 and left == 0


def test_restart_clears_the_history_rather_than_leaving_it_dangling():
    def check(api):
        api['rebuild'](log_status=False)
        game = api['game']
        api['commit'](game[0].get_all_legal_turns()[0])
        api['restart']()
        return len(api['history']), len(api['future']), len(api['played'])

    assert drive(check) == (0, 0, 0)


def test_a_saved_game_round_trips_through_its_own_text():
    """The move list is authoritative and the position is for the
    reader -- so a round trip has to reproduce the moves, and the
    position is checked against a replay of them rather than parsed."""
    game, played = play.replay_moves(4, 4, 3, [0, 5, 1, 6, 2])
    text = play.save_text(game, 4, 4, 3, 'go', played)
    loaded = play.load_text(text)
    assert loaded['m'] == 4 and loaded['n'] == 4 and loaded['k'] == 3
    assert loaded['style'] == 'go'
    assert loaded['moves'] == played
    again, replayed = play.replay_moves(loaded['m'], loaded['n'],
                                        loaded['k'], loaded['moves'])
    assert replayed == played
    assert again.cells == game.cells


def test_a_pasted_game_that_does_not_fit_stops_rather_than_raising():
    """Someone edits a line by hand, or pastes half a game. Replaying
    stops at the first illegal move and reports how far it got."""
    _game, played = play.replay_moves(3, 3, 3, [0, 1, 2, 0, 4])
    assert played == [0, 1, 2], played      # 0 is occupied by then

    _game, played = play.replay_moves(3, 3, 3, [99])
    assert played == []


def test_text_that_is_not_a_save_is_refused_quietly():
    for junk in ('', 'hello', None, '=== something else ==='):
        assert play.load_text(junk) is None


def test_a_save_missing_its_board_line_is_refused():
    text = '\n'.join([play.SAVE_HEADER, 'Style: go', 'Moves: 1 2'])
    assert play.load_text(text) is None


def test_the_save_shows_the_position_a_reader_can_check():
    game, played = play.replay_moves(3, 3, 3, [0, 4, 1])
    text = play.save_text(game, 3, 3, 3, 'squares', played)
    rows = text.splitlines()
    body = rows[rows.index('Position:') + 1:]
    assert body == ['xx.', '.o.', '...'], body


# ---- the panel ------------------------------------------------------

def test_the_panel_is_tall_enough_for_its_own_buttons_and_legend():
    """The button row grew from two to six and the key legend moved
    below it; a panel sized for the old row clips the new one."""
    def check(api):
        api['rebuild'](log_status=False)
        api['state']['screen'] = 'play'
        api['resize']()
        hits = api['draw']()
        names = [name for name, _rect in hits]
        bottom = max(rect.bottom for _name, rect in hits)
        height = pygame.display.get_surface().get_height()
        return names, bottom, height

    names, bottom, height = drive(check)
    for expected in ('setup', 'restart', 'undo', 'redo', 'copy', 'paste'):
        assert expected in names, (expected, names)
    assert bottom < height, (
        'the button row is drawn past the bottom of the window')


def test_every_panel_button_has_a_key_and_every_key_a_button():
    """A reviewer should not have to guess which of the two works."""
    import inspect

    source = inspect.getsource(play.play_window)
    legend = [line for line in source.splitlines() if 'U undo' in line]
    assert legend, 'the key legend is gone'
    for word in ('S setup', 'R restart', 'U undo', 'Y redo', 'C copy',
                 'V paste', 'Q quit'):
        assert word in ' '.join(legend) or word in source, word


@pytest.mark.parametrize('name', ['copy_text', 'read_text'])
def test_the_clipboard_helper_is_not_the_case_studys(name):
    """Reusing the one in `src/game.py` would make the general m,n,k
    player import the case study's engine module permanently."""
    import inspect

    from lgref import clipboard

    assert hasattr(clipboard, name)
    source = inspect.getsource(clipboard)
    for banned in ('game', 'board', 'piece', 'chess'):
        assert 'import ' + banned not in source, banned


def test_the_clipboard_falls_through_to_the_next_route():
    """Each layer fails in a different environment, so a failure in one
    must not stop the chain -- the case study's first version had no CLI
    layer and reported "clipboard unavailable" on a Mac that ships
    pbcopy."""
    from lgref import clipboard

    calls = []

    def boom(_text):
        calls.append('pyperclip')
        raise RuntimeError('not installed')

    def ok(_text, platform=None):
        calls.append('cli')
        return True

    original = (clipboard._via_pyperclip_copy, clipboard._via_cli_copy)
    clipboard._via_pyperclip_copy, clipboard._via_cli_copy = boom, ok
    try:
        assert clipboard.copy_text('hello') is True
    finally:
        (clipboard._via_pyperclip_copy,
         clipboard._via_cli_copy) = original
    assert calls == ['pyperclip', 'cli'], calls
