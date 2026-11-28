"""The memory guard (#419): hand-built cases whose answer is known."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tools'))

import memguard  # noqa: E402

VM_STAT = """Mach Virtual Memory Statistics: (page size of 16384 bytes)
Pages free:                               65536.
Pages active:                            100000.
Pages inactive:                           65536.
Pages speculative:                            0.
"""

PS = """  101 1  2048000 01:00:00 /usr/bin/python3 -m pytest -q lgref/tests
  102 1   512000    05:00 /usr/bin/python3 -u tools/train_royal_chess.py 71
  103 1  3000000 02:00:00 /usr/bin/python3 /repo/src/main.py
  104 1    10000    00:10 /usr/bin/python3 -c print(1)
  105 1  9000000 03:00:00 /Applications/Claude.app/Contents/MacOS/Claude
  106 1   600000 1-00:00:00 /usr/bin/python3 -u race_trace.py . 36 out
  107 106 700000   20:00 /usr/bin/python3 /tmp/worker.py
  108 106 400000   20:00 /usr/bin/python3 /tmp/worker.py
"""


def test_available_memory_counts_free_inactive_and_speculative():
    # (65536 + 65536) pages x 16 KiB = 2 GiB.
    assert memguard.available_gb(VM_STAT) == 2.0


def test_swap_is_read_in_megabytes_or_gigabytes():
    assert memguard.swap_used_gb(
        'vm.swapusage: total = 3072.00M  used = 1536.00M  free = 1M') == 1.5
    assert memguard.swap_used_gb('used = 9.50G') == 9.5
    assert memguard.swap_used_gb('nothing') == 0.0


def test_elapsed_time_parses_every_ps_form():
    assert memguard._seconds('00:10') == 10
    assert memguard._seconds('05:00') == 300
    assert memguard._seconds('01:00:00') == 3600
    assert memguard._seconds('1-00:00:00') == 86400


def test_heavy_jobs_are_research_python_only_newest_first():
    jobs = memguard.heavy_jobs(memguard.processes(PS), me=-1)
    pids = [job[0] for job in jobs]
    # pytest (marker, 2000 MB), training (marker), the race (marker).
    # The game window (main.py) and Claude are protected, and the tiny
    # one-off python is not heavy.
    assert pids == [102, 101, 106]
    # The race's two workers are part of the race, not two more jobs,
    # and their memory is counted with it.
    race = [job for job in jobs if job[0] == 106][0]
    assert abs(race[1] - (600000 + 700000 + 400000) / 1024.0) < 1e-6


def test_may_start_refuses_at_the_job_limit_and_on_low_memory():
    three = [(1, 500, 1, 'x')] * 3
    assert memguard.may_start(20.0, three, max_jobs=3)[0] is False
    assert memguard.may_start(20.0, three[:2], max_jobs=3) == (True, '')
    ok, why = memguard.may_start(4.0, [], max_jobs=3, min_free_gb=6.0)
    assert not ok and '4.0 GB' in why


def test_must_stop_on_low_memory_or_heavy_swap():
    assert memguard.must_stop(10.0, 1.0) == ''
    assert 'available' in memguard.must_stop(1.5, 1.0)
    assert 'swap' in memguard.must_stop(10.0, 9.0)
