"""Never exhaust the machine's memory: a guard for heavy jobs (#419).

WHY. On 2026-11-27 the Claude desktop app reached 395 GB and macOS ran
out of application memory, with all of these running at once:
- two training runs;
- a race;
- four version-table workers;
- three or four full test suites;
- several background agents.
Each job alone was fine; together they were not. This tool makes the
limit a check instead of a habit.

TWO MODES.

    python3 tools/memguard.py run [--max-jobs 3] [--min-free-gb 6] -- CMD...

waits until fewer than `--max-jobs` heavy jobs are running AND at least
`--min-free-gb` of memory is available, then runs CMD. Every heavy job
(suites, training, races, table workers) is started through it.

    python3 tools/memguard.py watch [--critical-gb 2] [--max-swap-gb 8]

checks every 30 seconds. When available memory falls below
`--critical-gb`, or swap in use passes `--max-swap-gb`, it sends SIGTERM
to the NEWEST heavy research job, one at a time, and logs what it
stopped and the command to resume it. Our long jobs save per game or
per round, so a SIGTERM loses at most the item in progress. It never
touches the user's own programs (the game window, editors), only Python
processes running this repository's research code.

    python3 tools/memguard.py status

prints available memory, swap and the heavy jobs.

"Heavy" means a Python process using more than `--heavy-mb` (default
300 MB) of resident memory, or running pytest, training or a race.
"""

import argparse
import os
import re
import signal
import subprocess  # nosec B404
import sys
import time

#: Command fragments that mark a research job as heavy whatever its size.
HEAVY_MARKERS = ('pytest', 'train_royal_chess', 'race_agents', 'race_trace',
                 'versions play', 'phase_race', 'te_bench', 'bootstrap')
#: Never stopped: the user's own programs.
PROTECTED_MARKERS = ('src/main.py', 'main_v0.py', 'main_v1.py',
                     'play_mnk', 'Visual Studio', 'Code Helper', 'Claude')


def _run(args):
    return subprocess.run(args, capture_output=True, text=True,  # nosec B603
                          check=False).stdout


def available_gb(vm_stat_text=None):
    """Free + inactive + speculative memory, in GB, from `vm_stat`."""
    text = vm_stat_text if vm_stat_text is not None else _run(['vm_stat'])
    size = re.search(r'page size of (\d+) bytes', text)
    page = int(size.group(1)) if size else 16384
    total = 0
    for name in ('Pages free', 'Pages inactive', 'Pages speculative'):
        found = re.search(name + r':\s+(\d+)', text)
        if found:
            total += int(found.group(1))
    return total * page / 1024 ** 3


def swap_used_gb(swap_text=None):
    """Swap in use, in GB, from `sysctl vm.swapusage`."""
    text = (swap_text if swap_text is not None
            else _run(['sysctl', 'vm.swapusage']))
    found = re.search(r'used = ([\d.]+)([MG])', text)
    if not found:
        return 0.0
    amount = float(found.group(1))
    return amount / 1024 if found.group(2) == 'M' else amount


def processes(ps_text=None):
    """`[(pid, ppid, rss_mb, elapsed_s, command)]` for every process."""
    text = (ps_text if ps_text is not None
            else _run(['ps', '-axo', 'pid=,ppid=,rss=,etime=,command=']))
    out = []
    for line in text.splitlines():
        parts = line.split(None, 4)
        if len(parts) < 5 or not parts[0].isdigit():
            continue
        out.append((int(parts[0]), int(parts[1]), int(parts[2]) / 1024.0,
                    _seconds(parts[3]), parts[4]))
    return out


def _seconds(etime):
    """ps etime ([[dd-]hh:]mm:ss) in seconds."""
    days, _, rest = etime.rpartition('-')
    fields = [int(x) for x in rest.split(':')]
    while len(fields) < 3:
        fields.insert(0, 0)
    hours, minutes, seconds = fields
    return ((int(days) if days else 0) * 86400 + hours * 3600
            + minutes * 60 + seconds)


