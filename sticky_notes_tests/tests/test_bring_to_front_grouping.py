"""§62: _bring_to_front is now show + raise + activate — NO always-on-top flag
toggle, so it never recreates the native window. Recreation was what re-attached
notes to Qt's shared X11 group (undoing showEvent's detach) and let pinning one
note lift them all / left a pinned-then-unpinned note unable to reappear.

Verify: raise_/activateWindow are called, the note's window flags are NOT changed
(no toggle), a pinned note keeps its always-on-top flag, and the helper-detach /
anti-lift experiments are gone.
"""
import sys, os, tempfile, atexit, shutil, time

_SB = tempfile.mkdtemp(prefix="sn_bf_")
atexit.register(lambda: shutil.rmtree(_SB, ignore_errors=True))
os.environ["HOME"] = _SB
os.environ["XDG_CONFIG_HOME"] = os.path.join(_SB, ".config")
os.environ["XDG_DATA_HOME"]   = os.path.join(_SB, ".local", "share")
os.environ.setdefault("XDG_RUNTIME_DIR", _SB)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ.pop("DISPLAY", None); os.environ.pop("WAYLAND_DISPLAY", None)
os.makedirs(os.path.join(_SB, ".local", "share", "sticky_notes"), exist_ok=True)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QApplication, QMessageBox, QWidget
from PyQt6.QtCore import Qt
QMessageBox.information = staticmethod(lambda *a, **k: None)
TOP = Qt.WindowType.WindowStaysOnTopHint

fails = []
def check(name, cond):
    print(f"  {'PASS' if cond else 'FAIL'}   {name}")
    if not cond: fails.append(name)

from sticky_notes.app import StickyNotesApp
from sticky_notes.note import StickyNote
app = StickyNotesApp(sys.argv[:1])
app._snap_to_grid = app._snap_to_notes = app._snap_size = False

def flags_of(w):
    h = w.windowHandle()
    return h.flags() if h is not None else Qt.WindowType(0)

# ── helper window: raise + activate ─────────────────────────────────────────
w = QWidget(); w.show(); QApplication.processEvents()
seen = {"r": 0, "a": 0}
w.raise_ = lambda: seen.__setitem__("r", seen["r"] + 1)
w.activateWindow = lambda: seen.__setitem__("a", seen["a"] + 1)
app._bring_to_front(w)
check("helper: raise_ called", seen["r"] == 1)
check("helper: activateWindow called", seen["a"] == 1)
w.deleteLater()

# ── unpinned note: raise + activate, flags UNCHANGED (no toggle/recreation) ──
note = StickyNote(app, "bf", {"id": "bf", "geometry": [100, 100, 300, 200]})
app.notes["bf"] = note; note.show(); QApplication.processEvents()
before = flags_of(note)
seen = {"r": 0, "a": 0}
note.raise_ = lambda: seen.__setitem__("r", seen["r"] + 1)
note.activateWindow = lambda: seen.__setitem__("a", seen["a"] + 1)
app._bring_to_front(note)
QApplication.processEvents()
check("note: raise_ called", seen["r"] == 1)
check("note: activateWindow called", seen["a"] == 1)
check("note: window flags unchanged (no always-on-top toggle)", flags_of(note) == before)
check("note: not given always-on-top", not (flags_of(note) & TOP))
note.hide(); note.deleteLater()

# ── pinned note: pin is EWMH ABOVE, not a Qt flag; _bring_to_front doesn't add one ──
pnote = StickyNote(app, "pf", {"id": "pf", "geometry": [50, 50, 300, 200], "pinned": True})
app.notes["pf"] = pnote; pnote.show(); QApplication.processEvents()
before = flags_of(pnote)
check("pinned note: no Qt always-on-top flag (uses EWMH ABOVE)", not (before & TOP))
app._bring_to_front(pnote)
QApplication.processEvents()
check("pinned note: _bring_to_front leaves flags unchanged", flags_of(pnote) == before)
pnote.hide(); pnote.deleteLater()

# ── structural: obsolete experiments removed ────────────────────────────────
check("no _detach_from_group (helper-detach removed)", not hasattr(app, "_detach_from_group"))
check("no _detach_all_notes (anti-lift removed)", not hasattr(app, "_detach_all_notes"))
check("no _reraise_visible_notes (delete no longer re-raises)",
      not hasattr(app, "_reraise_visible_notes"))

print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
