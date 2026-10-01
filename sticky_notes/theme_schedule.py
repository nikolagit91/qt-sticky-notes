"""Auto theme schedule — wall-clock trigger for the live theme switch.

A single QTimer polls every minute and compares the wall clock against the
user's dark period. Deliberately a poll rather than one long timer armed for
the next boundary: Qt timers run on CLOCK_MONOTONIC, which does not advance
through suspend, so a long timer fires late after a lid-close — while a poll
that re-reads the wall clock every minute is immune to suspend, DST and manual
clock changes by construction (same reasoning as reminders.py).

State model (docs/superpowers/specs/2026-07-20-auto-theme-schedule-design.md):
the persisted MODE ("light"/"dark"/"auto") lives in app._theme_mode; the
EFFECTIVE theme keeps its historical home app._theme ("light"/"dark" only), so
the dozens of `_theme == "dark"` checks across the app stay valid. A manual
toggle while in auto mode sets app._theme_override (memory only, never on
disk); this scheduler clears it when the schedule crosses a boundary.
"""

from datetime import datetime

from PyQt6.QtCore import QTimer

_TICK_MS = 60_000   # poll cadence: theme flips within a minute of a boundary


def coerce_hhmm(value, fallback: str) -> str:
    """Normalize a persisted "HH:MM" value; anything unusable -> fallback.

    settings.json is hand-editable and value types drift between versions
    (the note_opacity lesson) — a bad value must never crash startup."""
    try:
        parts = str(value).strip().split(":")
        h, m = int(parts[0]), int(parts[1])
        if 0 <= h <= 23 and 0 <= m <= 59:
            return f"{h:02d}:{m:02d}"
    except Exception:
        pass
    return fallback


def _minutes(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def scheduled_theme(now_min: int, start_min: int, end_min: int) -> str:
    """'dark' iff now_min lies in [start_min, end_min), wrapping midnight.
    Equal start/end = empty dark period = always 'light'."""
    if start_min == end_min:
        return "light"
    if start_min < end_min:                      # same-day period, e.g. 09:00-17:00
        in_dark = start_min <= now_min < end_min
    else:                                        # wraps midnight, e.g. 20:00-07:00
        in_dark = now_min >= start_min or now_min < end_min
    return "dark" if in_dark else "light"


def scheduled_theme_now(start_str: str, end_str: str, now=None) -> str:
    """Schedule verdict for a wall-clock moment (default: right now)."""
    now = now or datetime.now()
    return scheduled_theme(now.hour * 60 + now.minute,
                           _minutes(coerce_hhmm(start_str, "20:00")),
                           _minutes(coerce_hhmm(end_str, "07:00")))


class ThemeScheduler:
    """Owns the poll timer; the app creates one and calls start().

    Always running; _tick is a no-op outside auto mode, so switching modes
    needs no start/stop choreography (same shape as ReminderScheduler)."""

    def __init__(self, app):
        self._app = app
        self._last_verdict = None       # schedule verdict seen on previous tick
        self._now = datetime.now        # injectable for tests
        self._timer = QTimer(app)
        self._timer.setInterval(_TICK_MS)
        self._timer.timeout.connect(self._tick)

    def start(self):
        self._timer.start()

    def _tick(self):
        app = self._app
        if getattr(app, "_theme_mode", "light") != "auto":
            self._last_verdict = None   # forget stale state across mode hops
            return
        verdict = scheduled_theme_now(app._theme_dark_start,
                                      app._theme_dark_end, now=self._now())
        if self._last_verdict is not None and verdict != self._last_verdict:
            app._theme_override = None  # boundary crossed -> override expires
        self._last_verdict = verdict
        desired = app._theme_override or verdict
        if desired != app._theme:
            app._apply_effective_theme(desired)
