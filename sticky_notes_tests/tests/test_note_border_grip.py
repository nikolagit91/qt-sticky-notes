"""Two paintEvent fixes:

1) The outer border must be drawn whether or not the chrome is shown. It relied
   on the pen set while drawing the header separator (`if hh > 0`), so once the
   header collapsed (clean mode, hh==0) the border rect was stroked with NoPen —
   no border at all. Checked on rendered pixels via grab().

2) The resize-grip indicator followed `base.darker(180)` unconditionally, so on a
   dark note it went darker-than-dark and vanished. It now comes from the
   auto-contrast ink (lighter on dark notes, darker on light), like the border.
"""
import sys, os, tempfile, atexit, shutil
_SB = tempfile.mkdtemp(prefix="sn_bordergrip_")
atexit.register(lambda: shutil.rmtree(_SB, ignore_errors=True))
os.environ["HOME"] = _SB
os.environ["XDG_CONFIG_HOME"] = os.path.join(_SB, ".config")
os.environ["XDG_DATA_HOME"]   = os.path.join(_SB, ".local", "share")
os.environ.setdefault("XDG_RUNTIME_DIR", _SB)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ.pop("DISPLAY", None); os.environ.pop("WAYLAND_DISPLAY", None)
os.makedirs(os.path.join(_SB, ".local", "share", "sticky_notes"), exist_ok=True)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

fails = []
def check(name, cond):
    print(f"  {'PASS' if cond else 'FAIL'}   {name}")
    if not cond: fails.append(name)

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QColor
from sticky_notes.theme import note_ink, _rel_luminance
from sticky_notes.app import StickyNotesApp

app = StickyNotesApp(sys.argv[:1])
app._clean_mode = False
for e in list(app.notes.values()):
    e.hide(); e.deleteLater()
app.notes.clear()

# ── 1) no outer border — the note reads as a borderless card ─────────────────
# The 1px border was removed for a sleeker look (user's call). The left edge
# should now be the fill, not a distinct border line, in every chrome state.
n = app.create_new_note(content="hi")
n.resize(300, 220); n.show(); app.processEvents()

def left_edge_matches_body():
    """No border → the very left-edge pixel (where the 1px stroke used to sit, at
    x≈0) is the same fill as just inside it. At mid-height the edge is a straight
    line, not a rounded corner, so the body fill reaches x=0."""
    img = n.grab().toImage()
    y = img.height() // 2
    edge = img.pixelColor(0, y)
    body = img.pixelColor(8, y)
    return edge.name() == body.name() and edge.alpha() == body.alpha()

check("no border with the chrome visible", left_edge_matches_body())

n._set_clean_mode(True); app.processEvents()
n._hide_chrome(); n._on_header_anim_finished(); n._on_toolbar_anim_finished()
app.processEvents()
check("no border with the chrome hidden (clean mode)", left_edge_matches_body())

# The body fill + rounded corners stay — only the stroke is gone. A pixel outside
# the rounded corner must be transparent (the corner isn't squared off).
img = n.grab().toImage()
corner = img.pixelColor(0, 0)
check("rounded corner is still cut out (top-left pixel transparent)",
      corner.alpha() == 0)
check("body fill is intact", img.pixelColor(150, 110).name() == "#fff59d")

# ── 2) grip follows auto-contrast ────────────────────────────────────────────
dark  = QColor("#2b2b30")
light = QColor("#fff59d")
grip_dark  = QColor(note_ink(dark,  auto=True).grip)
grip_light = QColor(note_ink(light, auto=True).grip)
check("Ink exposes a grip colour", note_ink(light, auto=True).grip is not None)
check("grip is LIGHTER than a dark note's fill (so it's visible)",
      _rel_luminance(grip_dark) > _rel_luminance(dark))
check("grip is DARKER than a light note's fill (classic look kept)",
      _rel_luminance(grip_light) < _rel_luminance(light))
# It must be a clear step, not a hair — the old darker(180) on dark was invisible.
check("grip on a dark note is a clear step lighter",
      _rel_luminance(grip_dark) - _rel_luminance(dark) > 0.02)

# Pure black is the killer case: QColor.lighter() scales the HSV value, so
# lighter(black) stays black. The grip must blend toward white instead, so even
# a #000000 note shows its grip.
black = QColor("#000000")
grip_black = QColor(note_ink(black, auto=True).grip)
check("grip is visible on a pure-black note (lighter() would stay black)",
      _rel_luminance(grip_black) > 0.03)
check("near-black notes get a visible grip too",
      _rel_luminance(QColor(note_ink(QColor("#111111"), auto=True).grip)) > 0.03)

# auto-contrast OFF keeps the classic dark grip (consistent with ink staying dark)
check("auto-off keeps the darker grip even on a dark note",
      _rel_luminance(QColor(note_ink(dark, auto=False).grip)) < _rel_luminance(dark))

# the note caches the grip colour for paintEvent
check("note stores an ink-aware grip colour", getattr(n, "_qcolor_grip", None) is not None)

print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
