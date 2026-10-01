"""Dragging a note with the mouse must snap on release.

Bug: the header used QWindow.startSystemMove() (WM-driven drag). On the user's
Mutter the final moveEvent didn't reliably fire on drop, so the _snap_timer that
triggers _apply_snap never started for a mouse drag (resize + arrow keys, which
use other triggers, snapped fine). The header now drags the note itself so a
mouseReleaseEvent is guaranteed, where we snap.

Headless: we drive the header's mouse handlers with fake events and assert the
note moves during the drag and _apply_snap runs on release.
"""
import sys, os, tempfile, atexit, shutil

_SB = tempfile.mkdtemp(prefix="sn_drag_")
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
from PyQt6.QtCore import Qt, QPointF
QMessageBox.information = staticmethod(lambda *a, **k: None)

fails = []
def check(name, cond):
    print(f"  {'PASS' if cond else 'FAIL'}   {name}")
    if not cond: fails.append(name)

from sticky_notes.app import StickyNotesApp
from sticky_notes.note import StickyNote
app = StickyNotesApp(sys.argv[:1])
app._snap_to_grid = True          # grid snapping on
app._snap_to_notes = False
app._snap_size = False
app._grid_size = 20

n = StickyNote(app, "z", {"id": "z", "geometry": [100, 100, 300, 200]})
n.show()
hdr = n.header

class FakeEvt:
    def __init__(self, gx, gy, btn=Qt.MouseButton.LeftButton):
        self._p = QPointF(gx, gy); self._b = btn
    def globalPosition(self): return self._p
    def button(self): return self._b

snapped = []
n._apply_snap = lambda: snapped.append(n.pos())

# ── a slow, small drag to the right ─────────────────────────────────────────
hdr.mousePressEvent(FakeEvt(150, 120))      # press over the header
check("press starts a drag", hdr._dragging is True)
hdr.mouseMoveEvent(FakeEvt(157, 120))       # move +7px right (small/slow)
check("drag moves the note (+7 x)", n.pos().x() == 107)   # 100 origin + 7
hdr.mouseReleaseEvent(FakeEvt(157, 120))    # release
check("release ends the drag", hdr._dragging is False)
check("release triggers _apply_snap (snap on drop)", len(snapped) == 1)

# ── a locked note does not drag ─────────────────────────────────────────────
n.locked = True
hdr._dragging = False
hdr.mousePressEvent(FakeEvt(150, 120))
check("locked note: press does NOT start a drag", hdr._dragging is False)

print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
