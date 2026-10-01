"""Pin via EWMH _NET_WM_STATE_ABOVE (x11.set_above), NOT Qt's WindowStaysOnTopHint.
The Qt flag recreates the native window (flicker + drops skip-taskbar → dock dot);
the EWMH client message leaves the window intact. So a pinned note must:
  - carry NO Qt always-on-top flag,
  - call x11.set_above(win, True) on pin and (win, False) on unpin,
  - re-assert ABOVE on show (loaded-pinned note).
Headless: set_above/detach no-op or are spied; we assert the calls + absence of
the Qt flag.
"""
import sys, os, tempfile, atexit, shutil

_SB = tempfile.mkdtemp(prefix="sn_pin_")
atexit.register(lambda: shutil.rmtree(_SB, ignore_errors=True))
os.environ["HOME"] = _SB
os.environ["XDG_CONFIG_HOME"] = os.path.join(_SB, ".config")
os.environ["XDG_DATA_HOME"]   = os.path.join(_SB, ".local", "share")
os.environ.setdefault("XDG_RUNTIME_DIR", _SB)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ.pop("DISPLAY", None); os.environ.pop("WAYLAND_DISPLAY", None)
os.makedirs(os.path.join(_SB, ".local", "share", "sticky_notes"), exist_ok=True)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt
QMessageBox.information = staticmethod(lambda *a, **k: None)
TOP = Qt.WindowType.WindowStaysOnTopHint

fails = []
def check(name, cond):
    print(f"  {'PASS' if cond else 'FAIL'}   {name}")
    if not cond: fails.append(name)

from sticky_notes.app import StickyNotesApp
from sticky_notes.note import StickyNote
import sticky_notes.x11 as x11mod
app = StickyNotesApp(sys.argv[:1])
app._snap_to_grid = app._snap_to_notes = app._snap_size = False

x11mod.detach_window_group = lambda wid: True
above_calls = []                                   # (win_id, enable)
x11mod.set_above = lambda wid, enable: above_calls.append((wid, enable))

def flags_of(n):
    h = n.windowHandle()
    return h.flags() if h is not None else Qt.WindowType(0)

n = StickyNote(app, "n", {"id": "n", "geometry": [100, 100, 300, 200]})
app.notes["n"] = n
n.show(); QApplication.processEvents()
n_wid = int(n.winId())

check("unpinned note: no Qt always-on-top flag", not (flags_of(n) & TOP))

# ── pin: EWMH ADD ABOVE, still no Qt flag ───────────────────────────────────
above_calls.clear()
n._toggle_pin(); QApplication.processEvents()
check("pin: _pinned True", n._pinned is True)
check("pin: set_above(win, True) called", (n_wid, True) in above_calls)
check("pin: still NO Qt always-on-top flag (no recreation → no flicker)",
      not (flags_of(n) & TOP))

# ── unpin: EWMH REMOVE ABOVE ────────────────────────────────────────────────
above_calls.clear()
n._toggle_pin(); QApplication.processEvents()
check("unpin: _pinned False", n._pinned is False)
check("unpin: set_above(win, False) called", (n_wid, False) in above_calls)

# ── loaded-pinned note: re-asserts ABOVE on show, no Qt flag ─────────────────
above_calls.clear()
p = StickyNote(app, "p", {"id": "p", "geometry": [50, 50, 300, 200], "pinned": True})
app.notes["p"] = p; p.show(); QApplication.processEvents()
p_wid = int(p.winId())
check("loaded-pinned note: no Qt always-on-top flag", not (flags_of(p) & TOP))
check("loaded-pinned note: set_above(win, True) asserted on show",
      (p_wid, True) in above_calls)

for w in (n, p):
    w.hide(); w.deleteLater()
print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
