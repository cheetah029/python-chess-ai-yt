"""Nothing in either window may be slow except the computer thinking.

THE STANDING REQUIREMENT, in the reviewer's words: "make sure there is
no lag in any part of both GUIs whatsoever except for only when the
computer is thinking."

Every number here was a real complaint before it was a test:

  - loading a board took 10.4 seconds, because the agent's opening
    prior was estimated by playing 400 random games. The same quantity
    is read exactly from the win condition in 0.01s.
  - jumping to the start of a game took 38ms at 60 plies and 77ms at
    120, because each step rebuilt the whole board from its snapshot.
  - dragging a piece stuttered at 54ms because the thinking thread
    starved the UI.

THE BUDGETS ARE DELIBERATELY LOOSE. A test that asserts a tight time on
a shared machine fails for reasons that have nothing to do with the
code, and a flaky guard gets deleted. These are set where a PERSON
notices -- about 100ms for an action, a second for opening a board --
so they catch a regression of the kind that was actually reported, not
a slow afternoon.
"""

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

import pygame

pygame.init()
pygame.font.init()

#: What a person notices. Not what the machine can do.
INSTANT = 0.15
OPENING_A_BOARD = 2.0


def elapsed(action):
    started = time.time()
    result = action()
    return result, time.time() - started


# ---- m,n,k ----------------------------------------------------------

def test_the_opening_prior_is_read_not_sampled():
    """10.4 SECONDS ON 19x19, and the reviewer felt every one of them.
    The prior is now read from the win condition, which is both exact
    and free; sampling it was noise at that size anyway."""
    import lgref.play_mnk as play

    play._PRIORS.clear()
    for board in ((9, 9, 5), (19, 19, 5), (20, 20, 5)):
        play._PRIORS.clear()
        _prior, cost = elapsed(lambda b=board: play.opening_prior(*b))
        assert cost < INSTANT, (
            'building the opening prior for {0} took {1:.2f}s'.format(
                board, cost))


def test_the_prior_names_the_exact_centre_on_every_board():
    """The reviewer: "it played 13,12 on the first move". A sampled
    prior could not do better -- on 19x19 its error bar (0.038) was
    wider than the spread across its top ten cells (0.033)."""
    import lgref.play_mnk as play

    for m, n, k in ((9, 9, 5), (19, 19, 5), (13, 13, 5)):
        play._PRIORS.clear()
        prior = play.opening_prior(m, n, k)
        best = max(prior, key=prior.get)
        row, col = divmod(best, n)
        assert (m - row, col + 1) == ((m + 1) // 2, (n + 1) // 2), (
            '{0}x{1}: prior favours {2},{3}'.format(
                m, n, m - row, col + 1))


def test_starting_a_game_is_not_slow_even_on_the_largest_board():
    import lgref.play_mnk as play

    brain = play.Brain(rounds=1, games=2, seed=1, use_td_leaf=False,
                       depth=2, budget=1.0)
    taken = {}

    def probe(api):
        started = time.time()
        api['rebuild'](log_status=False)
        api['state']['screen'] = 'play'
        api['resize']()
        taken['start'] = time.time() - started
        return True

    play.play_window(19, 19, 5, brain, 2,
                     {play.FIRST: 'human', play.SECOND: 'human'},
                     probe=probe)
    assert taken['start'] < OPENING_A_BOARD, (
        'opening a 19x19 board took {0:.2f}s'.format(taken['start']))


def test_every_window_action_is_instant():
    """Undo, redo, jumping to either end, copying, flipping a setting
    -- none of these thinks, so none of them may take time."""
    import lgref.play_mnk as play

    brain = play.Brain(rounds=1, games=2, seed=1, use_td_leaf=False,
                       depth=2, budget=1.0)
    slow = {}

    def probe(api):
        api['rebuild'](log_status=False)
        api['state']['screen'] = 'play'
        api['resize']()
        for move in range(0, 60, 2):
            api['commit'](move)
        checks = (
            ('undo', api['undo']),
            ('redo', api['redo']),
            ('jump to start', lambda: [None for _ in iter(
                lambda: api['undo'](), False)]),
            ('jump to end', lambda: [None for _ in iter(
                lambda: api['redo'](), False)]),
            ('copy', api['copy_game']),
            ('draw', api['draw']),
            ('restart', api['restart']),
        )
        for name, action in checks:
            _result, cost = elapsed(action)
            if cost > INSTANT:
                slow[name] = cost
        return True

    play.play_window(19, 19, 5, brain, 2,
                     {play.FIRST: 'human', play.SECOND: 'human'},
                     probe=probe)
    assert not slow, 'these window actions were not instant: {0}'.format(
        slow)


# ---- the case study --------------------------------------------------

def test_the_case_study_window_opens_instantly():
    from game import Game

    _game, cost = elapsed(Game)
    assert cost < OPENING_A_BOARD, (
        'building the game took {0:.2f}s'.format(cost))


