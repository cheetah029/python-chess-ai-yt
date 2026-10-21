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


def test_the_save_no_longer_draws_the_position():
    """SUPERSEDED ON PURPOSE. v1 wrote the board as dots and marks and
    this test checked it. The drawn board is gone: it cannot be
    replayed, it duplicates the move list, and two sources of truth for
    one thing is how a loader comes to disagree with itself. What
    replaces it is the coordinate move list, checked above."""
    game, played = play.replay_moves(3, 3, 3, [0, 4, 1])
    text = play.save_text(game, 3, 3, 3, 'squares', played)
    assert 'Position:' not in text
    assert '1. 1,3 2,2' in text, text


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
    assert 'R restart' in source, 'the key legend is gone'
    for word in ('S setup', 'R restart', 'step', 'jump', 'C copy',
                 'V paste', 'Q quit'):
        assert word in source, word
    # Every button in the panel row must also have a key, and the
    # letters stay bound even though the legend now shows the arrows.
    for binding in ('pygame.K_r', 'pygame.K_u', 'pygame.K_y',
                    'pygame.K_c', 'pygame.K_v', 'pygame.K_s'):
        assert binding in source, binding


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


def test_the_arrow_keys_step_and_the_jump_keys_reach_the_ends():
    """ARROWS ALONGSIDE THE LETTERS, and Home/End (or Up/Down) to the
    ends. A reviewer asked for the arrows; the jump keys are the
    recommendation that came with them -- Home and End are what every
    editor and media player uses, and Up/Down are the alias for a laptop
    where Home is an fn-chord."""
    import inspect

    source = inspect.getsource(play.play_window)
    for binding in ('pygame.K_LEFT', 'pygame.K_RIGHT', 'pygame.K_HOME',
                    'pygame.K_END', 'pygame.K_UP', 'pygame.K_DOWN'):
        assert binding in source, binding

    def check(api):
        api['rebuild'](log_status=False)
        game = api['game']
        for _ply in range(4):
            turns = game[0].get_all_legal_turns()
            if not turns:
                break
            api['commit'](turns[0])
        played = len(api['played'])
        # Jump to the start: every move comes off.
        for _ in range(100):
            if not api['undo']():
                break
        at_start = len(api['played'])
        # Jump to the end: every move goes back.
        for _ in range(100):
            if not api['redo']():
                break
        return played, at_start, len(api['played'])

    played, at_start, at_end = drive(check)
    assert played > 0
    assert at_start == 0, (
        'jumping to the start left {0} moves played'.format(at_start))
    assert at_end == played, (at_end, played)


def test_jumping_stops_rather_than_spinning():
    """A step that stops making progress must end the jump. Trusting it
    to report exhaustion is how a window hangs."""
    import inspect

    source = inspect.getsource(play.play_window)
    assert 'def jump(' in source
    body = source[source.index('def jump('):]
    assert 'limit' in body[:400], 'the jump is unbounded'


def test_the_board_grows_with_the_window():
    """A 19x19 board at a fixed 620-pixel box gives 32-pixel cells,
    which is hard to see and harder to click. The cell size is derived
    from the room available, so dragging the window bigger -- or going
    full screen -- makes the board bigger."""
    def check(api):
        state = api['state']
        state['m'] = state['n'] = 19
        state['screen'] = 'play'
        small = api['resize']()[0]
        state['box'] = 1400
        large = api['resize']()[0]
        return small, large

    small, large = drive(check)
    assert large > small, (
        'the cell size did not grow with the room available: '
        '{0} -> {1}'.format(small, large))


def test_the_window_is_resizable_and_full_screen_is_bound():
    import inspect

    source = inspect.getsource(play.play_window)
    assert 'pygame.RESIZABLE' in source, (
        'the window cannot be dragged bigger')
    assert 'pygame.VIDEORESIZE' in source, (
        'a resize is not handled, so the board would not grow')
    assert 'pygame.K_F11' in source, 'full screen is not bound'
    assert 'FULLSCREEN' in source


def test_a_tiny_window_still_leaves_a_usable_cell():
    """Shrinking must not produce a zero-pixel cell, which would divide
    by zero in the click mapping."""
    def check(api):
        state = api['state']
        state['m'] = state['n'] = 20
        state['screen'] = 'play'
        state['box'] = 10
        return api['resize']()[0]

    assert drive(check) >= 12


