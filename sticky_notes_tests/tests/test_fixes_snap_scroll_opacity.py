"""Isolated scenario test for two of the §55 fixes:
  1. snap_to_edges pure geometry + the _apply_snap top-panel bounce fix
  2. background opacity → alpha on painted colours (text unaffected)

Headless + sandboxed, same as golden_suite. Run ISOLATED (one process).
"""
import sys, os, tempfile, atexit, shutil

_SB = tempfile.mkdtemp(prefix="sn_fix_")
atexit.register(lambda: shutil.rmtree(_SB, ignore_errors=True))
os.environ["HOME"] = _SB
os.environ["XDG_CONFIG_HOME"] = os.path.join(_SB, ".config")
os.environ["XDG_DATA_HOME"]   = os.path.join(_SB, ".local", "share")
os.environ.setdefault("XDG_RUNTIME_DIR", _SB)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ.pop("DISPLAY", None)
os.environ.pop("WAYLAND_DISPLAY", None)
os.makedirs(os.path.join(_SB, ".local", "share", "sticky_notes"), exist_ok=True)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import QRect
QMessageBox.information = staticmethod(lambda *a, **k: None)

fails = []
def check(name, cond):
    print(f"  {'PASS' if cond else 'FAIL'}   {name}")
    if not cond:
        fails.append(name)


# ── 1a. snap_to_edges (pure) ────────────────────────────────────────────────
from sticky_notes import snap as S
# work area: panel reserves top 32px on a 1920x1080 display
sx, sy, sw, sh = 0, 32, 1920, 1048
# note flush at panel edge → top grabs, x already at left edge
nx, ny, xh, yh = S.snap_to_edges(0, 32, 260, 200, sx, sy, sw, sh)
check("edge: top+left grab", (nx, ny, xh, yh) == (0, 32, True, True))
# note near top (y=36, 4px from panel) → grabs 32
_, ny2, _, yh2 = S.snap_to_edges(100, 36, 260, 200, sx, sy, sw, sh)
check("edge: near-top (4px) grabs panel", ny2 == 32 and yh2)
# bottom edge: note bottom 5px shy of work-area bottom (1080) → grabs
_, nyb, _, yhb = S.snap_to_edges(500, 900, 260, 175, sx, sy, sw, sh)
check("edge: bottom grab", nyb == (32 + 1048 - 175) and yhb)
# far from any edge → no hit
_, _, xh0, yh0 = S.snap_to_edges(600, 400, 260, 200, sx, sy, sw, sh)
check("edge: middle → no snap", (xh0, yh0) == (False, False))
# right edge: note right edge within threshold of screen right
nxr, _, xhr, _ = S.snap_to_edges(1920 - 260 - 6, 400, 260, 200, sx, sy, sw, sh)
check("edge: right grab", nxr == (1920 - 260) and xhr)


# ── build the real app once (offscreen) ─────────────────────────────────────
from sticky_notes.app import StickyNotesApp
from sticky_notes.note import StickyNote
app = StickyNotesApp(sys.argv[:1])

class _FakeScreen:
    def __init__(self, rect): self._r = rect
    def availableGeometry(self): return self._r

def _note(data=None):
    n = StickyNote(app, (data or {}).get("id", "t"), data or {})
    return n


# ── 1b. _apply_snap: no bounce off the top panel ────────────────────────────
app._snap_to_grid, app._snap_to_notes, app._snap_size = True, False, False
app._grid_size = 20
panel = _FakeScreen(QRect(0, 32, 1920, 1048))   # top panel = 32 (NOT grid-aligned)

n = _note({"id": "snap1", "geometry": [100, 32, 260, 200]})
n.screen = lambda: panel            # note sits flush at panel edge (y=32)
n._apply_snap()
check("apply_snap: stays at panel edge, no bounce to 40",
      n.geometry().y() == 32)       # pre-fix: grid rounds 32→40, pushes DOWN

# grid still works away from edges (107,205 → 100,200)
n2 = _note({"id": "snap2", "geometry": [107, 205, 260, 200]})
n2.screen = lambda: panel
n2._apply_snap()
check("apply_snap: grid still snaps mid-screen (100,200)",
      (n2.geometry().x(), n2.geometry().y()) == (100, 200))

# note nudged ABOVE the panel → grid would send it to 0 (under panel); clamp
# must pull it back onto the work area (32), never off-screen
n3 = _note({"id": "snap3", "geometry": [300, 10, 260, 200]})
n3.screen = lambda: panel
n3._apply_snap()
check("apply_snap: clamp keeps note on work area (y>=32)",
      n3.geometry().y() >= 32)

for x in (n, n2, n3):
    x.hide(); x.deleteLater()


# ── 2. background opacity → alpha on paper, text untouched ───────────────────
app._note_opacity = 60
nn = _note({"id": "op", "color": "#fff59d", "geometry": [10, 10, 260, 200]})
nn._apply_color()
a = round(60 * 255 / 100)   # 153
check("opacity: base alpha matches %", nn._qcolor_base.alpha() == a)
check("opacity: header inherits alpha", nn._qcolor_header.alpha() == a)
check("opacity: border inherits alpha", nn._qcolor_border.alpha() == a)
check("opacity: RGB of base is the note colour",
      (nn._qcolor_base.red(), nn._qcolor_base.green(), nn._qcolor_base.blue())
      == (255, 245, 157))
# text edit stylesheet colour is independent of opacity (stays #333 opaque)
check("opacity: text colour unaffected", "color: #333" in nn.text_edit.styleSheet())

# 100% → fully opaque
app._note_opacity = 100
nn._apply_color()
check("opacity: 100% → alpha 255 (opaque)", nn._qcolor_base.alpha() == 255)

# live app-wide apply updates an existing note (real notes live in app.notes,
# populated by create_new_note; register directly since we built it by hand)
app.notes[nn.note_id] = nn
app._note_opacity = 75
app._apply_note_opacity()
check("opacity: _apply_note_opacity updates live", nn._qcolor_base.alpha() == round(75 * 255 / 100))
nn.hide(); nn.deleteLater()


print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