def test_jumping_through_a_long_game_is_instant():
    """38ms at 60 plies and 77ms at 120 before the jump stopped
    rebuilding every position it passed through."""
    from game import Game

    game = Game()
    for _ply in range(200):
        game._history.append(game._snapshot())

    _ok, back = elapsed(game.jump_to_start)
    _ok2, forward = elapsed(game.jump_to_end)
    assert back < INSTANT, 'jump to start took {0:.3f}s'.format(back)
    assert forward < INSTANT, 'jump to end took {0:.3f}s'.format(forward)


def test_a_single_step_is_instant_too():
    from game import Game

    game = Game()
    for _ply in range(120):
        game._history.append(game._snapshot())
    _ok, cost = elapsed(game.undo)
    assert cost < INSTANT, 'one undo took {0:.3f}s'.format(cost)


def test_the_board_does_not_think_while_the_agent_does():
    """The only permitted slowness is the computer's turn, and while it
    is thinking the board must be LOCKED rather than merely slow -- a
    reviewer was able to drag the computer's pieces during its move."""
    from game import Game

    game = Game()
    assert hasattr(game, 'is_board_input_locked')


def test_the_tie_break_does_not_slow_the_search_down():
    """A 20x SLOWDOWN THAT BROKE THE THING IT WAS FIXING.

    `threat_count` is the general instrument and it clones the game
    once per legal move, so ranking one candidate on a 19x19 board cost
    0.108s and a full root sweep 9.74s against 0.47s without it. The
    window's five-second budget then could not finish even depth 1 --
    143 of 361 root moves -- so the agent played the best of an
    arbitrary partial set and stopped opening in the centre. The fix
    for the opening was breaking the opening.

    The threat level is now skipped when no move can change it, which
    the win condition decides: a move creates an immediate win only by
    taking a configuration from k-2 to k-1.
    """
    import lgref.play_mnk as play
    from lgref.experiments.mnk import MNK
    from lgref.experiments.search import Searcher

    brain = play.Brain(rounds=1, games=2, seed=1, use_td_leaf=False,
                       depth=2, budget=1.0)
    evaluate = brain.evaluation(19, 19, 5)
    game = MNK(m=19, n=19, k=5)
    turns = game.get_all_legal_turns()
    prior = play.opening_prior(19, 19, 5)

    def sweep(tie_break):
        searcher = Searcher(evaluate, max_depth=1, budget=60.0,
                            quiescence=0, use_tt=False,
                            tie_break=tie_break)
        started = time.time()
        searcher.choose_turn(turns, game)
        return time.time() - started

    plain = sweep(None)
    tilted = sweep(play.tie_breaker(game, prior))
    assert tilted < plain * 2.0 + 0.5, (
        'the tie-break costs {0:.2f}s against {1:.2f}s without it'
        .format(tilted, plain))


def test_the_agent_still_reaches_a_real_depth_on_the_largest_board():
    """depth_reached was 1 on 19x19 with 143 nodes searched of 361
    legal moves. A search that cannot finish one ply is not choosing
    among the moves -- it is choosing among whichever ones the clock
    allowed."""
    import lgref.play_mnk as play
    from lgref.experiments.mnk import MNK
    from lgref.experiments.search import Searcher

    brain = play.Brain(rounds=1, games=2, seed=1, use_td_leaf=False,
                       depth=2, budget=1.0)
    evaluate = brain.evaluation(19, 19, 5)
    game = MNK(m=19, n=19, k=5)
    searcher = Searcher(evaluate, max_depth=3, budget=5.0,
                        quiescence=0, use_tt=False,
                        tie_break=play.tie_breaker(
                            game, play.opening_prior(19, 19, 5)))
    searcher.choose_turn(game.get_all_legal_turns(), game)
    assert searcher.depth_reached >= 2, (
        'only reached depth {0} on a 19x19 board'.format(
            searcher.depth_reached))
    assert searcher.nodes > 361, (
        'searched {0} nodes for 361 legal moves -- not even one '
        'complete ply'.format(searcher.nodes))


def test_the_agent_opens_in_the_centre_at_the_depth_it_plays():
    """The reviewer's report, as a test, AT THE DEPTH THE WINDOW USES.
    A previous version passed this at depth 1 and failed in the window,
    because the window searches deeper and the slowdown only bit
    there."""
    import lgref.play_mnk as play
    from lgref.experiments.mnk import MNK
    from lgref.experiments.search import Searcher

    brain = play.Brain(rounds=1, games=2, seed=1, use_td_leaf=False,
                       depth=2, budget=1.0)
    evaluate = brain.evaluation(19, 19, 5)
    game = MNK(m=19, n=19, k=5)
    searcher = Searcher(evaluate, max_depth=3, budget=5.0,
                        quiescence=0, use_tt=False,
                        tie_break=play.tie_breaker(
                            game, play.opening_prior(19, 19, 5)))
    chosen = searcher.choose_turn(game.get_all_legal_turns(), game)
    row, col = divmod(chosen, 19)
    assert (19 - row, col + 1) == (10, 10), (
        'opened at {0},{1}'.format(19 - row, col + 1))