def test_the_save_uses_coordinates_and_names_who_was_playing():
    """A DRAWN BOARD IS PLEASANT AND USELESS. The first format wrote the
    position as a block of dots and marks: it cannot be replayed, it
    duplicates what the moves already say, and two sources of truth for
    one thing is how a loader comes to disagree with itself. The case
    study's save made the other choice and this one now matches it."""
    game, played = play.replay_moves(19, 19, 5, [180, 160, 181])
    text = play.save_text(game, 19, 19, 5, 'go', played,
                          {play.FIRST: 'human', play.SECOND: 'td'})
    assert play.SAVE_HEADER_V3 in text
    # NUMERIC, column first, 1-based, row counted from the bottom --
    # which puts the centre of 19x19 at `10,10`. The letter-number form
    # it replaces called the same cell `j10`.
    assert '1. 10,10 9,11' in text, text
    assert 'Mode: human_vs_td' in text
    assert 'Board: 19x19 k=5' in text
    # THE CONVENTION IS STATED IN THE FILE. `10,10` is ambiguous on a
    # non-square board unless the save says which number is which.
    assert 'Coordinates:' in text
    for word in ('column', 'row', 'bottom'):
        assert word in text.split('Coordinates:')[1].splitlines()[0]
    # No drawn board.
    assert 'Position:' not in text
    assert '...' not in text


def test_the_save_records_the_settings_that_produced_the_game():
    """A SAVE THAT NAMES THE BOARD BUT NOT THE DEPTH DESCRIBES A
    POSITION, NOT A GAME. The same moves at depth 2 and at depth 6 are
    two different agents playing, and a reviewer reporting "it
    blundered here" needs the file to say which one blundered."""
    game, played = play.replay_moves(5, 5, 4, [12, 6, 18])
    text = play.save_text(
        game, 5, 5, 4, 'squares', played,
        {play.FIRST: 'human', play.SECOND: 'td'},
        {'depth': 4, 'budget': 5,
         'training': 'rounds=6 games=60 seed=17 td_leaf=no budget=20s'})
    assert 'Depth: 4' in text
    assert 'SecondsPerMove: 5' in text
    assert 'seed=17' in text
    back = play.load_text(text)
    assert back['depth'] == 4
    assert back['budget'] == 5
    assert 'seed=17' in back['training']
    # AND A SAVE WITHOUT THEM LEAVES THEM ABSENT rather than inventing
    # defaults, so a caller restores what the file actually said.
    plain = play.load_text(play.save_text(game, 5, 5, 4, 'squares', played))
    assert 'depth' not in plain and 'budget' not in plain


def test_a_version_two_save_still_loads_with_its_letters():
    """A reviewer pasted a v2 game into this session. The letters have
    to keep working, and have to mean the same cells."""
    v2 = '\n'.join([
        play.SAVE_HEADER_V2, 'Board: 5x5 k=4', 'Style: squares',
        'Mode: human_vs_td', 'CurrentTurn: 3', '',
        play.SAVE_BEGIN, '1. c3 b4', '2. d2', play.SAVE_END])
    loaded = play.load_text(v2)
    assert loaded is not None
    assert loaded['moves'] == [12, 6, 18]
    assert loaded['m'] == 5 and loaded['n'] == 5 and loaded['k'] == 4


def test_coordinates_round_trip_through_their_own_names():
    for m, n in ((19, 19), (7, 11), (3, 3)):
        for cell in range(m * n):
            name = play.cell_name(cell, m, n)
            assert play.cell_from_name(name, m, n) == cell, (name, cell)
    assert play.cell_from_name('z1', 3, 3) is None
    assert play.cell_from_name('a99', 3, 3) is None
    assert play.cell_from_name('', 3, 3) is None
    # OFF THE BOARD IN EITHER NUMBER, and nonsense in either position.
    assert play.cell_from_name('4,1', 3, 3) is None
    assert play.cell_from_name('1,4', 3, 3) is None
    assert play.cell_from_name('0,1', 3, 3) is None
    assert play.cell_from_name('x,1', 3, 3) is None
    assert play.cell_from_name('1,x', 3, 3) is None
    # The letter form still names the same cells it did.
    for m, n in ((19, 19), (7, 11)):
        for cell in range(m * n):
            row, col = divmod(cell, n)
            if col < 26:
                legacy = '{0}{1}'.format(chr(ord('a') + col), m - row)
                assert play.cell_from_name(legacy, m, n) == cell


