"""Application configuration: data paths and version constants."""

import os

# ── Data storage ──────────────────────────────────────────────────────────────
DATA_DIR      = os.path.expanduser("~/.local/share/sticky_notes")
DATA_FILE     = os.path.join(DATA_DIR, "notes.json")
TRASH_FILE    = os.path.join(DATA_DIR, "closed.json")
ARCHIVE_FILE  = os.path.join(DATA_DIR, "archived.json")
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")
os.makedirs(DATA_DIR, exist_ok=True)

# ── Capacity limits ───────────────────────────────────────────────────────────
# Active/Archive are HARD stops (refuse past the cap so nothing is silently
# lost). Trash is FIFO — the oldest trashed note is evicted past the cap, since
# it's already on its way out.
ACTIVE_LIMIT  = 50
ARCHIVE_LIMIT = 50
TRASH_LIMIT   = 50

APP_VERSION = "1.0"

# ── Donations ─────────────────────────────────────────────────────────────────
# Shown as the "Buy me a coffee" button in the About dialog.
DONATE_URL = "https://ko-fi.com/G2A425K6GE"

# ── Source repository ─────────────────────────────────────────────────────────
# Shown as the "View on GitHub" link in the About dialog.
GITHUB_URL = "https://github.com/nikolagit91/qt-sticky-notes"

# ── Single-instance / IPC (D-Bus session bus) ─────────────────────────────────
# The first instance owns this well-known name and exports a small object that
# later invocations (e.g. the global "new note" hotkey) call into. D-Bus names
# allow only [A-Za-z0-9_] separated by dots — no hyphens — so they intentionally
# differ from the "sticky-notes" applicationName / desktop id.
DBUS_SERVICE = "org.stickynotes.StickyNotes"
DBUS_PATH    = "/org/stickynotes/StickyNotes"
