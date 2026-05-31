"""Smoke tests for the parallel self-play implementation in trainer.py.

These tests don't run a full training iteration (that takes ~30
minutes); they verify the parallel-self-play building blocks work:

- `_play_one_game_worker` can be called as a top-level function
  and produces the same (states, outcomes, info) shape that
  `play_training_game` does.
- The training_loop accepts the new `n_workers` parameter and
  defaults to 1 (sequential, unchanged behavior).
- multiprocessing.Pool can spawn workers that call the worker
  function and get back results.

For full end-to-end test we'd need to run a complete iteration
which is too slow; the smoke checks above are sufficient to catch
the most likely regressions (signature drift, pickle errors,
import errors in worker processes).
"""

import os
import sys
import multiprocessing
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Skip heavy torch+game imports at module load — only inside tests so
# pytest collection stays fast.


def test_play_one_game_worker_is_top_level():
    """Worker function must be importable as a top-level symbol so
    it's picklable (multiprocessing.Pool requirement)."""
    import trainer
    assert hasattr(trainer, '_play_one_game_worker')
    assert callable(trainer._play_one_game_worker)


def test_training_loop_accepts_n_workers_param():
    """The new --workers CLI flag is forwarded to training_loop via
    the n_workers keyword. Default is 1 (sequential)."""
    import trainer
    import inspect
    sig = inspect.signature(trainer.training_loop)
    assert 'n_workers' in sig.parameters
    assert sig.parameters['n_workers'].default == 1


def test_play_one_game_worker_signature():
    """Worker takes a single tuple arg (so Pool.map / imap_unordered
    can dispatch them one-per-iter)."""
    import trainer
    import inspect
    sig = inspect.signature(trainer._play_one_game_worker)
    params = list(sig.parameters.keys())
    assert len(params) == 1
    assert params[0] == 'args'


def test_play_one_game_worker_runs_a_full_game():
    """End-to-end: build a small network, run ONE game via the worker
    function, check returned shape."""
    import trainer
    import torch
    # Tiny network so the test is fast.
    net = trainer.ValueNetwork(
        conv_channels=8, num_res_blocks=1, fc_size=16)
    state_dict = net.state_dict()
    model_config = {
        'conv_channels': 8,
        'num_res_blocks': 1,
        'fc_size': 16,
    }
    args = (state_dict, model_config, 60, 0.5, 'freeze', 12345)
    states, outcomes, info = trainer._play_one_game_worker(args)
    assert isinstance(states, list)
    assert isinstance(outcomes, list)
    assert isinstance(info, dict)
    assert 'winner' in info
    assert 'total_turns' in info
    assert info['total_turns'] > 0


def test_play_one_game_worker_via_multiprocessing_pool():
    """The actual multiprocessing path — spawn one worker via
    Pool, run one game, get the result back. Verifies pickling +
    spawn-context safety.

    Uses tiny network to keep this fast (<10s)."""
    import trainer
    net = trainer.ValueNetwork(
        conv_channels=8, num_res_blocks=1, fc_size=16)
    state_dict = net.state_dict()
    model_config = {
        'conv_channels': 8,
        'num_res_blocks': 1,
        'fc_size': 16,
    }
    args = (state_dict, model_config, 60, 0.5, 'freeze', 999)
    ctx = multiprocessing.get_context('spawn')
    with ctx.Pool(1) as pool:
        result = pool.apply(trainer._play_one_game_worker, (args,))
    states, outcomes, info = result
    assert isinstance(states, list)
    assert isinstance(info, dict)
    assert info['total_turns'] > 0