def test_a_version_one_save_still_loads():
    """A reviewer has v1 saves. Breaking them to tidy the format would
    be a worse trade than reading two."""
    old = '\n'.join([play.SAVE_HEADER, 'Board: 5x5 k=4', 'Style: go',
                     'Moves: 12 6 13', 'Position:', '.....'])
    loaded = play.load_text(old)
    assert loaded is not None
    assert loaded['moves'] == [12, 6, 13]
    assert loaded['m'] == 5 and loaded['k'] == 4


def test_a_version_two_save_round_trips():
    game, played = play.replay_moves(9, 9, 5, [40, 30, 41, 31])
    text = play.save_text(game, 9, 9, 5, 'squares', played,
                          {play.FIRST: 'td', play.SECOND: 'human'})
    loaded = play.load_text(text)
    assert loaded['moves'] == played
    assert loaded['m'] == 9 and loaded['n'] == 9 and loaded['k'] == 5
    assert loaded['style'] == 'squares'
    assert loaded['sides'][play.FIRST] == 'td'


def test_undo_works_on_a_loaded_game():
    """LOADING USED TO JUMP TO THE FINAL POSITION WITH AN EMPTY
    HISTORY, so undo did nothing on a loaded game -- which is exactly
    when a reviewer wants to step back through it. The moves are
    replayed one at a time so the history exists."""
    from lgref import clipboard

    game, played = play.replay_moves(5, 5, 4, [12, 6, 13, 7])
    text = play.save_text(game, 5, 5, 4, 'squares', played,
                          {play.FIRST: 'human', play.SECOND: 'td'})

    def check(api):
        original = clipboard.read_text
        clipboard.read_text = lambda: text
        try:
            api['rebuild'](log_status=False)
            assert api['paste_game']() is True
            loaded = len(api['played'])
            depth = len(api['history'])
            steps = 0
            while api['undo']():
                steps += 1
            return loaded, depth, steps, len(api['played'])
        finally:
            clipboard.read_text = original

    loaded, depth, steps, left = drive(check, m=5, n=5, k=4)
    assert loaded == 4, loaded
    assert depth == 4, (
        'the history is empty after loading, so undo does nothing')
    assert steps > 0 and left == 0, (steps, left)


def test_a_game_can_be_loaded_from_the_setup_screen():
    """A saved game names its own board, so loading had to wait until a
    board was chosen and Start pressed -- which meant choosing the board
    twice."""
    import inspect

    def check(api):
        return 'load' in api['hits'], 'load' in api

    has_button, has_action = drive(check)
    assert has_button, 'no Load control on the setup card'
    assert has_action
    source = inspect.getsource(play.play_window)
    assert 'def load_into' in source
    assert 'pygame.K_v' in source


# ---- the reviewer's second list -------------------------------------

def test_restart_and_setup_ask_before_discarding_a_game():
    """BOTH THROW THE GAME AWAY and both sat one click from Undo on a
    row of six identical buttons. Undo cannot recover from them: the
    move list is gone, not stepped back.

    The first click arms, the second acts. Arming is also VISIBLE on
    the button -- a confirmation that lives only in the message line
    is one a reviewer answers by clicking the same place twice without
    reading it.
    """
    def check(api):
        api['rebuild'](log_status=False)
        api['state']['screen'] = 'play'
        api['resize']()
        api['commit'](0)
        api['commit'](1)
        before = list(api['played'])

        first = api['guard']('restart', api['restart'])
        armed = api['state']['confirm']
        still_there = list(api['played'])
        labels_while_armed = [
            name for name, _rect in api['draw']()]
        second = api['guard']('restart', api['restart'])
        after = list(api['played'])
        return (first, armed, still_there, before, after,
                api['state']['confirm'], labels_while_armed)

    (first, armed, still_there, before, after, cleared,
     labels) = drive(check)
    assert first is None, 'the first click acted instead of asking'
    assert armed == 'restart'
    assert still_there == before, 'the game was discarded by the ask'
    assert after == [], 'the second click did not restart'
    assert cleared is None, 'the confirmation stayed armed afterwards'
    assert 'restart' in labels


