#!/usr/bin/env python3
"""
Sticky Notes — Lightweight sticky notes app for Ubuntu
Built with Python & PyQt6

Entry point. Sets required environment variables BEFORE any Qt import, then
launches the application.
"""

import os
import json

# ── MUST be set before any Qt import ──────────────────────────────────────────
os.environ["QT_QPA_PLATFORM"] = "xcb"   # XWayland: allows window positioning

# Qt loads the GTK3 platform theme on GNOME when QApplication is constructed,
# which initializes GTK's AT-SPI accessibility bridge; on a session without the
# a11y daemon that prints a noisy "Couldn't connect to accessibility bus"
# warning to stderr. We don't use accessibility — disable the bridge here,
# before ANY Qt import, so it never initializes. (setdefault respects an
# explicit user override.)
os.environ.setdefault("NO_AT_BRIDGE", "1")

# The GNOME session often exports GTK_MODULES=gail:atk-bridge — legacy ATK
# accessibility modules. Modern GTK provides that functionality natively and
# prints a "Not loading module 'atk-bridge' … please try to not load it" notice
# to stderr when it sees them (GTK is loaded in-process via Qt's gtk3 platform
# theme and the AppIndicator tray menu). Drop those obsolete entries from OUR
# process's env only — this is exactly what GTK asks for, silences the notice,
# and doesn't touch the session or our accessibility (GTK handles it natively).
_gtk_mods = [m for m in os.environ.get("GTK_MODULES", "").split(":")
             if m and m not in ("atk-bridge", "gail")]
if _gtk_mods:
    os.environ["GTK_MODULES"] = ":".join(_gtk_mods)
else:
    os.environ.pop("GTK_MODULES", None)

# Apply the saved UI scale through Qt's OWN high-DPI scaling. Qt re-renders text
# and (vector) SVG icons at the target size — crisp at any factor — instead of
# letting GNOME bitmap-stretch the finished output (which is blurry). The factor
# is only read when QApplication is first constructed, so it must be set here,
# before any Qt import, from the value saved in settings.
def _saved_ui_scale() -> str:
    try:
        from sticky_notes.config import SETTINGS_FILE
        with open(SETTINGS_FILE, encoding="utf-8") as fh:
            scale = float(json.load(fh).get("ui_scale", 1.0))
        return str(max(1.0, min(2.0, scale)))   # clamp to the Settings slider range (100%–200%)
    except Exception:
        return "1"

os.environ["QT_SCALE_FACTOR"] = _saved_ui_scale()

import sys
from sticky_notes.app import StickyNotesApp


def main():
    app = StickyNotesApp(sys.argv)
    # A secondary instance has already forwarded its intent (e.g. --new-note) to
    # the running app inside __init__; just exit without starting an event loop.
    if getattr(app, "_is_secondary", False):
        return 0
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
