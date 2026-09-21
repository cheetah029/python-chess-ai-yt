"""Cost accounting — core-hours and dollars, printed at the end of every run.

Project rule: cost logging from day one. The Phase 0 audit found this
workload is CPU-bound (Apple MPS measured at 21.0 vs 21.6 plies/s on CPU
— no GPU benefit), so the unit that matters is the CORE-hour, not the
GPU-hour. A tracker that reported GPU-hours here would report ~0 for a
sweep that actually costs days.

Wall-clock alone understates cost on a parallel run and overstates it on
an idle one, so `CostTracker` records both wall-clock and core-hours
(wall-clock x worker count), and converts to dollars via an explicit,
recorded rate. The rate is a stated assumption, never a hidden constant:
it is written into the manifest so a later reader can re-price a run
without re-running it.
"""

import time


# Reference rates in USD per core-hour. These are ASSUMPTIONS recorded
# with each run, not measurements. `local` is 0.0 because hardware
# already owned has no marginal dollar cost — the real cost of a local
# run is the wall-clock the machine is unavailable, which is tracked
# separately.
RATE_USD_PER_CORE_HOUR = {
    'local': 0.0,
    'kaggle': 0.0,          # free tier, ~4 vCPU/session, ~9h session cap
    'colab': 0.0,           # free tier, ~2 vCPU
    'cloud_spot': 0.03,     # order-of-magnitude spot vCPU
    'cloud_ondemand': 0.05,
}


class CostTracker:
    """Accumulate wall-clock and core-hours for one run.

    `n_workers` is the parallelism the run actually used, which is what
    turns wall-clock into core-hours. Phase 0 measured only 2.3x
    aggregate speedup from 8 workers on this workload, so core-hours
    deliberately charge for every worker occupied rather than for
    useful work done — that is the honest number when deciding whether
    a sweep fits a budget.
    """

    def __init__(self, n_workers=1, venue='local', rate_usd_per_core_hour=None):
        self.n_workers = max(1, int(n_workers))
        self.venue = venue
        if rate_usd_per_core_hour is None:
            rate_usd_per_core_hour = RATE_USD_PER_CORE_HOUR.get(venue, 0.0)
        self.rate = float(rate_usd_per_core_hour)
        self._start = None
        self._elapsed = 0.0
        self.units = 0          # domain units processed (e.g. games)
        self.unit_name = 'unit'

    # ---- timing ---------------------------------------------------------

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *exc):
        self.stop()
        return False

    def start(self):
        if self._start is None:
            self._start = time.monotonic()
        return self

    def stop(self):
        if self._start is not None:
            self._elapsed += time.monotonic() - self._start
            self._start = None
        return self

    def add_units(self, n=1, unit_name=None):
        self.units += n
        if unit_name:
            self.unit_name = unit_name
        return self

    # ---- derived figures ------------------------------------------------

    @property
    def wall_clock_s(self):
        running = (time.monotonic() - self._start) if self._start else 0.0
        return self._elapsed + running

    @property
    def core_hours(self):
        return self.wall_clock_s * self.n_workers / 3600.0

    @property
    def usd(self):
        return self.core_hours * self.rate

    @property
    def seconds_per_unit(self):
        return (self.wall_clock_s / self.units) if self.units else None

    @property
    def core_seconds_per_unit(self):
        if not self.units:
            return None
        return self.wall_clock_s * self.n_workers / self.units

    # ---- reporting ------------------------------------------------------

    def as_dict(self):
        return {
            'venue': self.venue,
            'n_workers': self.n_workers,
            'rate_usd_per_core_hour': self.rate,
            'wall_clock_s': round(self.wall_clock_s, 3),
            'core_hours': round(self.core_hours, 4),
            'usd': round(self.usd, 4),
            'units': self.units,
            'unit_name': self.unit_name,
            'seconds_per_unit': self.seconds_per_unit,
            'core_seconds_per_unit': self.core_seconds_per_unit,
        }

    def project(self, total_units):
        """Extrapolate this run's measured rate to `total_units`.

        Used by the Phase 3 pilot to report a projected sweep cost —
        and, when it overruns, to say so before the sweep starts rather
        than after.
        """
        per = self.core_seconds_per_unit
        if per is None:
            return None
        core_h = per * total_units / 3600.0
        return {
            'total_units': total_units,
            'core_hours': round(core_h, 2),
            'usd': round(core_h * self.rate, 2),
            'wall_hours_at_current_parallelism':
                round(core_h / self.n_workers, 2),
        }

    def format_report(self, title='cost'):
        d = self.as_dict()
        lines = [
            '',
            '=' * 58,
            f'{title}: {d["wall_clock_s"]:.1f}s wall, '
            f'{d["core_hours"]:.3f} core-h, ${d["usd"]:.4f} '
            f'({d["venue"]}, {d["n_workers"]} workers)',
        ]
        if d['units']:
            lines.append(
                f'  {d["units"]} {d["unit_name"]}: '
                f'{d["seconds_per_unit"]:.2f}s each, '
                f'{d["core_seconds_per_unit"]:.2f} core-s each')
        lines.append('=' * 58)
        return '\n'.join(lines)

    def print_report(self, title='cost'):
        print(self.format_report(title))
        return self