def test_the_ask_is_skipped_when_there_is_nothing_to_lose():
    """An empty board is nothing to protect, and a confirmation that
    fires when nothing is at stake teaches the reviewer to click
    through it."""
    def check(api):
        api['rebuild'](log_status=False)
        api['state']['screen'] = 'play'
        api['resize']()
        empty = api['needs_confirm']()
        straight_through = api['guard']('restart', lambda: 'acted')
        api['commit'](0)
        mid_game = api['needs_confirm']()
        return empty, straight_through, mid_game

    empty, straight_through, mid_game = drive(check)
    assert empty is False
    assert straight_through == 'acted', 'it asked about an empty board'
    assert mid_game is True


def test_arming_one_button_disarms_the_other():
    """A mis-click on the neighbour cancels rather than confirming --
    the two sit next to each other and both discard the game."""
    def check(api):
        api['rebuild'](log_status=False)
        api['state']['screen'] = 'play'
        api['resize']()
        api['commit'](0)
        api['guard']('restart', api['restart'])
        api['guard']('setup', lambda: 'went to setup')
        return api['state']['confirm'], list(api['played'])

    confirm, played = drive(check)
    assert confirm == 'setup', 'the second button did not take the ask'
    assert played == [0], 'the game was discarded without confirmation'


def test_a_move_answers_a_pending_ask_with_no():
    def check(api):
        api['rebuild'](log_status=False)
        api['state']['screen'] = 'play'
        api['resize']()
        api['commit'](0)
        api['guard']('restart', api['restart'])
        api['state']['confirm'] = None  # what a board click does
        return api['guard']('restart', api['restart'])

    assert drive(check) is None, (
        'a move left the restart armed, so the next click would wipe '
        'the game')


def test_the_transient_message_does_not_sit_on_the_move_text():
    """COPYING A GAME REPLACED "O played 10,10 (optimal)" with "copied
    the game to the clipboard" -- the one line a reviewer was reading,
    overwritten by an acknowledgement they already had.

    Two slots, and the acknowledgement is BELOW the button row.
    """
    def check(api):
        api['rebuild'](log_status=False)
        api['state']['screen'] = 'play'
        api['resize']()
        api['state']['note'] = 'O played 10,10  (optimal)'
        api['copy_game']()
        hits = api['draw']()
        buttons = max(rect.bottom for _name, rect in hits)
        return (api['state']['note'], api['state'].get('flash'), buttons,
                pygame.display.get_surface().get_height())

    note, flash, buttons, height = drive(check)
    assert note == 'O played 10,10  (optimal)', (
        'the acknowledgement overwrote the move text')
    assert flash, 'nothing acknowledged the copy'
    assert buttons < height


def test_the_message_line_and_the_legend_fit_under_the_buttons():
    """The panel grew by a line; a panel sized for the old one clips
    whichever of the two is last."""
    import inspect

    source = inspect.getsource(play.play_window)
    panel = int(source.split('PANEL = ')[1].split('\n')[0])
    # The two lines are drawn at top+120 and top+142; the legend's own
    # glyphs are 12px, so the panel must clear 142 + 12.
    assert "top + 120" in source, 'the message line moved'
    assert "top + 142" in source, 'the legend moved'
    assert panel >= 142 + 14 + 4, (
        'the panel is {0}px and the legend is drawn at 142'.format(panel))


def test_the_board_is_labelled_with_the_coordinates_the_save_uses():
    """A coordinate in the save is only useful if the board shows the
    same numbers. Drawn INSIDE the playing area, because a margin would
    move every cell -- and every cell's position is also its hit-test.
    """
    def check(api):
        api['rebuild'](log_status=False)
        api['state']['screen'] = 'play'
        cell, _surface, _w, _h = api['resize']()
        api['draw']()
        # The top-left cell is index 0 and must still be AT the origin.
        return cell

    cell = drive(check, m=5, n=5, k=4)
    assert cell >= 20, 'the test board is too small to label'

    import inspect
    source = inspect.getsource(play.play_window)
    assert 'draw_coordinates' in source
    # Column numbers are 1-based and rows count from the bottom, which
    # is what `cell_name` says; the labels must not invent their own.
    assert 'str(rows - row)' in source, 'the row labels do not count from the bottom'
    assert 'str(col + 1)' in source, 'the column labels are not 1-based'


