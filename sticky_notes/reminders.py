"""In-process reminder scheduling — fires desktop notifications for notes whose
reminder time has arrived, for as long as the app is running.

A single timer polls every ``_TICK_MS`` and fires any due reminders. This is
deliberately a poll rather than one long timer per note: a per-note QTimer would
overflow past ~24 days and would not survive system suspend, whereas a poll
naturally catches up after a wake or a wall-clock change. Reminders that came due
while the app was closed are fired once shortly after startup.

Reminders only fire while the app is running (by design — see the handoff). When
one fires we surface the note and post a notification with a "Snooze" action;
even if the desktop has no notification daemon, the note is still brought to the
front so the reminder is never silently lost.
"""

import time
import shutil
import subprocess

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication

from .notify import Notifier
from .i18n import tr

_TICK_MS        = 15_000        # poll cadence (fire within ~15s of the due time)
_SNOOZE_SECONDS = 10 * 60       # "Snooze" pushes the reminder 10 minutes out
_STARTUP_DELAY_MS = 2500        # let windows settle before firing missed ones


def _play_alarm_sound():
    """Best-effort short system alarm when a reminder fires. Tries the common
    Linux players/sounds in turn and silently gives up if none are present — a
    missing sound must never break the reminder itself. Non-blocking (Popen)."""
    players = [
        ["canberra-gtk-play", "-i", "alarm-clock-elapsed"],
        ["paplay", "/usr/share/sounds/freedesktop/stereo/alarm-clock-elapsed.oga"],
        ["paplay", "/usr/share/sounds/freedesktop/stereo/complete.oga"],
        ["aplay", "-q", "/usr/share/sounds/alsa/Front_Center.wav"],
    ]
    for cmd in players:
        if shutil.which(cmd[0]):
            try:
                subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return
            except Exception:
                continue


class ReminderScheduler:
    """Owns the poll timer and the notifier; the app creates one and calls
    :meth:`start`."""

    def __init__(self, app):
        self._app = app
        self._notifier = Notifier()
        self._timer = QTimer(app)
        self._timer.setInterval(_TICK_MS)
        self._timer.timeout.connect(self._tick)

    def start(self):
        self._timer.start()
        # Catch reminders that came due while the app was closed — slightly
        # delayed so note windows are up before we raise them.
        QTimer.singleShot(_STARTUP_DELAY_MS, self._tick)

    def _tick(self):
        now = time.time()
        for note in list(self._app.notes.values()):
            when = getattr(note, "_reminder", None)
            if when is not None and when <= now:
                self._fire(note)

    def _fire(self, note):
        # Consume the reminder so it can't re-fire on the next tick; "Snooze"
        # sets a fresh one.
        note.set_reminder(None)
        # Surface the note above everything (incl. an always-on-top app) without
        # flickering the whole note group; drops the forced on-top shortly after.
        try:
            note._surface_for_reminder()
            QApplication.alert(note, 0)   # dash/overview attention as a fallback
        except RuntimeError:
            pass
        _play_alarm_sound()   # short system alarm; best-effort, never fatal

        title = tr("Sticky Notes — Reminder")
        body  = note.reminder_preview()
        sent = self._notifier.send(
            title, body,
            actions=[("snooze", tr("Snooze 10 min"))],
            on_action=lambda key, n=note: self._on_action(n, key),
        )
        if sent is None:
            # No notification daemon — fall back to a tray balloon if we have one.
            tray = getattr(self._app, "tray", None)
            if tray is not None:
                try:
                    tray.showMessage(title, body, tray.icon(), 10_000)
                except Exception:
                    pass

    def _on_action(self, note, key):
        if key == "snooze":
            note.set_reminder(time.time() + _SNOOZE_SECONDS)