def test_the_cheap_threat_path_agrees_with_the_full_one():
    """THE SHORTCUT MUST NOT CHANGE A RANKING, only its cost. Where a
    move CAN change the threat count the full computation still runs;
    the skip applies only where it provably cannot."""
    import lgref.play_mnk as play
    from lgref.experiments.mnk import MNK
    from lgref.experiments.validate import threat_count

    # A position where threats are live: one side is two from a line.
    game = MNK(m=5, n=5, k=4)
    for cell in (0, 20, 1, 21):
        game.execute_turn(cell)
    prior = play.opening_prior(5, 5, 4)
    rank = play.tie_breaker(game, prior)

    me = game.current_player
    probe = game.copy()
    probe.execute_turn(game.get_all_legal_turns()[0])
    opponent = probe.current_player
    was_mine = threat_count(game, me)
    was_theirs = threat_count(game, opponent)
    for turn in game.get_all_legal_turns():
        after = game.copy()
        after.execute_turn(turn)
        expected = (threat_count(after, me) > was_mine
                    or threat_count(after, opponent) < was_theirs
                    or (after.is_game_over()
                        and getattr(after, 'winner', None) == me))
        assert rank(turn)[0] == (1 if expected else 0), (
            'the cheap path disagrees about {0}'.format(turn))


def test_futility_pruning_is_off_where_its_premise_is_false():
    """THE MATE-IN-ONE BLUNDER. Futility pruning assumes a quiet move
    cannot change the score, so a position far enough below alpha may
    skip its quiet moves. That premise holds where the score is
    material and only captures move it. IT IS FALSE WHERE PLACING A
    STONE IS THE ONLY THING THAT HAPPENS.

    m,n,k turns are plain integers with no `is_capture`, so EVERY move
    counted as quiet and was eligible. Measured on the reviewer's
    position, with the opponent one move from five in a row: the guard
    pruned 305 moves INCLUDING THE BLOCK, and the agent played
    elsewhere and lost. Detected now, the way undo support is.
    """
    from lgref.experiments.mnk import MNK
    from lgref.experiments.search import Searcher, has_tactical_turns
    from experiments.variants import make_engine

    flat = MNK(m=5, n=5, k=4)
    assert has_tactical_turns(flat.get_all_legal_turns()) is False
    assert has_tactical_turns(
        make_engine('full', max_turns=40).get_all_legal_turns()) is True

    searcher = Searcher(lambda state, who: 0.5, max_depth=2,
                        budget=30.0, quiescence=0, use_tt=False)
    searcher.choose_turn(flat.get_all_legal_turns(), flat)
    assert searcher.futilities == 0, (
        'futility pruned {0} moves in a game with no quiet/forcing '
        'distinction'.format(searcher.futilities))


def test_the_agent_blocks_a_mate_in_one():
    """The reviewer's game, at the move it lost: White has four in a
    row on row 11 with one completion at 11,14. Anything else loses."""
    import lgref.play_mnk as play
    from lgref.experiments.mnk import MNK
    from lgref.experiments.search import Searcher

    size = 19
    def cell(row, col):
        return (size - row) * size + (col - 1)

    game = MNK(m=size, n=size, k=5)
    for row, col in [(10, 10), (11, 10), (12, 10), (12, 11), (13, 12),
                     (11, 11), (11, 8), (10, 11), (9, 11), (11, 12),
                     (11, 9), (11, 13)]:
        game.execute_turn(cell(row, col))

    brain = play.Brain(rounds=6, games=60, seed=17, use_td_leaf=False,
                       depth=10, budget=20.0)
    evaluate = brain.evaluation(size, size, 5)
    searcher = Searcher(evaluate, max_depth=3, budget=5.0,
                        quiescence=0, use_tt=False,
                        tie_break=play.tie_breaker(
                            game, play.opening_prior(size, size, 5)))
    chosen = searcher.choose_turn(game.get_all_legal_turns(), game)
    row, col = divmod(chosen, size)
    assert (size - row, col + 1) == (11, 14), (
        'played {0},{1} instead of blocking at 11,14'.format(
            size - row, col + 1))


def test_the_extraction_is_not_rebuilt_per_winning_line():
    """1,020 `Counter` constructions per evaluation on a 19x19 board --
    seventy per cent of the extraction by the profiler. Identical
    output, five times the speed."""
    import time as clock

    from lgref.experiments.features import mnk as extract
    from lgref.experiments.mnk import MNK

    game = MNK(m=19, n=19, k=5)
    game.execute_turn(180)
    started = clock.time()
    for _ in range(40):
        extract(game)
    per_call = (clock.time() - started) / 40
    assert per_call < 0.0008, (
        'extraction takes {0:.2f} ms on a 19x19 board'.format(
            per_call * 1000))