def test_full_screen_sets_the_mode_once_and_ignores_the_resize_it_causes():
    """THE FLICKER. `set_mode` makes the driver report a resize; the
    resize recomputed the board and called `set_mode` again. That cycle
    ran until it happened to settle on entering full screen, and ran
    again every time the window was MOVED -- a move reports a resize
    too, even though nothing resized.
    """
    def check(api):
        api['rebuild'](log_status=False)
        api['state']['screen'] = 'play'
        api['resize']()
        calls = []
        real = pygame.display.set_mode

        def counted(size, flags=0, *rest):
            calls.append((size, flags))
            return real(size, flags, *rest)

        pygame.display.set_mode = counted
        try:
            api['state']['fullscreen'] = True
            api['resize']()
            entered = len(calls)
            # The driver now reports the resize its own mode change
            # caused, twice, as a window manager does.
            api['fit_to']((1280, 800))
            api['fit_to']((1280, 800))
            after_resizes = len(calls)
            # And a WINDOWED move: same size, reported again.
            api['state']['fullscreen'] = False
            api['state']['mode'] = None
            api['resize']()
            back = len(calls)
            api['fit_to'](pygame.display.get_surface().get_size())
            api['fit_to'](pygame.display.get_surface().get_size())
            moved = len(calls)
        finally:
            pygame.display.set_mode = real
        return entered, after_resizes, back, moved

    entered, after_resizes, back, moved = drive(check)
    assert entered == 1, 'entering full screen set the mode {0} times'.format(
        entered)
    assert after_resizes == entered, (
        'the resize that full screen caused set the mode again -- that '
        'is the flicker')
    assert back == entered + 1, 'leaving full screen did not restore the window'
    assert moved == back, (
        'a resize event reporting the SAME size set the mode again, which '
        'is the flicker on a window move')


def test_loading_a_game_restores_the_settings_it_was_played_with():
    """The depth and the per-move clock come back with the moves. The
    TRAINING parameters do not: applying them would let a pasted file
    start a three-minute retrain with nothing asking first."""
    game, played = play.replay_moves(4, 4, 3, [5, 6])
    text = play.save_text(
        game, 4, 4, 3, 'squares', played,
        {play.FIRST: 'human', play.SECOND: 'td'},
        {'depth': 5, 'budget': 0,
         'training': 'rounds=99 games=999 seed=4242 td_leaf=yes budget=9s'})

    def check(api):
        api['rebuild'](log_status=False)
        api['state']['screen'] = 'play'
        api['resize']()
        api['state']['depth'] = 2
        api['state']['budget'] = 7
        play.clipboard.copy_text(text)
        if not api['paste_game']():
            return None
        return (api['state']['depth'], api['state']['budget'],
                api['state'].get('flash', ''), list(api['played']))

    got = drive(check)
    if got is None:
        pytest.skip('no clipboard in this environment')
    depth, budget, flash, moves = got
    assert depth == 5, 'the depth was not restored'
    assert budget == 0, 'the per-move clock was not restored'
    assert moves == [5, 6]
    assert '4242' in flash, (
        'the save was trained with different parameters and the window '
        'did not say so: {0!r}'.format(flash))


def test_a_budget_of_zero_means_no_clock_rather_than_no_search():
    """Zero seconds would stop the search before its first iteration if
    it were passed through as a number of seconds. It is the setting
    that REMOVES the clock, so the depth is exactly the depth -- the
    answer to why the depth was different every move."""
    import inspect

    source = inspect.getsource(play.play_window)
    assert "float(state['budget']) or float('inf')" in source, (
        'a budget of zero is passed to the searcher as zero seconds')
    assert "'no time limit'" in source, (
        'the panel does not say that the clock is off')
    assert "exactly" in source, (
        'the panel does not distinguish a fixed depth from a ceiling')


def test_the_key_legend_uses_characters_the_font_can_draw():
    """The legend named the step keys with the arrow characters, and
    they came out as empty boxes: the system font this falls back to
    has no glyph for them. A legend that names a key with a character
    the reader cannot see is worse than no legend, and nothing in a
    layout test could catch it -- the box has the same metrics as a
    letter.

    Checked as a rule rather than an instance: the panel's text is
    ASCII.
    """
    import inspect

    source = inspect.getsource(play.play_window)
    legend = source.split("'S setup", 1)[1].split('PALETTE', 1)[0]
    for char in legend:
        assert ord(char) < 128, (
            'the key legend uses {0!r}, which the fallback font may '
            'have no glyph for'.format(char))