def heavy_jobs(procs, heavy_mb=300.0, me=None):
    """The heavy research jobs among `procs`, newest first.

    ONE JOB, ONE ENTRY: a heavy process whose parent is itself a heavy
    job (a match's worker, a suite's subprocess) is part of that job and
    is not counted again. Counting each worker separately made one match
    look like three jobs, and a suite waiting behind it never started.
    Its memory is added to the parent's.
    """
    me = os.getpid() if me is None else me
    jobs = []
    for pid, _ppid, rss, elapsed, command in procs:
        if pid == me or 'memguard' in command:
            continue
        if not re.search(r'[Pp]ython', command):
            continue
        if any(mark in command for mark in PROTECTED_MARKERS):
            continue
        if rss >= heavy_mb or any(m in command for m in HEAVY_MARKERS):
            jobs.append((pid, rss, elapsed, command))
    parent = dict((proc[0], proc[1]) for proc in procs)
    heavy = dict((job[0], job) for job in jobs)

    def root(pid):
        seen = set()
        while parent.get(pid) in heavy and pid not in seen:
            seen.add(pid)
            pid = parent[pid]
        return pid

    merged = {}
    for pid, rss, elapsed, command in jobs:
        top = root(pid)
        if top in merged:
            entry = merged[top]
            merged[top] = (entry[0], entry[1] + rss, entry[2], entry[3])
        else:
            first = heavy[top]
            merged[top] = (first[0], (rss if top == pid else first[1]
                                      + rss), first[2], first[3])
    return sorted(merged.values(), key=lambda job: job[2])


def may_start(available, jobs, max_jobs=3, min_free_gb=6.0):
    """(True, '') when a new heavy job may start, else (False, why)."""
    if len(jobs) >= max_jobs:
        return False, '{0} heavy jobs already running (limit {1})'.format(
            len(jobs), max_jobs)
    if available < min_free_gb:
        return False, '{0:.1f} GB available (need {1:.1f})'.format(
            available, min_free_gb)
    return True, ''


def must_stop(available, swap, critical_gb=2.0, max_swap_gb=8.0):
    """Why memory is critical, or '' when it is not."""
    if available < critical_gb:
        return '{0:.1f} GB available (critical below {1:.1f})'.format(
            available, critical_gb)
    if swap > max_swap_gb:
        return '{0:.1f} GB of swap in use (limit {1:.1f})'.format(
            swap, max_swap_gb)
    return ''


def _log(path, text):
    with open(path, 'a') as handle:
        handle.write(time.strftime('%Y-%m-%d %H:%M:%S ') + text + '\n')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sub = parser.add_subparsers(dest='mode', required=True)
    run = sub.add_parser('run')
    run.add_argument('--max-jobs', type=int, default=3)
    run.add_argument('--min-free-gb', type=float, default=6.0)
    run.add_argument('--heavy-mb', type=float, default=300.0)
    run.add_argument('--poll', type=float, default=30.0)
    run.add_argument('command', nargs=argparse.REMAINDER)
    watch = sub.add_parser('watch')
    watch.add_argument('--critical-gb', type=float, default=2.0)
    watch.add_argument('--max-swap-gb', type=float, default=8.0)
    watch.add_argument('--heavy-mb', type=float, default=300.0)
    watch.add_argument('--poll', type=float, default=30.0)
    watch.add_argument('--log', default=os.path.expanduser(
        '~/memguard.log'))
    sub.add_parser('status')
    args = parser.parse_args(argv)

    if args.mode == 'status':
        jobs = heavy_jobs(processes())
        print('available {0:.1f} GB, swap used {1:.1f} GB, {2} heavy '
              'jobs'.format(available_gb(), swap_used_gb(), len(jobs)))
        for pid, rss, _elapsed, command in jobs:
            print('  {0:>6} {1:>7.0f} MB  {2}'.format(pid, rss,
                                                      command[:110]))
        return 0

    if args.mode == 'run':
        command = args.command[1:] if args.command[:1] == ['--'] else \
            args.command
        if not command:
            parser.error('run needs a command after --')
        while True:
            ok, why = may_start(available_gb(),
                                heavy_jobs(processes(), args.heavy_mb),
                                args.max_jobs, args.min_free_gb)
            if ok:
                break
            print('memguard: waiting, ' + why, file=sys.stderr, flush=True)
            time.sleep(args.poll)
        return subprocess.call(command)  # nosec B603

    while True:  # watch
        why = must_stop(available_gb(), swap_used_gb(), args.critical_gb,
                        args.max_swap_gb)
        if why:
            jobs = heavy_jobs(processes(), args.heavy_mb)
            if jobs:
                pid, rss, _elapsed, command = jobs[0]
                os.kill(pid, signal.SIGTERM)
                _log(args.log, 'STOPPED {0} ({1:.0f} MB) because {2}. '
                     'To resume, rerun: {3}'.format(pid, rss, why, command))
            else:
                _log(args.log, 'memory critical ({0}) but no heavy research '
                     'job to stop'.format(why))
        time.sleep(args.poll)


if __name__ == '__main__':
    sys.exit(main())
